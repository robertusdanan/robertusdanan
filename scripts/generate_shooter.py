#!/usr/bin/env python3
"""Generate an animated "contribution shooter" SVG from a GitHub contribution calendar.

A pixel spaceship sweeps under your contribution grid and shoots every active
day (the "invaders") one by one. Output is a self-contained SMIL-animated SVG
that GitHub renders inside README files.

Usage:
    GITHUB_TOKEN=xxx python generate_shooter.py --user robertusdanan --out dist
    python generate_shooter.py --sample --out dist        # offline preview
"""
import argparse
import json
import os
import random
import urllib.request

CELL, GAP = 12, 3
PITCH = CELL + GAP
MARGIN_X = 30
GRID_Y = 58
BULLET_SPEED = 720.0  # px / second
FIRE_GAP = 0.07       # seconds between bullets in one column
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

THEMES = {
    "dark": dict(
        bg="#0d1117", border="#30363d", empty="#161b22", text="#8b949e",
        title="#e6edf3", accent="#5eead4", star="#8b949e",
        enemy=["", "#134e4a", "#0f766e", "#14b8a6", "#5eead4"],
        ship="#ff4d6d", ship2="#ffd166", bullet="#ffd166", boom="#ff9e64"),
    "light": dict(
        bg="#ffffff", border="#d0d7de", empty="#eaeef2", text="#57606a",
        title="#1f2328", accent="#0f766e", star="#afb8c1",
        enemy=["", "#99f6e4", "#2dd4bf", "#0d9488", "#115e59"],
        ship="#e11d48", ship2="#d97706", bullet="#d97706", boom="#ea580c"),
}


