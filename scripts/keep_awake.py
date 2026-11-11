"""Visit the live Streamlit app in a headless browser so it doesn't go to sleep.

Streamlit Community Cloud puts apps to sleep after 12 hours without visitors. A real
browser visit counts as traffic; if the app is already asleep this clicks Streamlit's
"Yes, get this app back up!" button and waits for the app to load. Exits non-zero
when the app doesn't come up, so the scheduled GitHub Action fails and emails the owner.

    python scripts/keep_awake.py [URL]
"""
import os
import sys

from playwright.sync_api import sync_playwright

URL = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("APP_URL")) or "https://reapers-stats.streamlit.app/"
WAKE_TEXT = "get this app back up"
READY_TEXT = "Dashboard"  # in the app's sidebar navigation
WAKE_TIMEOUT_MS = 5 * 60 * 1000  # a cold start can take a few minutes


def app_ready(page, timeout_ms):
    """True once the app's own content shows, whether it's in Community Cloud's iframe or served directly."""
    waited = 0
    while waited < timeout_ms:
        for frame in page.frames:  # the main page and any iframes
            try:
                if frame.get_by_text(READY_TEXT).count():
                    return True
            except Exception:
                pass  # frame navigated away mid-check
        page.wait_for_timeout(2000)
        waited += 2000
    return False


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        print(f"Visiting {URL}")
        page.goto(URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(5000)

        wake = page.get_by_role("button", name=WAKE_TEXT)
        if wake.count():
            print("App was asleep: clicking the wake-up button")
            wake.first.click()
            ok = app_ready(page, WAKE_TIMEOUT_MS)
        else:
            ok = app_ready(page, 120_000)

        if ok:
            print("App is up")
        else:
            page.screenshot(path="keep-awake-failure.png", full_page=True)
            print("App did not load; see the keep-awake-failure screenshot artifact")
        browser.close()
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
