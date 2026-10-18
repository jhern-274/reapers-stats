"""Shareable player card: draws both sides of the My Stats card with Pillow and turns them
into a looping animation (front ~3 s, flip, back ~3 s, flip back) as a GIF or an MP4.

The look follows the .pcard CSS in app.py, drawn at 2x (a 300x420 CSS card -> 600x840 px).
"""
import io
import math
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

FONT_FILE = Path(__file__).parent / "assets" / "fonts" / "SourceSans3VF-Upright.woff2"

W, H = 600, 840              # card size
PAD = 40                     # margin around the card in the exported frame
FRAME_W, FRAME_H = W + 2 * PAD, H + 2 * PAD
BG = (22, 26, 36)            # frame background
PINK, PINK_LIGHT = (232, 120, 159), (240, 160, 188)
TEXT = (243, 240, 246)
HOLD_MS = 3000               # time on each side
FLIP_MS = 600                # time for one flip
FPS = 30                     # MP4 frame rate


# ── drawing helpers ───────────────────────────────────────────────────────────

@lru_cache(maxsize=64)
def _font(size: int, weight: int = 400):
    try:
        f = ImageFont.truetype(str(FONT_FILE), size)
        f.set_variation_by_axes([weight])
        return f
    except Exception:
        return ImageFont.load_default(size)


def _gradient(size, stops, angle_deg):
    """RGBA linear gradient. stops: [(pos 0..1, (r, g, b)), ...]; angle as in CSS (180 = top to bottom)."""
    w, h = size
    a = math.radians(angle_deg)
    dx, dy = math.sin(a), -math.cos(a)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    proj = (xs - w / 2) * dx + (ys - h / 2) * dy
    half = abs(w / 2 * dx) + abs(h / 2 * dy)
    t = np.clip((proj + half) / (2 * half), 0, 1)
    pos = [p for p, _ in stops]
    out = np.zeros((h, w, 4), np.uint8)
    for c in range(3):
        out[..., c] = np.interp(t, pos, [col[c] for _, col in stops]).astype(np.uint8)
    out[..., 3] = 255
    return Image.fromarray(out, "RGBA")


def _rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    return m


def _paste_rounded(base, img, xy, radius):
    base.paste(img, xy, _rounded_mask(img.size, radius))


def _overlay_rounded_rect(base, box, radius, fill=None, outline=None, width=1):
    """Translucent rounded rectangle composited onto base (fill/outline may carry alpha)."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(box, radius, fill=fill, outline=outline, width=width)
    base.alpha_composite(layer)


def _fit_text(text, font, max_w):
    """text, shortened with … so it fits max_w."""
    if font.getlength(text) <= max_w:
        return text
    while text and font.getlength(text + "…") > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def _spaced(draw, xy, text, font, fill, spacing):
    """Draw text with extra letter spacing (CSS letter-spacing). Returns the end x."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + spacing
    return x


def _spaced_len(text, font, spacing):
    return sum(font.getlength(ch) for ch in text) + spacing * max(len(text) - 1, 0)


def _runs(draw, xy, runs):
    """Draw [(text, font, fill), ...] one after another on a line."""
    x, y = xy
    for text, font, fill in runs:
        draw.text((x, y), text, font=font, fill=fill)
        x += font.getlength(text)


def _card_base():
    card = _gradient((W, H), [(0, (58, 39, 71)), (0.55, (30, 35, 48)), (1, (43, 29, 47))], 160)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _paste_rounded(out, card, (0, 0), 36)
    _overlay_rounded_rect(out, (6, 6, W - 7, H - 7), 30, outline=(255, 255, 255, 15), width=10)
    ImageDraw.Draw(out).rounded_rectangle((0, 0, W - 1, H - 1), 36, outline=PINK, width=6)
    return out


# ── the two sides ─────────────────────────────────────────────────────────────

