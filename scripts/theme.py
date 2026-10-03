"""Design tokens, embedded fonts and SVG primitives shared by every card."""
import base64
import html
import io
import re
from functools import lru_cache
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONTS = {400: FONT_DIR / "ibm-plex-mono-latin-400-normal.woff2", 600: FONT_DIR / "ibm-plex-mono-latin-600-normal.woff2"}

# Always-dark terminal palette: every card is a screen, so it reads the same on light and dark GitHub.
T = dict(bg="#090b0e", panel="#0e1217", line="#1d232c", grid="#161b22", text="#ebe7df", muted="#7d8796",
         amber="#ffb224", amber_dim="#2a1f08", ink="#161003", up="#35d07f", down="#ff5d62", cyan="#62c7ff")
CW = 0.6  # IBM Plex Mono advance width per em
W = 880   # native width of every card; GitHub scales it to the README column

# Motion language: nothing animates in. Panels are complete at rest; ambient loops read the data
# (crosshairs, row cursors), alert states breathe, and values that moved since the last render flash once.
BASE_CSS = """
.m{font-family:'Plex',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-numeric:tabular-nums}
.b{font-weight:600}
.live{animation:blink 1.6s ease-in-out infinite}
@keyframes blink{50%{opacity:.25}}
.breathe{animation:breathe 3.2s ease-in-out infinite}
@keyframes breathe{50%{stroke-opacity:.25}}
.flash{fill-opacity:0;animation:flash 2.6s .8s ease-out both}
@keyframes flash{0%{fill-opacity:0}12%{fill-opacity:.42}100%{fill-opacity:0}}
@media (prefers-reduced-motion:reduce){.live,.breathe,.flash{animation:none}}
"""


def esc(s):
    return html.escape(str(s), quote=True)


def text_width(s, size):
    return sum(size * (1.0 if ord(ch) > 0x2E80 else CW) for ch in str(s))


@lru_cache(maxsize=None)
def _subset(weight, chars):
    font = TTFont(FONTS[weight])
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "tnum", "lnum"]
    opts.name_IDs = []
    sub = subset.Subsetter(opts)
    sub.populate(text=chars)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def font_css(body):
    """Embed only the glyphs this card uses; GitHub's CSP allows data: fonts inside SVG images."""
    text = " ".join(html.unescape(t) for t in re.findall(r">([^<>]+)<", body))
    chars = "".join(sorted(set(text + " 0123456789.,%+-")))
    return "".join(f"@font-face{{font-family:'Plex';font-weight:{w};src:url(data:font/woff2;base64,{_subset(w, chars)}) format('woff2')}}\n"
                   for w in FONTS)


def svg_doc(w, h, body, title, css="", inset=(0, 0)):
    """inset=(left, right) leaves transparent gutter so side-by-side tiles meet the same gap as stacked ones."""
    l, r = inset
    frame = f'<rect x="{l + .5}" y=".5" width="{w - l - r - 1}" height="{h - 1}" rx="10" fill="{T["bg"]}" stroke="{T["line"]}"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{esc(title)}"><title>{esc(title)}</title>\n<style>\n{font_css(body)}{BASE_CSS}{css}\n</style>\n'
            f"{frame}\n{body}\n</svg>\n")


def chip(x, y, label, w=None, size=11.5):
    w = w or text_width(label, size) + 18
    return (f'<rect x="{x}" y="{y}" width="{w:.1f}" height="20" rx="3" fill="{T["amber"]}"/>'
            f'<text x="{x + w / 2:.1f}" y="{y + 14.5}" class="m b" font-size="{size}" fill="{T["ink"]}" text-anchor="middle">{esc(label)}</text>'), w


def title_bar(w, title, right=""):
    """Panel heading shared by every card: amber marker, amber title, muted right-aligned status."""
    out = (f'<rect x="18" y="19" width="6" height="11" rx="1" fill="{T["amber"]}"/>'
           f'<text x="32" y="28.5" class="m b" font-size="11.5" letter-spacing=".6" fill="{T["amber"]}">{esc(title)}</text>')
    if right:
        out += f'<text x="{w - 18}" y="28.5" class="m" font-size="11" fill="{T["muted"]}" text-anchor="end">{esc(right)}</text>'
    return out


def label(x, y, s, anchor="start", size=9.5, fill=None):
    return (f'<text x="{x}" y="{y}" class="m" font-size="{size}" letter-spacing=".8" fill="{fill or T["muted"]}" '
            f'text-anchor="{anchor}">{esc(s)}</text>')


