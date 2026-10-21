#!/usr/bin/env python3
"""Generate assets/header.svg: a header where the ship REALLY shoots the targets.

The ship slides under each invader, fires a bullet that travels up and stops exactly
on the target, the target blows up (flash + ring + debris) and disappears. After the
whole formation is cleared the banner shows and the targets respawn for the next loop.

Usage: python3 scripts/generate_header.py [--out assets/header.svg]
"""
import argparse

W, H = 855, 230
FX, FY = 610, 52          # formation origin
SZ = 14                    # invader size
SHIP_Y = 184               # ship centre line
NOSE = 16                  # nose offset above SHIP_Y
BULLET_SPEED = 520.0       # px/s
SHOT_GAP = 0.46            # s between shots
MOVE = 0.14                # s to slide one column
T = 13.0                   # loop length

# (col_x, col_y, colour) -- same shape as the old header, now with row coords
ROWS = {
    0: ([0, 24, 48, 72, 96], ["#14b8a6", "#5eead4", "#14b8a6", "#0f766e", "#5eead4"]),
    1: ([12, 36, 60, 84], ["#0f766e", "#14b8a6", "#5eead4", "#14b8a6"]),
    2: ([24, 48, 72], ["#5eead4", "#0f766e", "#14b8a6"]),
}
ROW_Y = {0: 0, 1: 24, 2: 48}

enemies = []
for r, (xs, cols) in ROWS.items():
    for x, c in zip(xs, cols):
        enemies.append(dict(r=r, x=FX + x, y=FY + ROW_Y[r], c=c, cx=FX + x + SZ / 2, cy=FY + ROW_Y[r] + SZ / 2))

# shooting order: left -> right by column centre, lower row first (so nothing blocks the bullet)
import random
rnd = random.Random(11)
order = enemies[:]
rnd.shuffle(order)
# a bullet cannot pass through a target: in a shared column the lower one must go first
for _ in range(len(order)):
    for a in range(len(order)):
        for b in range(a + 1, len(order)):
            if order[a]["cx"] == order[b]["cx"] and order[a]["r"] < order[b]["r"]:
                order[a], order[b] = order[b], order[a]