def render_front(d: dict) -> Image.Image:
    card = _card_base()
    draw = ImageDraw.Draw(card, "RGBA")
    px0, py0, px1, py1 = 26, 26, W - 26, H - 26 - 164  # photo area
    pw, ph = px1 - px0, py1 - py0
    if d.get("photo") is not None:
        photo = ImageOps.fit(d["photo"].convert("RGB"), (pw, ph), Image.LANCZOS, centering=(0.5, 0.3))
        _paste_rounded(card, photo.convert("RGBA"), (px0, py0), 24)
    else:
        _overlay_rounded_rect(card, (px0, py0, px1, py1), 24, fill=(232, 120, 159, 30))
        initials = "".join(w[0] for w in d["name"].split()[:2]).upper()
        f = _font(184, 800)
        draw.text(((px0 + px1) / 2, (py0 + py1) / 2), initials, font=f, fill=PINK_LIGHT, anchor="mm")
    _overlay_rounded_rect(card, (px0, py0, px1, py1), 24, outline=(255, 255, 255, 30), width=2)

    if d.get("logo") is not None:
        logo = d["logo"].convert("RGBA")
        logo.thumbnail((180, 68), Image.LANCZOS)
        lx, ly = W - 42 - logo.width, 42
        shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
        shadow.paste((0, 0, 0, 150), (lx, ly + 4), logo.split()[3])
        card.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))
        card.alpha_composite(logo, (lx, ly))

    # nameplate
    bx0, by0, bx1, by1 = 26, H - 26 - 148, W - 26, H - 26
    _paste_rounded(card, _gradient((bx1 - bx0, by1 - by0), [(0, PINK), (1, (180, 95, 154))], 90), (bx0, by0), 24)
    draw = ImageDraw.Draw(card, "RGBA")
    num = d.get("number") or ""
    text_right = bx1 - 28
    if num:
        fn, fh = _font(80, 900), _font(40, 800)
        nw = fn.getlength(num)
        nx = bx1 - 28 - nw
        draw.text((nx, (by0 + by1) / 2 + 4), num, font=fn, fill=(255, 255, 255), anchor="lm")
        draw.text((nx - fh.getlength("#") - 2, (by0 + by1) / 2 - 18), "#", font=fh,
                  fill=(255, 255, 255, 205), anchor="lm")
        text_right = nx - fh.getlength("#") - 24
    fname = _font(48, 800)
    draw.text((bx0 + 28, by0 + 22), _fit_text(d["name"], fname, text_right - bx0 - 28), font=fname, fill=(255, 255, 255))
    meta = " · ".join(x for x in (d.get("positions", ""), d.get("team", "")) if x).upper()
    fmeta = _font(22, 700)
    while meta and _spaced_len(meta, fmeta, 2.4) > text_right - bx0 - 28:
        meta = meta[:-1]
    _spaced(draw, (bx0 + 28, by0 + 92), meta, fmeta, (255, 255, 255, 235), 2.4)
    return card