def line_path(values, x0, y0, w, h, lo=None, hi=None):
    lo = min(values) if lo is None else lo
    hi = max(values) if hi is None else hi
    span = (hi - lo) or 1
    step = w / max(len(values) - 1, 1)
    pts = [(x0 + i * step, y0 + h - (v - lo) / span * h) for i, v in enumerate(values)]
    return pts, "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def signed(v, d=2, suffix="%"):
    return f"{'+' if v >= 0 else '-'}{abs(v):.{d}f}{suffix}"


def tone(v):
    return T["up"] if v >= 0 else T["down"]


def fmt_num(n):
    return f"{n / 1000:.1f}k" if n >= 10000 else f"{n:,}"


def fmt_price(p):
    return f"{p:,.0f}" if p >= 10000 else f"{p:,.2f}"


def _ease(u):
    """easeInOutCubic: a cursor leaves gently, travels, and settles."""
    return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2


def _lerp_pts(pts, f):
    i = min(int(f), len(pts) - 2)
    t = f - i
    (x1, y1), (x2, y2) = pts[i], pts[i + 1]
    return x1 + (x2 - x1) * t, y1 + (y2 - y1) * t


def crosshair(uid, path, stops, xlabels, ylabels, box, color=None, dwell=1.8, glide=1.1, hold=3.2, tags_top=None, tag_side=None):
    """A trader's crosshair. Glides along the real curve (`path`, every data point) with eased motion,
    settles on each stop and shows its readings as axis tags (date on top, value on the side), then
    rests on the latest point and fades. `stops` index into `path`; labels are per stop.
    box = (left, top, right, bottom) of the plot area."""
    color = color or T["amber"]
    left, top, right, bottom = box
    tags_top = top - 9 if tags_top is None else tags_top
    tag_side = right + 4 if tag_side is None else tag_side
    fade_in, fade_out, gap = .6, .8, 1.0
    # timeline of (seconds, fractional index into path); dwell windows for the tags
    events, windows, t = [(0, stops[0])], [], fade_in
    for k, idx in enumerate(stops):
        stay = hold if k == len(stops) - 1 else dwell
        events.append((t, idx))
        windows.append((t, t + stay))
        t += stay
        events.append((t, idx))
        if k < len(stops) - 1:
            nxt = stops[k + 1]
            for j in range(1, 17):
                u = j / 16
                events.append((t + glide * u, idx + (nxt - idx) * _ease(u)))
            t += glide
    end = t
    total = end + fade_out + gap
    pct = lambda sec: sec / total * 100
    pos = [(pct(sec), _lerp_pts(path, f)) for sec, f in events]
    kx = "".join(f"{q:.2f}%{{transform:translate({x:.1f}px,0)}}" for q, (x, _) in pos)
    ky = "".join(f"{q:.2f}%{{transform:translate(0,{y:.1f}px)}}" for q, (_, y) in pos)
    kd = "".join(f"{q:.2f}%{{transform:translate({x:.1f}px,{y:.1f}px)}}" for q, (x, y) in pos)
    css = (f"@keyframes {uid}x{{{kx}100%{{transform:translate({pos[-1][1][0]:.1f}px,0)}}}}\n"
           f"@keyframes {uid}y{{{ky}100%{{transform:translate(0,{pos[-1][1][1]:.1f}px)}}}}\n"
           f"@keyframes {uid}d{{{kd}100%{{transform:translate({pos[-1][1][0]:.1f}px,{pos[-1][1][1]:.1f}px)}}}}\n"
           f"@keyframes {uid}o{{0%{{opacity:0}}{pct(fade_in):.2f}%,{pct(end):.2f}%{{opacity:1}}{pct(end + fade_out):.2f}%,100%{{opacity:0}}}}\n"
           f".{uid}{{animation:{uid}o {total:.2f}s linear infinite}}"
           f".{uid}x{{animation:{uid}x {total:.2f}s linear infinite}}.{uid}y{{animation:{uid}y {total:.2f}s linear infinite}}"
           f".{uid}d{{animation:{uid}d {total:.2f}s linear infinite}}\n")
    xtags, ytags = "", ""
    for k, ((a, b), idx) in enumerate(zip(windows, stops)):
        x, y = _lerp_pts(path, idx)
        f0, f1 = pct(a), pct(min(a + .3, b))
        g0, g1 = pct(max(b - .25, a)), pct(b)
        css += (f"@keyframes {uid}t{k}{{0%,{f0:.2f}%{{opacity:0;transform:translateY(2px)}}{f1:.2f}%,{g0:.2f}%{{opacity:1;transform:none}}"
                f"{g1:.2f}%,100%{{opacity:0;transform:none}}}}\n")
        anim = f'style="opacity:0;animation:{uid}t{k} {total:.2f}s linear infinite"'
        if xlabels and xlabels[k]:
            w = text_width(xlabels[k], 9.5) + 12
            off = min(max(-w / 2, left - x), right - x - w)   # keep the tag inside the plot
            xtags += (f'<g {anim}><rect x="{off:.1f}" y="{tags_top - 11:.1f}" width="{w:.1f}" height="15" rx="2" fill="{color}"/>'
                      f'<text x="{off + 6:.1f}" y="{tags_top:.1f}" class="m b" font-size="9.5" fill="{T["ink"]}">{esc(xlabels[k])}</text></g>')
        if ylabels and ylabels[k]:
            w = text_width(ylabels[k], 9.5) + 10
            ytags += (f'<g {anim}><rect x="{tag_side:.1f}" y="-7.5" width="{w:.1f}" height="15" rx="2" fill="{T["bg"]}" stroke="{color}"/>'
                      f'<text x="{tag_side + 5:.1f}" y="3.5" class="m b" font-size="9.5" fill="{T["text"]}">{esc(ylabels[k])}</text></g>')
    line = f'stroke="{color}" stroke-opacity=".5" stroke-dasharray="3 3"'
    svg = (f'<g class="{uid}">'
           f'<g class="{uid}x"><line x1="0" y1="{top}" x2="0" y2="{bottom}" {line}/>{xtags}</g>'
           f'<g class="{uid}y"><line x1="{left}" y1="0" x2="{right}" y2="0" {line}/>{ytags}</g>'
           f'<circle r="6" fill="{color}" fill-opacity=".18" class="{uid}d"/>'
           f'<circle r="3.2" fill="{T["bg"]}" stroke="{color}" stroke-width="2" class="{uid}d"/></g>')
    css += f"@media (prefers-reduced-motion:reduce){{.{uid}{{display:none}}}}\n"
    return svg, css


