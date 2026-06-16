
import json
import re
from datetime import date
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from streamlit_sortables import sort_items

# ── Paths & constants ─────────────────────────────────────────────────────────

DATA_DIR    = Path(__file__).parent / "data"
CONFIG_FILE = DATA_DIR / "config.json"
PHOTO_FILE  = Path(__file__).parent / "assets" / "team_photo.jpg"

_LEG_ROSTER = DATA_DIR / "roster.json"
_LEG_GAMES  = DATA_DIR / "games.json"

def _roster_file(tid: str) -> Path:
    return DATA_DIR / f"{tid}_roster.json"

def _games_file(tid: str) -> Path:
    return DATA_DIR / f"{tid}_games.json"

OUTCOME_DISPLAY = {
    "1B":     "Single (1B)",
    "2B":     "Double (2B)",
    "3B":     "Triple (3B)",
    "HR_OTF": "Home Run – Over the Fence",
    "HR_ITP": "Home Run – Inside the Park",
    "BB":     "Walk (BB)",
    "K":      "Strikeout (K)",
    "OUT":    "Out",
    "FC":     "Fielder's Choice",
    "E":      "Reached on Error",
    "DP":     "Double Play (2 outs)",
    "SF":     "Sacrifice Fly",
    "TP":     "Triple Play (3 outs)",
}
HIT_CODES = {"1B", "2B", "3B", "HR_OTF", "HR_ITP"}
OUT_WEIGHTS = {"OUT": 1, "K": 1, "DP": 2, "TP": 3}  # outs recorded per outcome
OUTCOME_BASES = {
    "1B": 1, "2B": 2, "3B": 3, "HR_OTF": 4, "HR_ITP": 4,
    "BB": 1, "E": 1, "FC": 1,
    "SF": 0, "OUT": 0, "K": 0, "DP": 0, "TP": 0,
}

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Reapers Stats", page_icon="💀", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
<style>
.hero {
  padding: 28px 32px; border-radius: 16px;
  background: linear-gradient(135deg, #0a0a0a 0%, #1f0015 45%, #420028 100%);
  color: #fff; margin-bottom: 8px;
  box-shadow: 0 4px 32px rgba(255,20,147,0.25); text-align: center;
}
.hero h1 { font-size: 44px; margin: 0; font-weight: 800; letter-spacing: -1px; }
.hero .sub { opacity: 0.8; font-size: 15px; margin-top: 8px; }
.hero .badges { margin-top: 14px; display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; }
.badge {
  display: inline-block; padding: 5px 14px;
  background: rgba(255,20,147,0.18); color: #ff69b4;
  border: 1px solid rgba(255,20,147,0.45);
  border-radius: 999px; font-weight: 700; font-size: 13px;
}
.badge.green { background: rgba(80,200,120,0.18); color: #8ee8a8; border-color: rgba(80,200,120,0.4); }
.badge.red   { background: rgba(220,80,80,0.18);  color: #ff8a8a; border-color: rgba(220,80,80,0.4); }

.kpi-grid {
  display: grid; grid-template-columns: repeat(5, 1fr);
  gap: 10px; margin: 8px 0 20px 0;
}
.kpi-card {
  border: 1px solid rgba(255,20,147,0.22); border-radius: 10px;
  padding: 14px 16px; background: rgba(255,20,147,0.05);
}
.kpi-card .label { font-size: 11px; opacity: 0.65; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 700; }
.kpi-card .value { font-size: 26px; font-weight: 800; margin-top: 4px; line-height: 1.1; }
.kpi-card .hint  { font-size: 11px; opacity: 0.55; margin-top: 4px; }

.leader-card {
  border: 1px solid rgba(255,20,147,0.22); border-radius: 12px;
  padding: 16px 18px; background: rgba(255,20,147,0.04); height: 100%;
}
.leader-card h4 { margin: 0 0 12px 0; font-size: 12px; letter-spacing: 1px; text-transform: uppercase; opacity: 0.65; font-weight: 700; }
.leader-row { display: flex; justify-content: space-between; align-items: baseline; padding: 5px 0; font-size: 15px; }
.leader-row .rank { display: inline-block; width: 22px; text-align: center; font-weight: 800; margin-right: 8px; }
.leader-row.r1 .rank { color: #FF1493; }
.leader-row.r2 .rank { color: #ff69b4; }
.leader-row.r3 .rank { color: #ffaad4; }
.leader-row .name { flex: 1; font-weight: 500; }
.leader-row .val  { font-family: ui-monospace, "SF Mono", Consolas, monospace; opacity: 0.95; font-weight: 600; }

.recap {
  border-left: 4px solid #FF1493; background: rgba(255,20,147,0.07);
  padding: 14px 18px; border-radius: 6px; margin: 8px 0 20px 0;
}
.recap .title { font-size: 13px; opacity: 0.7; text-transform: uppercase; letter-spacing: 1px; }
.recap .score { font-size: 22px; font-weight: 800; margin: 4px 0; }

.stats-table-wrap {
  max-width: 1100px; margin: 8px auto; overflow-x: auto;
  border: 1px solid rgba(255,20,147,0.2); border-radius: 10px; background: #0a0a0a;
}
.stats-table { border-collapse: separate; border-spacing: 0; width: 100%; font-size: 14px; color: #fafafa; }
.stats-table th, .stats-table td {
  padding: 10px 14px; text-align: center;
  border-bottom: 1px solid rgba(255,20,147,0.08); white-space: nowrap;
}
.stats-table tbody tr:last-child td { border-bottom: none; }
.stats-table th {
  font-weight: 700; font-size: 11px; letter-spacing: 0.6px; text-transform: uppercase;
  opacity: 0.75; background: #14000d; position: sticky; top: 0; z-index: 1;
}
.stats-table td.player-cell {
  text-align: left; font-weight: 600; position: sticky; left: 0;
  background: #0a0a0a; z-index: 2; border-right: 1px solid rgba(255,20,147,0.18);
}
.stats-table th.player-th {
  text-align: left; position: sticky; left: 0; top: 0;
  background: #14000d; z-index: 3; border-right: 1px solid rgba(255,20,147,0.18);
}

.cmp-wrap { max-width: 720px; margin: 0 auto; }
.cmp-header {
  display: grid; grid-template-columns: 1fr 100px 1fr; align-items: center;
  padding: 18px 0; border-bottom: 2px solid rgba(255,20,147,0.3); margin-bottom: 6px;
}
.cmp-name { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }
.cmp-name.left  { text-align: right; padding-right: 12px; }
.cmp-name.right { text-align: left;  padding-left:  12px; }
.cmp-header .vs { text-align: center; font-size: 13px; font-weight: 700; opacity: 0.5; text-transform: uppercase; letter-spacing: 2px; }
.cmp-row {
  display: grid; grid-template-columns: 1fr 140px 1fr; align-items: center;
  padding: 11px 0; border-bottom: 1px solid rgba(255,20,147,0.08);
}
.cmp-row:last-child { border-bottom: none; }
.cmp-val { font-family: ui-monospace, "SF Mono", Consolas, monospace; font-size: 18px; font-weight: 500; opacity: 0.55; }
.cmp-val.left  { text-align: right; padding-right: 14px; }
.cmp-val.right { text-align: left;  padding-left:  14px; }
.cmp-val.winner { color: #FF1493; font-weight: 800; opacity: 1; }
.cmp-val.tie    { opacity: 0.85; }
.cmp-stat { text-align: center; font-size: 11px; font-weight: 600; opacity: 0.7; text-transform: uppercase; letter-spacing: 1px; }
.cmp-tally {
  text-align: center; margin-top: 16px; padding-top: 14px;
  border-top: 2px solid rgba(255,20,147,0.3); font-size: 14px; opacity: 0.9;
}

.hr-row {
  display: flex; align-items: center; padding: 10px 4px;
  border-bottom: 1px solid rgba(255,20,147,0.1);
}
.hr-row:last-child { border-bottom: none; }
.hr-name    { flex: 0 0 140px; font-weight: 600; font-size: 15px; }
.hr-markers { flex: 1; }
.hr-count   { opacity: 0.7; font-size: 13px; font-family: ui-monospace, "SF Mono", Consolas, monospace; }
.hr-dot {
  display: inline-block; width: 16px; height: 16px;
  border-radius: 50%; margin-right: 4px; vertical-align: middle;
}
.hr-otf { background: #FF1493; box-shadow: 0 0 6px rgba(255,20,147,0.6); }
.hr-itp { background: transparent; border: 2px solid #FF1493; }

/* ── Mobile ─────────────────────────────────────────────────────────────────── */
@media (max-width: 640px) {
  .hero h1          { font-size: 26px !important; }
  .hero .sub        { font-size: 12px !important; }
  .kpi-grid         { grid-template-columns: repeat(2, 1fr) !important; }
  .kpi-card .value  { font-size: 20px !important; }
  .cmp-name         { font-size: 17px !important; }
  .cmp-val          { font-size: 13px !important; }
  .cmp-stat         { font-size: 9px !important; letter-spacing: 0.3px !important; }
  .cmp-header       { grid-template-columns: 1fr 56px 1fr !important; }
  .cmp-row          { grid-template-columns: 1fr 90px 1fr !important; }
  .hr-name          { flex: 0 0 90px !important; font-size: 12px !important; }
  .leader-card      { padding: 10px 12px !important; }
  .leader-row       { font-size: 13px !important; }
}

/* Scoresheet touch targets */
div[data-testid='stHorizontalBlock'] div[data-testid='stButton'] button
{ padding:3px 2px; font-size:12px; font-weight:700; min-height:34px; line-height:1.1 }

@media (max-width: 640px) {
  div[data-testid='stHorizontalBlock'] div[data-testid='stButton'] button
  { min-height: 44px !important; font-size: 10px !important; padding: 2px 1px !important; }
}

/* ── Scoresheet cell colors by outcome ─────────────────────────────────────── */
/* Hits — green */
button[aria-label^="1B"],button[aria-label^="2B"],button[aria-label^="3B"],
button[aria-label^="HR"],button[aria-label^="ITP"]
{ background-color:rgba(50,205,80,0.10)!important;
  border-color:rgba(50,205,80,0.35)!important; color:#8ee89a!important }
/* Outs — red */
button[aria-label^="OUT"],button[aria-label^="K"],
button[aria-label^="DP"],button[aria-label^="TP"]
{ background-color:rgba(220,60,60,0.20)!important;
  border-color:rgba(220,60,60,0.60)!important; color:#f09898!important }
/* Walks / reach — blue */
button[aria-label^="BB"],button[aria-label^="E"],
button[aria-label^="FC"],button[aria-label^="SF"]
{ background-color:rgba(60,140,220,0.10)!important;
  border-color:rgba(60,140,220,0.30)!important; color:#88bbf0!important }
/* Run scored — green chip */
button[aria-label$=' RS']
{ background-color:rgba(50,205,80,0.22)!important;
  border-color:rgba(50,205,80,0.55)!important; color:#b0f5b0!important }

/* ── At-bat dialog outcome grid ─────────────────────────────────────────────── */
[role="dialog"] div[data-testid="stButton"] button {
  min-height: 58px !important;
  font-size: 15px !important;
  font-weight: 800 !important;
  border-radius: 12px !important;
  padding: 6px 4px !important;
  letter-spacing: 0.3px !important;
}
/* Category accent colors in dialog (unselected) */
[role="dialog"] button[aria-label="1B"],
[role="dialog"] button[aria-label="2B"],
[role="dialog"] button[aria-label="3B"],
[role="dialog"] button[aria-label="HR"],
[role="dialog"] button[aria-label="ITP"]
{ border-color:rgba(50,205,80,0.55)!important; color:#7ee89a!important }
[role="dialog"] button[aria-label="OUT"],
[role="dialog"] button[aria-label="K"],
[role="dialog"] button[aria-label="DP"],
[role="dialog"] button[aria-label="TP"]
{ border-color:rgba(220,60,60,0.55)!important; color:#f09898!important }
[role="dialog"] button[aria-label="BB"],
[role="dialog"] button[aria-label="E"],
[role="dialog"] button[aria-label="FC"],
[role="dialog"] button[aria-label="SF"]
{ border-color:rgba(60,140,220,0.55)!important; color:#88bbf0!important }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ── I/O ───────────────────────────────────────────────────────────────────────

def _load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default

def _github_sync(path: Path, content: str) -> None:
    try:
        token  = st.secrets.get("github_token", "")
        repo   = st.secrets.get("github_repo", "")
        branch = st.secrets.get("github_branch", "main")
        if not token or not repo:
            return
        import base64, requests as _req
        rel = path.relative_to(Path(__file__).parent).as_posix()
        url = f"https://api.github.com/repos/{repo}/contents/{rel}"
        hdrs = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
        r = _req.get(url, headers=hdrs, timeout=8)
        sha = r.json().get("sha") if r.status_code == 200 else None
        body = {"message": f"data: {rel}", "content": base64.b64encode(content.encode()).decode(), "branch": branch}
        if sha:
            body["sha"] = sha
        _req.put(url, json=body, headers=hdrs, timeout=10)
    except Exception:
        pass  # never crash the app over sync

def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(content, encoding="utf-8")
    _github_sync(path, content)

def load_config() -> dict:
    return _load(CONFIG_FILE, {"teams": []})

def save_config(cfg: dict) -> None:
    _save(CONFIG_FILE, cfg)

def load_roster(tid: str) -> dict:
    return _load(_roster_file(tid), {"players": []})

def save_roster(data: dict, tid: str) -> None:
    _save(_roster_file(tid), data)

def load_games_data(tid: str) -> dict:
    return _load(_games_file(tid), {"tournaments": [], "games": []})

def save_games_data(data: dict, tid: str) -> None:
    _save(_games_file(tid), data)

# ── Migration ─────────────────────────────────────────────────────────────────

def _run_migration() -> dict:
    if CONFIG_FILE.exists():
        return _load(CONFIG_FILE, {"teams": [{"id": "reapers", "name": "Reapers"}]})

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    config = {"teams": [{"id": "reapers", "name": "Reapers"}]}

    if _LEG_ROSTER.exists() and not _roster_file("reapers").exists():
        _save(_roster_file("reapers"), _load(_LEG_ROSTER, {"players": []}))
    if not _roster_file("reapers").exists():
        _save(_roster_file("reapers"), {"players": []})

    if _LEG_GAMES.exists() and not _games_file("reapers").exists():
        old = _load(_LEG_GAMES, {"games": []})
        tourn_name = old.get("tournament", f'{old.get("season", "2026")} Season')
        tourn = {"id": "default", "name": tourn_name, "year": old.get("season", "2026")}
        for g in old.get("games", []):
            g.setdefault("tournament_id", "default")
        _save(_games_file("reapers"), {"tournaments": [tourn], "games": old.get("games", [])})
    if not _games_file("reapers").exists():
        _save(_games_file("reapers"), {"tournaments": [], "games": []})

    _save(CONFIG_FILE, config)
    return config

# ── Stats ─────────────────────────────────────────────────────────────────────

def pas_to_stat_row(pas: list[dict], walks_as_hits: bool) -> dict:
    s = {"AB": 0, "1B": 0, "2B": 0, "3B": 0, "HR_OTF": 0, "HR_ITP": 0, "BB": 0, "SF": 0, "R": 0, "RBI": 0, "K": 0}
    for pa in pas:
        oc = pa.get("outcome", "OUT")
        if oc == "BB":
            s["BB"] += 1
            if walks_as_hits:
                s["AB"] += 1
                s["1B"] += 1
        elif oc == "SF":
            s["SF"] += 1
        else:
            s["AB"] += 1
            if oc in HIT_CODES:
                s[oc] += 1
            elif oc == "K":
                s["K"] += 1
        s["R"]   += int(pa.get("run_scored", False))
        s["RBI"] += int(pa.get("rbi", 0))
    return s


def _active_lineup_at(lineup: list, substitutions: list, inning: int) -> list:
    """Players in batting-order sequence after applying subs with inning <= `inning`."""
    slot = {s["order"]: s["player"] for s in lineup}
    for sub in sorted(substitutions, key=lambda s: s["inning"]):
        if sub["inning"] <= inning:
            for ord_n, pl in list(slot.items()):
                if pl == sub["out"]:
                    slot[ord_n] = sub["in"]
                    break
    return [p for _, p in sorted(slot.items())]


def _active_bench_at(lineup: list, bench_initial: list,
                     substitutions: list, inning: int = 9999) -> tuple:
    """(active_set, bench_set) after subs with inning <= `inning`."""
    active = {s["player"] for s in lineup}
    bench  = set(bench_initial)
    for sub in sorted(substitutions, key=lambda s: s["inning"]):
        if sub["inning"] <= inning:
            active.discard(sub["out"])
            bench.add(sub["out"])
            bench.discard(sub["in"])
            active.add(sub["in"])
    return active, bench


def _mini_diamond_svg(bases_reached: int, out_at=None) -> str:
    """Tiny 36×36 inline diamond for scoresheet chips."""
    out_at = out_at or []
    pink, dim, ldim, red = "#FF1493", "rgba(255,255,255,0.12)", "rgba(255,255,255,0.22)", "#e03030"
    def _bc(n): return red if n in out_at else (pink if bases_reached >= n else dim)
    b1, b2, b3, bh = _bc(1), _bc(2), _bc(3), _bc(4)
    l01 = pink if bases_reached >= 1 else ldim
    l12 = pink if bases_reached >= 2 else ldim
    l23 = pink if bases_reached >= 3 else ldim
    l30 = pink if bases_reached >= 4 else ldim
    def _dmnd(cx, cy, r, fill):
        return (f"<polygon points='{cx},{cy-r} {cx+r},{cy} {cx},{cy+r} {cx-r},{cy}'"
                f" fill='{fill}'/>")
    xs = ""
    for b, cx, cy in [(1,32,18),(2,18,4),(3,4,18),(4,18,32)]:
        if b in out_at:
            xs += (f"<line x1='{cx-3}' y1='{cy-3}' x2='{cx+3}' y2='{cy+3}' stroke='white' stroke-width='1.8'/>"
                   f"<line x1='{cx+3}' y1='{cy-3}' x2='{cx-3}' y2='{cy+3}' stroke='white' stroke-width='1.8'/>")
    return (
        "<div style='text-align:center;line-height:1'>"
        "<svg width='36' height='36' viewBox='0 0 36 36'>"
        f"<line x1='18' y1='32' x2='32' y2='18' stroke='{l01}' stroke-width='1.5'/>"
        f"<line x1='32' y1='18' x2='18' y2='4'  stroke='{l12}' stroke-width='1.5'/>"
        f"<line x1='18' y1='4'  x2='4'  y2='18' stroke='{l23}' stroke-width='1.5'/>"
        f"<line x1='4'  y1='18' x2='18' y2='32' stroke='{l30}' stroke-width='1.5'/>"
        f"{_dmnd(32,18,5,b1)}"
        f"{_dmnd(18,4,5,b2)}"
        f"{_dmnd(4,18,5,b3)}"
        f"{_dmnd(18,32,5,bh)}"
        f"{xs}"
        "</svg></div>"
    )


def _diamond_svg(bases_reached: int, out_at=None) -> str:
    """Return an SVG baseball diamond with the runner's path lit up to `bases_reached`."""
    out_at = out_at or []
    pink, dim, line_dim, red = "#FF1493", "rgba(255,255,255,0.12)", "rgba(255,255,255,0.22)", "#e03030"
    def _bc(n): return red if n in out_at else (pink if bases_reached >= n else dim)
    b1, b2, b3, bh = _bc(1), _bc(2), _bc(3), _bc(4)
    l01 = pink if bases_reached >= 1 else line_dim
    l12 = pink if bases_reached >= 2 else line_dim
    l23 = pink if bases_reached >= 3 else line_dim
    l30 = pink if bases_reached >= 4 else line_dim
    def _dmnd(cx, cy, r, fill):
        return (f"<polygon points='{cx},{cy-r} {cx+r},{cy} {cx},{cy+r} {cx-r},{cy}'"
                f" fill='{fill}'/>")
    xs = ""
    for b, cx, cy in [(1,77,45),(2,45,13),(3,13,45),(4,45,77)]:
        if b in out_at:
            xs += (f"<line x1='{cx-5}' y1='{cy-5}' x2='{cx+5}' y2='{cy+5}' stroke='white' stroke-width='2.5'/>"
                   f"<line x1='{cx+5}' y1='{cy-5}' x2='{cx-5}' y2='{cy+5}' stroke='white' stroke-width='2.5'/>")
    return (
        "<svg width='90' height='90' viewBox='0 0 90 90' "
        "style='display:block;margin:6px auto'>"
        f"<line x1='45' y1='77' x2='77' y2='45' stroke='{l01}' stroke-width='3'/>"
        f"<line x1='77' y1='45' x2='45' y2='13' stroke='{l12}' stroke-width='3'/>"
        f"<line x1='45' y1='13' x2='13' y2='45' stroke='{l23}' stroke-width='3'/>"
        f"<line x1='13' y1='45' x2='45' y2='77' stroke='{l30}' stroke-width='3'/>"
        f"{_dmnd(77,45,12,b1)}"
        f"{_dmnd(45,13,12,b2)}"
        f"{_dmnd(13,45,12,b3)}"
        f"{_dmnd(45,77,12,bh)}"
        "<text x='77' y='49' text-anchor='middle' font-size='9' fill='white' font-weight='bold'>1</text>"
        "<text x='45' y='17' text-anchor='middle' font-size='9' fill='white' font-weight='bold'>2</text>"
        "<text x='13' y='49' text-anchor='middle' font-size='9' fill='white' font-weight='bold'>3</text>"
        "<text x='45' y='81' text-anchor='middle' font-size='9' fill='white' font-weight='bold'>H</text>"
        f"{xs}"
        "</svg>"
    )



def add_derived(df: pd.DataFrame, walks_as_hits: bool) -> pd.DataFrame:
    df = df.copy()
    if "BB" not in df.columns:
        df["BB"] = 0
    df["HR"]  = df["HR_OTF"] + df["HR_ITP"]
    df["H"]   = df["1B"] + df["2B"] + df["3B"] + df["HR"]
    df["XBH"] = df["2B"] + df["3B"] + df["HR"]
    df["TB"]  = df["1B"] + 2 * df["2B"] + 3 * df["3B"] + 4 * df["HR"]
    df["AVG"] = (df["H"] / df["AB"]).where(df["AB"] > 0, 0).round(3)
    sf_col = df["SF"] if "SF" in df.columns else 0
    if walks_as_hits:
        df["OBP"] = df["AVG"]
    else:
        tot_pa = df["AB"] + df["BB"] + sf_col
        df["OBP"] = ((df["H"] + df["BB"]) / tot_pa).where(tot_pa > 0, 0).round(3)
    df["SLG"] = (df["TB"] / df["AB"]).where(df["AB"] > 0, 0).round(3)
    df["OPS"] = (df["OBP"] + df["SLG"]).round(3)
    return df

def build_per_game_df(games: list[dict], walks_as_hits: bool) -> pd.DataFrame:
    rows = []
    for g in games:
        pas = g.get("plate_appearances", [])
        for player in {pa["player"] for pa in pas}:
            ppas = [pa for pa in pas if pa["player"] == player]
            s = pas_to_stat_row(ppas, walks_as_hits)
            s.update({"player": player, "game_id": g["game_id"],
                      "date": g["date"], "opponent": g["opponent"],
                      "type": g.get("type", "regular")})
            rows.append(s)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for col in ["AB", "1B", "2B", "3B", "HR_OTF", "HR_ITP", "BB", "R", "RBI", "K"]:
        if col not in df.columns:
            df[col] = 0
    return add_derived(df, walks_as_hits)

def season_totals(pg: pd.DataFrame, walks_as_hits: bool) -> pd.DataFrame:
    if pg.empty:
        return pd.DataFrame()
    sum_cols = ["AB", "1B", "2B", "3B", "HR_OTF", "HR_ITP", "BB", "SF", "R", "RBI", "K"]
    avail = [c for c in sum_cols if c in pg.columns]
    tot = pg.groupby("player", as_index=False)[avail].sum()
    g_counts = pg.groupby("player")["game_id"].nunique().reset_index()
    g_counts.columns = ["player", "G"]
    tot = tot.merge(g_counts, on="player", how="left")
    return add_derived(tot, walks_as_hits)

# ── Rendering helpers ─────────────────────────────────────────────────────────

def leader_html(title: str, df: pd.DataFrame, col: str, fmt: str = "{:.3f}", n: int = 3) -> str:
    count_cols = {"HR", "RBI", "R", "H", "XBH", "BB", "K"}
    if df.empty or col not in df.columns:
        inner = '<div class="leader-row"><span class="name" style="opacity:0.4">—</span></div>'
    else:
        candidates = df[df[col] > 0] if col in count_cols else df
        top = candidates.sort_values(col, ascending=False).head(n)
        if top.empty:
            inner = '<div class="leader-row"><span class="name" style="opacity:0.4">—</span></div>'
        else:
            inner = ""
            for rank, (_, r) in enumerate(top.iterrows(), 1):
                inner += (
                    f'<div class="leader-row r{rank}">'
                    f'<span><span class="rank">{rank}</span>'
                    f'<span class="name">{r["player"]}</span></span>'
                    f'<span class="val">{fmt.format(r[col])}</span>'
                    f'</div>'
                )
    return f'<div class="leader-card"><h4>{title}</h4>{inner}</div>'

def render_stats_table(table: pd.DataFrame) -> None:
    rate_cols = {"AVG", "OBP", "SLG", "OPS"}
    color_map = {"OPS": (255, 20, 147), "HR": (80, 180, 110), "RBI": (80, 180, 110), "R": (80, 180, 110)}
    fns = {}
    for c, rgb in color_map.items():
        if c in table.columns and table[c].max() > table[c].min():
            vmin, vmax = float(table[c].min()), float(table[c].max())
            r, g, b = rgb
            def _fn(v, vn=vmin, vx=vmax, r=r, g=g, b=b):
                norm = (float(v) - vn) / (vx - vn)
                a = 0.08 + 0.45 * norm
                return f"background-color: rgba({r},{g},{b},{a:.2f})"
            fns[c] = _fn

    labels = {"player": "Player", "G": "G", "AB": "AB", "H": "H",
              "1B": "1B", "2B": "2B", "3B": "3B", "HR": "HR",
              "HR_OTF": "OTF", "HR_ITP": "ITP", "BB": "BB", "SF": "SF",
              "R": "R", "RBI": "RBI", "K": "K",
              "AVG": "AVG", "OBP": "OBP", "SLG": "SLG", "OPS": "OPS"}

    headers = [
        f'<th class="{"player-th" if c == "player" else ""}">{labels.get(c, c)}</th>'
        for c in table.columns
    ]
    body = []
    for _, row in table.iterrows():
        cells = []
        for c in table.columns:
            v = row[c]
            if c == "player":
                cells.append(f'<td class="player-cell">{v}</td>')
                continue
            bg = fns[c](v) if c in fns else ""
            text = f"{v:.3f}" if c in rate_cols else f"{int(v)}"
            style = f' style="{bg}"' if bg else ""
            cells.append(f"<td{style}>{text}</td>")
        body.append(f'<tr>{"".join(cells)}</tr>')

    st.markdown(
        '<div class="stats-table-wrap"><table class="stats-table">'
        f'<thead><tr>{"".join(headers)}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody>'
        '</table></div>',
        unsafe_allow_html=True,
    )

def _slug(name: str, existing: set) -> str:
    raw = re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_') or "item"
    tid = raw
    n = 2
    while tid in existing:
        tid = f"{raw}_{n}"
        n += 1
    return tid

# ── Bootstrap ─────────────────────────────────────────────────────────────────

config = _run_migration()

if "active_team_id" not in st.session_state:
    st.session_state.active_team_id = config["teams"][0]["id"] if config["teams"] else "reapers"
if "active_tournament_id" not in st.session_state:
    st.session_state.active_tournament_id = None

active_team_id = st.session_state.active_team_id
team_ids = [t["id"] for t in config.get("teams", [])]
if active_team_id not in team_ids and team_ids:
    st.session_state.active_team_id = team_ids[0]
    active_team_id = team_ids[0]

roster_data      = load_roster(active_team_id)
games_data       = load_games_data(active_team_id)
player_names     = [p["name"] for p in roster_data.get("players", [])]
active_team_name = next((t["name"] for t in config.get("teams", []) if t["id"] == active_team_id), "Reapers")
tournaments      = games_data.get("tournaments", [])

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    teams = config.get("teams", [])

    if len(teams) > 1:
        team_names = [t["name"] for t in teams]
        cur_idx = next((i for i, t in enumerate(teams) if t["id"] == active_team_id), 0)
        sel_team = st.selectbox("Team", team_names, index=cur_idx)
        new_tid = next(t["id"] for t in teams if t["name"] == sel_team)
        if new_tid != active_team_id:
            st.session_state.active_team_id = new_tid
            st.session_state.active_tournament_id = None
            st.session_state.pop("lg_game", None)
            st.rerun()

    st.markdown(f"## 💀 {active_team_name}")

    if tournaments:
        tourn_opts = ["All Tournaments"] + [t["name"] for t in tournaments]
        cur_tourn = st.session_state.active_tournament_id
        tourn_idx = 0
        if cur_tourn:
            for i, t in enumerate(tournaments):
                if t["id"] == cur_tourn:
                    tourn_idx = i + 1
                    break
        sel_tourn = st.selectbox("🏆 Tournament", tourn_opts, index=tourn_idx)
        if sel_tourn == "All Tournaments":
            st.session_state.active_tournament_id = None
        else:
            st.session_state.active_tournament_id = next(
                t["id"] for t in tournaments if t["name"] == sel_tourn
            )

    active_tournament_id = st.session_state.active_tournament_id

    st.markdown("---")
    _pages = ["📊 Dashboard", "👥 Roster", "⚾ Log Game", "📋 History", "⚙️ Settings"]
    page = st.radio(
        "Navigate", _pages,
        index=st.session_state.get("_nav_idx", 0),
        label_visibility="collapsed",
    )
    st.session_state["_nav_idx"] = _pages.index(page)
    st.markdown("---")
    walks_as_hits = st.toggle(
        "Walks count as hits",
        value=False,
        help="ON = walk recorded as single (league rule). OFF = standard OBP.",
    )
    st.caption("League mode (BB = hit)" if walks_as_hits else "Standard mode (BB → OBP only)")

# ── Build stats ───────────────────────────────────────────────────────────────

all_games = sorted(games_data.get("games", []), key=lambda g: g["game_id"])
if active_tournament_id:
    games = [g for g in all_games if g.get("tournament_id") == active_tournament_id]
else:
    games = all_games

pg     = build_per_game_df(games, walks_as_hits)
totals = season_totals(pg, walks_as_hits) if not pg.empty else pd.DataFrame()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

if page == "📊 Dashboard":
    wins   = sum(1 for g in games if g.get("result") == "W")
    losses = sum(1 for g in games if g.get("result") == "L")
    ties   = sum(1 for g in games if g.get("result") == "T")
    rf     = sum(g.get("team_runs") or 0 for g in games)
    ra     = sum(g.get("opp_runs")  or 0 for g in games)
    record = f"{wins}-{losses}" + (f"-{ties}" if ties else "")

    tourn_label = "All Tournaments"
    if active_tournament_id and tournaments:
        tn = next((t for t in tournaments if t["id"] == active_tournament_id), None)
        tourn_label = tn["name"] if tn else "All Tournaments"
    elif not tournaments:
        tourn_label = str(date.today().year)

    rc = "green" if wins > losses else ("red" if losses > wins else "")
    r_badge = f'<span class="badge {rc}">{record}</span>'
    g_badge = f'<span class="badge">{len(games)} game{"s" if len(games) != 1 else ""}</span>'
    d_badge = f'<span class="badge">Run diff {rf - ra:+d}</span>'

    st.markdown(
        f'<div class="hero"><h1>💀 {active_team_name}</h1>'
        f'<div class="sub">{tourn_label}</div>'
        f'<div class="badges">{r_badge}{g_badge}{d_badge}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if PHOTO_FILE.exists():
        col_img, _ = st.columns([1, 3])
        col_img.image(str(PHOTO_FILE), use_container_width=True)

    if not games:
        st.info("No games logged yet — go to **Log Game** to add your first game.")
        st.stop()

    latest = games[-1]
    rw = {"W": "Won", "L": "Lost", "T": "Tied"}.get(latest["result"], latest["result"])
    st.markdown(
        f'<div class="recap">'
        f'<div class="title">Latest game · {latest["date"]}</div>'
        f'<div class="score">{rw} {latest["team_runs"]}–{latest["opp_runs"]} vs {latest["opponent"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not totals.empty:
        gp       = len(games)
        team_ab  = int(totals["AB"].sum())
        team_h   = int(totals["H"].sum())
        team_tb  = int(totals["TB"].sum())
        team_bb  = int(totals["BB"].sum()) if "BB" in totals.columns else 0
        team_avg = round(team_h / team_ab, 3) if team_ab else 0
        team_slg = round(team_tb / team_ab, 3) if team_ab else 0
        team_obp = team_avg if walks_as_hits else (round((team_h + team_bb) / (team_ab + team_bb), 3) if (team_ab + team_bb) else 0)
        team_ops = round(team_obp + team_slg, 3)
        team_hr  = int(totals["HR"].sum())
        team_otf = int(totals["HR_OTF"].sum())
        team_itp = int(totals["HR_ITP"].sum())

        st.markdown(
            '<div class="kpi-grid">'
            f'<div class="kpi-card"><div class="label">Runs / Game</div><div class="value">{rf/gp:.1f}</div></div>'
            f'<div class="kpi-card"><div class="label">Team AVG</div><div class="value">{team_avg:.3f}</div></div>'
            f'<div class="kpi-card"><div class="label">Team OPS</div><div class="value">{team_ops:.3f}</div></div>'
            f'<div class="kpi-card"><div class="label">Home Runs</div><div class="value">{team_hr}</div>'
            f'<div class="hint">{team_otf} OTF · {team_itp} ITP</div></div>'
            f'<div class="kpi-card"><div class="label">Total Hits</div><div class="value">{team_h}</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )

    tab_ovr, tab_lead, tab_cmp, tab_tbl, tab_log = st.tabs(
        ["📈 Overview", "🏆 Leaders", "⚔️ Compare", "📊 Stats Table", "🗓️ Game Log"]
    )

    with tab_ovr:
        if totals.empty:
            st.info("No stats yet.")
        else:
            left, right = st.columns([1.2, 1])

            with left:
                st.markdown("##### Team hit mix")
                singles = int(totals["1B"].sum())
                hit_mix = pd.DataFrame([
                    {"Type": "Singles",   "Count": singles},
                    {"Type": "Doubles",   "Count": int(totals["2B"].sum())},
                    {"Type": "Triples",   "Count": int(totals["3B"].sum())},
                    {"Type": "Home Runs", "Count": int(totals["HR"].sum())},
                ])
                total_hits = hit_mix["Count"].sum()
                hit_mix["Pct"] = (hit_mix["Count"] / total_hits * 100).round(1) if total_hits else 0.0
                chart = (
                    alt.Chart(hit_mix).mark_bar()
                    .encode(
                        x=alt.X("Type:N", sort=["Singles", "Doubles", "Triples", "Home Runs"],
                                title=None, axis=alt.Axis(labelAngle=0)),
                        y=alt.Y("Count:Q", title="Hits"),
                        color=alt.Color("Type:N",
                            scale=alt.Scale(
                                domain=["Singles", "Doubles", "Triples", "Home Runs"],
                                range=["#3b0a2a", "#8b0057", "#cc0080", "#FF1493"],
                            ), legend=None),
                        tooltip=["Type:N", "Count:Q", alt.Tooltip("Pct:Q", format=".1f", title="% of hits")],
                    ).properties(height=260)
                )
                st.altair_chart(chart, use_container_width=True)

            with right:
                st.markdown("##### Top 8 by OPS")
                min_ab = max(1, int(totals["AB"].max() * 0.5))
                chart_df = totals[totals["AB"] >= min_ab].sort_values("OPS", ascending=False).head(8)
                if not chart_df.empty:
                    st.altair_chart(
                        alt.Chart(chart_df).mark_bar(color="#FF1493")
                        .encode(
                            y=alt.Y("player:N", sort="-x", title=None),
                            x=alt.X("OPS:Q", axis=alt.Axis(format=".3f")),
                            tooltip=["player", "AB", "H", "HR",
                                     alt.Tooltip("AVG:Q", format=".3f"),
                                     alt.Tooltip("OPS:Q", format=".3f")],
                        ).properties(height=260),
                        use_container_width=True,
                    )
                    st.caption(f"Qualified: ≥{min_ab} AB")

            st.markdown("##### Home run tracker")
            hr_df = totals[(totals["HR_OTF"] + totals["HR_ITP"]) > 0] if not totals.empty else pd.DataFrame()
            if hr_df.empty:
                st.caption("No home runs yet.")
            else:
                rows_html = ""
                for _, r in hr_df.sort_values("HR", ascending=False).iterrows():
                    otf, itp = int(r["HR_OTF"]), int(r["HR_ITP"])
                    dots = ('<span class="hr-dot hr-otf"></span>' * otf
                            + '<span class="hr-dot hr-itp"></span>' * itp)
                    rows_html += (
                        f'<div class="hr-row">'
                        f'<span class="hr-name">{r["player"]}</span>'
                        f'<span class="hr-markers">{dots}</span>'
                        f'<span class="hr-count">{otf + itp} HR</span>'
                        f'</div>'
                    )
                st.markdown(
                    '<div style="font-size:13px;opacity:0.8;margin-bottom:8px">'
                    '<span class="hr-dot hr-otf"></span> Over the fence &nbsp;·&nbsp; '
                    '<span class="hr-dot hr-itp"></span> Inside the park'
                    '</div>' + rows_html,
                    unsafe_allow_html=True,
                )

    with tab_lead:
        if totals.empty:
            st.info("No stats yet.")
        else:
            max_ab = int(totals["AB"].max())
            default_min = max(1, min(max_ab, 2 * len(games)))
            min_ab = st.slider("Min AB (rate stats)", 0, max(max_ab, 1), value=default_min)
            qual = totals[totals["AB"] >= min_ab]

            r1 = st.columns(3)
            r1[0].markdown(leader_html("Batting Average", qual, "AVG"), unsafe_allow_html=True)
            r1[1].markdown(leader_html("OPS", qual, "OPS"), unsafe_allow_html=True)
            r1[2].markdown(leader_html("Slugging", qual, "SLG"), unsafe_allow_html=True)

            r2 = st.columns(3)
            r2[0].markdown(leader_html("Home Runs", totals, "HR", "{:.0f}"), unsafe_allow_html=True)
            r2[1].markdown(leader_html("RBIs", totals, "RBI", "{:.0f}"), unsafe_allow_html=True)
            r2[2].markdown(leader_html("Runs Scored", totals, "R", "{:.0f}"), unsafe_allow_html=True)

            r3 = st.columns(3)
            r3[0].markdown(leader_html("Hits", totals, "H", "{:.0f}"), unsafe_allow_html=True)
            r3[1].markdown(leader_html("Extra-Base Hits", totals, "XBH", "{:.0f}"), unsafe_allow_html=True)
            if not walks_as_hits:
                r3[2].markdown(leader_html("Walks", totals, "BB", "{:.0f}"), unsafe_allow_html=True)

    with tab_cmp:
        if totals.empty or len(totals) < 2:
            st.info("Need at least 2 players with stats to compare.")
        else:
            pl = sorted(totals["player"].tolist())
            ca, cb = st.columns(2)
            p1 = ca.selectbox("Player A", pl, index=0)
            p2 = cb.selectbox("Player B", pl, index=min(1, len(pl) - 1))

            if p1 == p2:
                st.warning("Pick two different players.")
            else:
                r1 = totals[totals["player"] == p1].iloc[0]
                r2 = totals[totals["player"] == p2].iloc[0]

                specs = [
                    ("G",   "Games",           "{:.0f}", "high"),
                    ("AB",  "At-Bats",         "{:.0f}", "high"),
                    ("H",   "Hits",            "{:.0f}", "high"),
                    ("AVG", "Batting Avg",     "{:.3f}", "high"),
                    ("OBP", "On-Base %",       "{:.3f}", "high"),
                    ("SLG", "Slugging",        "{:.3f}", "high"),
                    ("OPS", "OPS",             "{:.3f}", "high"),
                    ("HR",  "Home Runs",       "{:.0f}", "high"),
                    ("XBH", "Extra-Base Hits", "{:.0f}", "high"),
                    ("R",   "Runs Scored",     "{:.0f}", "high"),
                    ("RBI", "RBIs",            "{:.0f}", "high"),
                    ("K",   "Strikeouts",      "{:.0f}", "low"),
                ]
                if not walks_as_hits:
                    specs.insert(-1, ("BB", "Walks", "{:.0f}", "high"))

                lw = rw = tc = 0
                rows_html = ""
                for stat, label, fmt, direction in specs:
                    if stat not in r1.index:
                        continue
                    v1, v2 = r1[stat], r2[stat]
                    if direction == "high":
                        w = "left" if v1 > v2 else ("right" if v2 > v1 else "tie")
                    else:
                        w = "left" if v1 < v2 else ("right" if v2 < v1 else "tie")
                    if w == "left":    lw += 1; lc, rc = "winner", ""
                    elif w == "right": rw += 1; lc, rc = "", "winner"
                    else:              tc += 1; lc = rc = "tie"
                    rows_html += (
                        f'<div class="cmp-row">'
                        f'<div class="cmp-val left {lc}">{fmt.format(v1)}</div>'
                        f'<div class="cmp-stat">{label}</div>'
                        f'<div class="cmp-val right {rc}">{fmt.format(v2)}</div>'
                        f'</div>'
                    )
                st.markdown(
                    '<div class="cmp-wrap">'
                    f'<div class="cmp-header">'
                    f'<div class="cmp-name left">{p1}</div>'
                    f'<div class="vs">vs</div>'
                    f'<div class="cmp-name right">{p2}</div>'
                    f'</div>'
                    + rows_html +
                    f'<div class="cmp-tally">'
                    f'<b>{p1}</b> leads in <b>{lw}</b> &nbsp;·&nbsp; '
                    f'<b>{p2}</b> leads in <b>{rw}</b> &nbsp;·&nbsp; '
                    f'Tied in <b>{tc}</b></div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

    with tab_tbl:
        if totals.empty:
            st.info("No stats yet.")
        else:
            sort_by = st.selectbox("Sort by", ["OPS", "AVG", "HR", "RBI", "R", "H", "AB"])
            cols = ["player", "G", "AB", "H", "1B", "2B", "3B", "HR", "HR_OTF", "HR_ITP"]
            if not walks_as_hits:
                cols.append("BB")
            cols += ["SF", "R", "RBI", "K", "AVG", "OBP", "SLG", "OPS"]
            cols = [c for c in cols if c in totals.columns]
            render_stats_table(
                totals[cols].sort_values(sort_by, ascending=False).reset_index(drop=True)
            )

    with tab_log:
        glog = pd.DataFrame([{
            "Game": g["game_id"], "Date": g["date"], "Opponent": g["opponent"],
            "Result": g.get("result") or "Live",
            "Score": (f'{g["team_runs"]}-{g["opp_runs"]}' if g.get("result") else "In progress"),
            "Type": g.get("type", "regular").title(),
            "Tournament": next((t["name"] for t in tournaments if t["id"] == g.get("tournament_id")), "—"),
        } for g in games])
        st.dataframe(glog, hide_index=True, use_container_width=True)

        if not pg.empty:
            st.markdown("##### Per-player game log")
            sel = st.selectbox("Player", sorted(pg["player"].unique()))
            pdf = pg[pg["player"] == sel].sort_values("game_id")
            cols = ["date", "opponent", "AB", "H", "1B", "2B", "3B", "HR", "HR_OTF", "HR_ITP"]
            if not walks_as_hits:
                cols.append("BB")
            cols += ["R", "RBI", "K", "AVG", "SLG", "OPS"]
            cols = [c for c in cols if c in pdf.columns]
            st.dataframe(
                pdf[cols].style.format({c: "{:.3f}" for c in ["AVG", "SLG", "OPS"]}),
                hide_index=True, use_container_width=True,
            )

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ROSTER
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "👥 Roster":
    st.markdown(f"## 👥 Roster — {active_team_name}")

    players = roster_data.get("players", [])

    if "editing_player" not in st.session_state:
        st.session_state.editing_player = None

    if players:
        for i, p in enumerate(players):
            if st.session_state.editing_player == i:
                c1, c2, c3 = st.columns([3, 1, 1])
                new_name = c1.text_input(
                    "Name", value=p["name"], key=f"edit_nm_{i}",
                    label_visibility="collapsed"
                )
                if c2.button("Save", key=f"save_p_{i}"):
                    stripped = new_name.strip()
                    if stripped and stripped.lower() != p["name"].lower() and stripped.lower() in {x["name"].lower() for j, x in enumerate(players) if j != i}:
                        st.error(f"{stripped} already exists.")
                    elif stripped:
                        players[i]["name"] = stripped
                        save_roster(roster_data, active_team_id)
                        st.session_state.editing_player = None
                        st.rerun()
                if c3.button("Cancel", key=f"cancel_p_{i}"):
                    st.session_state.editing_player = None
                    st.rerun()
            else:
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{p['name']}**")
                if c2.button("✏️ Edit", key=f"edit_p_{i}"):
                    st.session_state.editing_player = i
                    st.rerun()
                if c3.button("✕", key=f"del_p_{i}"):
                    players.pop(i)
                    save_roster(roster_data, active_team_id)
                    st.rerun()
    else:
        st.info("No players on the roster yet.")

    st.markdown("---")
    st.markdown("#### Add Player")

    with st.form("add_player"):
        new_name = st.text_input("Name")
        if st.form_submit_button("Add Player"):
            if not new_name.strip():
                st.error("Name is required.")
            elif new_name.strip().lower() in {p["name"].lower() for p in players}:
                st.error(f"{new_name} is already on the roster.")
            else:
                players.append({"name": new_name.strip()})
                save_roster(roster_data, active_team_id)
                st.success(f"Added {new_name.strip()}.")
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: LOG GAME
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "⚾ Log Game":
    st.markdown("## ⚾ Log Game")

    if not player_names:
        st.warning("Add players to the roster first.")
        st.stop()

    if "lg_game" not in st.session_state:
        st.session_state.lg_game = None

    # ── Create new game ───────────────────────────────────────────────────────────

    if st.session_state.lg_game is None:
        game_mode = st.radio(
            "Mode",
            ["▶  Live — log as you play", "📋  Log a finished game"],
            horizontal=True, label_visibility="collapsed",
        )
        is_live = "Live" in game_mode
        st.markdown(f"#### {'Start a live game' if is_live else 'Log a finished game'}")

        tourn_list    = games_data.get("tournaments", [])
        tourn_display = [t["name"] for t in tourn_list]

        result = "W"; team_runs = 0; opp_runs = 0  # defaults for finished path

        with st.form("new_game"):
            c1, c2 = st.columns(2)
            opponent  = c1.text_input("Opponent")
            game_date = c2.date_input("Date", value=date.today())
            ha1, ha2 = st.columns(2)
            home_away = ha1.radio("Home or Away?", ["Away", "Home"], horizontal=True)
            game_type = ha2.selectbox("Type", ["tournament", "regular", "playoff", "scrimmage"])

            if not is_live:
                r1, r2, r3 = st.columns(3)
                result    = r1.selectbox("Result", ["W", "L", "T"])
                team_runs = r2.number_input("Your runs", min_value=0, value=0, step=1)
                opp_runs  = r3.number_input("Opp runs",  min_value=0, value=0, step=1)

            default_tidx = 0
            if active_tournament_id:
                for i, t in enumerate(tourn_list):
                    if t["id"] == active_tournament_id:
                        default_tidx = i; break

            if tourn_display:
                tourn_choice = st.selectbox(
                    "Tournament", tourn_display + ["+ New tournament"],
                    index=default_tidx,
                )
            else:
                tourn_choice = "+ New tournament"
                st.caption("No tournaments yet — create one below.")

            new_tourn_name = new_tourn_year = ""
            if tourn_choice == "+ New tournament" or not tourn_display:
                nc1, nc2 = st.columns(2)
                new_tourn_name = nc1.text_input("Tournament name", placeholder="e.g. Summer 2026")
                new_tourn_year = nc2.text_input("Year", value=str(date.today().year))

            go = st.form_submit_button("▶ Start Game" if is_live else "Create Game →")

        if go:
            if not opponent.strip():
                st.error("Opponent name is required.")
            elif tourn_choice == "+ New tournament" and not new_tourn_name.strip():
                st.error("Tournament name is required.")
            else:
                if tourn_choice == "+ New tournament":
                    tourn_id = _slug(new_tourn_name.strip(), {t["id"] for t in tourn_list})
                    tourn_list.append({
                        "id": tourn_id, "name": new_tourn_name.strip(),
                        "year": new_tourn_year.strip() or str(date.today().year),
                    })
                    games_data["tournaments"] = tourn_list
                    save_games_data(games_data, active_team_id)
                    st.session_state.active_tournament_id = tourn_id
                else:
                    tourn_id = next(t["id"] for t in tourn_list if t["name"] == tourn_choice)

                ids = [g["game_id"] for g in all_games]
                new_id = max(ids) + 1 if ids else 1
                st.session_state.lg_game = {
                    "game_id":   new_id,
                    "date":      str(game_date),
                    "opponent":  opponent.strip(),
                    "result":    None if is_live else result,
                    "team_runs": None if is_live else int(team_runs),
                    "opp_runs":  None if is_live else int(opp_runs),
                    "type":      game_type,
                    "live_mode":  is_live,
                    "home_away":  home_away,
                    "tournament_id": tourn_id,
                    "current_inning": 1,
                    "lineup":        [],
                    "bench_players": [],
                    "substitutions": [],
                    "plate_appearances": [],
                }
                st.session_state.lg_current_inning = 1
                st.rerun()

    # ── In-progress / editing ─────────────────────────────────────────────────────

    else:
        g = st.session_state.lg_game
        editing_id = st.session_state.get("editing_game_id")
        g_tourn    = next((t["name"] for t in tournaments if t["id"] == g.get("tournament_id", "")), "")

        # Live score strip (always editable for live games)
        if g.get("live_mode"):
            st.markdown(
                f"<div style='padding:8px 0;font-size:16px;font-weight:700'>"
                f"🔴 <span style='color:#FF1493'>LIVE</span>"
                f" vs {g['opponent']}"
                f"{'  ·  ' + g_tourn if g_tourn else ''}"
                f"<span style='opacity:0.45;font-size:12px;margin-left:8px'>{g['date']}</span></div>",
                unsafe_allow_html=True,
            )
        else:
            mode_label = "Editing" if editing_id else "In progress"
            score_str  = f"{g.get('result','?')} {g.get('team_runs','?')}–{g.get('opp_runs','?')}"
            st.markdown(
                f'<div class="recap">'
                f'<div class="title">{mode_label} · {g["date"]}'
                f'{("  ·  " + g_tourn) if g_tourn else ""}</div>'
                f'<div class="score">{score_str} vs {g["opponent"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        tab_lu, tab_ab, tab_sv = st.tabs(["1 · Lineup", "2 · Scoresheet", "3 · Review & Save"])

        # ── Tab 1: Lineup ─────────────────────────────────────────────────────────

        with tab_lu:
            # Seed lineup/bench from roster on first open
            if not g["lineup"] and not g.get("bench_players"):
                g["lineup"]        = [{"order": i + 1, "player": p} for i, p in enumerate(player_names)]
                g["bench_players"] = []

            lineup_players = [s["player"] for s in sorted(g["lineup"], key=lambda x: x["order"])]
            bench_players  = list(g.get("bench_players", []))

            # Any new roster players land on bench by default
            for p in player_names:
                if p not in lineup_players and p not in bench_players:
                    bench_players.append(p)
            g["bench_players"] = bench_players

            st.markdown("**Batting order** — drag to reorder")
            _lu_key = "ls_" + "_".join(p[:5].replace(" ", "") for p in lineup_players)
            new_order = sort_items(lineup_players, direction="vertical", key=_lu_key)
            if new_order != lineup_players:
                g["lineup"] = [{"order": i + 1, "player": p}
                                for i, p in enumerate(new_order)]
                st.rerun()

            if lineup_players:
                bench_sel = st.pills(
                    "Tap a player to bench them",
                    lineup_players,
                    key="lu_bench_sel",
                )
                if bench_sel:
                    g["lineup"] = [{"order": j + 1, "player": x["player"]}
                                   for j, x in enumerate(
                                       sorted([x for x in g["lineup"]
                                               if x["player"] != bench_sel],
                                              key=lambda x: x["order"]))]
                    bench_players.append(bench_sel)
                    g["bench_players"] = bench_players
                    st.session_state.pop("lu_bench_sel", None)
                    st.rerun()

            if bench_players:
                st.markdown("---")
                st.markdown("**Bench**")
                for player in bench_players:
                    lc, rc = st.columns([5, 1])
                    lc.markdown(f"<div style='padding:7px 0;opacity:0.5'>{player}</div>",
                                unsafe_allow_html=True)
                    if rc.button("⬆", key=f"to_lineup_{player}", help="Add to lineup"):
                        bench_players.remove(player)
                        g["bench_players"] = bench_players
                        next_ord = max((x["order"] for x in g["lineup"]), default=0) + 1
                        g["lineup"].append({"order": next_ord, "player": player})
                        st.rerun()

        # ── Tab 2: Scoresheet ─────────────────────────────────────────────────────

        with tab_ab:
            pas = g["plate_appearances"]

            # cur_inn must be known before lineup computation (subs are inning-aware)
            if "lg_current_inning" not in st.session_state:
                st.session_state.lg_current_inning = g.get("current_inning", 1)
            cur_inn = st.session_state.lg_current_inning

            lineup_order = _active_lineup_at(g["lineup"], g["substitutions"], cur_inn)
            order_map    = {p: (i + 1) for i, p in enumerate(lineup_order)}
            _known_all   = ([s["player"] for s in g["lineup"]]
                            + g.get("bench_players", [])
                            + [s["in"] for s in g["substitutions"]])
            _seen_set    = set()
            bench_ab     = [p for p in _known_all
                            if p not in set(lineup_order)
                            and not (p in _seen_set or _seen_set.add(p))]

            CELL_SHORT = {
                "1B":"1B","2B":"2B","3B":"3B","HR_OTF":"HR","HR_ITP":"ITP",
                "BB":"BB","K":"K","OUT":"OUT","FC":"FC","E":"E","DP":"DP","SF":"SF",
                "TP":"TP",
            }
            _OUTCOME_ROWS = [
                ["1B",    "2B",  "3B",  "HR_OTF"      ],
                ["HR_ITP","BB",  "E",   "FC"           ],
                ["OUT",   "K",   "DP",  "SF",  "TP"   ],
            ]
            _BTN_LABEL         = {k: CELL_SHORT[k] for k in CELL_SHORT}
            _BTN_LABEL["DP"]   = "DP (2)"
            _BTN_LABEL["TP"]   = "TP (3)"
            _ROW_CAPTION       = ["Hits", "On Base", "Outs"]

            # ── At-bat dialog ──────────────────────────────────────────────────────
            @st.dialog("Log At-Bat")
            def _ab_dialog(sel_player, sel_inning, existing, pa_count_in_inn):
                pa_label = f"PA #{pa_count_in_inn + 1} this inning" if existing is None else "Edit at-bat"
                cell_key = (f"{sel_player}__{sel_inning}__"
                            f"{existing['pa_num'] if existing else 'new'}")
                out_key    = f"dlg_out_{cell_key}"
                bases_key  = f"dlg_bases_{cell_key}"
                outat_key  = f"dlg_outat_{cell_key}"
                if out_key not in st.session_state:
                    st.session_state[out_key] = existing["outcome"] if existing else None
                if bases_key not in st.session_state:
                    _def_b = OUTCOME_BASES.get(existing["outcome"], 0) if existing else 0
                    st.session_state[bases_key] = existing.get("bases_reached", _def_b) if existing else 0
                if outat_key not in st.session_state:
                    st.session_state[outat_key] = existing.get("out_at", []) if existing else []

                cur_code = st.session_state[out_key]
                cur_name = OUTCOME_DISPLAY.get(cur_code, "") if cur_code else ""
                status_html = (
                    f"<span style='background:rgba(255,20,147,0.18);color:#ff69b4;"
                    f"padding:3px 10px;border-radius:99px;font-size:13px;font-weight:700'>"
                    f"{cur_name}</span>" if cur_code else
                    "<span style='opacity:0.45;font-size:13px'>— select below —</span>"
                )
                st.markdown(
                    f"<div style='margin-bottom:14px'>"
                    f"<div style='font-size:20px;font-weight:800;margin-bottom:4px'>"
                    f"<span style='color:#FF1493'>{sel_player}</span>"
                    f"&nbsp;<span style='opacity:0.4;font-size:14px'>Inn {sel_inning} · {pa_label}</span></div>"
                    f"{status_html}</div>",
                    unsafe_allow_html=True,
                )

                # Outs already recorded this inning (excluding the current PA if editing)
                _dlg_outs = sum(
                    (1 if p.get("outcome") == "FC"
                     or (p.get("outcome") in HIT_CODES and p.get("fc_out_player"))
                     else OUT_WEIGHTS.get(p.get("outcome"), 0))
                    for p in pas if p.get("inning") == sel_inning
                )
                if existing:
                    _ex_oc = existing.get("outcome", "")
                    _ex_w  = (1 if _ex_oc == "FC"
                              or (_ex_oc in HIT_CODES and existing.get("fc_out_player"))
                              else OUT_WEIGHTS.get(_ex_oc, 0))
                    _dlg_outs -= _ex_w

                for row_idx, row_codes in enumerate(_OUTCOME_ROWS):
                    st.caption(_ROW_CAPTION[row_idx])
                    cols = st.columns(len(row_codes))
                    for col_idx, oc in enumerate(row_codes):
                        def _pick_oc(code=oc, okey=out_key, bkey=bases_key, oak=outat_key, ck=cell_key):
                            st.session_state[okey] = code
                            st.session_state[bkey] = OUTCOME_BASES.get(code, 0)
                            st.session_state[oak]  = []
                            st.session_state.pop(f"dlg_fc_player_{ck}", None)
                            st.session_state.pop(f"dlg_fc_base_{ck}", None)
                        _disabled = (oc == "SF" and _dlg_outs >= 2)
                        cols[col_idx].button(
                            _BTN_LABEL[oc],
                            key=f"dlg_btn_{cell_key}_{oc}",
                            type="primary" if cur_code == oc else "secondary",
                            use_container_width=True, on_click=_pick_oc,
                            disabled=_disabled,
                        )

                outcome    = st.session_state.get(out_key)
                is_hr      = outcome in {"HR_OTF", "HR_ITP"}
                cur_bases  = st.session_state.get(bases_key, 0)
                is_out_oc  = outcome in OUT_WEIGHTS or outcome == "SF"
                cur_out_at = st.session_state.get(outat_key, [])
                is_fc_dp   = outcome in {"FC", "DP"}

                # ── Base advancement diamond ───────────────────────────────────────
                st.markdown(_diamond_svg(cur_bases, out_at=cur_out_at), unsafe_allow_html=True)
                if outcome and not is_hr and not is_out_oc:
                    bc1, bc2, bc3, bc4 = st.columns(4)
                    for col, bval, blbl in [
                        (bc1, 1, "1st"), (bc2, 2, "2nd"),
                        (bc3, 3, "3rd"), (bc4, 4, "Scored"),
                    ]:
                        def _set_base(v=bval, bk=bases_key,
                                      rk=f"dlg_run_{cell_key}"):
                            st.session_state[bk] = v
                            if v >= 4:
                                st.session_state[rk] = True
                        col.button(
                            blbl, key=f"base_{cell_key}_{bval}",
                            type="primary" if cur_bases == bval else "secondary",
                            use_container_width=True, on_click=_set_base,
                        )

                # ── Runner thrown out (FC / hits) or DP runner out ────────────────
                _runner_out_oc = outcome in {"FC", "1B", "2B", "3B"}
                if is_fc_dp or _runner_out_oc:
                    if _runner_out_oc:
                        fc_player_key = f"dlg_fc_player_{cell_key}"
                        fc_base_key   = f"dlg_fc_base_{cell_key}"
                        if fc_player_key not in st.session_state:
                            st.session_state[fc_player_key] = (existing.get("fc_out_player", "")
                                                                if existing else "")
                        if fc_base_key not in st.session_state:
                            st.session_state[fc_base_key] = (existing.get("fc_out_at", 0)
                                                              if existing else 0)
                        _others = [p for p in lineup_order if p != sel_player]
                        st.markdown(
                            "<div style='font-size:12px;opacity:0.6;margin-top:8px'>"
                            "Runner thrown out:</div>",
                            unsafe_allow_html=True)
                        _fp_opts = ["— pick runner —"] + _others
                        _cur_fp  = st.session_state.get(fc_player_key, "")
                        _fp_idx  = _fp_opts.index(_cur_fp) if _cur_fp in _fp_opts else 0
                        def _set_fc_player(pk=fc_player_key, ck=cell_key):
                            sel = st.session_state.get(f"_fc_psel_{ck}", "")
                            st.session_state[pk] = sel if sel != "— pick runner —" else ""
                        st.selectbox("", _fp_opts, index=_fp_idx,
                                     key=f"_fc_psel_{cell_key}",
                                     label_visibility="collapsed",
                                     on_change=_set_fc_player)
                        # FC: runner must be ahead of batter. Hits: any base.
                        _valid_fb = [(bval, blbl) for bval, blbl in
                                     [(1,"1st"),(2,"2nd"),(3,"3rd"),(4,"Home")]
                                     if outcome != "FC" or bval > cur_bases]
                        if _valid_fb:
                            st.markdown(
                                "<div style='font-size:12px;opacity:0.6;margin-top:6px'>"
                                "Out at:</div>",
                                unsafe_allow_html=True)
                            cur_fc_base = st.session_state.get(fc_base_key, 0)
                            _fbc = st.columns(len(_valid_fb))
                            for col, (bval, blbl) in zip(_fbc, _valid_fb):
                                def _set_fc_base(v=bval, bk=fc_base_key):
                                    st.session_state[bk] = v
                                col.button(blbl, key=f"fcbase_{cell_key}_{bval}",
                                           type="primary" if cur_fc_base == bval else "secondary",
                                           use_container_width=True, on_click=_set_fc_base)
                    else:  # DP
                        st.markdown(
                            "<div style='font-size:12px;opacity:0.6;margin-top:8px'>"
                            "Runner out at:</div>",
                            unsafe_allow_html=True)
                        _oa_cols = st.columns(4)
                        for col, (bval, blbl) in zip(_oa_cols,
                                                     [(1,"1st"),(2,"2nd"),(3,"3rd"),(4,"Home")]):
                            def _tog_out(v=bval, oak=outat_key):
                                cur = list(st.session_state.get(oak, []))
                                if v in cur: cur.remove(v)
                                else: cur.append(v)
                                st.session_state[oak] = cur
                            col.button(blbl, key=f"outat_{cell_key}_{bval}",
                                       type="primary" if bval in cur_out_at else "secondary",
                                       use_container_width=True, on_click=_tog_out)

                # ── Batter thrown out extending the hit ───────────────────────
                if outcome in {"1B", "2B", "3B"}:
                    _bout_key      = f"dlg_bout_{cell_key}"
                    _bout_base_key = f"dlg_bout_base_{cell_key}"
                    if _bout_key not in st.session_state:
                        st.session_state[_bout_key] = bool(existing.get("batter_out_at", 0)) if existing else False
                    if _bout_base_key not in st.session_state:
                        st.session_state[_bout_base_key] = existing.get("batter_out_at", 0) if existing else 0
                    _batter_thrown_out = st.checkbox(
                        "Batter thrown out extending?", key=_bout_key)
                    if _batter_thrown_out:
                        _valid_ext = [(bval, blbl) for bval, blbl in
                                      [(1,"1st"),(2,"2nd"),(3,"3rd"),(4,"Home")]
                                      if bval > cur_bases]
                        if _valid_ext:
                            st.markdown(
                                "<div style='font-size:12px;opacity:0.6;margin-top:4px'>"
                                "Out at:</div>", unsafe_allow_html=True)
                            cur_bout = st.session_state.get(_bout_base_key, 0)
                            _ext_cols = st.columns(len(_valid_ext))
                            for _ec, (_bv, _bl) in zip(_ext_cols, _valid_ext):
                                def _set_bout(v=_bv, bk=_bout_base_key):
                                    st.session_state[bk] = v
                                _ec.button(_bl, key=f"bout_{cell_key}_{_bv}",
                                           type="primary" if cur_bout == _bv else "secondary",
                                           use_container_width=True, on_click=_set_bout)

                st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)

                if is_hr:
                    hr_rbi_key = f"hr_rbi_{cell_key}"
                    if hr_rbi_key not in st.session_state:
                        st.session_state[hr_rbi_key] = existing.get("rbi", 1) if existing else 1
                    st.markdown("**Runs scored on this HR:**")
                    hr_cols = st.columns(4)
                    for rv, rl in [(1,"Solo"),(2,"2-Run"),(3,"3-Run"),(4,"Grand Slam")]:
                        def _pick_hr_rbi(v=rv, k=hr_rbi_key):
                            st.session_state[k] = v
                        hr_cols[rv - 1].button(
                            rl, key=f"hr_rbi_{cell_key}_{rv}",
                            type="primary" if st.session_state[hr_rbi_key] == rv else "secondary",
                            use_container_width=True, on_click=_pick_hr_rbi,
                        )
                    rbi = st.session_state[hr_rbi_key]
                    run_scored = True
                    st.markdown(
                        "<div style='font-size:12px;color:#4CAF50;margin-top:6px'>"
                        "● Run scored automatically</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    cr, cs2 = st.columns(2)
                    rbi = cr.number_input("RBIs", min_value=0, max_value=4,
                                          value=existing.get("rbi", 0) if existing else 0,
                                          step=1, key=f"dlg_rbi_{cell_key}")
                    _run_key = f"dlg_run_{cell_key}"
                    def _sync_run(bk=bases_key, ok=out_key, rk=_run_key):
                        if st.session_state.get(rk):
                            st.session_state[bk] = 4
                        else:
                            st.session_state[bk] = OUTCOME_BASES.get(
                                st.session_state.get(ok), 0
                            )
                    run_scored = cs2.checkbox(
                        "Run scored",
                        value=existing.get("run_scored", False) if existing else False,
                        key=_run_key,
                        on_change=_sync_run,
                    )

                cb1, cb2 = st.columns(2)
                if cb1.button("✓  Save", type="primary", use_container_width=True,
                              key=f"dlg_save_{cell_key}"):
                    if not outcome:
                        st.warning("Select an outcome first.")
                    else:
                        # Edit: remove only the specific PA being replaced
                        if existing:
                            g["plate_appearances"] = [
                                p for p in g["plate_appearances"]
                                if p.get("pa_num") != existing["pa_num"]
                            ]
                        bases_reached_val  = st.session_state.get(bases_key, OUTCOME_BASES.get(outcome, 0))
                        run_scored_final   = bool(run_scored) or (bases_reached_val >= 4)
                        out_at_val         = st.session_state.get(outat_key, [])
                        fc_out_player_val  = st.session_state.get(f"dlg_fc_player_{cell_key}", "")
                        fc_out_at_val      = st.session_state.get(f"dlg_fc_base_{cell_key}", 0)
                        _bout_val = 0
                        if outcome in {"1B", "2B", "3B"} and st.session_state.get(f"dlg_bout_{cell_key}"):
                            _bout_val = st.session_state.get(f"dlg_bout_base_{cell_key}", 0)
                        new_num = max((p.get("pa_num", 0) for p in g["plate_appearances"]), default=0) + 1
                        g["plate_appearances"].append({
                            "pa_num": new_num, "inning": sel_inning,
                            "player": sel_player, "outcome": outcome,
                            "rbi": int(rbi), "run_scored": run_scored_final,
                            "bases_reached": bases_reached_val,
                            "out_at": out_at_val,
                            "fc_out_player": fc_out_player_val if outcome in {"FC","1B","2B","3B"} else "",
                            "fc_out_at":     fc_out_at_val     if outcome in {"FC","1B","2B","3B"} else 0,
                            "batter_out_at": _bout_val,
                        })
                        st.session_state.pop(out_key, None)
                        st.session_state.pop(bases_key, None)
                        st.session_state.pop(outat_key, None)
                        st.session_state.pop(f"dlg_fc_player_{cell_key}", None)
                        st.session_state.pop(f"dlg_fc_base_{cell_key}", None)
                        st.session_state.pop(f"dlg_bout_{cell_key}", None)
                        st.session_state.pop(f"dlg_bout_base_{cell_key}", None)
                        st.session_state["ss_sel"] = st.session_state["ss_edit_pa"] = None
                        st.rerun()

                if existing and cb2.button("✕  Clear", use_container_width=True,
                                           key=f"dlg_clear_{cell_key}"):
                    g["plate_appearances"] = [
                        p for p in g["plate_appearances"]
                        if p.get("pa_num") != existing["pa_num"]
                    ]
                    st.session_state.pop(out_key, None)
                    st.session_state["ss_sel"] = st.session_state["ss_edit_pa"] = None
                    st.rerun()

            # Open dialog if a cell is selected
            sel = st.session_state.get("ss_sel")
            if sel:
                sp, si = sel
                edit_pa      = st.session_state.get("ss_edit_pa")
                pa_cnt_in_inn = sum(1 for pa in pas
                                    if pa["player"] == sp and pa.get("inning") == si)
                _ab_dialog(sp, si, edit_pa, pa_cnt_in_inn)

            # ── Box score ──────────────────────────────────────────────────────────
            _max_inn  = max(
                [pa.get("inning", 1) for pa in pas] + [g.get("current_inning", 1)]
            )
            _all_inn  = list(range(1, max(_max_inn, 7) + 1))
            _inn_r    = {i: sum(1 for pa in pas
                                if pa.get("inning") == i and pa.get("run_scored"))
                         for i in _all_inn}
            _total_r  = sum(_inn_r.values())
            _total_h  = sum(1 for pa in pas if pa.get("outcome") in HIT_CODES)
            _total_e  = g.get("errors", 0)
            _opp_name = g.get("opponent", "Opp")
            g.setdefault("opp_innings", {})

            _is_home = g.get("home_away", "Away") == "Home"

            # ── Box score HTML table ───────────────────────────────────────────────
            _td  = "border-right:1px solid rgba(255,255,255,0.10);padding:5px 4px;text-align:center;"
            _td_cur = ("border-right:1px solid rgba(255,20,147,0.45);"
                       "border-left:1px solid rgba(255,20,147,0.45);"
                       "background:rgba(255,20,147,0.13);padding:5px 4px;text-align:center;")
            _td_rhe = "padding:5px 6px;text-align:center;border-left:1px solid rgba(255,255,255,0.14);"
            _row_sep = "border-top:1px solid rgba(255,255,255,0.08);"

            # Header row
            _hdr_inn = ""
            for _inn in _all_inn:
                if _inn == cur_inn:
                    _hdr_inn += (f"<th style='{_td_cur}font-size:15px;font-weight:800;"
                                 f"color:#FF1493;letter-spacing:0.5px'>{_inn}</th>")
                else:
                    _hdr_inn += (f"<th style='{_td}font-size:11px;font-weight:600;"
                                 f"opacity:0.45'>{_inn}</th>")
            _hdr = (f"<tr style='border-bottom:1px solid rgba(255,255,255,0.12)'>"
                    f"<th style='text-align:left;padding:5px 8px;font-size:11px;"
                    f"opacity:0.4;font-weight:600'>Team</th>"
                    f"{_hdr_inn}"
                    f"<th style='{_td_rhe}font-size:11px;opacity:0.45;font-weight:600'>R</th>"
                    f"<th style='{_td_rhe}font-size:11px;opacity:0.45;font-weight:600'>H</th>"
                    f"<th style='{_td_rhe}font-size:11px;opacity:0.45;font-weight:600'>E</th>"
                    f"</tr>")

            # Our team row
            _our_inn = ""
            for _inn in _all_inn:
                _v  = _inn_r[_inn]
                _st = _td_cur if _inn == cur_inn else _td
                _cl = "color:#FF1493;" if _v else ""
                _our_inn += f"<td style='{_st}font-weight:700;{_cl}'>{_v}</td>"
            _our_row = (f"<tr style='{_row_sep}'>"
                        f"<td style='text-align:left;padding:5px 8px;font-size:13px;"
                        f"font-weight:700;color:#FF1493'>{active_team_name}</td>"
                        f"{_our_inn}"
                        f"<td style='{_td_rhe}font-weight:700;color:#FF1493'>{_total_r}</td>"
                        f"<td style='{_td_rhe}font-weight:700'>{_total_h}</td>"
                        f"<td style='{_td_rhe}font-weight:700'>{_total_e}</td>"
                        f"</tr>")

            # Opp row (display only — input handled below)
            _opp_inn_total = 0
            _opp_inn_cells = ""
            for _inn in _all_inn:
                _stored = g["opp_innings"].get(str(_inn), 0)
                _st = _td_cur if _inn == cur_inn else _td
                if _inn < cur_inn:
                    _opp_inn_cells += f"<td style='{_st}font-weight:700'>{_stored}</td>"
                    _opp_inn_total += _stored
                elif _inn == cur_inn:
                    _opp_inn_cells += (f"<td style='{_st}font-weight:700;"
                                       f"color:#FF1493'>{_stored if _stored else '—'}</td>")
                    _opp_inn_total += _stored
                else:
                    _opp_inn_cells += f"<td style='{_st}opacity:0.3'>-</td>"
            _opp_row = (f"<tr style='{_row_sep}'>"
                        f"<td style='text-align:left;padding:5px 8px;font-size:13px;"
                        f"font-weight:700;opacity:0.65'>{_opp_name}</td>"
                        f"{_opp_inn_cells}"
                        f"<td style='{_td_rhe}font-weight:700'>{_opp_inn_total}</td>"
                        f"<td style='{_td_rhe}opacity:0.3'>-</td>"
                        f"<td style='{_td_rhe}opacity:0.3'>-</td>"
                        f"</tr>")

            _body_rows = (_opp_row + _our_row) if _is_home else (_our_row + _opp_row)
            st.markdown(
                f"<table style='width:100%;border-collapse:collapse;font-size:13px;"
                f"border:1px solid rgba(255,255,255,0.10);border-radius:8px;"
                f"overflow:hidden;margin-bottom:6px'>"
                f"<thead>{_hdr}</thead>"
                f"<tbody>{_body_rows}</tbody>"
                f"</table>",
                unsafe_allow_html=True,
            )

            # Opp current-inning runs input
            _stored_cur = g["opp_innings"].get(str(cur_inn), 0)
            _inp_c, _ = st.columns([1, 3])
            _raw = _inp_c.text_input(
                f"{_opp_name} — inn. {cur_inn}",
                value=str(_stored_cur) if _stored_cur else "",
                placeholder="0",
                key=f"opp_inn_{g['game_id']}_{cur_inn}",
            )
            try:
                _nv = max(0, int(_raw)) if _raw.strip() else 0
            except ValueError:
                _nv = _stored_cur
            if _nv != _stored_cur:
                g["opp_innings"][str(cur_inn)] = _nv
                _opp_inn_total = _opp_inn_total - _stored_cur + _nv

            g["opp_runs"]  = _opp_inn_total
            g["team_runs"] = _total_r
            if _total_r > _opp_inn_total:
                g["result"] = "W"
            elif _total_r < _opp_inn_total:
                g["result"] = "L"
            else:
                g["result"] = "T"

            st.markdown(
                "<hr style='margin:6px 0 10px;border-color:rgba(255,20,147,0.15)'>",
                unsafe_allow_html=True)

            # ── Inning situation summary ───────────────────────────────────────────
            outs_this_inn = sum(
                (1 if pa.get("outcome") == "FC"
                 or (pa.get("outcome") in HIT_CODES and pa.get("fc_out_player"))
                 or (pa.get("outcome") in HIT_CODES and pa.get("batter_out_at"))
                 else OUT_WEIGHTS.get(pa.get("outcome"), 0))
                for pa in pas if pa.get("inning") == cur_inn
            )
            _cur_inn_runs = _inn_r.get(cur_inn, 0)

            # Approximate who is on base: replay PAs in order, track player→base
            _runners_on = {}
            for _rpa in sorted([p for p in pas if p.get("inning") == cur_inn],
                                key=lambda p: p.get("pa_num", 0)):
                _rpl = _rpa.get("player")
                _rbr = _rpa.get("bases_reached", 0)
                _roc = _rpa.get("outcome", "")
                if _roc not in OUT_WEIGHTS and _roc != "SF":
                    if (1 <= _rbr <= 3
                            and not _rpa.get("run_scored")
                            and not _rpa.get("batter_out_at")):
                        _runners_on[_rpl] = _rbr
                    else:
                        _runners_on.pop(_rpl, None)
                tout = _rpa.get("fc_out_player")
                if tout:
                    _runners_on.pop(tout, None)

            _out_circles = "".join(
                f"<span style='color:#e03030;font-size:17px'>●</span>" if i < outs_this_inn
                else f"<span style='opacity:0.18;font-size:17px'>●</span>"
                for i in range(3)
            )
            _out_lbl = f"{outs_this_inn} out{'s' if outs_this_inn != 1 else ''}"

            _base_names = {1: "1st", 2: "2nd", 3: "3rd"}
            if _runners_on:
                _runner_chips = " ".join(
                    f"<span style='background:rgba(255,200,50,0.14);"
                    f"border:1px solid rgba(255,200,50,0.3);padding:2px 8px;"
                    f"border-radius:6px;font-size:12px;white-space:nowrap'>"
                    f"{p.split()[0]} @{_base_names[b]}</span>"
                    for p, b in sorted(_runners_on.items(), key=lambda x: -x[1])
                )
            else:
                _runner_chips = "<span style='opacity:0.3;font-size:12px'>bases empty</span>"

            # Warn if two runners share a base
            _base_counts = {}
            for _p, _b in _runners_on.items():
                _base_counts.setdefault(_b, []).append(_p.split()[0])
            _collisions = [
                f"{' & '.join(names)} both on {_base_names[base]}"
                for base, names in _base_counts.items() if len(names) > 1
            ]
            if _collisions:
                st.warning("Base conflict: " + " · ".join(_collisions))

            # Warn if a runner may not have been advanced after a subsequent hit
            _inn_pas_ordered = sorted(
                [p for p in pas if p.get("inning") == cur_inn],
                key=lambda p: p.get("pa_num", 0),
            )
            _force_warns = []
            for _rpl, _rbase in _runners_on.items():
                # Find this runner's most recent PA in the inning
                _rpl_pa = next(
                    (p for p in reversed(_inn_pas_ordered) if p.get("player") == _rpl), None
                )
                if not _rpl_pa:
                    continue
                _rpl_panum = _rpl_pa.get("pa_num", 0)
                # Check every subsequent batter who reached a base >= this runner's base
                for _npa in _inn_pas_ordered:
                    if _npa.get("pa_num") <= _rpl_panum:
                        continue
                    _noc = _npa.get("outcome", "")
                    _nbr = _npa.get("bases_reached", 0)
                    if _noc in OUT_WEIGHTS or _noc == "SF":
                        continue
                    if _nbr >= _rbase:
                        _force_warns.append(
                            f"{_rpl.split()[0]} still at {_base_names[_rbase]} "
                            f"after {_npa['player'].split()[0]}'s "
                            f"{CELL_SHORT.get(_noc, _noc)}"
                        )
                        break
            if _force_warns:
                st.warning("Runner may not have advanced: " + " · ".join(_force_warns))

            st.markdown(
                f"<div style='background:rgba(255,255,255,0.04);"
                f"border:1px solid rgba(255,255,255,0.07);border-radius:10px;"
                f"padding:9px 14px;margin-bottom:10px;"
                f"display:flex;gap:18px;align-items:center;flex-wrap:wrap'>"
                f"<div style='display:flex;gap:3px;align-items:center'>"
                f"{_out_circles}"
                f"<span style='font-size:11px;opacity:0.5;margin-left:5px'>{_out_lbl}</span>"
                f"</div>"
                f"<div style='flex:1'>{_runner_chips}</div>"
                f"<div><span style='font-size:20px;font-weight:800;color:#FF1493'>"
                f"{_cur_inn_runs}</span>"
                f"<span style='font-size:11px;opacity:0.45'> R this inning</span></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # ── Inning navigation ──────────────────────────────────────────────────
            inn_ab_count = sum(1 for pa in pas if pa.get("inning") == cur_inn)
            nav_prev, nav_mid, nav_next = st.columns([1, 5, 2])
            if nav_prev.button("◀", key="inn_prev", disabled=(cur_inn <= 1)):
                st.session_state.lg_current_inning -= 1
                st.rerun()
            nav_mid.markdown(
                f"<div style='text-align:center;padding:6px 0'>"
                f"<span style='font-size:22px;font-weight:800'>Inning {cur_inn}</span>"
                f"<span style='opacity:0.4;font-size:13px;margin-left:10px'>{inn_ab_count} AB</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if nav_next.button("▶ Next inn.", key="inn_next", type="primary"):
                st.session_state.lg_current_inning += 1
                g["current_inning"] = max(g.get("current_inning", 1),
                                          st.session_state.lg_current_inning)
                st.rerun()

            # ── 3-outs prompt ──────────────────────────────────────────────────────
            if outs_this_inn >= 3:
                inn_runs   = sum(1 for pa in pas
                                 if pa.get("inning") == cur_inn and pa.get("run_scored"))
                total_runs = sum(1 for pa in g["plate_appearances"] if pa.get("run_scored"))
                run_detail = (f"  ·  {inn_runs} run{'s' if inn_runs != 1 else ''} this inning"
                              f"  ·  {total_runs} total")
                pc, bc = st.columns([3, 1])
                pc.success(f"3 outs — inning {cur_inn} over{run_detail}")
                if bc.button(f"→ Inning {cur_inn + 1}", key="three_outs_next", type="primary"):
                    st.session_state.lg_current_inning = cur_inn + 1
                    g["current_inning"] = max(g.get("current_inning", 1), cur_inn + 1)
                    st.rerun()

            st.markdown(
                "<div style='text-align:right;font-size:11px;opacity:0.4;margin:2px 0 4px'>"
                "<span style='color:#FF1493'>●</span> = leads off this inning</div>",
                unsafe_allow_html=True,
            )
            st.markdown("<hr style='margin:2px 0 10px;border-color:rgba(255,20,147,0.2)'>",
                        unsafe_allow_html=True)

            # ── Previous inning recap strip ────────────────────────────────────────
            if cur_inn > 1:
                prev_inn     = cur_inn - 1
                all_prev_pas = sorted(
                    [pa for pa in pas if pa.get("inning") == prev_inn],
                    key=lambda p: p.get("pa_num", 0),
                )
                prev_pas = all_prev_pas[-3:]  # last 3 ABs only
                if prev_pas:
                    prev_runs = sum(1 for pa in all_prev_pas if pa.get("run_scored"))
                    chip_parts = []
                    for pa in prev_pas:
                        lbl   = CELL_SHORT.get(pa["outcome"], pa["outcome"])
                        pname = pa["player"].split()[0]
                        if pa.get("rbi"):        lbl += f"+{pa['rbi']}"
                        if pa.get("run_scored"): lbl += " RS"
                        cat = ("hit" if pa["outcome"] in HIT_CODES
                               else "out" if pa["outcome"] in OUT_WEIGHTS else "base")
                        fg_bg = {
                            "hit":  ("#8ee89a", "rgba(50,205,80,0.12)",  "rgba(50,205,80,0.35)"),
                            "out":  ("#f09898", "rgba(220,60,60,0.10)",  "rgba(220,60,60,0.30)"),
                            "base": ("#88bbf0", "rgba(60,140,220,0.10)", "rgba(60,140,220,0.30)"),
                        }
                        fg, bg, border = (
                            ("#b0f5b0", "rgba(50,205,80,0.25)", "rgba(50,205,80,0.6)")
                            if pa.get("run_scored") else fg_bg[cat]
                        )
                        chip_parts.append(
                            f"<span style='white-space:nowrap;margin-right:8px'>"
                            f"<span style='font-size:11px;opacity:0.5;margin-right:3px'>{pname}</span>"
                            f"<span style='background:{bg};color:{fg};border:1px solid {border};"
                            f"border-radius:99px;padding:1px 8px;font-size:12px;font-weight:700'>"
                            f"{lbl}</span></span>"
                        )

                    run_txt = f"{prev_runs} run{'s' if prev_runs != 1 else ''}"
                    ab_txt  = f"{len(all_prev_pas)} AB"
                    st.markdown(
                        f"<div style='background:rgba(255,255,255,0.04);"
                        f"border:1px solid rgba(255,255,255,0.1);"
                        f"border-radius:8px;padding:8px 12px;margin-bottom:10px'>"
                        f"<div style='font-size:11px;font-weight:700;text-transform:uppercase;"
                        f"letter-spacing:.5px;opacity:0.4;margin-bottom:6px'>"
                        f"← Inning {prev_inn} · {run_txt} · {ab_txt}</div>"
                        f"<div style='display:flex;flex-wrap:wrap;align-items:center;line-height:2.4'>"
                        f"{''.join(chip_parts)}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            # ── Player rows ────────────────────────────────────────────────────────
            inning_full  = outs_this_inn >= 3

            # Find who leads off this inning (use the lineup from the inning the last AB occurred in)
            leadoff_this_inn = None
            if lineup_order:
                prior_sorted = sorted(
                    [pa for pa in pas if pa.get("inning", 0) < cur_inn],
                    key=lambda p: (p.get("inning", 0), p.get("pa_num", 0)),
                )
                if prior_sorted:
                    last_pa      = prior_sorted[-1]
                    last_inn_lu  = _active_lineup_at(
                        g["lineup"], g["substitutions"], last_pa.get("inning", 1)
                    )
                    try:
                        last_slot = last_inn_lu.index(last_pa["player"]) + 1
                    except ValueError:
                        last_slot = 1
                    nxt_slot = (last_slot % len(lineup_order)) + 1
                else:
                    nxt_slot = 1
                if 1 <= nxt_slot <= len(lineup_order):
                    leadoff_this_inn = lineup_order[nxt_slot - 1]

            all_scoresheet_players = lineup_order + [p for p in bench_ab if p not in lineup_order]

            # Runners thrown out this inning (FC or runner thrown out on a hit)
            _fc_outs_inn = {}
            for _fpa in pas:
                if (_fpa.get("inning") == cur_inn
                        and _fpa.get("fc_out_player")
                        and _fpa.get("fc_out_at")):
                    _fc_outs_inn[_fpa["fc_out_player"]] = _fpa["fc_out_at"]

            _bn_lbl = {1: "1st", 2: "2nd", 3: "3rd", 4: "Home"}
            _circ   = {1: "①", 2: "②", 3: "③"}

            # Map pa_num → first out number it accounts for in this inning
            _out_nums = {}
            _out_run  = 0
            for _pa in sorted([p for p in pas if p.get("inning") == cur_inn],
                               key=lambda p: p.get("pa_num", 0)):
                _oc = _pa.get("outcome", "")
                _w  = (1 if _oc == "FC"
                       or (_oc in HIT_CODES and _pa.get("fc_out_player"))
                       or (_oc in HIT_CODES and _pa.get("batter_out_at"))
                       else OUT_WEIGHTS.get(_oc, 0))
                if _w > 0:
                    _out_nums[_pa.get("pa_num")] = _out_run + 1
                    _out_run += _w

            for player in all_scoresheet_players:
                on_bench = player in bench_ab and player not in lineup_order
                player_inn_pas = sorted(
                    [pa for pa in pas
                     if pa["player"] == player and pa.get("inning") == cur_inn],
                    key=lambda p: p.get("pa_num", 0),
                )
                has_scored = any(pa.get("run_scored") for pa in player_inn_pas)

                n_chips  = min(len(player_inn_pas), 3)
                overflow = len(player_inn_pas) > 3
                col_ws   = [2.5] + [1.1] * n_chips
                if overflow:   col_ws += [0.55]
                col_ws += [0.7]
                if g.get("live_mode"): col_ws += [0.7]
                row = st.columns(col_ws)

                name_color  = ("#4CAF50" if has_scored
                               else "rgba(255,255,255,0.42)" if on_bench else "inherit")
                ord_lbl     = str(order_map.get(player, "")) if not on_bench else "·"
                dot         = (" <span style='color:#FF1493;font-size:10px;vertical-align:middle'>●</span>"
                               if player == leadoff_this_inn else "")
                subbed_in   = {sub["in"] for sub in g["substitutions"]}
                italic_style = "font-style:italic;" if player in subbed_in else ""
                _fc_out_base = _fc_outs_inn.get(player)
                _fc_pa_num   = next((p.get("pa_num") for p in pas
                                     if p.get("inning") == cur_inn
                                     and p.get("fc_out_player") == player), None)
                _fc_out_num  = _out_nums.get(_fc_pa_num)
                _fc_out_circ = _circ.get(_fc_out_num, "") if _fc_out_num else ""
                _fc_ann      = (f"<div style='font-size:9px;color:#e03030;margin-top:1px'>"
                                f"✕ {_fc_out_circ} out at {_bn_lbl.get(_fc_out_base,'?')}</div>"
                                if _fc_out_base else "")
                row[0].markdown(
                    f"<div style='padding:7px 0;font-weight:{'400' if on_bench else '600'};"
                    f"{italic_style}font-size:16px;color:{name_color}'>"
                    f"<span style='opacity:0.55;font-size:13px;margin-right:6px'>{ord_lbl}</span>"
                    f"{player}{dot}</div>{_fc_ann}",
                    unsafe_allow_html=True,
                )

                ci = 1
                _n_chips_shown = min(len(player_inn_pas), 3)
                for ei, pa in enumerate(player_inn_pas[:3]):
                    lbl     = CELL_SHORT.get(pa["outcome"], pa["outcome"])
                    if pa.get("run_scored"): lbl += " RS"
                    _br      = pa.get("bases_reached",
                                      OUTCOME_BASES.get(pa.get("outcome", "OUT"), 0))
                    _batter_oa = pa.get("batter_out_at", 0)
                    _is_out  = (pa.get("outcome") in OUT_WEIGHTS
                                or pa.get("outcome") == "SF"
                                or bool(_batter_oa))
                    _out_n   = _out_nums.get(pa.get("pa_num"))
                    if _is_out and _out_n:
                        _oc_w = OUT_WEIGHTS.get(pa.get("outcome"), 1)
                        lbl += "".join(_circ.get(_out_n + i, str(_out_n + i))
                                       for i in range(_oc_w))
                    # On the last chip: if this player was thrown out on an FC, show the red X
                    _is_last = (ei == _n_chips_shown - 1)
                    def _edit_chip(p=player, i=cur_inn, pa=pa):
                        st.session_state["ss_sel"]     = (p, i)
                        st.session_state["ss_edit_pa"] = pa
                    with row[ci]:
                        st.button(lbl, key=f"chip_{player}_{cur_inn}_{ei}",
                                  use_container_width=True, on_click=_edit_chip)
                        if pa.get("outcome") == "FC":
                            _chip_out_at = []
                            _disp_br = _br
                        elif _batter_oa:
                            _chip_out_at = [_batter_oa]
                            _disp_br = _batter_oa
                        elif _is_last and _fc_out_base and _br > 0:
                            _chip_out_at = [_fc_out_base]
                            _disp_br = _fc_out_base
                        else:
                            _chip_out_at = pa.get("out_at", [])
                            _disp_br = _br
                        st.markdown(_mini_diamond_svg(_disp_br, out_at=_chip_out_at),
                                    unsafe_allow_html=True)
                        if pa.get("run_scored"):
                            st.markdown(
                                "<div style='font-size:9px;text-align:center;"
                                "color:#50cd78;margin-top:-2px'>RS</div>",
                                unsafe_allow_html=True)
                        if pa.get("rbi"):
                            st.markdown(
                                f"<div style='font-size:9px;text-align:center;"
                                f"color:#f0c040;margin-top:-2px'>+{pa['rbi']} RBI</div>",
                                unsafe_allow_html=True)
                        if pa.get("fc_out_player") and pa.get("fc_out_at"):
                            _bn = {1:"1st",2:"2nd",3:"3rd",4:"H"}
                            st.markdown(
                                f"<div style='font-size:9px;opacity:0.55;text-align:center;"
                                f"color:#e03030'>✕ {pa['fc_out_player'].split()[0]}"
                                f"→{_bn.get(pa['fc_out_at'],'?')}</div>",
                                unsafe_allow_html=True)
                        if not _is_out:
                            _opts = ["1B", "2B", "3B", "H"]
                            _cv   = _opts[_br - 1] if 1 <= _br <= 4 else None
                            _pk   = f"qbp_{player}_{cur_inn}_{ei}_{_br}"
                            def _save_qb(pn=pa.get("pa_num"), pk=_pk):
                                sel = st.session_state.get(pk)
                                bv  = {"1B": 1, "2B": 2, "3B": 3, "H": 4}.get(sel, 0)
                                for _pa in g["plate_appearances"]:
                                    if _pa.get("pa_num") == pn:
                                        _pa["bases_reached"] = bv
                                        if bv >= 4:
                                            _pa["run_scored"] = True
                                        break
                            st.pills("", _opts, default=_cv, key=_pk,
                                     label_visibility="collapsed",
                                     on_change=_save_qb)
                    ci += 1

                if overflow:
                    row[ci].markdown(
                        f"<div style='padding:8px 0;text-align:center;opacity:0.4;font-size:11px'>"
                        f"+{len(player_inn_pas)-3}</div>",
                        unsafe_allow_html=True,
                    )
                    ci += 1

                def _new_pa(p=player, i=cur_inn):
                    st.session_state["ss_sel"]     = (p, i)
                    st.session_state["ss_edit_pa"] = None
                row[ci].button("+ AB", key=f"add_{player}_{cur_inn}",
                               use_container_width=True, on_click=_new_pa,
                               disabled=inning_full)
                ci += 1

                if g.get("live_mode"):
                    def _toggle_run(p=player, i=cur_inn):
                        paps = sorted(
                            [pa for pa in g["plate_appearances"]
                             if pa["player"] == p and pa.get("inning") == i],
                            key=lambda x: x.get("pa_num", 0),
                        )
                        if paps:
                            new_val = not paps[-1].get("run_scored", False)
                            paps[-1]["run_scored"] = new_val
                            if new_val:
                                paps[-1]["bases_reached"] = 4
                            else:
                                paps[-1]["bases_reached"] = OUTCOME_BASES.get(
                                    paps[-1].get("outcome", "OUT"), 0
                                )
                    row[ci].button(
                        "Run Scored" if has_scored else "Run Scored",
                        key=f"run_{player}_{cur_inn}",
                        type="primary" if has_scored else "secondary",
                        use_container_width=True, on_click=_toggle_run,
                    )

            # ── Substitution form ──────────────────────────────────────────────────
            st.markdown(
                "<hr style='margin:16px 0 10px;border-color:rgba(255,255,255,0.08)'>",
                unsafe_allow_html=True,
            )
            with st.expander("🔄 Sub / lineup change"):
                st.caption("Re-entry is allowed — the original player can come back in later.")
                _cur_active, _cur_bench = _active_bench_at(
                    g["lineup"], g.get("bench_players", []), g["substitutions"]
                )
                out_opts = sorted(_cur_active) if _cur_active else player_names
                in_opts  = sorted(_cur_bench)  if _cur_bench  else player_names
                with st.form("add_sub"):
                    cs1, cs2, cs3 = st.columns(3)
                    out_p   = cs1.selectbox("Out", out_opts)
                    in_p    = cs2.selectbox("In",  in_opts)
                    sub_inn = cs3.number_input("Inning", min_value=1,
                                               value=cur_inn, step=1)
                    if st.form_submit_button("Log Sub"):
                        if out_p == in_p:
                            st.error("In and Out must be different.")
                        else:
                            g["substitutions"].append(
                                {"out": out_p, "in": in_p, "inning": int(sub_inn)}
                            )
                            if in_p not in lineup_order and in_p not in bench_ab:
                                g["bench_players"].append(in_p)
                            st.success(f"{in_p} in for {out_p} (inning {sub_inn})")
                            st.rerun()
                if g["substitutions"]:
                    for sub in g["substitutions"]:
                        st.markdown(f"- Inn {sub['inning']}: **{sub['in']}** in for **{sub['out']}**")

        # ── Tab 3: Review & Save ──────────────────────────────────────────────────

        with tab_sv:
            pas = g["plate_appearances"]
            if pas:
                st.markdown("**Per-player summary:**")
                summary = []
                for player in sorted({pa["player"] for pa in pas}):
                    ppas = [pa for pa in pas if pa["player"] == player]
                    s = pas_to_stat_row(ppas, walks_as_hits)
                    h = s["1B"] + s["2B"] + s["3B"] + s["HR_OTF"] + s["HR_ITP"]
                    summary.append({
                        "Player": player, "PA": len(ppas), "AB": s["AB"],
                        "H": h, "HR": s["HR_OTF"] + s["HR_ITP"],
                        "BB": s["BB"], "SF": s["SF"], "R": s["R"], "RBI": s["RBI"], "K": s["K"],
                    })
                summary_df = pd.DataFrame(summary)
                num_cols = [c for c in ["PA","AB","H","HR","BB","SF","R","RBI","K"]
                            if c in summary_df.columns]
                totals_row = {"Player": "TOTAL",
                              **{c: int(summary_df[c].sum()) for c in num_cols}}
                summary_df = pd.concat([summary_df, pd.DataFrame([totals_row])],
                                       ignore_index=True)
                st.dataframe(summary_df, hide_index=True, use_container_width=True)
            else:
                st.info("No at-bats logged yet.")

            st.markdown("---")
            cs, cc = st.columns(2)
            if cs.button("💾 Save Game", type="primary"):
                editing_id = st.session_state.get("editing_game_id")
                if editing_id is not None:
                    games_data["games"] = [
                        g if x["game_id"] == editing_id else x
                        for x in games_data["games"]
                    ]
                    st.session_state.pop("editing_game_id", None)
                else:
                    games_data["games"].append(g)
                save_games_data(games_data, active_team_id)
                st.session_state.lg_game = None
                st.session_state.pop("lg_current_inning", None)
                st.success(f"Saved game vs {g['opponent']}!")
                st.balloons()
                st.rerun()
            if cc.button("🗑️ Discard"):
                st.session_state.pop("editing_game_id", None)
                st.session_state.pop("lg_current_inning", None)
                st.session_state.lg_game = None
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📋 History":
    st.markdown("## 📋 Game History")

    if not games:
        if active_tournament_id:
            st.info("No games in this tournament yet.")
        else:
            st.info("No games logged yet.")
    else:
        for g in reversed(games):
            rw = {"W": "Won", "L": "Lost", "T": "Tied"}.get(g.get("result"), "🔴 Live")
            g_tourn = next((t["name"] for t in tournaments if t["id"] == g.get("tournament_id", "")), "")
            tourn_tag = f"  [{g_tourn}]" if g_tourn else ""
            score_part = (f"{g.get('team_runs','?')}-{g.get('opp_runs','?')}"
                          if g.get("result") else "In progress")
            label = f'{g["date"]}  ·  {rw} {score_part}  vs  {g["opponent"]}  [{g.get("type","regular").title()}]{tourn_tag}'
            with st.expander(label):
                pas = g.get("plate_appearances", [])
                if pas:
                    rows = []
                    for player in sorted({pa["player"] for pa in pas}):
                        ppas = [pa for pa in pas if pa["player"] == player]
                        s = pas_to_stat_row(ppas, walks_as_hits)
                        h = s["1B"] + s["2B"] + s["3B"] + s["HR_OTF"] + s["HR_ITP"]
                        rows.append({
                            "Player": player, "AB": s["AB"], "H": h,
                            "HR": s["HR_OTF"] + s["HR_ITP"],
                            "BB": s["BB"], "R": s["R"], "RBI": s["RBI"], "K": s["K"],
                        })
                    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

                    if st.checkbox("Full PA log", key=f"pa_chk_{g['game_id']}"):
                        pa_rows = [{
                            "#": pa["pa_num"],
                            "Inn": pa.get("inning", ""),
                            "Player": pa["player"],
                            "Outcome": OUTCOME_DISPLAY.get(pa["outcome"], pa["outcome"]),
                            "RBI": pa["rbi"],
                            "Scored": "✓" if pa.get("run_scored") else "",
                        } for pa in pas]
                        st.dataframe(pd.DataFrame(pa_rows), hide_index=True, use_container_width=True)
                else:
                    st.caption("No plate appearances logged.")

                if g.get("substitutions"):
                    st.markdown("**Subs:**")
                    for sub in g["substitutions"]:
                        st.markdown(f"- Inning {sub['inning']}: **{sub['in']}** for {sub['out']}")

                ec, dc = st.columns(2)
                if ec.button("✏️ Edit game", key=f"edit_g_{g['game_id']}", use_container_width=True):
                    import copy
                    st.session_state.lg_game = copy.deepcopy(g)
                    st.session_state["editing_game_id"] = g["game_id"]
                    st.session_state["lg_current_inning"] = g.get("current_inning", 1)
                    st.session_state["_nav_idx"] = 2
                    st.rerun()
                if dc.button("🗑️ Delete game", key=f"del_g_{g['game_id']}", use_container_width=True):
                    games_data["games"] = [x for x in games_data["games"] if x["game_id"] != g["game_id"]]
                    save_games_data(games_data, active_team_id)
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "⚙️ Settings":
    st.markdown("## ⚙️ Settings")

    tab_teams, tab_tourns = st.tabs(["🏟️ Teams", "🏆 Tournaments"])

    with tab_teams:
        st.markdown("#### Teams")
        teams = config.get("teams", [])

        for i, team in enumerate(teams):
            game_count = len(_load(_games_file(team["id"]), {"games": []}).get("games", []))
            player_count = len(_load(_roster_file(team["id"]), {"players": []}).get("players", []))
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{team['name']}** · {player_count} player{'s' if player_count != 1 else ''} · {game_count} game{'s' if game_count != 1 else ''}")
            active_indicator = " ← active" if team["id"] == active_team_id else ""
            c1.caption(f"`{team['id']}`{active_indicator}")
            del_disabled = len(teams) <= 1 or team["id"] == active_team_id
            if c2.button("✕", key=f"del_team_{i}", disabled=del_disabled,
                         help="Switch to another team before deleting this one" if team["id"] == active_team_id else "Cannot delete the only team" if len(teams) <= 1 else ""):
                config["teams"].pop(i)
                save_config(config)
                st.rerun()

        st.markdown("---")
        st.markdown("#### Add New Team")
        with st.form("add_team"):
            new_team_name = st.text_input("Team name", placeholder="e.g. Outlaws")
            if st.form_submit_button("Create Team"):
                if not new_team_name.strip():
                    st.error("Name required.")
                else:
                    tid = _slug(new_team_name.strip(), {t["id"] for t in teams})
                    config["teams"].append({"id": tid, "name": new_team_name.strip()})
                    save_config(config)
                    save_roster({"players": []}, tid)
                    save_games_data({"tournaments": [], "games": []}, tid)
                    st.success(f"Team **{new_team_name.strip()}** created! Switch to it using the team selector in the sidebar.")
                    st.rerun()

    with tab_tourns:
        st.markdown(f"#### Tournaments — {active_team_name}")
        tourn_list = games_data.get("tournaments", [])

        if "editing_tourn" not in st.session_state:
            st.session_state.editing_tourn = None

        if tourn_list:
            for i, t in enumerate(tourn_list):
                game_count = sum(1 for g in all_games if g.get("tournament_id") == t["id"])
                if st.session_state.editing_tourn == i:
                    ec1, ec2, ec3, ec4 = st.columns([3, 1, 1, 1])
                    new_tname = ec1.text_input("Name", value=t["name"], key=f"ren_tname_{i}",
                                               label_visibility="collapsed")
                    new_tyear = ec2.text_input("Year", value=t.get("year", ""), key=f"ren_tyear_{i}",
                                               label_visibility="collapsed")
                    if ec3.button("Save", key=f"ren_tsave_{i}"):
                        if new_tname.strip():
                            tourn_list[i]["name"] = new_tname.strip()
                            tourn_list[i]["year"] = new_tyear.strip()
                            games_data["tournaments"] = tourn_list
                            save_games_data(games_data, active_team_id)
                            st.session_state.editing_tourn = None
                            st.rerun()
                    if ec4.button("Cancel", key=f"ren_tcancel_{i}"):
                        st.session_state.editing_tourn = None
                        st.rerun()
                else:
                    c1, c2, c3 = st.columns([4, 1, 1])
                    c1.markdown(f"**{t['name']}** · {t.get('year', '')} · {game_count} game{'s' if game_count != 1 else ''}")
                    if active_tournament_id == t["id"]:
                        c1.caption("← active filter")
                    if c2.button("✏️", key=f"ren_tourn_{i}", help="Rename"):
                        st.session_state.editing_tourn = i
                        st.rerun()
                    del_disabled = game_count > 0
                    if c3.button("✕", key=f"del_tourn_{i}", disabled=del_disabled,
                                 help="Remove all games from this tournament first"):
                        tourn_list.pop(i)
                        games_data["tournaments"] = tourn_list
                        save_games_data(games_data, active_team_id)
                        if active_tournament_id == t["id"]:
                            st.session_state.active_tournament_id = None
                        st.rerun()
        else:
            st.info("No tournaments yet.")

        st.markdown("---")
        st.markdown("#### Add Tournament")
        with st.form("add_tourn"):
            tc1, tc2 = st.columns(2)
            new_tourn_name = tc1.text_input("Name", placeholder="e.g. Summer 2026")
            new_tourn_year = tc2.text_input("Year", value=str(date.today().year))
            if st.form_submit_button("Add Tournament"):
                if not new_tourn_name.strip():
                    st.error("Name required.")
                else:
                    tid = _slug(new_tourn_name.strip(), {t["id"] for t in tourn_list})
                    tourn_list.append({
                        "id": tid,
                        "name": new_tourn_name.strip(),
                        "year": new_tourn_year.strip() or str(date.today().year),
                    })
                    games_data["tournaments"] = tourn_list
                    save_games_data(games_data, active_team_id)
                    st.success(f"Tournament **{new_tourn_name.strip()}** added!")
                    st.rerun()