def render_back(d: dict) -> Image.Image:
    card = _card_base()
    draw = ImageDraw.Draw(card, "RGBA")
    x0, x1, y = 34, W - 34, 34

    # header: name left, "#21 · LF, C" right
    right = " · ".join(x for x in ((f"#{d['number']}" if d.get("number") else ""), d.get("positions", "")) if x)
    fpos, fname = _font(22, 700), _font(38, 800)
    rw = _spaced_len(right, fpos, 2) if right else 0
    draw.text((x0, y), _fit_text(d["name"], fname, x1 - x0 - rw - 20), font=fname, fill=TEXT)
    if right:
        _spaced(draw, (x1 - rw, y + 14), right, fpos, PINK_LIGHT, 2)
    y += 58
    draw.rectangle((x0, y, x1, y + 3), fill=PINK)
    y += 16
    fscope = _font(20, 400)
    _spaced(draw, (x0, y), d.get("scope", "").upper(), fscope, (243, 240, 246, 150), 2)
    y += 36

    # 3 x 4 stat grid
    gap, cols = 10, 3
    cw = (x1 - x0 - gap * (cols - 1)) / cols
    ch = 112 if any(c[2] for c in d["cells"]) else 92
    fk, fv, fr = _font(19, 700), _font(34, 800), _font(18, 600)
    for i, (k, v, rank, hi) in enumerate(d["cells"]):
        cx0 = x0 + (i % cols) * (cw + gap)
        cy0 = y + (i // cols) * (ch + gap)
        _overlay_rounded_rect(card, (cx0, cy0, cx0 + cw, cy0 + ch), 16,
                              fill=(255, 255, 255, 13), outline=(255, 255, 255, 20), width=2)
        mid = cx0 + cw / 2
        kw = _spaced_len(k, fk, 1.6)
        _spaced(draw, (mid - kw / 2, cy0 + 10), k, fk, (243, 240, 246, 155), 1.6)
        draw.text((mid, cy0 + 56), str(v), font=fv, fill=PINK_LIGHT if hi else TEXT, anchor="mm")
        if rank:
            top = rank.split(" of ")[0].lstrip("T-") == "1st"
            draw.text((mid, cy0 + 92), rank, font=fr, fill=PINK_LIGHT if top else (243, 240, 246, 180), anchor="mm")

    # footer, pinned to the bottom
    f, fb = _font(21, 400), _font(21, 700)
    lines = []
    sk = d["streaks"]
    lines.append([("Best hit streak: ", f, TEXT), (str(sk["games"]), fb, PINK_LIGHT), (" games · ", f, TEXT),
                  (str(sk["abs"]), fb, PINK_LIGHT), (" at-bats", f, TEXT)])
    if d.get("leads"):
        more = f" +{len(d['leads']) - 3} more" if len(d["leads"]) > 3 else ""
        lead_txt = _fit_text(", ".join(d["leads"][:3]), fb, x1 - x0 - f.getlength("Team leader: " + more))
        lines.append([("Team leader: ", f, TEXT), (lead_txt, fb, PINK_LIGHT), (more, f, TEXT)])
    if d.get("qual_note"):
        lines.append([(_fit_text(d["qual_note"], f, x1 - x0), f, (243, 240, 246, 150))])
    ly = H - 30 - 30 * len(lines)
    for ln in lines:
        _runs(draw, (x0, ly), ln)
        ly += 30
    return card


# ── animation ─────────────────────────────────────────────────────────────────

def _flip_frame(front, back, t):
    """Frame at flip progress t (0 = front, 1 = back): the card squeezes edge-on and opens on the other side."""
    ang = math.pi * (0.5 - 0.5 * math.cos(math.pi * t))  # eased 0..pi
    face = front if ang < math.pi / 2 else back
    sx = abs(math.cos(ang))
    lift = 1 + 0.05 * math.sin(ang)  # comes slightly toward the viewer mid-flip
    w, h = max(2, round(W * sx * lift)), round(H * lift)
    img = face.resize((w, h), Image.LANCZOS)
    shade = 0.35 * math.sin(ang)  # darker while edge-on
    if shade > 0.01:
        r, g, b, a = img.split()
        img = Image.merge("RGBA", [c.point(lambda v: round(v * (1 - shade))) for c in (r, g, b)] + [a])
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), BG + (255,))
    frame.alpha_composite(img, ((FRAME_W - w) // 2, (FRAME_H - h) // 2))
    return frame.convert("RGB")


def _still(face):
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), BG + (255,))
    frame.alpha_composite(face, (PAD, PAD))
    return frame.convert("RGB")


def _flip(a, b, n):
    return [_flip_frame(a, b, i / n) for i in range(1, n)]


def make_gif(front, back) -> bytes:
    """Looping GIF: front 3 s, flip, back 3 s, flip back."""
    n = 10
    step = FLIP_MS // n

    def q(img, dither):  # stills get full dithering; flip frames flash by, so plain colors keep the file small
        if dither:
            return img.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
        return img.quantize(colors=128, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)

    pal = ([q(_still(front), True)] + [q(f, False) for f in _flip(front, back, n)]
           + [q(_still(back), True)] + [q(f, False) for f in _flip(back, front, n)])
    durations = [HOLD_MS] + [step] * (n - 1) + [HOLD_MS] + [step] * (n - 1)
    buf = io.BytesIO()
    pal[0].save(buf, "GIF", save_all=True, append_images=pal[1:], duration=durations, loop=0, disposal=1)
    return buf.getvalue()


def _ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def make_mp4(front, back):
    """Same loop as an H.264 MP4 (sharper than a GIF; best for Instagram/WhatsApp status). None if ffmpeg is missing."""
    exe = _ffmpeg()
    if not exe:
        return None
    hold, n = HOLD_MS * FPS // 1000, FLIP_MS * FPS // 1000
    f_still, b_still = _still(front).tobytes(), _still(back).tobytes()
    with tempfile.TemporaryDirectory() as tmp:  # +faststart needs a seekable file, not a pipe
        out = Path(tmp) / "card.mp4"
        cmd = [exe, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{FRAME_W}x{FRAME_H}",
               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "veryfast",
               "-movflags", "+faststart", str(out)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:  # stream frame by frame: the whole clip as raw RGB would be ~400 MB
            for chunk in ([f_still] * hold + [f.tobytes() for f in _flip(front, back, n)]
                          + [b_still] * hold + [f.tobytes() for f in _flip(back, front, n)]):
                proc.stdin.write(chunk)
            proc.stdin.close()
            proc.wait(timeout=120)
        except Exception:
            proc.kill()
            return None
        return out.read_bytes() if proc.returncode == 0 and out.exists() else None
