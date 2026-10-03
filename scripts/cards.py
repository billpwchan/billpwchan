"""Card renderers. Each returns a complete SVG document string."""
import datetime as dt
import math
from collections import Counter

from theme import (CW, T, W, chip, crosshair, esc, flash, fmt_num, fmt_price, glide_cursor, label, line_path, signed, svg_doc,
                   text_width, title_bar, tone)


SECTIONS = ["DES", "WORK", "LAB", "FLOW"]


def tabs(x, y, active):
    """Screen tabs repeated on every section strip; the active screen is amber and underlined."""
    out = ""
    for i, tab in enumerate(SECTIONS):
        s = f"{i + 1}) {tab}"
        w = text_width(s, 11.5)
        on = tab == active
        out += f'<text x="{x:.1f}" y="{y}" class="m{" b" if on else ""}" font-size="11.5" fill="{T["amber"] if on else T["muted"]}">{s}</text>'
        if on:
            out += f'<rect x="{x:.1f}" y="{y + 5}" width="{w:.1f}" height="2" fill="{T["amber"]}"/>'
        x += w + 20
    return out


def strip(active, status):
    """Section divider: the terminal switching to another screen."""
    h = 40
    b = [chip(16, 10, "BILL <GO>", w=88, size=12)[0], tabs(122, 24.5, active),
         f'<text x="{W - 18}" y="24.5" class="m" font-size="11" fill="{T["muted"]}" text-anchor="end">{esc(status)}</text>']
    return svg_doc(W, h, "".join(b), f"Section {SECTIONS.index(active) + 1}: {active}")


def keycap(code, title, sub, pos, n, accent=None):
    """Link key styled like a trading-keyboard key; pos/n decide which sides get a gutter."""
    w, h, g = W / n, 52, 3
    inset = (0 if pos == 0 else g, 0 if pos == n - 1 else g)
    x0 = inset[0]
    col = accent or T["amber"]
    cw = text_width(code, 10.5) + 14
    b = [f'<rect x="{x0 + 12}" y="16" width="{cw:.1f}" height="20" rx="3" fill="{col}"/>'
         f'<text x="{x0 + 12 + cw / 2:.1f}" y="30" class="m b" font-size="10.5" fill="{T["ink"]}" text-anchor="middle">{esc(code)}</text>'
         f'<text x="{x0 + 12 + cw + 10:.1f}" y="24" class="m b" font-size="11.5" fill="{T["text"]}">{esc(title)}</text>'
         f'<text x="{x0 + 12 + cw + 10:.1f}" y="39" class="m" font-size="9.5" fill="{T["muted"]}">{esc(sub)}</text>']
    return svg_doc(round(w), h, "".join(b), f"{title}: {sub}", inset=inset)


def recent(repos, ago):
    rows = repos[:5]
    H = 48 + len(rows) * 30 + 14
    b = [title_bar(W, "RECENT PUSHES", "MOST RECENTLY UPDATED PUBLIC REPOSITORIES")]
    for i, r in enumerate(rows):
        y = 64 + i * 30
        name = r["name"]
        desc = (r["description"] or "").strip()
        limit = 76 - len(name)
        out, width = "", 0.0
        for ch in desc:
            cw = 1.0 if ord(ch) > 0x2E80 else CW
            if width + cw > limit * CW:
                out = out.rstrip() + "..."
                break
            out, width = out + ch, width + cw
        lang = ((r.get("primaryLanguage") or {}).get("name") or "").upper()
        b.append(f'<g><text x="18" y="{y}" class="m b" font-size="12.5" fill="{T["text"]}">{esc(name)}</text>'
                 f'<text x="{18 + text_width(name, 12.5) + 14:.1f}" y="{y}" class="m" font-size="11.5" fill="{T["muted"]}">{esc(out)}</text>'
                 f'<text x="{W - 110}" y="{y}" class="m" font-size="10" fill="{T["cyan"]}" text-anchor="end">{esc(lang)}</text>'
                 f'<text x="{W - 18}" y="{y}" class="m" font-size="11" fill="{T["amber"]}" text-anchor="end">{esc(ago(r).upper())}</text></g>'
                 + (f'<line x1="18" y1="{y + 12.5}" x2="{W - 18}" y2="{y + 12.5}" stroke="{T["grid"]}"/>' if i < len(rows) - 1 else ""))
    cur, css = glide_cursor("rs", [(10, 64 + i * 30 - 18, W - 20, 26) for i in range(len(rows))], dwell=2.6, glide=.7)
    b.insert(1, cur)
    return svg_doc(W, H, "\n".join(b), "Recently pushed repositories", css)


def snake_panel(snake_svg):
    """Wrap Platane/snk output in the terminal frame so it reads as one more panel."""
    import re
    inner = snake_svg[snake_svg.index(">", snake_svg.index("<svg")) + 1:snake_svg.rindex("</svg>")]
    x0, y0, vw, vh = [float(v) for v in re.search(r'viewBox="([^"]+)"', snake_svg).group(1).split()]
    # keep the grid plus the snake's path around it; drop snk's progress bar and the dead space above it
    y0, vh = y0 + 12, min(vh, 7 * 16 + 44)
    vb = f"{x0:g} {y0:g} {vw:g} {vh:g}"
    ch = (W - 24) * vh / vw
    H = round(44 + ch + 8)
    head = title_bar(W, "CONTRIBUTION GRID", "LAST 12 MONTHS · THE SNAKE EATS EVERY ACTIVE DAY")
    body = head + f'<svg x="12" y="44" width="{W - 24}" height="{ch:.1f}" viewBox="{vb}">{inner}</svg>'
    return svg_doc(W, H, body, "Contribution grid with snake animation")


