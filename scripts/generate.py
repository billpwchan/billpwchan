"""Render the profile README cards into dist/ and refresh the README's text sections.

Usage: GH_TOKEN=... python scripts/generate.py [out_dir]
Each data source is isolated: if one feed fails, its card is skipped and the previous render stays live.
"""
import sys
import traceback
from pathlib import Path
from zoneinfo import ZoneInfo

import cards
import data
import theme

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist"
HKT = ZoneInfo("Asia/Hong_Kong")
NOW = data.NOW

HIDDEN = {data.USER, "JChart-Security"}
PROFILE = dict(
    name="BILL CHAN",
    role="QUANT DEVELOPER · HONG KONG",
    rows=[("EDGE", "Market microstructure: HK, A-shares & crypto"),
          ("BUILD", "Trading infra: tick capture -> backtest -> live"),
          ("NOW", "Shipping a local-first order-flow terminal"),
          ("EDU", "MSc Computing (Mgmt & Finance) · Imperial"),
          ("TALK", "Quant dev & trading roles · fintech / Web3")],
)
WORK = {
    "futu_algo": dict(tag="LIVE TRADING", pitch="Algorithmic trading framework on Futu OpenAPI",
                      zh="基於富途 OpenAPI 的量化交易程序"),
    "futu_tick_downloader": dict(tag="MARKET DATA", pitch="24/7 capture of HK real-time tick data",
                                 zh="港股實時分筆數據自動存儲方案"),
    "strategy_powerbacktest": dict(tag="BACKTESTING", pitch="Backtesting engine with custom strategies",
                                   zh="基於 Futu OpenAPI 的專業回測工具"),
    "DeepTrust": dict(tag="ARXIV PAPER", pitch="Knowledge retrieval for pricing anomalies",
                      zh="金融知識檢索與定價異常分析"),
}
# Header banners embedded at the top of each project's README (referenced from the output branch).
BANNERS = {
    "futu_tick_downloader": dict(kicker="TRADING INFRA · 1 OF 3", visual="ticks",
                                 pitch="24/7 HK tick capture into SQLite WAL",
                                 zh="港股逐筆行情採集：佇列、批次寫入、品質報告與日終歸檔",
                                 tags=["FUTU OPEND", "SQLITE WAL", "SYSTEMD", "TELEGRAM OPS"]),
    "strategy_powerbacktest": dict(kicker="TRADING INFRA · 2 OF 3", visual="pipeline",
                                   pitch="Bar-by-bar backtesting on Futu data",
                                   zh="逐根 K 線回測：佣金與每手股數，完整風險指標",
                                   tags=["BAR-BY-BAR", "COST-AWARE", "RISK METRICS"],
                                   steps=[("DATA", ["Futu OpenAPI", "1m to 1d bars", "SQLite cache"]),
                                          ("SIGNAL", ["MACD, MA cross", "BaseStrategy", "warm-up aware"]),
                                          ("REPORT", ["Sharpe, Sortino", "max DD, VaR", "win rate, PF"])],
                                   caption="BARS -> STRATEGY -> FILLS WITH COMMISSION -> METRICS"),
    "futu_algo": dict(kicker="TRADING INFRA · 3 OF 3", visual="stars",
                      pitch="Algorithmic trading framework on Futu OpenAPI",
                      zh="基於富途 OpenAPI 的量化交易程序：數據、篩選、策略、實盤",
                      tags=["HK EQUITIES", "LIVE TRADING", "STOCK SCREENER"]),
    "DeepTrust": dict(kicker="RESEARCH · ARXIV 2203.08144", visual="pipeline",
                      pitch="Explaining extreme pricing anomalies",
                      zh="以可信的金融知識檢索解釋極端價格異動",
                      tags=["NLP", "FINBERT", "RELIABILITY", "ARXIV"],
                      steps=[("DETECT", ["price anomaly", "Refinitiv Eikon", "event window"]),
                             ("RETRIEVE", ["Twitter stream", "query expansion", "relevance rank"]),
                             ("VERIFY", ["argument mining", "GPT-text traces", "subjectivity"])],
                      caption="ANOMALY -> RETRIEVAL -> RELIABILITY ASSESSMENT",
                      footer="PAPER · ARXIV.ORG/ABS/2203.08144 · Q-FIN.ST, CS.CL, CS.LG"),
}

# (yahoo symbol, label, shown in risk monitor)
TAPE = [("BTC-USD", "BTC", True), ("ETH-USD", "ETH", True), ("SOL-USD", "SOL", True), ("^GSPC", "SPX", True),
        ("^NDX", "NDX", True), ("^HSI", "HSI", True), ("GC=F", "GOLD", True), ("^TNX", "US10Y", False), ("CNH=X", "USDCNH", False)]
CRYPTO = {"BTC", "ETH", "SOL"}
STACK = ["PYTHON", "C++", "TYPESCRIPT", "SQL", "SOLIDITY"]
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
    return [("HKEX", hkex), ("NYSE", nyse), ("CRYPTO", "24/7")]


