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

BASE_CSS = """
.m{font-family:'Plex',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-numeric:tabular-nums}
.b{font-weight:600}
.rise{animation:rise .5s ease-out backwards}
@keyframes rise{from{opacity:0;transform:translateY(5px)}}
.draw{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1.8s .4s cubic-bezier(.4,0,.2,1) forwards}
@keyframes draw{to{stroke-dashoffset:0}}
.fadein{animation:fade 1s 1s both}
@keyframes fade{from{opacity:0}}
.live{animation:blink 1.6s ease-in-out infinite}
@keyframes blink{50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){.rise,.fadein,.live{animation:none}.draw{animation:none;stroke-dashoffset:0}}
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


def svg_doc(w, h, body, title, css=""):
    frame = f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="12" fill="{T["bg"]}" stroke="{T["line"]}"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{esc(title)}"><title>{esc(title)}</title>\n<style>\n{font_css(body)}{BASE_CSS}{css}\n</style>\n'
            f"{frame}\n{body}\n</svg>\n")


def chip(x, y, label, w=None, size=11.5):
    w = w or text_width(label, size) + 18
    return (f'<rect x="{x}" y="{y}" width="{w:.1f}" height="20" rx="3" fill="{T["amber"]}"/>'
            f'<text x="{x + w / 2:.1f}" y="{y + 14.5}" class="m b" font-size="{size}" fill="{T["ink"]}" text-anchor="middle">{esc(label)}</text>'), w


def title_bar(w, code, title, right=""):
    """Terminal function bar: amber mnemonic, title, right-aligned status."""
    c, cw = chip(16, 14, code)
    out = c + f'<text x="{16 + cw + 14:.1f}" y="28.5" class="m" font-size="11.5" fill="{T["text"]}">{esc(title)}</text>'
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