def fetch_calendar(user, token):
    query = """query($login:String!){user(login:$login){contributionsCollection{
      contributionCalendar{totalContributions weeks{contributionDays{
      contributionCount contributionLevel weekday}}}}}}"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "contribution-shooter"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = []
    for w in cal["weeks"]:
        col = [None] * 7
        for d in w["contributionDays"]:
            col[d["weekday"]] = (LEVELS[d["contributionLevel"]], d["contributionCount"])
        weeks.append(col)
    return weeks, cal["totalContributions"]


def sample_calendar():
    rnd = random.Random(7)
    weeks, total = [], 0
    for c in range(53):
        col = []
        for r in range(7):
            lvl = 0 if rnd.random() < (0.45 + (0.25 if r in (0, 6) else 0)) else rnd.choice([1, 1, 2, 2, 3, 4])
            n = lvl * rnd.randint(1, 4)
            total += n
            col.append((lvl, n))
        weeks.append(col)
    return weeks, total


def f(x):
    return f"{x:.4f}".rstrip("0").rstrip(".")


def anim(attr, frames, T, extra=""):
    """frames = [(seconds, value)]; builds a looping <animate> with exact keyTimes."""
    frames = sorted(frames, key=lambda p: p[0])
    if frames[0][0] > 0:
        frames.insert(0, (0, frames[0][1]))
    if frames[-1][0] < T:
        frames.append((T, frames[-1][1]))
    kt = ";".join(f"{min(1.0, t / T):.6f}" for t, _ in frames)
    vals = ";".join(str(v) for _, v in frames)
    return (f'<animate attributeName="{attr}" dur="{f(T)}s" repeatCount="indefinite" '
            f'keyTimes="{kt}" values="{vals}" {extra}/>')


def build(weeks, total, user, theme):
    t = THEMES[theme]
    ncol = len(weeks)
    W = MARGIN_X * 2 + ncol * PITCH - GAP
    grid_bottom = GRID_Y + 7 * PITCH - GAP
    ship_y = grid_bottom + 78
    H = ship_y + 34
    cx = lambda c: MARGIN_X + c * PITCH + CELL / 2
    cy = lambda r: GRID_Y + r * PITCH + CELL / 2

    # ---- timeline ---------------------------------------------------------
    active = [c for c in range(ncol) if any(d and d[0] > 0 for d in weeks[c])]
    t_now, ship_keys, shots = 0.8, [], []   # shots: (col,row,fire_t,hit_t)
    first_x = cx(active[0]) if active else cx(0)
    ship_keys.append((0, first_x))
    for c in active:
        rows = [r for r in range(6, -1, -1) if weeks[c][r] and weeks[c][r][0] > 0]  # bottom first
        hold = max(0.45, 0.2 + len(rows) * FIRE_GAP + 0.15)
        ship_keys.append((t_now, cx(c)))
        for k, r in enumerate(rows):
            ft = t_now + 0.1 + k * FIRE_GAP
            ht = ft + (ship_y - 16 - cy(r)) / BULLET_SPEED
            shots.append((c, r, ft, ht))
        t_now += hold
        ship_keys.append((t_now, cx(c)))
        t_now += 0.1
    clear_t = max([s[3] for s in shots], default=0) + 0.3
    T = max(t_now, clear_t) + 2.6
    reset_t = T - 0.5
    ship_keys.append((T - 0.7, first_x))
    ship_anim_vals = [(tt, f"{f(x)} {f(ship_y)}") for tt, x in ship_keys]

    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
             f'role="img" aria-label="Contribution shooter for {user}">')
    o.append(f'<defs><filter id="glow" x="-100%" y="-100%" width="300%" height="300%">'
             f'<feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/>'
             f'<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>')
    o.append(f'<style>text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}}</style>')
    o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="{t["bg"]}" stroke="{t["border"]}"/>')

    # starfield
    rnd = random.Random(42)
    for _ in range(46):
        x, y = rnd.uniform(14, W - 14), rnd.uniform(14, H - 14)
        r, d = rnd.choice([0.7, 0.9, 1.2]), rnd.uniform(2.2, 5)
        o.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{r}" fill="{t["star"]}" opacity=".5">'
                 f'<animate attributeName="opacity" values=".15;.8;.15" dur="{f(d)}s" begin="-{f(rnd.uniform(0,d))}s" repeatCount="indefinite"/></circle>')

    # HUD
    o.append(f'<text x="{MARGIN_X}" y="30" font-size="12" fill="{t["accent"]}" letter-spacing="2">PLAYER 1</text>')
    o.append(f'<text x="{MARGIN_X + 80}" y="30" font-size="12" fill="{t["title"]}" letter-spacing="1">{user.upper()}</text>')
    o.append(f'<text x="{W/2}" y="30" font-size="12" fill="{t["text"]}" text-anchor="middle" letter-spacing="2">{total} CONTRIBUTIONS · LAST 12 MONTHS</text>')
    o.append(f'<text x="{W-MARGIN_X}" y="30" font-size="12" fill="{t["ship"]}" text-anchor="end" letter-spacing="3">♥ ♥ ♥</text>')

    # grid: empty slots + enemies
    for c in range(ncol):
        for r in range(7):
            d = weeks[c][r]
            x, y = MARGIN_X + c * PITCH, GRID_Y + r * PITCH
            if d is None:
                continue
            if d[0] == 0:
                o.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{t["empty"]}"/>')
    hit = {(c, r): ht for c, r, ft, ht in shots}
    for c in range(ncol):
        for r in range(7):
            d = weeks[c][r]
            if not d or d[0] == 0:
                continue
            x, y = MARGIN_X + c * PITCH, GRID_Y + r * PITCH
            ht = hit[(c, r)]
            a = anim("opacity", [(0, 1), (ht, 1), (ht + 0.06, 0), (reset_t, 0), (T, 1)], T)
            o.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{t["enemy"][d[0]]}">{a}</rect>')

    # bullets + explosions
    for c, r, ft, ht in shots:
        x = cx(c) - 1.5
        y0, y1 = ship_y - 18, cy(r) - 4
        o.append(
            f'<rect x="{f(x)}" y="{f(y0)}" width="3" height="9" rx="1.5" fill="{t["bullet"]}" opacity="0" filter="url(#glow)">'
            + anim("opacity", [(ft - 0.001, 0), (ft, 1), (ht, 1), (ht + 0.001, 0)], T)
            + anim("y", [(ft, f(y0)), (ht, f(y1)), (T, f(y1))], T) + '</rect>')
        o.append(
            f'<circle cx="{f(cx(c))}" cy="{f(cy(r))}" r="0" fill="none" stroke="{t["boom"]}" stroke-width="2" opacity="0">'
            + anim("r", [(ht - 0.001, 0), (ht, 2), (ht + 0.3, 12), (ht + 0.301, 0)], T)
            + anim("opacity", [(ht - 0.001, 0), (ht, 1), (ht + 0.3, 0)], T) + '</circle>')

    # ship
    o.append(f'<g transform="translate({f(first_x)} {f(ship_y)})">')
    o.append(anim("transform", ship_anim_vals, T).replace('<animate attributeName="transform"', '<animateTransform attributeName="transform" type="translate"'))
    o.append(f'<path d="M0 -16 L5 -5 L13 4 L13 11 L5 8 L0 12 L-5 8 L-13 11 L-13 4 L-5 -5 Z" fill="{t["ship"]}" filter="url(#glow)"/>')
    o.append(f'<path d="M0 -9 L3 -2 L0 3 L-3 -2 Z" fill="{t["bg"]}" opacity=".85"/>')
    o.append(f'<path d="M-3 11 L0 {14}  L3 11 Z" fill="{t["ship2"]}"><animate attributeName="d" '
             f'values="M-3 11 L0 15 L3 11 Z;M-3 11 L0 21 L3 11 Z;M-3 11 L0 15 L3 11 Z" dur=".18s" repeatCount="indefinite"/></path>')
    o.append('</g>')

    # sector cleared banner
    cl = anim("opacity", [(clear_t, 0), (clear_t + 0.2, 1), (reset_t - 0.2, 1), (reset_t, 0)], T)
    o.append(f'<text x="{W/2}" y="{f((GRID_Y + grid_bottom)/2 + 5)}" font-size="20" fill="{t["accent"]}" '
             f'text-anchor="middle" letter-spacing="8" opacity="0" filter="url(#glow)">SECTOR CLEARED{cl}</text>')
    o.append('</svg>')
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_USER", "robertusdanan"))
    ap.add_argument("--out", default="dist")
    ap.add_argument("--sample", action="store_true")
    a = ap.parse_args()
    if a.sample:
        weeks, total = sample_calendar()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is required (or use --sample)")
        weeks, total = fetch_calendar(a.user, token)
    os.makedirs(a.out, exist_ok=True)
    for theme in THEMES:
        path = os.path.join(a.out, f"shooter-{theme}.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(build(weeks, total, a.user, theme))
        print("wrote", path)


if __name__ == "__main__":
    main()
