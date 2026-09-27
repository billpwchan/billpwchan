import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

USER = "billpwchan"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "asset" / "generated"
README = ROOT / "README.md"
HKT = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(dt.timezone.utc)

FEATURED = ["futu_algo", "DeepTrust", "strategy_powerbacktest", "futu_tick_downloader", "SlippageSim", "Itarle-Quant-Assessment"]
WATCHLIST = [
    ("BTC-USD", "BTC", "Bitcoin"),
    ("ETH-USD", "ETH", "Ethereum"),
    ("SOL-USD", "SOL", "Solana"),
    ("^GSPC", "SPX", "S&P 500"),
    ("^NDX", "NDX", "Nasdaq 100"),
    ("^HSI", "HSI", "Hang Seng"),
    ("MS", "MS", "Morgan Stanley"),
]
IGNORED_LANGS = {"HTML", "CSS", "SCSS", "Less", "TeX", "Jupyter Notebook", "Makefile", "Dockerfile", "Shell",
                 "Batchfile", "PowerShell", "CMake", "Procfile", "Roff", "Smarty", "Mako", "Tcl", "IDL"}

THEMES = {
    "dark": dict(bg="#0d1117", panel="#161b22", border="#30363d", text="#e6edf3", muted="#8b949e", faint="#21262d",
                 accent="#f0b429", up="#3fb950", down="#f85149", link="#58a6ff"),
    "light": dict(bg="#ffffff", panel="#f6f8fa", border="#d0d7de", text="#1f2328", muted="#656d76", faint="#eaeef2",
                  accent="#b7791f", up="#1a7f37", down="#cf222e", link="#0969da"),
}
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"


def http(url, data=None, headers=None, retries=3):
    headers = {"User-Agent": "Mozilla/5.0 (profile-readme-bot)", **(headers or {})}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"retry {url[:80]}: {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))


def gql(query, **variables):
    token = os.environ["GH_TOKEN"]
    body = json.dumps({"query": query, "variables": variables}).encode()
    res = http("https://api.github.com/graphql", body, {"Authorization": f"bearer {token}"})
    if res.get("errors"):
        raise RuntimeError(res["errors"])
    return res["data"]


def fetch_profile():
    repos, cursor = [], None
    while True:
        d = gql("""query($login:String!,$cursor:String){user(login:$login){id createdAt followers{totalCount}
          repositories(first:100,after:$cursor,privacy:PUBLIC,ownerAffiliations:OWNER,isFork:false){
            pageInfo{hasNextPage endCursor}
            nodes{name description url stargazerCount forkCount pushedAt isArchived
              primaryLanguage{name color}
              languages(first:12,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}""",
                login=USER, cursor=cursor)["user"]
        repos += d["repositories"]["nodes"]
        if not d["repositories"]["pageInfo"]["hasNextPage"]:
            break
        cursor = d["repositories"]["pageInfo"]["endCursor"]
    return d, repos