def glide_cursor(uid, spots, dwell=1.7, glide=.6, color=None, readouts=None, readout_xy=None):
    """A highlight that eases from spot to spot (rows of a blotter, cells of a matrix), settling on each;
    optional read-out text crossfades in a fixed footer position."""
    color = color or T["amber"]
    n = len(spots)
    total = n * (dwell + glide)
    pct = lambda sec: sec / total * 100
    kf, t = "", 0.0
    for x, y, _, _ in spots:
        kf += f"{pct(t):.2f}%,{pct(t + dwell):.2f}%{{transform:translate({x:.1f}px,{y:.1f}px)}}"
        t += dwell + glide
    x0, y0 = spots[0][:2]
    w, h = spots[0][2], spots[0][3]
    css = (f"@keyframes {uid}{{{kf}100%{{transform:translate({x0:.1f}px,{y0:.1f}px)}}}}\n"
           f".{uid}{{animation:{uid} {total:.2f}s cubic-bezier(.65,0,.35,1) infinite}}\n")
    svg = f'<g class="{uid}"><rect width="{w:.1f}" height="{h:.1f}" rx="5" fill="{color}" fill-opacity=".07" stroke="{color}" stroke-opacity=".55"/></g>'
    if readouts:
        rx, ry = readout_xy
        t = 0.0
        for k, txt in enumerate(readouts):
            a, b = t, t + dwell
            css += (f"@keyframes {uid}r{k}{{0%,{pct(a):.2f}%{{opacity:0}}{pct(a + .3):.2f}%,{pct(b - .2):.2f}%{{opacity:1}}"
                    f"{pct(b):.2f}%,100%{{opacity:0}}}}\n")
            svg += (f'<text x="{rx}" y="{ry}" class="m" font-size="10" fill="{T["text"]}" text-anchor="end" style="opacity:0;'
                    f'animation:{uid}r{k} {total:.2f}s linear infinite">{txt}</text>')
            t += dwell + glide
    css += f"@media (prefers-reduced-motion:reduce){{.{uid}{{display:none}}}}\n"
    return svg, css

# Values from the previous render (state.json on the output branch) and this one.
PREV, CURR = {}, {}


def flash(key, value, x, y, w, h, tol=0.0):
    """Record a value; if it moved by more than `tol` since the last render, return a one-shot
    green/red flash behind it, like a quote cell updating on a terminal."""
    CURR[key] = value
    old = PREV.get(key)
    if old is None or abs(value - old) <= tol:
        return ""
    col = T["up"] if value > old else T["down"]
    return f'<rect class="flash" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="3" fill="{col}"/>'
