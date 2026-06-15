
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
    "DP":     "Double Play",
    "SF":     "Sacrifice Fly",
}
HIT_CODES = {"1B", "2B", "3B", "HR_OTF", "HR_ITP"}

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

button[aria-label^='● ']
{ background-color:rgba(50,205,80,0.22)!important;
  border-color:rgba(50,205,80,0.55)!important; color:#7ee89a!important }
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
    wins   = sum(1 for g in games if g["result"] == "W")
    losses = sum(1 for g in games if g["result"] == "L")
    ties   = sum(1 for g in games if g["result"] == "T")
    rf     = sum(g["team_runs"] for g in games)
    ra     = sum(g["opp_runs"]  for g in games)
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
            "Result": g["result"], "Score": f'{g["team_runs"]}-{g["opp_runs"]}',
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

    if st.session_state.lg_game is None:
        st.markdown("#### Start a new game")

        tourn_list = games_data.get("tournaments", [])
        tourn_display = [t["name"] for t in tourn_list]

        with st.form("new_game"):
            c1, c2, c3 = st.columns(3)
            opponent  = c1.text_input("Opponent")
            game_date = c2.date_input("Date", value=date.today())
            game_type = c3.selectbox("Type", ["tournament", "regular", "playoff", "scrimmage"])
            c4, c5, c6 = st.columns(3)
            result    = c4.selectbox("Result", ["W", "L", "T"])
            team_runs = c5.number_input("Your runs", min_value=0, value=0, step=1)
            opp_runs  = c6.number_input("Opp runs",  min_value=0, value=0, step=1)

            # Tournament selector
            default_tidx = 0
            if active_tournament_id:
                for i, t in enumerate(tourn_list):
                    if t["id"] == active_tournament_id:
                        default_tidx = i
                        break

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

            go = st.form_submit_button("Create Game →")

        if go:
            if not opponent.strip():
                st.error("Opponent name is required.")
            elif tourn_choice == "+ New tournament" and not new_tourn_name.strip():
                st.error("Tournament name is required.")
            else:
                if tourn_choice == "+ New tournament":
                    tourn_id = _slug(new_tourn_name.strip(), {t["id"] for t in tourn_list})
                    tourn_list.append({
                        "id": tourn_id,
                        "name": new_tourn_name.strip(),
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
                    "game_id": new_id,
                    "date": str(game_date),
                    "opponent": opponent.strip(),
                    "result": result,
                    "team_runs": int(team_runs),
                    "opp_runs": int(opp_runs),
                    "type": game_type,
                    "tournament_id": tourn_id,
                    "lineup": [],
                    "substitutions": [],
                    "plate_appearances": [],
                }
                st.rerun()

    else:
        g = st.session_state.lg_game

        editing_id = st.session_state.get("editing_game_id")
        mode_label = "Editing" if editing_id else "In progress"
        g_tourn = next((t["name"] for t in tournaments if t["id"] == g.get("tournament_id", "")), "")

        st.markdown(
            f'<div class="recap">'
            f'<div class="title">{mode_label} · {g["date"]}'
            f'{(" · " + g_tourn) if g_tourn else ""}</div>'
            f'<div class="score">{g["result"]} {g["team_runs"]}–{g["opp_runs"]} vs {g["opponent"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        tab_lu, tab_ab, tab_sv = st.tabs(["1 · Lineup", "2 · Scoresheet", "3 · Review & Save"])

        with tab_lu:
            if not g["lineup"]:
                g["lineup"] = [{"order": i + 1, "player": p} for i, p in enumerate(player_names)]

            ordered = [s["player"] for s in sorted(g["lineup"], key=lambda x: x["order"])]

            for p in player_names:
                if p not in ordered:
                    ordered.append(p)

            st.markdown("**Drag players to set the batting order:**")
            st.caption("Grab any name and drag it up or down. Order saves automatically.")

            new_order = sort_items(ordered, direction="vertical", key="lineup_sort")

            if new_order != ordered:
                g["lineup"] = [{"order": i + 1, "player": p} for i, p in enumerate(new_order)]
                ordered = new_order

            st.markdown("---")
            st.markdown("**Add substitution:**")
            with st.form("add_sub"):
                cs1, cs2, cs3 = st.columns(3)
                out_p   = cs1.selectbox("Out", ordered if ordered else player_names)
                in_p    = cs2.selectbox("In", player_names)
                sub_inn = cs3.number_input("Inning", min_value=1, value=1, step=1)
                if st.form_submit_button("Add Sub"):
                    if out_p == in_p:
                        st.error("In and Out players must be different.")
                    else:
                        g["substitutions"].append({"out": out_p, "in": in_p, "inning": int(sub_inn)})
                        if in_p not in ordered:
                            ordered.append(in_p)
                            g["lineup"].append({"order": len(ordered), "player": in_p})
                        st.success(f"{in_p} in for {out_p} (inning {sub_inn})")
                        st.rerun()

            if g["substitutions"]:
                st.markdown("**Substitutions:**")
                for sub in g["substitutions"]:
                    st.markdown(f"- Inning {sub['inning']}: **{sub['in']}** in for {sub['out']}")

        with tab_ab:
            pas = g["plate_appearances"]
            order_map    = {s["player"]: s["order"] for s in g["lineup"]}
            lineup_order = sorted(player_names, key=lambda p: order_map.get(p, 99))
            cell_map     = {(pa["player"], pa.get("inning", 1)): pa for pa in pas}

            if "lg_innings" not in st.session_state:
                st.session_state["lg_innings"] = 7
            ni_col, _ = st.columns([1, 5])
            n_innings = ni_col.number_input(
                "Innings", min_value=1, max_value=15,
                value=st.session_state["lg_innings"], step=1,
            )
            st.session_state["lg_innings"] = int(n_innings)
            innings = list(range(1, int(n_innings) + 1))

            CELL_SHORT = {
                "1B": "1B", "2B": "2B", "3B": "3B",
                "HR_OTF": "HR", "HR_ITP": "ITP",
                "BB": "BB", "K": "K", "OUT": "OUT",
                "FC": "FC", "E": "E", "DP": "DP", "SF": "SF",
            }

            @st.dialog("Log At-Bat")
            def _ab_dialog(sel_player, sel_inning, existing, cell_map_ref):
                cell_key = f"{sel_player}__{sel_inning}"
                st.markdown(
                    f"<div style='font-size:18px;font-weight:800;margin-bottom:4px'>"
                    f"<span style='color:#FF1493'>{sel_player}</span>"
                    f"&nbsp;·&nbsp;Inning {sel_inning}</div>",
                    unsafe_allow_html=True,
                )
                if existing:
                    st.caption(
                        f"Currently: **{OUTCOME_DISPLAY[existing['outcome']]}** · "
                        f"{existing.get('rbi', 0)} RBI · "
                        f"{'Scored ✓' if existing.get('run_scored') else 'Did not score'}"
                    )

                outcome = st.pills(
                    "Outcome",
                    options=list(OUTCOME_DISPLAY.keys()),
                    format_func=lambda k: OUTCOME_DISPLAY[k],
                    default=existing["outcome"] if existing else None,
                    key=f"dlg_outcome_{cell_key}",
                )

                cr, cs2 = st.columns(2)
                rbi = cr.number_input(
                    "RBIs", min_value=0, max_value=4,
                    value=existing.get("rbi", 0) if existing else 0,
                    step=1, key=f"dlg_rbi_{cell_key}",
                )
                run_scored = cs2.checkbox(
                    "Run scored",
                    value=existing.get("run_scored", False) if existing else False,
                    key=f"dlg_run_{cell_key}",
                )

                cb1, cb2 = st.columns(2)
                if cb1.button("✓  Save", type="primary", use_container_width=True, key=f"dlg_save_{cell_key}"):
                    if not outcome:
                        st.warning("Select an outcome first.")
                    else:
                        g["plate_appearances"] = [
                            p for p in g["plate_appearances"]
                            if not (p["player"] == sel_player and p.get("inning") == sel_inning)
                        ]
                        g["plate_appearances"].append({
                            "pa_num":     len(g["plate_appearances"]) + 1,
                            "inning":     sel_inning,
                            "player":     sel_player,
                            "outcome":    outcome,
                            "rbi":        int(rbi),
                            "run_scored": bool(run_scored),
                        })
                        st.session_state["ss_sel"] = None
                        st.rerun()

                if existing and cb2.button("✕  Clear", use_container_width=True, key=f"dlg_clear_{cell_key}"):
                    g["plate_appearances"] = [
                        p for p in g["plate_appearances"]
                        if not (p["player"] == sel_player and p.get("inning") == sel_inning)
                    ]
                    st.session_state["ss_sel"] = None
                    st.rerun()

            def _pick_cell(p, i):
                st.session_state["ss_sel"] = (p, i)

            sel = st.session_state.get("ss_sel")

            if sel:
                sel_player, sel_inning = sel
                existing = cell_map.get((sel_player, sel_inning))
                _ab_dialog(sel_player, sel_inning, existing, cell_map)

            st.caption("Tap any cell to log that at-bat. Use landscape mode on phone for best experience.")

            hcols = st.columns([2] + [1] * len(innings))
            hcols[0].markdown(
                "<div style='font-size:11px;font-weight:700;text-transform:uppercase;"
                "letter-spacing:.5px;opacity:.5;padding-bottom:4px'>Player</div>",
                unsafe_allow_html=True,
            )
            for idx, inn in enumerate(innings):
                hcols[idx + 1].markdown(
                    f"<div style='text-align:center;font-size:11px;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:.5px;opacity:.5;"
                    f"padding-bottom:4px'>{inn}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown(
                "<hr style='margin:0 0 2px 0;border-color:rgba(255,20,147,0.2)'>",
                unsafe_allow_html=True,
            )

            for player in lineup_order:
                rcols = st.columns([2] + [1] * len(innings))
                is_active = sel and sel[0] == player
                rcols[0].markdown(
                    f"<div style='font-weight:700;padding-top:6px;"
                    f"color:{'#FF1493' if is_active else 'inherit'}'>{player}</div>",
                    unsafe_allow_html=True,
                )
                for idx, inn in enumerate(innings):
                    pa          = cell_map.get((player, inn))
                    is_selected = sel == (player, inn)
                    if pa:
                        lbl   = CELL_SHORT.get(pa["outcome"], pa["outcome"])
                        xtra  = "+" + str(pa["rbi"]) if pa.get("rbi") else ""
                        label = f"{lbl} {xtra}".strip() if xtra else lbl
                        if pa.get("run_scored"):
                            label = "● " + label
                    else:
                        label = "+"
                    rcols[idx + 1].button(
                        label,
                        key=f"cell_{player}_{inn}",
                        use_container_width=True,
                        type="primary" if is_selected else "secondary",
                        on_click=_pick_cell,
                        args=(player, inn),
                    )

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
                num_cols = [c for c in ["PA", "AB", "H", "HR", "BB", "SF", "R", "RBI", "K"] if c in summary_df.columns]
                totals_row = {"Player": "TOTAL", **{c: int(summary_df[c].sum()) for c in num_cols}}
                summary_df = pd.concat([summary_df, pd.DataFrame([totals_row])], ignore_index=True)
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
                st.success(f"Saved game vs {g['opponent']}!")
                st.balloons()
                st.rerun()
            if cc.button("🗑️ Discard"):
                st.session_state.pop("editing_game_id", None)
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
            rw = {"W": "Won", "L": "Lost", "T": "Tied"}.get(g["result"], g["result"])
            g_tourn = next((t["name"] for t in tournaments if t["id"] == g.get("tournament_id", "")), "")
            tourn_tag = f"  [{g_tourn}]" if g_tourn else ""
            label = f'{g["date"]}  ·  {rw} {g["team_runs"]}-{g["opp_runs"]}  vs  {g["opponent"]}  [{g.get("type","regular").title()}]{tourn_tag}'
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
