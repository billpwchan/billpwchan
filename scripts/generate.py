"""Render the profile README cards into dist/ and refresh the README's text sections.

Usage: GH_TOKEN=... python scripts/generate.py [out_dir]
Each data source is isolated: if one feed fails, its card is skipped and the previous render stays live.
"""
import re
import sys
import traceback
from pathlib import Path
from zoneinfo import ZoneInfo

import cards
import data

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist"
README = ROOT / "README.md"
HKT = ZoneInfo("Asia/Hong_Kong")
NOW = data.NOW

HIDDEN = {data.USER, "JChart-Security"}
PROFILE = dict(
    name="BILL CHAN",
    role="QUANT DEVELOPER · HONG KONG",
    rows=[("DES", "MSc Computing (Mgmt & Fin) · Imperial College"),
          ("FOCUS", "HK/A-share microstructure · crypto derivs"),
          ("NOW", "Local-first order-flow research terminal"),
          ("OPEN", "Quant trading · quant dev · web3 infra"),
          ("STACK", "Python · C++ · TypeScript · SQL · Solidity")],
)
WORK = {
    "futu_algo": dict(tag="LIVE TRADING", pitch="Algorithmic trading framework on Futu OpenAPI",
                      zh="基於富途 OpenAPI 的量化交易程序"),
    "futu_tick_downloader": dict(tag="MARKET DATA", pitch="24/7 capture of HK real-time tick data",
                                 zh="港股實時分筆數據自動存儲方案"),
    "strategy_powerbacktest": dict(tag="BACKTESTING", pitch="Backtesting engine with custom strategies",
                                   zh="基於 Futu OpenAPI 的專業回測工具"),
    "DeepTrust": dict(tag="ML / NLP", pitch="Knowledge retrieval for pricing anomalies",
                      zh="金融知識檢索與定價異常分析"),
}
# (yahoo symbol, label, shown in risk monitor)
TAPE = [("BTC-USD", "BTC", True), ("ETH-USD", "ETH", True), ("SOL-USD", "SOL", True), ("^GSPC", "SPX", True),
        ("^NDX", "NDX", True), ("^HSI", "HSI", True), ("GC=F", "GOLD", True), ("^TNX", "US10Y", False), ("CNH=X", "USDCNH", False)]
CRYPTO = {"BTC", "ETH", "SOL"}
PERPS = ["BTC", "ETH", "SOL", "HYPE", "XRP"]


def ago(ts):
    days = (NOW - ts).days
    if days < 1:
        return "today"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def streak(days):
    counts = [c for _, c in days]
    i = len(counts) - 1
    if counts and counts[i] == 0:
        i -= 1
    n = 0
    while i >= 0 and counts[i]:
        n, i = n + 1, i - 1
    return n


def sessions(now):
    hk, ny = now.astimezone(HKT), now.astimezone(ZoneInfo("America/New_York"))
    hm = hk.hour * 60 + hk.minute
    if hk.weekday() >= 5 or not 570 <= hm < 960:
        hkex = "CLOSED"
    else:
        hkex = "LUNCH" if 720 <= hm < 780 else "OPEN"
    nm = ny.hour * 60 + ny.minute
    nyse = "OPEN" if ny.weekday() < 5 and 570 <= nm < 960 else "CLOSED"
    return [("HKEX", hkex), ("NYSE", nyse)]


def write(name, svg):
    (OUT / f"{name}.svg").write_text(svg)
    print(f"wrote {name}.svg ({len(svg) // 1024} KB)")


def guarded(label, fn, *args):
    try:
        return fn(*args)
    except Exception:
        print(f"[{label}] failed, keeping previous render", file=sys.stderr)
        traceback.print_exc()
        return None


def update_readme(repos):
    recent = sorted((r for r in repos if r["name"] not in HIDDEN and not r["isArchived"]),
                    key=lambda r: r["pushedAt"], reverse=True)[:4]
    rows = ["| Repository | What it is | Last push |", "|:--|:--|:--:|"]
    for r in recent:
        desc = (r["description"] or "-").replace("|", "\\|")
        rows.append(f'| [`{r["name"]}`]({r["url"]}) | {desc} | {ago(data.parse_ts(r["pushedAt"])).replace(" ", "&nbsp;")} |')
    text = README.read_text()
    new = re.sub(r"(<!-- RECENT:START -->).*?(<!-- RECENT:END -->)", lambda m: f"{m[1]}\n" + "\n".join(rows) + f"\n{m[2]}", text, flags=re.S)
    if new != text:
        README.write_text(new)


def github_cards():
    user, repos = data.fetch_profile()
    days = data.fetch_calendar(user["createdAt"])
    year = [c for _, c in days[-365:]]
    by_name = {r["name"]: r for r in repos}
    return user, repos, days, year, by_name


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = NOW.astimezone(HKT).strftime("%d %b %H:%M HKT").upper()

    gh = guarded("github", github_cards)
    series = {}
    for symbol, short, _ in TAPE:
        s = guarded(f"yahoo {symbol}", data.fetch_chart, symbol)
        if s and len(s) >= 2:
            series[short] = s

    # hero: needs GitHub; the tape degrades to GitHub stats alone if every market feed is down
    if gh:
        user, repos, days, year, by_name = gh
        tape = []
        for _, short, _ in TAPE:
            if short in series:
                vals = list(series[short].values())
                last = vals[-1]
                tape.append((short, f"{last:.2f}%" if short == "US10Y" else fmt(last, short), (last / vals[-2] - 1) * 100))
        tape += [("BILL:GH", f"{sum(year):,} 12M", None),
                 ("STARS", f"{sum(r['stargazerCount'] for r in repos):,}", None),
                 ("FORKS", f"{sum(r['forkCount'] for r in repos):,}", None)]
        write("hero", cards.hero(dict(PROFILE, stamp=stamp, sessions=sessions(NOW), tape=tape, year=year,
                                      total=sum(c for _, c in days), streak=streak(days))))
        for name, copy in WORK.items():
            if name in by_name:
                r = dict(by_name[name], _ago=f"UPDATED {ago(data.parse_ts(by_name[name]['pushedAt'])).upper()}")
                stars = guarded(f"stars {name}", data.fetch_stars, name) or []
                write(f"work-{name}", cards.work_card(r, copy, stars, NOW))
        times = guarded("commit times", data.fetch_commit_times, user["id"], repos, HKT)
        if times:
            write("activity", cards.activity(times))
        update_readme(repos)

    risk = {short: series[short] for _, short, show in TAPE if show and short in series}
    if len(risk) >= 3:
        guarded("risk", lambda: write("risk", cards.risk_monitor(risk, CRYPTO, stamp)))

    vol = {}
    for ccy in ("BTC", "ETH"):
        summ = guarded(f"deribit {ccy}", data.fetch_deribit, ccy)
        if summ:
            vol[ccy] = cards.atm_term_structure(summ, NOW)
    hl = guarded("hyperliquid", data.fetch_hyperliquid) or {}
    perps = {k: hl[k] for k in PERPS if k in hl}
    # always rendered: an empty feed shows an explicit "unavailable" state instead of a broken image
    guarded("derivatives", lambda: write("derivatives", cards.derivatives(vol, perps, stamp)))


def fmt(v, short):
    if short == "USDCNH":
        return f"{v:.4f}"
    return f"{v:,.0f}" if v >= 10000 else f"{v:,.2f}"


if __name__ == "__main__":
    main()