def f(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def anim(attr, frames, extra="", tag="animate"):
    frames = sorted(frames, key=lambda p: p[0])
    if frames[0][0] > 0:
        frames.insert(0, (0, frames[0][1]))
    if frames[-1][0] < T:
        frames.append((T, frames[-1][1]))
    kt = ";".join(f"{min(1.0, t / T):.6f}" for t, _ in frames)
    vals = ";".join(str(v) for _, v in frames)
    return (f'<{tag} attributeName="{attr}" dur="{f(T)}s" repeatCount="indefinite" '
            f'keyTimes="{kt}" values="{vals}" {extra}/>')


# ---- timeline ----------------------------------------------------------------
t0 = 1.0
ship_keys = [(0, order[0]["cx"])]
last_x = order[0]["cx"]
t = t0
for i, e in enumerate(order):
    if abs(e["cx"] - last_x) > 0.01:                      # slide to the new column
        mv = max(MOVE, abs(e["cx"] - last_x) / 380.0)
        t += mv
        ship_keys.append((t - mv, last_x))
        ship_keys.append((t, e["cx"]))
        last_x = e["cx"]
    e["fire"] = t + 0.05
    e["hit"] = e["fire"] + ((SHIP_Y - NOSE) - e["cy"] - 2) / BULLET_SPEED
    e["n"] = i
    t += SHOT_GAP
last_hit = order[-1]["hit"]
clear_t = last_hit + 0.5
respawn = T - 1.4
ship_keys.append((last_hit + 0.2, last_x))
ship_keys.append((T - 0.6, order[0]["cx"]))

o = []
o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="Robertus Danan - Creator, ViberCoder, TraderBot">')
o.append('''<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1020"/><stop offset="1" stop-color="#101a33"/></linearGradient>
<linearGradient id="title" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5eead4"/><stop offset=".55" stop-color="#7dd3fc"/><stop offset="1" stop-color="#c4b5fd"/></linearGradient>
<pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M28 0H0V28" fill="none" stroke="#1e2a4a" stroke-width="1"/></pattern>
<filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<clipPath id="type"><rect x="40" y="130" width="0" height="30"><animate attributeName="width" values="0;570;570;0" keyTimes="0;.45;.9;1" dur="7s" repeatCount="indefinite"/></rect></clipPath>
</defs>
<style>text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}.sans{font-family:'Segoe UI',Inter,Helvetica,Arial,sans-serif}</style>''')
o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="url(#bg)" stroke="#30363d"/>')
o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" fill="url(#grid)" opacity=".55"/>')

# stars
o.append('<g fill="#9fb3d9">')
for cx, cy, r, d in [(60, 40, 1, 3), (210, 190, 1.2, 4), (520, 30, 1, 2.6), (700, 215, 1.2, 3.4), (800, 120, 1, 4.4), (580, 150, 1, 3.8), (350, 205, 1, 2.9)]:
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}"><animate attributeName="opacity" values=".2;.9;.2" dur="{d}s" repeatCount="indefinite"/></circle>')
o.append('</g>')

# text block (unchanged)
o.append('<text x="40" y="44" font-size="12" fill="#5eead4" letter-spacing="4">PLAYER 1 · READY</text>')
o.append('<text class="sans" x="40" y="108" font-size="52" font-weight="800" fill="url(#title)" letter-spacing="2">ROBERTUS DANAN</text>')
o.append('<g clip-path="url(#type)"><text x="40" y="150" font-size="15" fill="#cbd5e1" letter-spacing="1">Creator · ViberCoder (Web Android Ai-Agent) · TraderBot</text></g>')
o.append('<text x="40" y="190" font-size="12" fill="#64748b" letter-spacing="2">TULUNGAGUNG, EAST JAVA · INDONESIA</text>')
o.append('<text x="40" y="212" font-size="12" fill="#ffd166" letter-spacing="4">▶ PRESS START<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.2s" repeatCount="indefinite"/></text>')

# score (discrete counter)
n = len(order)
o.append(f'<text x="{W-30}" y="30" font-size="11" fill="#64748b" text-anchor="end" letter-spacing="3">SCORE</text>')
for k in range(n + 1):
    start = 0 if k == 0 else order[k - 1]["hit"]
    end = T if k == n else order[k]["hit"]
    frames = [(0, 0)]
    if k == 0:
        frames = [(0, 1), (end, 0)]
    else:
        frames = [(start - 0.001, 0), (start, 1), (end if k < n else respawn, 1), ((end if k < n else respawn) + 0.001, 0)]
    a = anim("opacity", frames, 'calcMode="discrete"') if False else anim("opacity", frames)
    o.append(f'<text x="{W-30}" y="48" font-size="15" fill="#ffd166" text-anchor="end" letter-spacing="3" opacity="0">{k*100:05d}{a}</text>')

# invaders
for e in order:
    a = anim("opacity", [(0, 1), (e["hit"], 1), (e["hit"] + 0.05, 0), (respawn, 0), (respawn + 0.6, 1)])
    # white flash right at impact
    fl = anim("opacity", [(e["hit"] - 0.001, 0), (e["hit"], 1), (e["hit"] + 0.08, 0)])
    o.append(f'<rect x="{f(e["x"])}" y="{f(e["y"])}" width="{SZ}" height="{SZ}" rx="3" fill="{e["c"]}" opacity="1">{a}</rect>')
    o.append(f'<rect x="{f(e["x"]-1)}" y="{f(e["y"]-1)}" width="{SZ+2}" height="{SZ+2}" rx="4" fill="#ffffff" opacity="0" filter="url(#glow)">{fl}</rect>')

# bullets, muzzle flashes, explosions
import math
for e in order:
    bx, y0, y1 = e["cx"] - 1.5, SHIP_Y - NOSE - 10, e["cy"] - 3
    o.append(f'<rect x="{f(bx)}" y="{f(y0)}" width="3" height="10" rx="1.5" fill="#ffd166" opacity="0" filter="url(#glow)">'
             + anim("opacity", [(e["fire"] - 0.001, 0), (e["fire"], 1), (e["hit"], 1), (e["hit"] + 0.001, 0)])
             + anim("y", [(e["fire"], f(y0)), (e["hit"], f(y1))]) + '</rect>')
    o.append(f'<circle cx="{f(e["cx"])}" cy="{f(SHIP_Y - NOSE - 2)}" r="5" fill="#fff3b0" opacity="0" filter="url(#glow)">'
             + anim("opacity", [(e["fire"] - 0.001, 0), (e["fire"], 1), (e["fire"] + 0.07, 0)]) + '</circle>')
    h = e["hit"]
    o.append(f'<circle cx="{f(e["cx"])}" cy="{f(e["cy"])}" r="0" fill="none" stroke="#ff9e64" stroke-width="2" opacity="0">'
             + anim("r", [(h - 0.001, 0), (h, 3), (h + 0.35, 17), (h + 0.351, 0)])
             + anim("opacity", [(h - 0.001, 0), (h, 1), (h + 0.35, 0)]) + '</circle>')
    for k in range(7):
        ang = (k / 7) * 2 * math.pi + e["n"] * 0.7
        dist = 16 + (k % 3) * 5
        col = ["#ffd166", "#ff9e64", "#5eead4"][k % 3]
        o.append(f'<circle r="1.8" fill="{col}" opacity="0">'
                 + anim("cx", [(h - 0.001, f(e["cx"])), (h, f(e["cx"])), (h + 0.4, f(e["cx"] + math.cos(ang) * dist))])
                 + anim("cy", [(h - 0.001, f(e["cy"])), (h, f(e["cy"])), (h + 0.4, f(e["cy"] + math.sin(ang) * dist))])
                 + anim("opacity", [(h - 0.001, 0), (h, 1), (h + 0.4, 0)]) + '</circle>')

# sector cleared
o.append(f'<text x="{f(FX + 55)}" y="{FY + 34}" font-size="12" fill="#5eead4" text-anchor="middle" letter-spacing="4" opacity="0" filter="url(#glow)">SECTOR CLEARED'
         + anim("opacity", [(clear_t, 0), (clear_t + 0.25, 1), (respawn - 0.2, 1), (respawn, 0)]) + '</text>')

# ship
vals = [(tt, f"{f(x)} {SHIP_Y}") for tt, x in ship_keys]
o.append(f'<g transform="translate({f(order[0]["cx"])} {SHIP_Y})">')
o.append(anim("transform", vals, 'type="translate"', tag="animateTransform"))
o.append('<path d="M0 -16 L5 -5 L13 4 L13 11 L5 8 L0 12 L-5 8 L-13 11 L-13 4 L-5 -5 Z" fill="#ff4d6d" filter="url(#glow)"/>')
o.append('<path d="M0 -9 L3 -2 L0 3 L-3 -2 Z" fill="#0b1020" opacity=".85"/>')
o.append('<path d="M-3 11 L0 15 L3 11 Z" fill="#ffd166"><animate attributeName="d" values="M-3 11 L0 15 L3 11 Z;M-3 11 L0 21 L3 11 Z;M-3 11 L0 15 L3 11 Z" dur=".18s" repeatCount="indefinite"/></path>')
o.append('</g>')
o.append('</svg>')

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="assets/header.svg")
    a = ap.parse_args()
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(o))
    print("wrote", a.out, "| hits end at %.2fs, loop %.1fs" % (last_hit, T))