# ================================================================ hero
def hero(p):
    H = 344
    b = ['<defs><pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse">'
         '<rect width="4" height="1" fill="#ffffff" fill-opacity=".018"/></pattern>'
         '<radialGradient id="vig" cx="50%" cy="45%" r="75%"><stop offset="60%" stop-color="#000" stop-opacity="0"/>'
         '<stop offset="100%" stop-color="#000" stop-opacity=".45"/></radialGradient>'
         f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{T["amber"]}" stop-opacity=".28"/>'
         f'<stop offset="1" stop-color="{T["amber"]}" stop-opacity="0"/></linearGradient>'
         f'<clipPath id="tapeclip"><rect x="1" y="41" width="{W - 2}" height="30"/></clipPath>'
         f'<clipPath id="frame"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="11"/></clipPath></defs>']

    # function bar
    c, cw = chip(16, 11, "BILL <GO>", w=88, size=12)
    b.append(c)
    b.append(tabs(16 + cw + 18, 25.5, "DES"))
    right = [(p["stamp"] + "  ", T["muted"])]
    for name, state in p["sessions"]:
        live = state in ("OPEN", "24/7")
        right += [(f"{name} ", T["muted"]), (f"{state}  ", T["up"] if live else T["amber"] if state == "LUNCH" else T["muted"])]
    spans = "".join(f'<tspan fill="{col}">{esc(s)}</tspan>' for s, col in right)
    b.append(f'<text x="{W - 18 + text_width("  ", 11):.1f}" y="25.5" class="m" font-size="11" text-anchor="end" xml:space="preserve">{spans}</text>')
    b.append(f'<line x1="0" y1="40.5" x2="{W}" y2="40.5" stroke="{T["line"]}"/>'
             f'<rect x="1" y="41" width="{W - 2}" height="30" fill="{T["panel"]}"/>'
             f'<line x1="0" y1="71.5" x2="{W}" y2="71.5" stroke="{T["line"]}"/>')

    # ticker tape: one segment repeated, translated by exactly one segment width for a seamless loop
    fs, seg, pills, x = 12.5, [], [], 0.0
    for name, value, change, hot in p["tape"]:
        if hot:
            pills.append(f'<rect x="{x - 4:.1f}" y="47" width="{text_width(name, fs) + 8:.1f}" height="18" rx="3" fill="{T["amber"]}"/>')
        parts = [(name, T["ink"] if hot else T["amber"], "b"), (value, T["text"], "")]
        if change is not None:
            parts.append((signed(change), tone(change), ""))
        for s, col, cls in parts:
            seg.append(f'<tspan x="{x:.1f}" fill="{col}" class="{cls}">{esc(s)}</tspan>')
            x += (len(s) + 1) * fs * CW
        seg.append(f'<tspan x="{x:.1f}" fill="{T["line"]}">/</tspan>')
        x += 3 * fs * CW
    seg_w = x
    copies = max(2, math.ceil(W / seg_w) + 1)
    tape = "".join(f'<g transform="translate({k * seg_w:.1f},0)">{"".join(pills)}<text y="61" class="m" font-size="{fs}">{"".join(seg)}</text></g>'
                   for k in range(copies))
    b.append(f'<g clip-path="url(#tapeclip)"><g class="tape" style="animation-duration:{seg_w / 38:.1f}s"><g transform="translate(16,0)">{tape}</g></g></g>')

    # identity + function-code rows typed out once
    b.append(f'<text x="32" y="128" class="m b" font-size="38" letter-spacing="1" fill="{T["text"]}">{esc(p["name"])}</text>'
             f'<text x="34" y="154" class="m" font-size="12.5" letter-spacing="2.2" fill="{T["amber"]}">{esc(p["role"])}</text>')
    fs = 13.5
    for i, (code, val) in enumerate(p["rows"]):
        y = 188 + i * 28
        b.append(f'<rect x="32" y="{y - 14}" width="50" height="19" rx="2.5" fill="{T["amber_dim"]}" stroke="{T["amber"]}" stroke-opacity=".55"/>'
                 f'<text x="57" y="{y}" class="m b" font-size="10.5" fill="{T["amber"]}" text-anchor="middle">{esc(code)}</text>'
                 f'<text x="96" y="{y}" class="m" font-size="{fs}" fill="{T["text"]}">{esc(val)}</text>')
    ylast = 188 + (len(p["rows"]) - 1) * 28
    b.append(f'<rect class="cur" x="{96 + text_width(p["rows"][-1][1], fs) + 4:.1f}" y="{ylast - 12}" width="8" height="15" '
             f'fill="{T["amber"]}"/>')

    # contributions panel
    px, py, pw, ph = 548, 90, 308, 234
    year = p["year"]
    cum, acc = [], 0
    for v in year:
        acc += v
        cum.append(acc)
    big = f"{cum[-1]:,}"
    b.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="8" fill="{T["panel"]}" stroke="{T["line"]}"/>'
             f'<text x="{px + 16}" y="{py + 26}" class="m b" font-size="11.5" fill="{T["amber"]}">BILL:GH</text>'
             f'<text x="{px + 76}" y="{py + 26}" class="m" font-size="10.5" fill="{T["muted"]}">CONTRIBUTIONS · 52W</text>'
             + flash("hero.contrib12m", cum[-1], px + 12, py + 38, text_width(big, 28) + 8, 32)
             + f'<text x="{px + 16}" y="{py + 62}" class="m b" font-size="28" fill="{T["text"]}">{big}</text>'
             f'<text x="{px + 16 + text_width(big, 28) + 10:.1f}" y="{py + 62}" class="m" font-size="11.5" fill="{T["up"]}">12M · {fmt_num(p["total"]).upper()} ALL-TIME</text>')
    cx0, cy0, cw_, ch = px + 16, py + 80, pw - 60, 96
    for k in range(4):
        gy = cy0 + k * ch / 3
        val = cum[-1] * (1 - k / 3)
        b.append(f'<line x1="{cx0}" y1="{gy:.1f}" x2="{cx0 + cw_}" y2="{gy:.1f}" stroke="{T["line"]}" stroke-dasharray="2 3"/>'
                 f'<text x="{px + pw - 12}" y="{gy + 3.5:.1f}" class="m" font-size="9.5" fill="{T["muted"]}" text-anchor="end">'
                 f'{f"{val / 1000:.1f}k" if val >= 1000 else f"{val:.0f}"}</text>')
    pts, line = line_path(cum, cx0, cy0, cw_, ch, lo=0, hi=max(cum[-1], 1))
    b.append(f'<path d="{line} L{cx0 + cw_},{cy0 + ch} L{cx0},{cy0 + ch} Z" fill="url(#area)"/>'
             f'<path d="{line}" fill="none" stroke="{T["amber"]}" stroke-width="1.8" stroke-linejoin="round"/>'
             f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3.2" fill="{T["amber"]}"/>')
    # crosshair settles every two months along the real curve, then rests on today
    import datetime as _dt
    end = _dt.date.fromisoformat(p["end"]) if p.get("end") else None
    stops = [round(k * (len(cum) - 1) / 6) for k in range(7)]
    day = lambda i: (end - _dt.timedelta(days=len(cum) - 1 - i)).strftime("%d %b").upper() if end else ""
    xh_svg, xh_css = crosshair("xh", pts, stops, [day(i) for i in stops], [f"{cum[i]:,}" for i in stops],
                               (cx0, cy0, cx0 + cw_, cy0 + ch), tags_top=cy0 + 12, tag_side=cx0 + cw_ + 2)
    b.append(xh_svg)
    vy, vh, vmax, bw = cy0 + ch + 8, 26, max(max(year), 1), cw_ / len(year)
    bars = "".join(f'<rect x="{cx0 + i * bw:.2f}" y="{vy + vh - v / vmax * vh:.1f}" width="{max(bw - .3, .6):.2f}" height="{v / vmax * vh:.1f}"/>'
                   for i, v in enumerate(year) if v)
    b.append(f'<g fill="{T["amber"]}" fill-opacity=".45">{bars}</g>')
    stats = [("STREAK", f'{p["streak"]}D'), ("ACTIVE", f'{sum(1 for v in year if v)}/{len(year)}'), ("BEST", str(max(year)))]
    spans = "".join(f'{k} <tspan fill="{T["text"]}">{esc(v)}</tspan>   ' for k, v in stats)
    b.append(f'<text x="{px + 16}" y="{py + ph - 12}" class="m" font-size="10" fill="{T["muted"]}" xml:space="preserve">{spans.rstrip()}</text>')
    b.append(f'<rect width="{W}" height="{H}" fill="url(#scan)" clip-path="url(#frame)"/>'
             f'<rect width="{W}" height="{H}" fill="url(#vig)" clip-path="url(#frame)"/>')
    css = f"""
.tape{{animation:tape linear infinite}}
@keyframes tape{{to{{transform:translateX(-{seg_w:.1f}px)}}}}
.cur{{animation:cur 1.05s steps(1) infinite}}
@keyframes cur{{50%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{.tape,.cur{{animation:none}}}}
""" + xh_css
    return svg_doc(W, H, "\n".join(b), f'{p["name"]} — {p["role"].title()}', css)


# ================================================================ work cards
def work_card(r, copy, stars, now, side, dur=19):
    w, h = W // 2, 214
    inset = (0, 3) if side == 0 else (3, 0)
    lang = (r.get("primaryLanguage") or {}).get("name", "")
    b = [f'<text x="20" y="34" class="m b" font-size="15" fill="{T["amber"]}">{esc(r["name"])}</text>',
         f'<text x="{w - 18}" y="34" class="m" font-size="10" fill="{T["muted"]}" text-anchor="end">{esc(" · ".join(x for x in (lang.upper(), copy["tag"]) if x))}</text>',
         f'<text x="20" y="58" class="m" font-size="12" fill="{T["text"]}">{esc(copy["pitch"])}</text>',
         f'<text x="20" y="77" class="m" font-size="11.5" fill="{T["muted"]}">{esc(copy["zh"])}</text>']
    # stars as an equity curve since the first star
    cx, cy, cw, ch = 20, 100, w - 40, 58
    b.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" fill="{T["panel"]}" rx="4"/>')
    year_ago = now.replace(year=now.year - 1)
    gained = sum(1 for s in stars if s >= year_ago)
    if len(stars) >= 2:
        t0, t1 = stars[0].timestamp(), now.timestamp()
        n = 60
        buckets = [sum(1 for s in stars if s.timestamp() <= t0 + (t1 - t0) * k / (n - 1)) for k in range(n)]
        pts, line = line_path(buckets, cx + 6, cy + 8, cw - 12, ch - 16, lo=0, hi=max(buckets[-1], 1))
        b.append(f'<path d="{line} L{cx + cw - 6},{cy + ch - 8} L{cx + 6},{cy + ch - 8} Z" fill="{T["amber"]}" fill-opacity=".12"/>'
                 f'<path d="{line}" fill="none" stroke="{T["amber"]}" stroke-width="1.5"/>'
                 f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.6" fill="{T["amber"]}"/>'
                 + label(cx + 8, cy + ch + 13, str(stars[0].year), size=9)
                 + label(cx + cw - 2, cy + ch + 13, "NOW", "end", size=9))
        stops = [round(k * (n - 1) / 4) for k in range(5)]
        when = [dt.datetime.fromtimestamp(t0 + (t1 - t0) * i / (n - 1), dt.timezone.utc) for i in stops]
        xh, xh_css = crosshair(f"w{side}{len(stars) % 97}", pts, stops,
                               [f'{d.strftime("%b %y").upper()} · {buckets[i]:,}' for d, i in zip(when, stops)], None,
                               (cx + 6, cy + 8, cx + cw - 6, cy + ch - 8), tags_top=cy + 20, dwell=2.2, glide=1.4,
                               hold=3.6 + dur / 10)
        b.append(xh)
    else:
        xh_css = ""
        b.append(label(cx + cw / 2, cy + ch / 2 + 3, "STAR HISTORY BUILDING", "middle"))
    stats = [("STARS", fmt_num(r["stargazerCount"]), T["text"]), ("FORKS", fmt_num(r["forkCount"]), T["text"]),
             ("STARS 12M", f"+{gained}", T["up"] if gained else T["muted"])]
    x = 20
    css = xh_css
    for j, (k, v, col) in enumerate(stats):
        if j == 0:
            b.append(flash(f'stars.{r["name"].lower()}', r["stargazerCount"], x - 4, h - 24, text_width(v, 12.5) + 8, 19))
        b.append(label(x, h - 26, k, size=9) + f'<text x="{x}" y="{h - 10}" class="m b" font-size="12.5" fill="{col}">{esc(v)}</text>')
        x += 92
    b.append(f'<text x="{w - 18}" y="{h - 10}" class="m" font-size="10" fill="{T["muted"]}" text-anchor="end">{esc(r["_ago"])}</text>')
    body = "\n".join(b)
    if side:
        body = f'<g transform="translate(3,0)">{body}</g>'
    return svg_doc(w, h, body, f'{r["name"]}: {copy["pitch"]}', css, inset=inset)


# ================================================================ risk monitor
def _rets(xs):
    return [math.log(b / a) for a, b in zip(xs, xs[1:]) if a and b]


def _std(xs):
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return cov / den if den else 0.0


def risk_stats(series, crypto):
    rows = []
    for sym, s in series.items():
        closes = list(s.values())
        r = _rets(closes)
        if len(r) < 25:
            continue
        ann = math.sqrt(365 if sym in crypto else 252) * 100
        roll = [_std(r[i - 20:i]) * ann for i in range(20, len(r) + 1)]
        peak, mdd = closes[0], 0.0
        for v in closes:
            peak = max(peak, v)
            mdd = min(mdd, v / peak - 1)
        rows.append(dict(sym=sym, rv20=roll[-1], rv60=_std(r[-60:]) * ann, lo=min(roll), hi=max(roll), mdd=mdd * 100,
                         dd=(closes[-1] / peak - 1) * 100, pct=(roll[-1] - min(roll)) / ((max(roll) - min(roll)) or 1)))
    syms = [row["sym"] for row in rows]
    common = sorted(set.intersection(*(set(series[s]) for s in syms)))[-61:]
    R = {s: _rets([series[s][d] for d in common]) for s in syms}
    M = [[_corr(R[a], R[b]) for b in syms] for a in syms]
    return rows, syms, M, len(common) - 1


def risk_monitor(series, crypto, stamp):
    rows, syms, M, n_obs = risk_stats(series, crypto)
    n = len(syms)
    cs = 38 if n <= 7 else 32
    H = max(92 + n * 32 + 40, 86 + n * cs + 48)
    b = [title_bar(W, "CROSS-ASSET RISK MONITOR", f"DAILY CLOSES · AS OF {stamp}")]
    for x, a, lab in [(18, "start", "ASSET"), (150, "end", "RV 20D"), (230, "end", "RV 60D"), (250, "start", "20D RV WITHIN 6M RANGE"), (500, "end", "6M MAX DD")]:
        b.append(label(x, 66, lab, a))
    b.append(f'<line x1="18" y1="74.5" x2="500" y2="74.5" stroke="{T["line"]}"/>')
    for i, r in enumerate(rows):
        y = 100 + i * 32
        pos = (r["rv20"] - r["lo"]) / ((r["hi"] - r["lo"]) or 1)
        b.append('<g>' + flash(f'rv20.{r["sym"]}', round(r["rv20"], 1), 96, y - 15, 58, 21, tol=1.0) +
                 f'<text x="18" y="{y}" class="m b" font-size="13" fill="{T["text"]}">{esc(r["sym"])}</text>'
                 f'<text x="150" y="{y}" class="m" font-size="13" fill="{T["text"]}" text-anchor="end">{r["rv20"]:.1f}%</text>'
                 f'<text x="230" y="{y}" class="m" font-size="13" fill="{T["muted"]}" text-anchor="end">{r["rv60"]:.1f}%</text>'
                 f'<rect x="250" y="{y - 6}" width="150" height="4" rx="2" fill="{T["line"]}"/>'
                 f'<rect x="250" y="{y - 6}" width="{max(pos * 150, 3):.1f}" height="4" rx="2" fill="{T["amber"]}" fill-opacity=".55"/>'
                 f'<rect x="{250 + pos * 150 - 1.5:.1f}" y="{y - 10}" width="3" height="12" rx="1" fill="{T["amber"]}"/>'
                 + label(250, y + 11, f'{r["lo"]:.0f}%', size=8.5) + label(400, y + 11, f'{r["hi"]:.0f}%', "end", size=8.5) +
                 f'<text x="500" y="{y}" class="m" font-size="13" fill="{T["down"] if r["mdd"] < 0 else T["muted"]}" text-anchor="end">{r["mdd"]:.1f}%</text></g>')
    hx = W - 18 - n * cs
    b.append(label(hx + n * cs / 2, 62, f"CORRELATION · {n_obs}D LOG RETURNS", "middle"))
    for j, s in enumerate(syms):
        b.append(label(hx + j * cs + cs / 2, 80, s, "middle", size=9.5) + label(hx - 8, 86 + j * cs + cs / 2 + 3, s, "end", size=9.5))
    for i in range(n):
        for j in range(n):
            v = M[i][j]
            col = T["amber"] if v >= 0 else T["cyan"]
            op = .12 + .78 * abs(v) if i != j else .06
            x, y = hx + j * cs, 86 + i * cs
            txt = "-" if i == j else f"{v:+.2f}"
            fill = T["ink"] if abs(v) >= .6 and i != j else T["text"]
            b.append(f'<g><rect x="{x + 2}" y="{y + 2}" width="{cs - 4}" height="{cs - 4}" rx="4" fill="{col}" fill-opacity="{op:.2f}"/>'
                     f'<text x="{x + cs / 2:.1f}" y="{y + cs / 2 + 3.5:.1f}" class="m" font-size="{10 if cs >= 38 else 9}" fill="{fill}" text-anchor="middle">{txt}</text></g>')
    # the matrix cursor visits only the strongest relationships, strongest first
    pairs_ij = sorted(((i, j) for i in range(n) for j in range(i + 1, n)), key=lambda ij: -abs(M[ij[0]][ij[1]]))[:7]
    cell, scan_css = glide_cursor("cx", [(hx + j * cs + 1, 86 + i * cs + 1, cs - 2, cs - 2) for i, j in pairs_ij], dwell=2.2, glide=.7,
                                  color=T["text"], readouts=[f'{syms[i]} x {syms[j]}  <tspan fill="{T["amber"] if M[i][j] >= 0 else T["cyan"]}">{M[i][j]:+.2f}</tspan>'
                                                             for i, j in pairs_ij], readout_xy=(W - 18, H - 16))
    b.append(cell)
    cur, cur_css = glide_cursor("rk", [(10, 100 + i * 32 - 20, 500, 30) for i in range(len(rows))], dwell=1.9, glide=.6)
    b.insert(1, cur)
    scan_css += cur_css
    crypto_syms = [s for s in syms if s in crypto]
    eq = [s for s in syms if s in ("SPX", "NDX")]
    pairs = [M[syms.index(a)][syms.index(e)] for a in crypto_syms for e in eq]
    note = f"CRYPTO/US EQUITY AVG CORR {sum(pairs) / len(pairs):+.2f}  ·  " if pairs else ""
    b.append(label(18, H - 16, f"{note}SOURCE: YAHOO FINANCE DAILY CLOSES", size=9.5))
    return svg_doc(W, H, "\n".join(b), "Cross-asset realized volatility and correlation", scan_css)


# ================================================================ derivatives
def atm_term_structure(summaries, now):
    """ATM implied vol per expiry from Deribit option summaries (strike nearest the forward)."""
    by_exp = {}
    for s in summaries:
        try:
            _, exp, strike, kind = s["instrument_name"].split("-")
            expiry = dt.datetime.strptime(exp, "%d%b%y").replace(hour=8, tzinfo=dt.timezone.utc)
        except (ValueError, KeyError):
            continue
        if not s.get("mark_iv") or not s.get("underlying_price"):
            continue
        by_exp.setdefault(expiry, []).append((float(strike), kind, s["mark_iv"], s["underlying_price"], s.get("open_interest") or 0))
    out, oi = [], {"C": 0.0, "P": 0.0}
    for expiry, rows in sorted(by_exp.items()):
        for _, kind, _, _, o in rows:
            oi[kind] = oi.get(kind, 0) + o
        dte = (expiry - now).total_seconds() / 86400
        if dte < 1:
            continue
        fwd = sum(r[3] for r in rows) / len(rows)
        k = min({r[0] for r in rows}, key=lambda x: abs(x - fwd))
        ivs = [r[2] for r in rows if r[0] == k]
        out.append((dte, sum(ivs) / len(ivs), expiry))
    pc = oi["P"] / oi["C"] if oi["C"] else None
    return out, pc


def derivatives(vol, perps, stamp):
    """vol: {"BTC": (term, pc), ...} or empty; perps: {"BTC": ctx, ...} or empty."""
    H = 288
    b = [title_bar(W, "CRYPTO DERIVATIVES", f"DERIBIT OPTIONS · HYPERLIQUID PERPS · {stamp}")]
    # left: ATM IV term structure
    x0, y0, cw, ch = 50, 100, 420, 128
    b.append(label(18, 62, "ATM IMPLIED VOL TERM STRUCTURE"))
    colors = {"BTC": T["amber"], "ETH": T["cyan"]}
    curves = {k: v[0] for k, v in vol.items() if v and len(v[0]) >= 2}
    if curves:
        all_iv = [iv for c in curves.values() for _, iv, _ in c]
        step = 5 if max(all_iv) - min(all_iv) <= 20 else 10
        lo, hi = math.floor(min(all_iv) / step) * step, math.ceil(max(all_iv) / step) * step
        hi = max(hi, lo + step)
        maxd = max(d for c in curves.values() for d, _, _ in c)
        X = lambda d: x0 + math.log1p(d) / math.log1p(maxd) * cw
        Y = lambda v: y0 + ch - (v - lo) / (hi - lo) * ch
        for v in range(int(lo), int(hi) + 1, step):
            b.append(f'<line x1="{x0}" y1="{Y(v):.1f}" x2="{x0 + cw}" y2="{Y(v):.1f}" stroke="{T["line"]}" stroke-dasharray="2 4"/>'
                     + label(x0 - 8, Y(v) + 3.5, f"{v:.0f}", "end"))
        for d in (7, 30, 90, 180, 365):
            if d <= maxd:
                b.append(label(X(d), y0 + ch + 16, f"{d}D", "middle"))
        lx = 18
        for name, curve in curves.items():
            pts = [(X(d), Y(iv)) for d, iv, _ in curve]
            path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            col = colors.get(name, T["text"])
            b.append(f'<path d="{path}" fill="none" stroke="{col}" stroke-width="1.8" stroke-linejoin="round"/>')
            b.append("".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="{col}"/>' for x, y in pts))
            front = curve[0][1]
            pc = vol[name][1]
            txt = f"{name} {front:.1f}% FRONT" + (f" · P/C OI {pc:.2f}" if pc else "")
            b.append(f'<rect x="{lx}" y="77" width="10" height="3" fill="{col}"/>' + label(lx + 16, 82, txt, fill=col))
            lx += text_width(txt, 9.5) + len(txt) * .8 + 40
        lead = "BTC" if "BTC" in curves else next(iter(curves))
        other = next((k for k in curves if k != lead), None)

        def iv_at(curve, d):
            for (d1, v1, _), (d2, v2, _) in zip(curve, curve[1:]):
                if d1 <= d <= d2:
                    return v1 + (v2 - v1) * (d - d1) / ((d2 - d1) or 1)
            return None
        pts_lead = [(X(d), Y(iv)) for d, iv, _ in curves[lead]]
        labels = []
        for d, iv, _ in curves[lead]:
            o = iv_at(curves[other], d) if other else None
            labels.append(f"{d:.0f}D  {lead} {iv:.1f}" + (f"  {other} {o:.1f}" if o is not None else ""))
        xh, xh_css = crosshair("dv", pts_lead, list(range(len(pts_lead))), labels, None, (x0, y0, x0 + cw, y0 + ch),
                               color=colors.get(lead), tags_top=y0 - 2, dwell=2.0, glide=1.0)
        b.append(xh)
    else:
        xh_css = ""
        b.append(label(x0 + cw / 2, y0 + ch / 2, "OPTIONS FEED UNAVAILABLE THIS HOUR", "middle"))
    # right: perps
    tx = 520
    b.append(label(tx, 62, "PERP FUNDING (APR) · OPEN INTEREST"))
    cols = [(tx, "start", "PERP"), (tx + 130, "end", "MARK"), (tx + 205, "end", "FUNDING"), (W - 18, "end", "OI (USD)")]
    for x, a, lab in cols:
        b.append(label(x, 86, lab, a, size=9))
    b.append(f'<line x1="{tx}" y1="94.5" x2="{W - 18}" y2="94.5" stroke="{T["line"]}"/>')
    if perps:
        for i, (name, c) in enumerate(perps.items()):
            y = 118 + i * 30
            mark = float(c["markPx"])
            apr = float(c["funding"]) * 24 * 365 * 100
            oi = float(c["openInterest"]) * mark
            b.append('<g>' + flash(f"fund.{name}", round(apr, 1), tx + 145, y - 15, 64, 21, tol=1.0) +
                     f'<text x="{tx}" y="{y}" class="m b" font-size="13" fill="{T["text"]}">{esc(name)}</text>'
                     f'<text x="{tx + 130}" y="{y}" class="m" font-size="12.5" fill="{T["text"]}" text-anchor="end">{fmt_price(mark)}</text>'
                     f'<text x="{tx + 205}" y="{y}" class="m" font-size="12.5" fill="{tone(apr)}" text-anchor="end">{signed(apr, 1)}</text>'
                     f'<text x="{W - 18}" y="{y}" class="m" font-size="12.5" fill="{T["muted"]}" text-anchor="end">{oi / 1e6:,.0f}M</text></g>')
    else:
        b.append(label((tx + W - 18) / 2, 160, "PERP FEED UNAVAILABLE THIS HOUR", "middle"))
    b.append(label(18, H - 16, "ATM = STRIKE NEAREST THE FORWARD, CALL/PUT MARK IV AVERAGED · FUNDING ANNUALIZED FROM THE HOURLY RATE", size=9))
    return svg_doc(W, H, "\n".join(b), "Crypto options term structure and perpetual funding", xh_css)


# ================================================================ commit volume profile
def activity(times):
    H = 262
    b = [title_bar(W, "COMMIT VOLUME PROFILE", f"LAST {len(times)} AUTHORED COMMITS · HKT")]
    hours = Counter(t.hour for t in times)
    weekdays = Counter(t.weekday() for t in times)
    x0, y0, cw, ch = 24, 66, 560, 136
    peak = max(hours.values() or [1])
    bw = cw / 24
    for a, z, lab in [(9, 12, "HK AM"), (13, 16, "HK PM"), (21, 24, "US OPEN")]:
        b.append(f'<rect x="{x0 + a * bw:.1f}" y="{y0}" width="{(z - a) * bw:.1f}" height="{ch}" fill="{T["amber"]}" fill-opacity=".06"/>'
                 + label(x0 + (a + z) / 2 * bw, y0 + 12, lab, "middle", size=8.5, fill=T["amber"]))
    top = max(range(24), key=lambda hr: hours.get(hr, 0))
    for hr in range(24):
        v = hours.get(hr, 0)
        bh = v / peak * (ch - 22)
        col = T["amber"] if hr == top else T["up"]
        b.append(f'<rect x="{x0 + hr * bw + 2:.1f}" y="{y0 + ch - bh:.1f}" '
                 f'width="{bw - 4:.1f}" height="{max(bh, 1):.1f}" rx="1.5" fill="{col}" fill-opacity="{.95 if hr == top else .6}"/>')
        if hr % 3 == 0:
            b.append(label(x0 + hr * bw + bw / 2, y0 + ch + 16, f"{hr:02d}", "middle"))
    b.append(f'<line x1="{x0}" y1="{y0 + ch}" x2="{x0 + cw}" y2="{y0 + ch}" stroke="{T["line"]}"/>' + label(x0, y0 + ch + 36, "HOUR OF DAY"))
    wx, total = 630, len(times) or 1
    wpeak = max(weekdays.values() or [1])
    for i, d in enumerate(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]):
        y = y0 + 4 + i * 19
        v = weekdays.get(i, 0)
        b.append(label(wx, y + 9, d, size=10) +
                 f'<rect x="{wx + 36}" y="{y}" width="160" height="11" rx="2" fill="{T["grid"]}"/>'
                 f'<rect x="{wx + 36}" y="{y}" width="{max(v / wpeak * 160, 1):.1f}" height="11" rx="2" fill="{T["cyan"]}" fill-opacity=".7"/>'
                 + label(W - 24, y + 9, f"{v / total * 100:.0f}%", "end", size=10))
    night = sum(hours.get(hr, 0) for hr in (*range(21, 24), *range(0, 5))) / total * 100
    b.append(f'<text x="{wx}" y="{y0 + ch + 36}" class="m" font-size="10" fill="{T["muted"]}">PEAK <tspan fill="{T["amber"]}">{top:02d}:00</tspan>'
             f'  ·  AFTER-HOURS <tspan fill="{T["amber"]}">{night:.0f}%</tspan></text>')
    tops = [(x0 + hr * bw + bw / 2, y0 + ch - hours.get(hr, 0) / peak * (ch - 22)) for hr in range(24)]
    stops = sorted({3, 9, 14, 21, top} | {max(range(9, 17), key=lambda hr: hours.get(hr, 0))})
    xh, xh_css = crosshair("ph", tops, stops, [f"{hr:02d}:00" for hr in stops], [f"{hours.get(hr, 0)}" for hr in stops],
                           (x0, y0 + 18, x0 + cw, y0 + ch), color=T["text"], tags_top=y0 + 30, tag_side=x0 + cw + 4)
    b.append(xh)
    return svg_doc(W, H, "\n".join(b), "Commit volume profile by hour and weekday", xh_css)


# ================================================================ regime monitor
def _few(names):
    return ", ".join(names[:2]) + (f" +{len(names) - 2}" if len(names) > 2 else "")


def regime(rows, syms, M, crypto, term, funding):
    """Rule-based state flags: the panel says what the numbers mean, not just what they are."""
    tiles = []
    hot = [r["sym"] for r in rows if r["pct"] >= .8]
    cold = [r["sym"] for r in rows if r["pct"] <= .2]
    if hot:
        tiles.append(("VOLATILITY", "ELEVATED", _few(hot) + " NEAR 6M HIGHS", "ALERT"))
    elif len(cold) >= len(rows) / 2:
        tiles.append(("VOLATILITY", "COMPRESSED", _few(cold) + " NEAR 6M LOWS", "WATCH"))
    else:
        tiles.append(("VOLATILITY", "NORMAL", "20D RV MID-RANGE", "CALM"))
    pairs = [M[syms.index(a)][syms.index(e)] for a in syms if a in crypto for e in ("SPX", "NDX") if e in syms]
    if pairs:
        c = sum(pairs) / len(pairs)
        state, note = ("ALERT", "RISK-ON COUPLING") if c >= .5 else ("WATCH", "DECOUPLED") if c <= .1 else ("CALM", "TYPICAL RANGE")
        tiles.append(("CRYPTO / EQUITY", f"{c:+.2f}", note, state))
    else:
        tiles.append(("CRYPTO / EQUITY", "N/A", "NO OVERLAP", "OFF"))
    worst = min(rows, key=lambda r: r["dd"])
    state = "ALERT" if worst["dd"] <= -15 else "WATCH" if worst["dd"] <= -8 else "CALM"
    tiles.append(("DRAWDOWN", f'{worst["sym"]} {worst["dd"]:.1f}%', "WORST, FROM 6M HIGH", state))
    if term and len(term) >= 2:
        front = term[0][1]
        mid = min(term, key=lambda t: abs(t[0] - 90))[1]
        slope = mid - front
        tiles.append(("BTC VOL CURVE", f"{slope:+.1f} PTS", "INVERTED: EVENT PRICED" if slope < 0 else "CONTANGO, 90D VS FRONT",
                      "ALERT" if slope < 0 else "CALM"))
    else:
        tiles.append(("BTC VOL CURVE", "N/A", "OPTIONS FEED OFFLINE", "OFF"))
    if funding is not None:
        state, note = ("ALERT", "LONGS CROWDED") if funding > 25 else ("WATCH", "SHORTS PAYING") if funding < 0 else ("CALM", "NEUTRAL CARRY")
        tiles.append(("BTC FUNDING APR", signed(funding, 1), note, state))
    else:
        tiles.append(("BTC FUNDING APR", "N/A", "PERP FEED OFFLINE", "OFF"))

    H, n = 128, len(tiles)
    active = sum(1 for t in tiles if t[3] in ("ALERT", "WATCH"))
    b = [title_bar(W, "REGIME MONITOR", f"RULE-BASED SIGNALS · {active} ACTIVE")]
    tw = (W - 36) / n
    for i, (title, value, note, state) in enumerate(tiles):
        x = 18 + i * tw
        alert, watch = state == "ALERT", state == "WATCH"
        breathe = ' class="breathe"' if alert else ""
        stroke = T["amber"] if alert or watch else T["line"]
        fill = T["amber_dim"] if alert else T["panel"]
        vcol = T["amber"] if alert else T["text"] if state != "OFF" else T["muted"]
        b.append(f'<g><rect x="{x + 3:.1f}" y="46" width="{tw - 6:.1f}" height="66" rx="6" fill="{fill}" stroke="{stroke}" '
                 f'stroke-opacity="{1 if alert else .6 if watch else 1}"{breathe}/>'
                 + label(x + 15, 64, title, size=9)
                 + f'<text x="{x + 15:.1f}" y="86" class="m b" font-size="15" fill="{vcol}">{esc(value)}</text>'
                 + label(x + 15, 102, note, size=8.5, fill=T["amber"] if alert or watch else T["muted"]))
        if alert:
            b.append(f'<circle cx="{x + tw - 17:.1f}" cy="60" r="3.5" fill="{T["amber"]}" class="live"/>')
        b.append("</g>")
    return svg_doc(W, H, "\n".join(b), "Regime monitor: rule-based market state signals")


# ================================================================ repo banners
SUITE = ["futu_tick_downloader", "strategy_powerbacktest", "futu_algo"]
SUITE_LABEL = {"futu_tick_downloader": "TICK CAPTURE", "strategy_powerbacktest": "BACKTEST", "futu_algo": "LIVE TRADING"}


def _visual_stars(stars, now, x, y, w, h):
    if len(stars) < 2:
        return label(x + w / 2, y + h / 2, "STAR HISTORY BUILDING", "middle")
    t0, t1, n = stars[0].timestamp(), now.timestamp(), 80
    buckets = [sum(1 for s in stars if s.timestamp() <= t0 + (t1 - t0) * k / (n - 1)) for k in range(n)]
    pts, line = line_path(buckets, x, y, w, h, lo=0, hi=max(buckets[-1], 1))
    return (f'<path d="{line} L{x + w},{y + h} L{x},{y + h} Z" fill="{T["amber"]}" fill-opacity=".12"/>'
            f'<path d="{line}" fill="none" stroke="{T["amber"]}" stroke-width="1.8"/>'
            f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3" fill="{T["amber"]}"/>'
            + label(x, y + h + 16, f"STARS SINCE {stars[0].year}", size=9) + label(x + w, y + h + 16, f"{len(stars)} TODAY", "end", size=9))


def _visual_ticks(x, y, w, h):
    """A mock tick feed scrolling upward, labelled as such: the real collector output stays private."""
    rows = [("09:30:00.112", "00700", "381.20", "500", "B"), ("09:30:00.118", "09988", "84.35", "1,200", "S"),
            ("09:30:00.131", "00700", "381.40", "300", "B"), ("09:30:00.140", "03690", "142.10", "800", "S"),
            ("09:30:00.156", "00005", "71.05", "2,400", "B"), ("09:30:00.171", "00700", "381.20", "700", "S"),
            ("09:30:00.188", "09988", "84.40", "900", "B"), ("09:30:00.204", "01299", "63.85", "1,600", "B")]
    lh, n = 17, len(rows)
    body = ""
    for k in range(n * 2):
        t, code, px, qty, side = rows[k % n]
        yy = y + 14 + k * lh
        col = T["up"] if side == "B" else T["down"]
        body += (f'<text x="{x}" y="{yy}" class="m" font-size="10.5" fill="{T["muted"]}">{t}</text>'
                 f'<text x="{x + 92}" y="{yy}" class="m b" font-size="10.5" fill="{T["amber"]}">{code}</text>'
                 f'<text x="{x + 190}" y="{yy}" class="m" font-size="10.5" fill="{T["text"]}" text-anchor="end">{px}</text>'
                 f'<text x="{x + 250}" y="{yy}" class="m" font-size="10.5" fill="{T["muted"]}" text-anchor="end">{qty}</text>'
                 f'<text x="{x + w}" y="{yy}" class="m b" font-size="10.5" fill="{col}" text-anchor="end">{side}</text>')
    return (f'<clipPath id="feed"><rect x="{x - 4}" y="{y}" width="{w + 8}" height="{h}"/></clipPath>'
            f'<g clip-path="url(#feed)"><g class="feed" style="--d:-{n * lh}px">{body}</g></g>'
            + label(x, y + h + 16, "MOCK FEED · OPEND -> QUEUE -> SQLITE WAL -> ZSTD", size=9))


def _visual_pipeline(x, y, w, h, steps, caption):
    """Boxes joined by a wire with a pulse travelling along it."""
    n = len(steps)
    bw, gap = (w - (n - 1) * 14) / n, 14
    out = f'<line x1="{x}" y1="{y + h / 2}" x2="{x + w}" y2="{y + h / 2}" stroke="{T["line"]}" stroke-width="2"/>'
    out += f'<circle cx="{x}" cy="{y + h / 2}" r="3.5" fill="{T["amber"]}" class="pulse" style="--w:{w}px"/>'
    for i, (head, lines) in enumerate(steps):
        bx = x + i * (bw + gap)
        out += (f'<g><rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{h}" rx="6" fill="{T["panel"]}" stroke="{T["line"]}"/>'
                f'<text x="{bx + 10:.1f}" y="{y + 20}" class="m b" font-size="10" fill="{T["amber"]}">{esc(head)}</text>')
        for j, ln in enumerate(lines):
            out += f'<text x="{bx + 10:.1f}" y="{y + 40 + j * 15}" class="m" font-size="9.5" fill="{T["text"] if j == 0 else T["muted"]}">{esc(ln)}</text>'
        out += "</g>"
    return out + label(x, y + h + 16, caption, size=9)


def banner(r, spec, stars, now):
    """Repository header in the profile's terminal language, with live repo stats."""
    H = 250
    lang = ((r.get("primaryLanguage") or {}).get("name") or "").upper()
    ticker = r["name"].upper()
    c, cw = chip(16, 10, f"{ticker} <GO>", size=12)
    stat = f'{r["stargazerCount"]:,} STARS · {r["forkCount"]:,} FORKS · {lang} · {r["_ago"].upper()}'
    b = [c, f'<text x="{16 + cw + 16:.1f}" y="24.5" class="m" font-size="11" fill="{T["muted"]}">{esc(spec["kicker"])}</text>',
         f'<text x="{W - 18}" y="24.5" class="m" font-size="11" fill="{T["muted"]}" text-anchor="end">{esc(stat)}</text>',
         f'<line x1="0" y1="40.5" x2="{W}" y2="40.5" stroke="{T["line"]}"/>']
    size = 34 if len(r["name"]) <= 16 else 28
    b.append(f'<text x="32" y="{96}" class="m b" font-size="{size}" fill="{T["text"]}">{esc(r["name"])}</text>'
             f'<text x="32" y="126" class="m" font-size="13.5" fill="{T["text"]}">{esc(spec["pitch"])}</text>'
             f'<text x="32" y="148" class="m" font-size="12.5" fill="{T["muted"]}">{esc(spec["zh"])}</text>')
    x = 32
    for tag in spec["tags"]:
        tw = text_width(tag, 10) + 16
        b.append(f'<rect x="{x}" y="164" width="{tw:.1f}" height="20" rx="3" fill="{T["amber_dim"]}" stroke="{T["amber"]}" stroke-opacity=".5"/>'
                 f'<text x="{x + tw / 2:.1f}" y="178" class="m b" font-size="10" fill="{T["amber"]}" text-anchor="middle">{esc(tag)}</text>')
        x += tw + 8
    # footer: where this repo sits in the suite, or its research provenance
    if r["name"] in SUITE:
        fx = 32
        b.append(label(fx, H - 22, "PIPELINE", size=9))
        fx += 76
        for i, name in enumerate(SUITE):
            on = name == r["name"]
            s = f"{i + 1} {SUITE_LABEL[name]}"
            b.append(f'<text x="{fx}" y="{H - 22}" class="m{" b" if on else ""}" font-size="10.5" fill="{T["amber"] if on else T["muted"]}">{s}</text>')
            if on:
                b.append(f'<rect x="{fx}" y="{H - 17}" width="{text_width(s, 10.5):.1f}" height="2" fill="{T["amber"]}"/>')
            fx += text_width(s, 10.5) + 12
            if i < len(SUITE) - 1:
                b.append(f'<text x="{fx}" y="{H - 22}" class="m" font-size="10.5" fill="{T["line"]}">-&gt;</text>')
                fx += 30
    else:
        b.append(label(32, H - 22, spec.get("footer", ""), size=9.5, fill=T["amber"]))
    # right visual
    vx, vy, vw, vh = 530, 62, 326, 140
    b.append(f'<rect x="{vx - 14}" y="{vy - 12}" width="{vw + 28}" height="{vh + 46}" rx="8" fill="{T["panel"]}" stroke="{T["line"]}"/>')
    kind = spec["visual"]
    if kind == "stars":
        b.append(_visual_stars(stars, now, vx, vy + 10, vw, vh - 20))
    elif kind == "ticks":
        b.append(_visual_ticks(vx, vy, vw, vh))
    else:
        b.append(_visual_pipeline(vx, vy + 22, vw, vh - 34, spec["steps"], spec["caption"]))
    css = """
.feed{animation:feed 7s linear infinite}
@keyframes feed{to{transform:translateY(var(--d))}}
.pulse{animation:pulse 2.4s ease-in-out infinite}
@keyframes pulse{0%{transform:translateX(0);opacity:0}10%{opacity:1}90%{opacity:1}100%{transform:translateX(var(--w));opacity:0}}
@media (prefers-reduced-motion:reduce){.feed,.pulse{animation:none}}
"""
    return svg_doc(W, H, "\n".join(b), f'{r["name"]}: {spec["pitch"]}', css)
