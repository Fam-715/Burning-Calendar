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

/* ---------- page: deep orbital night, fire glow on the horizon ---------- */
.stApp {
  isolation: isolate;
  background-color: #05070f;
  background-image:
    radial-gradient(120% 55% at 50% 118%, rgba(255,106,40,.20), rgba(255,106,40,.05) 45%, transparent 70%),
    radial-gradient(60% 45% at 88% -5%, rgba(79,157,255,.13), transparent 70%),
    radial-gradient(45% 40% at 8% 20%, rgba(120,90,255,.07), transparent 70%);
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
  background: rgba(9,14,26,.78); border-right: 1px solid #1a2438;
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
}
[data-testid="stMainBlockContainer"] { padding-top: 2.4rem; }

/* ---------- headline numbers: glass cards that lift ---------- */
[data-testid="stMetric"] {
  padding: .9rem 1rem .8rem; border-radius: 14px;
  background: linear-gradient(160deg, rgba(22,32,56,.66), rgba(9,14,27,.58));
  border: 1px solid rgba(130,165,230,.16);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.05), 0 10px 30px rgba(0,0,0,.35);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  transition: transform .25s cubic-bezier(.2,.8,.2,1), border-color .25s ease, box-shadow .25s ease;
}
[data-testid="stMetric"]:hover {
  transform: translateY(-4px); border-color: rgba(255,138,61,.55);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.07), 0 16px 36px rgba(0,0,0,.45), 0 0 26px rgba(255,120,50,.18);
}
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
[data-testid="stMetricValue"] p {
  background: linear-gradient(180deg, #ffffff 25%, #ffc58f 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}

/* ---------- sky behind the whole page: stars, meteors, rising embers ---------- */
.bc-sky { position: fixed; inset: 0; z-index: -1; overflow: hidden; pointer-events: none; }
.bc-stars { position: absolute; inset: 0; }
.bc-stars-a {
  background-image:
    radial-gradient(1px 1px at 23px 41px, rgba(255,255,255,.75), transparent 60%),
    radial-gradient(1px 1px at 131px 97px, rgba(200,220,255,.60), transparent 60%),
    radial-gradient(1.5px 1.5px at 71px 163px, rgba(255,255,255,.50), transparent 60%);
  background-size: 260px 260px, 340px 340px, 410px 410px;
  animation: bc-twinkle 6s ease-in-out infinite alternate;
}
.bc-stars-b {
  background-image:
    radial-gradient(1px 1px at 211px 19px, rgba(255,236,210,.65), transparent 60%),
    radial-gradient(1px 1px at 301px 233px, rgba(255,255,255,.50), transparent 60%),
    radial-gradient(2px 2px at 417px 120px, rgba(190,215,255,.55), transparent 60%);
  background-size: 530px 530px, 610px 610px, 790px 790px;
  animation: bc-twinkle 9s ease-in-out -4s infinite alternate-reverse;
}
.bc-meteor {
  position: absolute; top: var(--top); left: var(--left); width: 170px; height: 1.5px; border-radius: 2px;
  background: linear-gradient(90deg, rgba(255,255,255,.95), rgba(255,190,130,.55) 25%, rgba(255,140,60,0));
  filter: drop-shadow(0 0 5px rgba(255,200,150,.7));
  opacity: 0; animation: bc-meteor var(--t) linear var(--d) infinite;
}
.bc-ember {
  position: absolute; bottom: -12px; left: var(--x); width: var(--s); height: var(--s); border-radius: 50%;
  background: #ffc98a;
  box-shadow: 0 0 6px 2px rgba(255,138,61,.7), 0 0 14px 4px rgba(255,90,30,.25);
  opacity: 0; animation: bc-rise var(--t) linear var(--d) infinite;
}
@keyframes bc-meteor {
  0%   { transform: rotate(-32deg) translateX(0); opacity: 0; }
  1.5% { opacity: 1; }
  9%   { transform: rotate(-32deg) translateX(-780px); opacity: 0; }
  100% { transform: rotate(-32deg) translateX(-780px); opacity: 0; }
}
@keyframes bc-rise {
  0%   { transform: translate(0, 0); opacity: 0; }
  8%   { opacity: .85; }
  50%  { transform: translate(var(--w), -34vh); opacity: .55; }
  100% { transform: translate(calc(var(--w) * -0.6), -72vh); opacity: 0; }
}

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
.bc-yr { transition: color .2s ease; }
.bc-head span { transition: color .2s ease; }
.bc-row:hover .bc-yr { color: #ffb072; }
/*MONTH_RULES*/
.bc-cell {
  position: relative; height: 24px; border-radius: 4px; background: var(--c);
  transition: transform .24s cubic-bezier(.34,1.56,.64,1), box-shadow .2s ease, opacity .25s ease;
  animation: bc-ignite .45s cubic-bezier(.2,.8,.2,1) backwards;
  animation-delay: calc(var(--i) * 16ms);
}
/* the square under the pointer pops out of the grid; the rest fall back */
.bc-cal:has(.bc-cell:hover) .bc-cell:not(:hover) { opacity: .45; }
.bc-cell:hover {
  transform: scale(1.6) translateY(-3px); z-index: 20;
  box-shadow: 0 12px 28px rgba(0,0,0,.7), 0 0 0 1px rgba(255,255,255,.9), 0 0 26px 2px var(--c);
}
/* the fiercest months smoulder */
.bc-hot::after {
  content: ""; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
  box-shadow: 0 0 11px 1px var(--c);
  animation: bc-smoulder 2.6s ease-in-out infinite alternate;
  animation-delay: calc(var(--i) * -170ms);
}
@keyframes bc-ignite { from { opacity: 0; transform: scale(.3); filter: brightness(2.2); } }
@keyframes bc-smoulder { from { opacity: .15; } to { opacity: .9; } }
.bc-yr { line-height: 24px; }
.bc-empty { height: 24px; border-radius: 4px; border: 1px dashed #1c2740; }
.bc-tip {
  position: absolute; bottom: calc(100% + 9px); left: 50%; width: 18.5rem;
  transform: translateX(-50%) scale(.625); transform-origin: bottom center;
  padding: .68rem .86rem; border-radius: 10px; background: rgba(14,22,38,.96); border: 1.6px solid #2a3a58;
  color: #c3c8d4; font-size: 1.18rem; line-height: 1.4; text-align: left;
  opacity: 0; visibility: hidden; pointer-events: none; transition: opacity .15s ease .05s;
  box-shadow: 0 12px 32px rgba(0,0,0,.65);
}
.bc-tip b { display: block; color: #eef2fa; font-size: 1.3rem; }
.bc-tip i { display: block; font-style: normal; color: #8b97ad; font-size: 1.05rem; margin-top: .2rem; }
.bc-cell:hover .bc-tip { opacity: 1; visibility: visible; }
.bc-left .bc-tip  { left: 0; transform: scale(.625); transform-origin: bottom left; }
.bc-right .bc-tip { left: auto; right: 0; transform: scale(.625); transform-origin: bottom right; }
.bc-low .bc-tip   { bottom: auto; top: calc(100% + 9px); }
.bc-low.bc-cell .bc-tip { transform-origin: top center; }
.bc-low.bc-left .bc-tip { transform-origin: top left; }
.bc-low.bc-right .bc-tip { transform-origin: top right; }

.bc-legend { display: flex; align-items: flex-start; gap: 1.6rem; margin: .2rem 0 1rem 3.2rem; color: #8b97ad; font-size: .8rem; }
.bc-scale { flex: 0 1 22rem; min-width: 12rem; }
.bc-bar { height: 10px; border-radius: 5px; }
.bc-ticks { position: relative; height: 1.1rem; margin-top: 4px; font-size: .75rem; }
.bc-ticks span { position: absolute; top: 0; transform: translateX(-50%); white-space: nowrap; }
.bc-legend > span { line-height: 10px; }

/* ---------- motion tied to scrolling ----------
   Uses CSS scroll-driven animations (Chrome, Edge, Safari 26+).
   Other browsers skip this block and show the page still. */
.bc-progress, .bc-limb, .bc-scan, .bc-glow { display: none; }
@supports (animation-timeline: view()) {
  [data-testid="stMain"] { scroll-timeline: --bc-page block; }

  /* each block rises into place as it enters the screen */
  [data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:not(:has(.bc-sky)) {
    animation: bc-reveal linear both; animation-timeline: view(); animation-range: entry 0% entry 150px;
  }
  /* the banner sinks back as it leaves */
  .bc-hero { animation: bc-hero-out linear both; animation-timeline: view(); animation-range: exit 0% exit 100%; }

  /* burn line across the top: how far down the page you are */
  .bc-progress {
    display: block; position: fixed; top: 0; left: 0; right: 0; height: 3px; z-index: 999999;
    transform-origin: 0 50%; transform: scaleX(0); pointer-events: none;
    background: linear-gradient(90deg, #a53d14, #ff8a3d 60%, #ffe2b8);
    box-shadow: 0 0 12px rgba(255,138,61,.8);
    animation: bc-progress linear both; animation-timeline: --bc-page;
  }

  /* stars drift at two depths */
  .bc-stars { inset: 0 0 -40% 0; }
  .bc-stars-a { animation: bc-twinkle 6s ease-in-out infinite alternate, bc-drift-a linear both;
                animation-timeline: auto, --bc-page; }
  .bc-stars-b { animation: bc-twinkle 9s ease-in-out -4s infinite alternate-reverse, bc-drift-b linear both;
                animation-timeline: auto, --bc-page; }

  /* the fire glow strengthens and the burning Earth rises as you descend */
  .bc-glow {
    display: block; position: absolute; left: 0; right: 0; bottom: 0; height: 65vh;
    background: radial-gradient(90% 100% at 50% 100%, rgba(255,106,40,.30), rgba(255,106,40,.07) 50%, transparent 72%);
    animation: bc-glow linear both; animation-timeline: --bc-page;
  }
  .bc-limb {
    display: block; position: absolute; left: 50%; top: 100%; width: 4800px; height: 4800px;
    margin-left: -2400px; border-radius: 50%;
    background: radial-gradient(circle at 50% 0%, #1a2c4a 0, #0a1426 3%, #060b16 8%);
    box-shadow: 0 0 60px 6px rgba(255,120,50,.28), 0 0 2px 1px rgba(255,200,160,.7);
    animation: bc-limb linear both; animation-timeline: --bc-page;
  }

  /* a satellite tracks down the right edge with the scroll position */
  .bc-scan { display: block; position: absolute; right: 30px; top: 12vh; bottom: 14vh; width: 1px;
             background: linear-gradient(180deg, transparent, rgba(120,170,255,.28) 12%, rgba(120,170,255,.28) 88%, transparent); }
  .bc-scan-sat { position: absolute; left: 0; top: 0; width: 0; height: 0;
                 animation: bc-descend linear both; animation-timeline: --bc-page; }

  /* room below the last block so everything can finish animating in */
  [data-testid="stMainBlockContainer"] { padding-bottom: 12rem; }

  /* charts draw themselves as you reach them: lines from left to right, bars up from the baseline */
  [data-testid="stVegaLiteChart"] {
    animation: bc-wipe linear both; animation-timeline: view(); animation-range: entry 30% contain 30%;
  }
  [class*="st-key-bars_"] [data-testid="stVegaLiteChart"] { animation-name: bc-grow; }
  /* the map opens from its centre */
  [data-testid="stDeckGlJsonChart"] {
    animation: bc-iris linear both; animation-timeline: view(); animation-range: entry 20% contain 25%;
  }
  /* number cards pop in (uses "scale" so the hover lift, which uses "transform", still works) */
  [data-testid="stMetric"] {
    animation: bc-pop linear both; animation-timeline: view(); animation-range: cover 0% cover 22%;
  }
  /* calendar rows slide in one after another */
  .bc-row { position: relative; }
  .bc-row:hover { z-index: 30; }
  .bc-row:not(.bc-head) {
    animation: bc-row-in linear both; animation-timeline: view(); animation-range: cover 0% cover 14%;
  }
  /* section headings get an ember underline that draws in */
  [data-testid="stHeading"] h3 {
    padding-bottom: .45rem;
    background: linear-gradient(90deg, #ff8a3d, rgba(255,138,61,0)) no-repeat 0 100% / 110px 2px;
    animation: bc-underline linear both; animation-timeline: view(); animation-range: cover 0% cover 25%;
  }

  @keyframes bc-wipe      { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
  @keyframes bc-grow      { from { clip-path: inset(100% 0 0 0); } to { clip-path: inset(0 0 0 0); } }
  @keyframes bc-iris      { from { clip-path: circle(0% at 50% 50%); } to { clip-path: circle(75% at 50% 50%); } }
  @keyframes bc-pop       { from { opacity: 0; scale: .88; } }
  @keyframes bc-row-in    { from { opacity: 0; transform: translateX(-36px); } }
  @keyframes bc-underline { from { background-size: 0 2px; } }
  @keyframes bc-reveal   { from { opacity: 0; transform: translateY(40px) scale(.97); } }
  @keyframes bc-hero-out { to { opacity: .2; transform: translateY(40px) scale(.93); } }
  @keyframes bc-progress { to { transform: scaleX(1); } }
  @keyframes bc-drift-a  { to { transform: translateY(-10%); } }
  @keyframes bc-drift-b  { to { transform: translateY(-24%); } }
  @keyframes bc-glow     { from { opacity: 0; } to { opacity: 1; } }
  @keyframes bc-limb     { to { transform: translateY(-150px); } }
  @keyframes bc-descend  { to { transform: translateY(74vh); } }
}
@media (max-width: 900px) { .bc-scan { display: none; } }

@media (prefers-reduced-motion: reduce) {
  .bc-progress, .bc-limb, .bc-scan, .bc-glow { display: none; }
  [data-testid="stMainBlockContainer"] [data-testid="stElementContainer"], .bc-hero { animation: none; }
  [data-testid="stVegaLiteChart"], [data-testid="stDeckGlJsonChart"], [data-testid="stMetric"],
  .bc-row:not(.bc-head), [data-testid="stHeading"] h3 { animation: none; }
  .bc-hero-stars, .bc-fire, .bc-orbit, .bc-stars, .bc-cell, .bc-hot::after { animation: none; }
  .bc-meteor, .bc-ember { display: none; }
  .bc-cell, .bc-tip, [data-testid="stMetric"] { transition: none; }
}
</style>
"""

# hovering a square lights up its month heading
CSS = CSS.replace("/*MONTH_RULES*/", "\n".join(
    f".bc-cal:has(.bc-m{m}:hover) .bc-head span:nth-child({m + 1}) {{ color: #ffb072; }}"
    for m in range(1, 13)))

# meteors: (top, left, cycle seconds, delay seconds)
METEORS = [("6%", "78%", 11, 1.5), ("18%", "96%", 17, 6.0), ("2%", "52%", 23, 12.0), ("30%", "99%", 14, 9.0)]

# embers rising from the fire glow: (left %, size px, rise seconds, delay seconds, sideways drift px)
EMBERS = [(4, 3, 19, -2, 30), (11, 2, 24, -14, -24), (17, 4, 21, -8, 40), (24, 2, 27, -20, -34),
          (31, 3, 18, -5, 22), (38, 2, 25, -17, -28), (45, 3, 22, -11, 36), (52, 2, 28, -3, -20),
          (59, 4, 20, -15, 28), (66, 2, 26, -9, -38), (73, 3, 19, -18, 24), (80, 2, 23, -6, -30),
          (87, 3, 27, -22, 34), (94, 2, 21, -12, -22)]

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
    meteors = "".join(
        f'<span class="bc-meteor" style="--top:{top};--left:{left};--t:{t}s;--d:{d}s"></span>'
        for top, left, t, d in METEORS)
    embers = "".join(
        f'<span class="bc-ember" style="--x:{x}%;--s:{s}px;--t:{t}s;--d:{d}s;--w:{w}px"></span>'
        for x, s, t, d, w in EMBERS)
    st.html(f"""
<div class="bc-sky" aria-hidden="true">
  <div class="bc-stars bc-stars-a"></div><div class="bc-stars bc-stars-b"></div>
  <div class="bc-glow"></div><div class="bc-limb">{fires}</div>
  <div class="bc-scan"><div class="bc-scan-sat"><div class="bc-beam"></div>{SATELLITE}</div></div>
  {meteors}{embers}
</div>
<div class="bc-progress" aria-hidden="true"></div>
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


def standalone(title, body):
    """A complete web page holding the calendar, for the download button."""
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f"<title>{html.escape(title)}</title>{CSS}</head>"
            '<body style="margin:0;padding:28px 32px 48px;background:#060912;color:#e6ebf5;'
            'font-family:\'Segoe UI\',Arial,sans-serif">'
            f'<h2 style="margin:0 0 4px;font-weight:600">{html.escape(title)}</h2>'
            '<p style="margin:0 0 20px;color:#8b97ad;font-size:.9rem">VIIRS-equivalent hotspots from NASA FIRMS '
            "active-fire data (MODIS and VIIRS, harmonised). Hover over a square for the figures.</p>"
            f"{body}</body></html>")


def calendar(view, by_count=True):
    st.html(calendar_html(view, by_count))


def calendar_html(view, by_count=True):
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
            hot = " bc-hot" if t >= 0.8 else ""
            cells.append(f'<div class="bc-cell bc-m{month}{side}{low}{hot}" style="--c:{colour};--i:{i + month}">'
                         f'<span class="bc-tip">{tip}</span></div>')
        out.append('<div class="bc-row">' + "".join(cells) + "</div>")
    out.append("</div>")
    return "".join(out)
