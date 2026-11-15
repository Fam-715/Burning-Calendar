# ============================================================
# Burning Calendar - look and feel
# Night-side Earth seen from orbit: a satellite pass over glowing hotspots,
# plus the hover-to-lift burning calendar. Pure HTML and CSS, no JavaScript.
# Note: written with AI assistance (declared on the project page).
# ============================================================
import html

import numpy as np
import streamlit as st

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# chart colours for the dark surface
BLUE, ORANGE, GREY, INK2 = "#3987e5", "#d95926", "#465066", "#c3c8d4"

# colour ramps: (position 0-1, hex)
EMBER = [(0.00, "#141b2d"), (0.15, "#4a1f10"), (0.40, "#a53d14"),
         (0.65, "#ef6c25"), (0.85, "#ffab5e"), (1.00, "#ffe2b8")]
DIVERGE = [(0.00, "#3987e5"), (0.50, "#2a3040"), (1.00, "#ff6b3d")]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Michroma&display=swap');

/* ---------- page: deep orbital night with a still starfield ---------- */
.stApp {
  background-color: #060912;
  background-image:
    radial-gradient(1px 1px at 23px 41px, rgba(255,255,255,.55), transparent 60%),
    radial-gradient(1px 1px at 131px 97px, rgba(200,220,255,.45), transparent 60%),
    radial-gradient(1.5px 1.5px at 71px 163px, rgba(255,255,255,.35), transparent 60%),
    radial-gradient(1px 1px at 211px 19px, rgba(255,236,210,.40), transparent 60%),
    radial-gradient(1px 1px at 301px 233px, rgba(255,255,255,.30), transparent 60%);
  background-size: 260px 260px, 340px 340px, 410px 410px, 530px 530px, 610px 610px;
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #0a101d; border-right: 1px solid #1a2438; }
[data-testid="stMainBlockContainer"] { padding-top: 2.4rem; }
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }

/* ---------- hero: a satellite pass over the night side ---------- */
.bc-hero {
  position: relative; height: 290px; overflow: hidden; border-radius: 14px;
  border: 1px solid #1a2438;
  background: linear-gradient(180deg, #04060c 0%, #070d1c 55%, #0b1830 100%);
}
.bc-hero-stars {
  position: absolute; inset: 0;
  background-image:
    radial-gradient(1px 1px at 37px 29px, #fff, transparent 60%),
    radial-gradient(1px 1px at 149px 83px, #cfe0ff, transparent 60%),
    radial-gradient(1.5px 1.5px at 97px 131px, #fff, transparent 60%),
    radial-gradient(1px 1px at 233px 47px, #ffe9cf, transparent 60%);
  background-size: 190px 150px, 270px 170px, 330px 190px, 410px 210px;
  opacity: .55; animation: bc-twinkle 7s ease-in-out infinite alternate;
}
.bc-earth {
  position: absolute; left: 50%; top: 192px; width: 4800px; height: 4800px;
  margin-left: -2400px; border-radius: 50%;
  background: radial-gradient(circle at 50% 0%, #10233f 0, #0a1426 4%, #060b16 9%);
  box-shadow: 0 0 46px 4px rgba(79,157,255,.30), 0 0 2px 1px rgba(170,205,255,.75);
}
.bc-fire {
  position: absolute; left: 50%; top: 0; width: 5px; height: 5px; margin-left: -2.5px;
  border-radius: 50%; background: #ffd9a0;
  box-shadow: 0 0 7px 2px rgba(255,138,61,.85), 0 0 16px 5px rgba(255,90,30,.35);
  transform-origin: 2.5px 2400px;
  transform: rotate(var(--a)) translateY(var(--y));
  animation: bc-flicker var(--t) ease-in-out var(--d) infinite alternate;
}
.bc-orbit {
  position: absolute; left: 50%; top: 150px; width: 0; height: 0;
  transform-origin: 0 2442px;
  animation: bc-pass 36s linear -11s infinite;
}
.bc-sat { position: absolute; left: -18px; top: -7px; width: 36px; height: 14px;
  display: flex; align-items: center; justify-content: space-between; }
.bc-panel { width: 12px; height: 8px; border-radius: 1px; background: #2f6fd0; border: 1px solid #9cc4ff; box-sizing: border-box; }
.bc-body { width: 8px; height: 14px; border-radius: 2px; background: #dfe7f3; box-shadow: 0 0 6px rgba(190,215,255,.7); }
.bc-beam {
  position: absolute; left: -20px; top: 7px; width: 40px; height: 58px;
  background: linear-gradient(180deg, rgba(120,180,255,.34), rgba(120,180,255,0));
  clip-path: polygon(50% 0, 100% 100%, 0 100%);
}
.bc-copy { position: absolute; left: 34px; top: 30px; right: 34px; z-index: 2; }
.bc-copy h1 {
  margin: 0; padding: 0; color: #eef2fa;
  font-family: 'Michroma', 'Eurostile', 'Segoe UI', sans-serif;
  font-size: clamp(1.6rem, 3.4vw, 2.5rem); font-weight: 400; letter-spacing: .04em; line-height: 1.15;
}
.bc-copy p { margin: .55rem 0 0; max-width: 46rem; color: #9aa6bd; font-size: 1rem; line-height: 1.5; }

@keyframes bc-twinkle { from { opacity: .30; } to { opacity: .70; } }
@keyframes bc-flicker {
  from { opacity: .35; box-shadow: 0 0 4px 1px rgba(255,138,61,.6), 0 0 8px 2px rgba(255,90,30,.2); }
  to   { opacity: 1;   box-shadow: 0 0 9px 3px rgba(255,138,61,.9), 0 0 22px 8px rgba(255,90,30,.4); }
}
@keyframes bc-pass {
  0%   { transform: rotate(-19deg); opacity: 0; }
  6%   { opacity: 1; }
  94%  { opacity: 1; }
  100% { transform: rotate(19deg); opacity: 0; }
}

/* ---------- burning calendar ---------- */
.bc-cal { margin-top: .4rem; }
.bc-row { display: grid; grid-template-columns: 3rem repeat(12, minmax(0, 1fr)); gap: 3px; margin-bottom: 3px; }
.bc-head span { text-align: center; color: #8b97ad; font-size: .8rem; padding-bottom: 2px; }
.bc-yr { color: #8b97ad; font-size: .8rem; line-height: 22px; font-variant-numeric: tabular-nums; }
.bc-cell {
  position: relative; height: 22px; border-radius: 3px; background: var(--c);
  transition: transform .17s cubic-bezier(.2,.8,.2,1), box-shadow .17s ease;
}
.bc-cell:hover {
  transform: scale(1.3) translateY(-2px); z-index: 20;
  box-shadow: 0 8px 22px rgba(0,0,0,.65), 0 0 0 1px rgba(255,255,255,.85), 0 0 18px var(--c);
}
.bc-empty { height: 22px; border-radius: 3px; border: 1px dashed #1c2740; }
.bc-tip {
  position: absolute; bottom: calc(100% + 7px); left: 50%; width: 15rem;
  transform: translateX(-50%) scale(.77); transform-origin: bottom center;
  padding: .55rem .7rem; border-radius: 8px; background: #0e1626; border: 1px solid #2a3a58;
  color: #c3c8d4; font-size: .95rem; line-height: 1.4; text-align: left;
  opacity: 0; visibility: hidden; pointer-events: none; transition: opacity .12s ease;
  box-shadow: 0 10px 28px rgba(0,0,0,.6);
}
.bc-tip b { display: block; color: #eef2fa; font-size: 1.05rem; }
.bc-tip i { display: block; font-style: normal; color: #8b97ad; font-size: .85rem; margin-top: .15rem; }
.bc-cell:hover .bc-tip { opacity: 1; visibility: visible; }
.bc-left .bc-tip  { left: 0; transform: scale(.77); transform-origin: bottom left; }
.bc-right .bc-tip { left: auto; right: 0; transform: scale(.77); transform-origin: bottom right; }
.bc-low .bc-tip   { bottom: auto; top: calc(100% + 7px); }
.bc-low.bc-cell .bc-tip { transform-origin: top center; }
.bc-low.bc-left .bc-tip { transform-origin: top left; }
.bc-low.bc-right .bc-tip { transform-origin: top right; }

.bc-legend { display: flex; align-items: flex-start; gap: 1.6rem; margin: .2rem 0 1rem 3.2rem; color: #8b97ad; font-size: .8rem; }
.bc-scale { flex: 0 1 22rem; min-width: 12rem; }
.bc-bar { height: 10px; border-radius: 5px; }
.bc-ticks { position: relative; height: 1.1rem; margin-top: 4px; font-size: .75rem; }
.bc-ticks span { position: absolute; top: 0; transform: translateX(-50%); white-space: nowrap; }
.bc-legend > span { line-height: 10px; }

@media (prefers-reduced-motion: reduce) {
  .bc-hero-stars, .bc-fire, .bc-orbit { animation: none; }
  .bc-cell, .bc-tip { transition: none; }
}
</style>
"""

SATELLITE = ('<div class="bc-sat"><span class="bc-panel"></span>'
             '<span class="bc-body"></span><span class="bc-panel"></span></div>')

# hotspots on the night side: (angle from the top of the Earth, depth below the limb, flicker time, delay)
FIRES = [(-14.2, 26, 2.6, 0.0), (-11.5, 58, 3.4, 0.9), (-9.1, 18, 2.2, 1.7), (-6.4, 44, 3.0, 0.4),
         (-3.8, 70, 2.8, 2.1), (-1.5, 30, 3.6, 1.2), (1.2, 52, 2.4, 0.2), (3.3, 22, 3.2, 1.5),
         (5.9, 64, 2.7, 0.7), (8.4, 36, 3.5, 2.4), (10.8, 16, 2.3, 1.0), (13.6, 48, 3.1, 0.5)]


def inject_css():
    st.html(CSS)


def hero(first_year, last_year):
    fires = "".join(
        f'<span class="bc-fire" style="--a:{a}deg;--y:{y}px;--t:{t}s;--d:{d}s"></span>'
        for a, y, t, d in FIRES)
    st.html(f"""
<div class="bc-hero" role="img" aria-label="A satellite passing over fire hotspots on the night side of the Earth">
  <div class="bc-hero-stars"></div>
  <div class="bc-earth">{fires}</div>
  <div class="bc-orbit"><div class="bc-beam"></div>{SATELLITE}</div>
  <div class="bc-copy">
    <h1>Burning Calendar</h1>
    <p>Twenty-five years of fire hotspots over Malaysia and Indonesia, {first_year} to {last_year},
       with NASA's MODIS and VIIRS records harmonised into one.</p>
  </div>
</div>""")


def _hex_to_rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def ramp(t, stops):
    """Colour at position t (0-1) along a ramp of (position, hex) stops."""
    t = float(np.clip(t, 0, 1))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            f = (t - p0) / (p1 - p0)
            rgb = _hex_to_rgb(c0) + f * (_hex_to_rgb(c1) - _hex_to_rgb(c0))
            return "#{:02x}{:02x}{:02x}".format(*[int(round(v)) for v in rgb])
    return stops[-1][1]


def _gradient(stops):
    return "linear-gradient(90deg, " + ", ".join(f"{c} {p * 100:.0f}%" for p, c in stops) + ")"


def _compact(v):
    if v >= 1e6:
        return f"{v / 1e6:.1f}M"
    if v >= 1e4:
        return f"{v / 1e3:.0f}k"
    if v >= 1e3:
        return f"{v / 1e3:.1f}k"
    return f"{v:.0f}"


def calendar(view, by_count=True):
    """Burning calendar: one row per year, one square per month. Squares lift on hover."""
    top = max(float(view["hotspots"].max()), 1.0)
    years = sorted(view["year"].unique())
    lookup = {(r.year, r.month): r for r in view.itertuples()}

    if by_count:
        ticks = [(p, _compact(top * p * p)) for p in (0, .25, .5, .75, 1)]      # square-root scale
        bar, caption = _gradient(EMBER), "Hotspots in the month"
    else:
        ticks = [(0, "1/8×"), (1 / 6, "1/4×"), (2 / 6, "1/2×"), (.5, "usual"), (4 / 6, "2×"), (5 / 6, "4×"), (1, "8×")]
        bar, caption = _gradient(DIVERGE), "Blue: quieter than usual. Orange: more fire than usual."
    tick_html = "".join(f'<span style="left:{p * 100:.1f}%">{t}</span>' for p, t in ticks)
    out = [f'<div class="bc-legend"><div class="bc-scale"><div class="bc-bar" style="background:{bar}"></div>'
           f'<div class="bc-ticks">{tick_html}</div></div><span>{caption}</span></div>',
           '<div class="bc-cal">',
           '<div class="bc-row bc-head"><span></span>' + "".join(f"<span>{m}</span>" for m in MONTHS) + "</div>"]

    for i, year in enumerate(years):
        cells = [f'<span class="bc-yr">{year}</span>']
        for month in range(1, 13):
            r = lookup.get((year, month))
            if r is None:
                cells.append('<div class="bc-empty"></div>')
                continue
            t = np.sqrt(r.hotspots / top) if by_count else (r.log_ratio + 3) / 6
            colour = ramp(t, EMBER if by_count else DIVERGE)
            side = " bc-left" if month <= 2 else " bc-right" if month >= 11 else ""
            low = " bc-low" if i < 3 else ""
            tip = (f"<b>{MONTHS[month - 1]} {year}: {r.hotspots:,.0f} hotspots</b>"
                   f"Usual {MONTHS[month - 1]}: {r.usual:,.0f} ({r.times_usual:.1f} times)"
                   f"<i>{html.escape(r.source)}</i>")
            cells.append(f'<div class="bc-cell{side}{low}" style="--c:{colour}"><span class="bc-tip">{tip}</span></div>')
        out.append('<div class="bc-row">' + "".join(cells) + "</div>")
    out.append("</div>")
    st.html("".join(out))
