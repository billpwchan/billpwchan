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


def _windows(n, start, end):
    """Split [start, end] (percent of the loop) into n equal dwell windows."""
    step = (end - start) / n
    return [(start + i * step, start + (i + 1) * step) for i in range(n)]


def scrub(uid, pts, labels, top, bottom, right_edge, dur=16, color=None):
    """Auto-playing crosshair that reads a chart like a trader would: glides through `pts`,
    showing each label as it passes, holds on the latest value, fades, repeats."""
    color = color or T["amber"]
    n = len(pts)
    wins = _windows(n, 4, 78)
    move = "".join(f"{a:.2f}%{{transform:translate({x:.1f}px,0)}}" for (a, _), (x, _) in zip(wins, pts))
    dot = "".join(f"{a:.2f}%{{transform:translate({x:.1f}px,{y:.1f}px)}}" for (a, _), (x, y) in zip(wins, pts))
    css = (f"@keyframes {uid}m{{0%{{transform:translate({pts[0][0]:.1f}px,0)}}{move}100%{{transform:translate({pts[-1][0]:.1f}px,0)}}}}\n"
           f"@keyframes {uid}d{{0%{{transform:translate({pts[0][0]:.1f}px,{pts[0][1]:.1f}px)}}{dot}100%{{transform:translate({pts[-1][0]:.1f}px,{pts[-1][1]:.1f}px)}}}}\n"
           f"@keyframes {uid}f{{0%,2%{{opacity:0}}5%,90%{{opacity:1}}96%,100%{{opacity:0}}}}\n"
           f".{uid}{{animation:{uid}f {dur}s linear infinite}}\n"
           f".{uid}m{{animation:{uid}m {dur}s linear infinite}}\n.{uid}d{{animation:{uid}d {dur}s linear infinite}}\n")
    out = [f'<g class="{uid}">',
           f'<g class="{uid}m"><line x1="0" y1="{top}" x2="0" y2="{bottom}" stroke="{color}" stroke-opacity=".55" stroke-dasharray="2 2"/>']
    for i, ((a, b), (x, _), lab) in enumerate(zip(wins, pts, labels)):
        last = i == n - 1
        end = 92 if last else b
        css += f"@keyframes {uid}l{i}{{0%,{a - .01:.2f}%{{opacity:0}}{a:.2f}%,{end:.2f}%{{opacity:1}}{end + .01:.2f}%,100%{{opacity:0}}}}\n"
        w = text_width(lab, 10) + 12
        lx = 6 if x + 6 + w < right_edge else -6 - w
        out.append(f'<g style="animation:{uid}l{i} {dur}s linear infinite;opacity:0">'
                   f'<rect x="{lx:.1f}" y="{top - 2}" width="{w:.1f}" height="17" rx="3" fill="{T["bg"]}" stroke="{color}" stroke-opacity=".7"/>'
                   f'<text x="{lx + 6:.1f}" y="{top + 10}" class="m" font-size="10" fill="{T["text"]}">{esc(lab)}</text></g>')
    out.append(f'</g><circle r="3.6" fill="{T["bg"]}" stroke="{color}" stroke-width="2" class="{uid}d"/></g>')
    css += f"@media (prefers-reduced-motion:reduce){{.{uid}{{display:none}}}}\n"
    return "".join(out), css


def row_scan(uid, rects, dur, color=None):
    """A cursor that steps down a blotter, resting on each row in turn."""
    color = color or T["amber"]
    wins = _windows(len(rects), 0, 100)
    kf = "".join(f"{a:.2f}%,{b - .01:.2f}%{{transform:translate({x:.1f}px,{y:.1f}px)}}" for (a, b), (x, y, _, _) in zip(wins, rects))
    w, h = rects[0][2], rects[0][3]
    css = (f"@keyframes {uid}{{{kf}}}\n.{uid}{{animation:{uid} {dur}s steps(1) infinite}}\n"
           f"@media (prefers-reduced-motion:reduce){{.{uid}{{display:none}}}}\n")
    svg = (f'<g class="{uid}"><rect width="{w:.1f}" height="{h:.1f}" rx="4" fill="{color}" fill-opacity=".07"/>'
           f'<rect width="2" height="{h:.1f}" fill="{color}"/></g>')
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