def session_focus(sess, now):
    """Which instruments lead the tape, and how the LAB strip describes the moment."""
    state = dict(sess)
    if state["HKEX"] in ("OPEN", "LUNCH"):
        return {"HSI", "USDCNH"}, "HONG KONG SESSION LIVE"
    if state["NYSE"] == "OPEN":
        return {"SPX", "NDX", "US10Y", "GOLD"}, "US SESSION LIVE"
    if now.astimezone(HKT).weekday() >= 5 and now.astimezone(ZoneInfo("America/New_York")).weekday() >= 5:
        return CRYPTO, "WEEKEND · CRYPTO TRADES 24/7"
    return CRYPTO, "CASH MARKETS CLOSED · CRYPTO 24/7"


# Power-on order, top to bottom, in seconds: the page boots like a terminal instead of every tile animating at once.
BOOT = {"hero": 0, "key-web": .3, "key-in": .38, "key-mail": .46, "key-ig": .54, "key-gh": .62, "strip-work": .75,
        "work-futu_algo": .85, "work-futu_tick_downloader": .95, "work-strategy_powerbacktest": 1.05, "work-DeepTrust": 1.15,
        "strip-lab": 1.3, "regime": 1.4, "risk": 1.55, "derivatives": 1.75, "strip-flow": 1.95, "activity": 2.05,
        "snake": 2.25, "recent": 2.45}


def write(name, svg):
    svg = theme.boot(svg, BOOT.get(name, 0))
    (OUT / f"{name}.svg").write_text(svg)
    print(f"wrote {name}.svg ({len(svg) // 1024} KB)")


def guarded(label, fn, *args):
    try:
        return fn(*args)
    except Exception:
        print(f"[{label}] failed, keeping previous render", file=sys.stderr)
        traceback.print_exc()
        return None


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

    sess = sessions(NOW)
    lead, lab_status = session_focus(sess, NOW)

    # hero: needs GitHub; the tape degrades to GitHub stats alone if every market feed is down
    if gh:
        user, repos, days, year, by_name = gh
        tape = []
        for _, short, _ in sorted(TAPE, key=lambda t: t[1] not in lead):
            if short in series:
                vals = list(series[short].values())
                last = vals[-1]
                tape.append((short, f"{last:.2f}%" if short == "US10Y" else fmt(last, short), (last / vals[-2] - 1) * 100, short in lead))
        tape += [("BILL:GH", f"{sum(year):,} 12M", None, False),
                 ("STARS", f"{sum(r['stargazerCount'] for r in repos):,}", None, False),
                 ("FORKS", f"{sum(r['forkCount'] for r in repos):,}", None, False)]
        write("hero", cards.hero(dict(PROFILE, stamp=stamp, sessions=sess, tape=tape, year=year,
                                      total=sum(c for _, c in days), streak=streak(days))))
        for i, (name, copy) in enumerate(WORK.items()):
            if name in by_name:
                r = dict(by_name[name], _ago=f"UPDATED {ago(data.parse_ts(by_name[name]['pushedAt'])).upper()}")
                stars = guarded(f"stars {name}", data.fetch_stars, name) or []
                write(f"work-{name}", cards.work_card(r, copy, stars, NOW, i % 2))
                if name in BANNERS:
                    write(f"banner-{name}", cards.banner(r, BANNERS[name], stars, NOW))
        times = guarded("commit times", data.fetch_commit_times, user["id"], repos, HKT)
        if times:
            write("activity", cards.activity(times))
        visible = sorted((r for r in repos if r["name"] not in HIDDEN and not r["isArchived"]),
                         key=lambda r: r["pushedAt"], reverse=True)
        write("recent", cards.recent(visible, lambda r: ago(data.parse_ts(r["pushedAt"]))))
        stars_total = sum(r["stargazerCount"] for r in repos)
        keys = [("WEB", "Website", "billpwchan.com"),
                ("IN", "LinkedIn", "in/billpwchan1998"),
                ("MAIL", "Email", "Drop me a line"),
                ("IG", "Instagram", "@billpwchan"),
                ("GH", f"{stars_total:,} stars", f"{user['followers']['totalCount']} followers")]
        for i, (code, title, sub) in enumerate(keys):
            write(f"key-{code.lower()}", cards.keycap(code, title, sub, i, len(keys)))
        langs = " · ".join(STACK)
        write("strip-work", cards.strip("WORK", f"SELECTED PROJECTS · {langs}"))
        write("strip-flow", cards.strip("FLOW", f"HOW I SHIP · {sum(year):,} CONTRIBUTIONS IN 12M"))
    write("strip-lab", cards.strip("LAB", f"{lab_status} · YAHOO · DERIBIT · HYPERLIQUID"))

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

    if len(risk) >= 3:
        def render_regime():
            rows, syms, M, _ = cards.risk_stats(risk, CRYPTO)
            term = vol.get("BTC", (None,))[0]
            funding = float(perps["BTC"]["funding"]) * 24 * 365 * 100 if "BTC" in perps else None
            write("regime", cards.regime(rows, syms, M, CRYPTO, term, funding))
        guarded("regime", render_regime)


def fmt(v, short):
    if short == "USDCNH":
        return f"{v:.4f}"
    return f"{v:,.0f}" if v >= 10000 else f"{v:,.2f}"


if __name__ == "__main__":
    main()