def fetch_calendar(created_at):
    days = {}
    start = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    while start < NOW:
        end = min(start + dt.timedelta(days=365), NOW)
        c = gql("""query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
          contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}""",
                login=USER, **{"from": start.isoformat(), "to": end.isoformat()})
        for w in c["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for day in w["contributionDays"]:
                days[day["date"]] = day["contributionCount"]
        start = end
    return sorted(days.items())


def fetch_commit_times(user_id, repos):
    recent = sorted((r for r in repos if r["name"] != USER), key=lambda r: r["pushedAt"], reverse=True)[:20]
    parts = [f'r{i}:repository(owner:"{USER}",name:"{r["name"]}"){{defaultBranchRef{{target{{... on Commit{{'
             f'history(first:100,author:{{id:$id}}){{nodes{{authoredDate}}}}}}}}}}}}' for i, r in enumerate(recent)]
    d = gql("query($id:ID!){" + " ".join(parts) + "}", id=user_id)
    times = []
    for v in d.values():
        ref = (v or {}).get("defaultBranchRef")
        if ref:
            times += [dt.datetime.fromisoformat(n["authoredDate"].replace("Z", "+00:00")).astimezone(HKT)
                      for n in ref["target"]["history"]["nodes"]]
    return times


def fetch_quote(symbol):
    q = urllib.parse.quote(symbol)
    d = http(f"https://query1.finance.yahoo.com/v8/finance/chart/{q}?range=3mo&interval=1d")["chart"]["result"][0]
    closes = [c for c in d["indicators"]["quote"][0]["close"] if c is not None]
    last = d["meta"].get("regularMarketPrice") or closes[-1]
    if abs(closes[-1] - last) / last > 1e-4:
        closes.append(last)
    else:
        closes[-1] = last
    return closes


def streaks(days):
    counts = [c for _, c in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current, i = 0, len(counts) - 1
    if counts and counts[i] == 0:
        i -= 1
    while i >= 0 and counts[i]:
        current, i = current + 1, i - 1
    return current, longest


def esc(s):
    return html.escape(str(s), quote=True)


def text_width(s, size):
    return sum(size * (1.0 if ord(ch) > 0x2E80 else 0.52) for ch in s)


def wrap(s, size, width, lines):
    out, cur = [], ""
    for token in re.findall(r"[⺀-￿]|\S+\s*", s):
        if text_width(cur + token, size) > width and cur:
            out.append(cur.rstrip())
            cur = ""
            if len(out) == lines:
                break
        cur += token
    if len(out) < lines and cur:
        out.append(cur.rstrip())
    elif len(out) == lines and cur:
        last = out[-1]
        while text_width(last + "…", size) > width:
            last = last[:-1]
        out[-1] = last.rstrip() + "…"
    return out


def fmt_num(n):
    return f"{n / 1000:.1f}k" if n >= 10000 else f"{n:,}"


def fmt_price(p):
    return f"{p:,.0f}" if p >= 10000 else f"{p:,.2f}"


def pct(a, b):
    return (a / b - 1) * 100 if b else 0.0


def ago(iso):
    days = (NOW - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    if days < 1:
        return "today"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def svg(w, h, t, body, title):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">
<title>{esc(title)}</title>
<style>
text{{font-family:{SANS};fill:{t['text']}}}
.mono{{font-family:{MONO}}}
.muted{{fill:{t['muted']}}}
.accent{{fill:{t['accent']}}}
.up{{fill:{t['up']}}}
.down{{fill:{t['down']}}}
.link{{fill:{t['link']}}}
.fade{{animation:fade .6s ease-out backwards}}
@keyframes fade{{from{{opacity:0;transform:translateY(4px)}}to{{opacity:1;transform:none}}}}
@keyframes blink{{50%{{opacity:.25}}}}
.live{{animation:blink 1.6s ease-in-out infinite}}
@media (prefers-reduced-motion:reduce){{.fade,.live{{animation:none}}}}
</style>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="10" fill="{t['bg']}" stroke="{t['border']}"/>
{body}
</svg>
"""


def header(t, w, title, right=""):
    body = (f'<circle class="live" cx="24" cy="26" r="4" fill="{t["accent"]}"/>'
            f'<text x="36" y="31" font-size="14" font-weight="600" letter-spacing=".4">{esc(title)}</text>')
    if right:
        body += f'<text x="{w - 24}" y="31" font-size="11" class="muted mono" text-anchor="end">{esc(right)}</text>'
    return body


def path_for(values, x0, y0, w, h):
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = w / max(len(values) - 1, 1)
    pts = [(x0 + i * step, y0 + h - (v - lo) / span * h) for i, v in enumerate(values)]
    return pts, "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def stats_card(t, s):
    W, H = 495, 240
    rows = [
        ("Total stars", fmt_num(s["stars"])), ("Forks", fmt_num(s["forks"])),
        ("Followers", fmt_num(s["followers"])), ("Public repos", fmt_num(s["repos"])),
        ("Contributions · 12M", fmt_num(s["year"])), ("All-time contributions", fmt_num(s["total"])),
        ("Current streak", f'{s["current"]}d'), ("Longest streak", f'{s["longest"]}d'),
    ]
    body = header(t, W, "GITHUB PROFILE", f"since {s['since']}")
    for i, (k, v) in enumerate(rows):
        x = 24 if i % 2 == 0 else 262
        y = 62 + (i // 2) * 24
        body += (f'<g class="fade" style="animation-delay:{i * 60}ms">'
                 f'<text x="{x}" y="{y}" font-size="12" class="muted">{esc(k)}</text>'
                 f'<text x="{x + 209}" y="{y}" font-size="13" font-weight="600" class="mono" text-anchor="end">{esc(v)}</text></g>')
    cum, acc = [], 0
    for _, c in s["days"][-365:]:
        acc += c
        cum.append(acc)
    x0, y0, cw, ch = 24, 180, W - 48, 40
    pts, line = path_for(cum, x0, y0, cw, ch)
    body += (f'<line x1="{x0}" y1="{y0 + ch}" x2="{x0 + cw}" y2="{y0 + ch}" stroke="{t["faint"]}"/>'
             f'<path d="{line} L{x0 + cw},{y0 + ch} L{x0},{y0 + ch} Z" fill="{t["up"]}" fill-opacity=".12"/>'
             f'<path d="{line}" fill="none" stroke="{t["up"]}" stroke-width="1.6" stroke-linejoin="round"/>'
             f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3" fill="{t["up"]}"/>'
             f'<text x="{x0}" y="{y0 - 8}" font-size="10" class="muted">CUMULATIVE CONTRIBUTIONS · 52W</text>'
             f'<text x="{x0 + cw}" y="{y0 - 8}" font-size="10" class="mono up" text-anchor="end">+{fmt_num(cum[-1])}</text>')
    return svg(W, H, t, body, "GitHub profile statistics")


def languages_card(t, langs):
    W, H = 495, 240
    total = sum(v for v, _ in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: kv[1][0], reverse=True)[:8]
    body = header(t, W, "LANGUAGE ALLOCATION", "equal-weighted across public repos")
    x, bw = 24, W - 48
    body += f'<clipPath id="bar"><rect x="24" y="50" width="{bw}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">'
    shown = sum(v for _, (v, _) in top)
    for name, (v, color) in top:
        w = v / shown * bw
        body += f'<rect x="{x:.2f}" y="50" width="{w + .5:.2f}" height="10" fill="{color or t["muted"]}"/>'
        x += w
    body += "</g>"
    for i, (name, (v, color)) in enumerate(top):
        cx = 24 if i < 4 else 262
        y = 90 + (i % 4) * 30
        share = v / total * 100
        body += (f'<g class="fade" style="animation-delay:{i * 60}ms">'
                 f'<circle cx="{cx + 5}" cy="{y - 4}" r="5" fill="{color or t["muted"]}"/>'
                 f'<text x="{cx + 18}" y="{y}" font-size="12.5">{esc(name)}</text>'
                 f'<text x="{cx + 209}" y="{y}" font-size="12" class="mono muted" text-anchor="end">{share:.1f}%</text>'
                 f'<rect x="{cx + 18}" y="{y + 7}" width="191" height="2" rx="1" fill="{t["faint"]}"/>'
                 f'<rect x="{cx + 18}" y="{y + 7}" width="{max(share / 100 * 191, 2):.1f}" height="2" rx="1" fill="{color or t["muted"]}"/></g>')
    return svg(W, H, t, body, "Language allocation")


def market_card(t, quotes):
    W = 900
    row_h = 40
    H = 88 + row_h * len(quotes) + 14
    stamp = NOW.strftime("%Y-%m-%d %H:%M UTC")
    body = header(t, W, "MARKET WATCH", f"daily close · as of {stamp}")
    cols = [(24, "start", "SYMBOL"), (330, "end", "LAST"), (430, "end", "1D"), (530, "end", "1M"),
            (630, "end", "3M"), (660, "start", "3M TREND"), (W - 24, "end", "RANGE")]
    for x, anchor, label in cols:
        body += f'<text x="{x}" y="68" font-size="10" class="muted" letter-spacing=".8" text-anchor="{anchor}">{label}</text>'
    body += f'<line x1="24" y1="78" x2="{W - 24}" y2="78" stroke="{t["border"]}"/>'
    for i, (sym, name, closes) in enumerate(quotes):
        y = 78 + row_h * i
        mid = y + row_h / 2 + 4
        if i % 2:
            body += f'<rect x="12" y="{y + 1}" width="{W - 24}" height="{row_h - 1}" rx="4" fill="{t["panel"]}"/>'
        g = f'<g class="fade" style="animation-delay:{i * 70}ms">'
        g += f'<text x="24" y="{mid}" font-size="13" font-weight="700" class="mono">{esc(sym)}</text>'
        g += f'<text x="82" y="{mid}" font-size="12" class="muted">{esc(name)}</text>'
        if not closes:
            g += f'<text x="330" y="{mid}" font-size="12" class="muted mono" text-anchor="end">n/a</text></g>'
            body += g
            continue
        last = closes[-1]
        changes = [pct(last, closes[-2]), pct(last, closes[-min(22, len(closes))]), pct(last, closes[0])]
        g += f'<text x="330" y="{mid}" font-size="13" class="mono" text-anchor="end">{fmt_price(last)}</text>'
        for x, c in zip((430, 530, 630), changes):
            cls = "up" if c >= 0 else "down"
            g += f'<text x="{x}" y="{mid}" font-size="12.5" class="mono {cls}" text-anchor="end">{"▲" if c >= 0 else "▼"} {abs(c):.2f}%</text>'
        color = t["up"] if changes[2] >= 0 else t["down"]
        sx, sw, sy, sh = 660, W - 24 - 660 - 64, y + 8, row_h - 16
        pts, line = path_for(closes, sx, sy, sw, sh)
        lo, hi = min(closes), max(closes)
        g += (f'<path d="{line} L{sx + sw},{sy + sh} L{sx},{sy + sh} Z" fill="{color}" fill-opacity=".10"/>'
              f'<path d="{line}" fill="none" stroke="{color}" stroke-width="1.4" stroke-linejoin="round"/>'
              f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2.5" fill="{color}"/>')
        pos = (last - lo) / ((hi - lo) or 1)
        rx = W - 24 - 52
        g += (f'<rect x="{rx}" y="{mid - 5}" width="52" height="3" rx="1.5" fill="{t["faint"]}"/>'
              f'<rect x="{rx + pos * 49:.1f}" y="{mid - 8}" width="3" height="9" rx="1" fill="{t["accent"]}"/></g>')
        body += g
    body += (f'<text x="24" y="{H - 12}" font-size="9.5" class="muted">Source: Yahoo Finance · '
             f'refreshed daily by GitHub Actions · not investment advice</text>')
    return svg(W, H, t, body, "Market watchlist")


def activity_card(t, times):
    W, H = 900, 250
    stamp = f"last {len(times)} authored commits · HKT"
    body = header(t, W, "COMMIT VOLUME PROFILE", stamp)
    hours = Counter(ts.hour for ts in times)
    weekdays = Counter(ts.weekday() for ts in times)
    x0, y0, cw, ch = 24, 70, 560, 130
    peak = max(hours.values() or [1])
    bw = cw / 24
    sessions = [(9, 12, "HK AM"), (13, 16, "HK PM"), (21, 24, "US OPEN")]
    for a, b, label in sessions:
        body += (f'<rect x="{x0 + a * bw:.1f}" y="{y0 - 4}" width="{(b - a) * bw:.1f}" height="{ch + 4}" fill="{t["accent"]}" fill-opacity=".07"/>'
                 f'<text x="{x0 + (a + b) / 2 * bw:.1f}" y="{y0 + 8}" font-size="8.5" class="accent" text-anchor="middle" letter-spacing=".6">{label}</text>')
    top_hour = max(range(24), key=lambda h: hours.get(h, 0))
    for h in range(24):
        v = hours.get(h, 0)
        bh = v / peak * (ch - 20)
        color = t["accent"] if h == top_hour else t["up"]
        body += (f'<rect class="fade" style="animation-delay:{h * 25}ms" x="{x0 + h * bw + 2:.1f}" y="{y0 + ch - bh:.1f}" '
                 f'width="{bw - 4:.1f}" height="{max(bh, 1):.1f}" rx="2" fill="{color}" fill-opacity="{.95 if h == top_hour else .7}"/>')
        if h % 3 == 0:
            body += f'<text x="{x0 + h * bw + bw / 2:.1f}" y="{y0 + ch + 16}" font-size="9.5" class="muted mono" text-anchor="middle">{h:02d}</text>'
    body += f'<line x1="{x0}" y1="{y0 + ch}" x2="{x0 + cw}" y2="{y0 + ch}" stroke="{t["border"]}"/>'
    body += f'<text x="{x0}" y="{y0 + ch + 36}" font-size="10" class="muted">HOUR OF DAY</text>'

    wx, wlabel = 630, ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    wpeak = max(weekdays.values() or [1])
    total = len(times) or 1
    for i, d in enumerate(wlabel):
        y = y0 + i * 19
        v = weekdays.get(i, 0)
        body += (f'<text x="{wx}" y="{y + 9}" font-size="10" class="muted mono">{d}</text>'
                 f'<rect x="{wx + 36}" y="{y}" width="160" height="11" rx="2" fill="{t["faint"]}"/>'
                 f'<rect class="fade" style="animation-delay:{i * 50}ms" x="{wx + 36}" y="{y}" width="{max(v / wpeak * 160, 1):.1f}" height="11" rx="2" fill="{t["link"]}" fill-opacity=".75"/>'
                 f'<text x="{W - 24}" y="{y + 9}" font-size="10" class="mono muted" text-anchor="end">{v / total * 100:.0f}%</text>')
    night = sum(hours.get(h, 0) for h in (*range(21, 24), *range(0, 5))) / total * 100
    body += (f'<text x="{wx}" y="{y0 + ch + 36}" font-size="10" class="muted">PEAK '
             f'<tspan class="accent mono">{top_hour:02d}:00</tspan>  ·  AFTER-HOURS <tspan class="accent mono">{night:.0f}%</tspan></text>')
    return svg(W, H, t, body, "Commit volume profile by hour and weekday")


def repo_card(t, r):
    W, H = 440, 132
    lang = r["primaryLanguage"] or {}
    body = (f'<path transform="translate(22,17) scale(1)" fill="{t["muted"]}" d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z"/>'
            f'<text x="46" y="30" font-size="14.5" font-weight="600" class="link">{esc(r["name"])}</text>')
    for i, line in enumerate(wrap(r["description"] or "No description.", 12.5, W - 44, 2)):
        body += f'<text x="22" y="{58 + i * 19}" font-size="12.5" class="muted">{esc(line)}</text>'
    x = 22
    if lang:
        body += (f'<circle cx="{x + 6}" cy="{H - 24}" r="6" fill="{lang.get("color") or t["muted"]}"/>'
                 f'<text x="{x + 17}" y="{H - 20}" font-size="12">{esc(lang["name"])}</text>')
        x += 30 + text_width(lang["name"], 12)
    body += (f'<text x="{x}" y="{H - 20}" font-size="12" class="mono">★ {fmt_num(r["stargazerCount"])}</text>'
             f'<text x="{x + 64}" y="{H - 20}" font-size="12" class="mono">⑂ {fmt_num(r["forkCount"])}</text>'
             f'<text x="{W - 22}" y="{H - 20}" font-size="11" class="muted" text-anchor="end">updated {ago(r["pushedAt"])}</text>')
    return svg(W, H, t, body, f"{r['name']} repository")


def update_readme(repos):
    recent = sorted((r for r in repos if r["name"] != USER and not r["isArchived"]),
                    key=lambda r: r["pushedAt"], reverse=True)[:5]
    rows = ["| Repository | What it is | Last push |", "|:--|:--|:--:|"]
    for r in recent:
        desc = (r["description"] or "—").replace("|", "\\|")
        rows.append(f'| [`{r["name"]}`]({r["url"]}) | {desc} | {ago(r["pushedAt"])} |')
    block = "\n".join(rows)
    text = README.read_text()
    new = re.sub(r"(<!-- RECENT:START -->).*?(<!-- RECENT:END -->)", lambda m: f"{m[1]}\n{block}\n{m[2]}", text, flags=re.S)
    README.write_text(new)


def write(name, render, *args):
    for theme, t in THEMES.items():
        (OUT / f"{name}-{theme}.svg").write_text(render(t, *args))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    user, repos = fetch_profile()
    days = fetch_calendar(user["createdAt"])
    current, longest = streaks(days)

    langs = {}
    for r in repos:
        edges = [e for e in r["languages"]["edges"] if e["node"]["name"] not in IGNORED_LANGS]
        repo_total = sum(e["size"] for e in edges)
        for e in edges:
            name = e["node"]["name"]
            weight, color = langs.get(name, (0, e["node"]["color"]))
            langs[name] = (weight + e["size"] / repo_total, color)

    stats = dict(
        stars=sum(r["stargazerCount"] for r in repos), forks=sum(r["forkCount"] for r in repos),
        followers=user["followers"]["totalCount"], repos=len(repos),
        year=sum(c for _, c in days[-365:]), total=sum(c for _, c in days),
        current=current, longest=longest, since=user["createdAt"][:4], days=days,
    )
    write("stats", stats_card, stats)
    write("languages", languages_card, langs)
    write("activity", activity_card, fetch_commit_times(user["id"], repos))

    by_name = {r["name"]: r for r in repos}
    for name in FEATURED:
        if name in by_name:
            write(f"repo-{name}", repo_card, by_name[name])

    quotes = []
    for symbol, short, name in WATCHLIST:
        try:
            quotes.append((short, name, fetch_quote(symbol)))
        except Exception as e:
            print(f"quote {symbol} failed: {e}", file=sys.stderr)
            quotes.append((short, name, []))
    if any(q[2] for q in quotes):
        write("market", market_card, quotes)

    update_readme(repos)


if __name__ == "__main__":
    main()
