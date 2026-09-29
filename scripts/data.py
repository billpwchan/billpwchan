"""Fetchers for GitHub, market and derivatives data.

Set PROFILE_CACHE=<dir> to save every raw response; add PROFILE_OFFLINE=1 to render from that cache
without network access (useful for iterating on the design locally).
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

USER = "billpwchan"
NOW = dt.datetime.now(dt.timezone.utc)
CACHE = Path(os.environ["PROFILE_CACHE"]) if os.environ.get("PROFILE_CACHE") else None
OFFLINE = os.environ.get("PROFILE_OFFLINE") == "1"


def http_json(key, url, data=None, headers=None, retries=3):
    if OFFLINE:
        return json.loads((CACHE / f"{key}.json").read_text())
    headers = {"User-Agent": "Mozilla/5.0 (profile-readme-bot)", **(headers or {})}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.load(r)
            break
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(f"retry {url[:80]}: {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    if CACHE:
        CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / f"{key}.json").write_text(json.dumps(res))
    return res


def gql(key, query, **variables):
    headers = {} if OFFLINE else {"Authorization": f"bearer {os.environ['GH_TOKEN']}"}
    body = json.dumps({"query": query, "variables": variables}).encode()
    res = http_json(key, "https://api.github.com/graphql", body, headers)
    if res.get("errors"):
        raise RuntimeError(res["errors"])
    return res["data"]


def parse_ts(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))


# ---------------------------------------------------------------- GitHub
def fetch_profile():
    repos, cursor, page = [], None, 0
    while True:
        d = gql(f"gh-profile-{page}", """query($login:String!,$cursor:String){user(login:$login){id createdAt followers{totalCount}
          repositories(first:100,after:$cursor,privacy:PUBLIC,ownerAffiliations:OWNER,isFork:false){
            pageInfo{hasNextPage endCursor}
            nodes{name description url stargazerCount forkCount pushedAt isArchived primaryLanguage{name color}}}}}""",
                login=USER, cursor=cursor)["user"]
        repos += d["repositories"]["nodes"]
        if not d["repositories"]["pageInfo"]["hasNextPage"]:
            return d, repos
        cursor, page = d["repositories"]["pageInfo"]["endCursor"], page + 1


def fetch_calendar(created_at):
    days, start, i = {}, parse_ts(created_at), 0
    while start < NOW:
        end = min(start + dt.timedelta(days=365), NOW)
        c = gql(f"gh-calendar-{i}", """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
          contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}""",
                login=USER, **{"from": start.isoformat(), "to": end.isoformat()})
        for w in c["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for day in w["contributionDays"]:
                days[day["date"]] = day["contributionCount"]
        start, i = end, i + 1
    return sorted(days.items())


def fetch_commit_times(user_id, repos, tz):
    recent = sorted((r for r in repos if r["name"] != USER), key=lambda r: r["pushedAt"], reverse=True)[:20]
    parts = [f'r{i}:repository(owner:"{USER}",name:"{r["name"]}"){{defaultBranchRef{{target{{... on Commit{{'
             f'history(first:100,author:{{id:$id}}){{nodes{{authoredDate}}}}}}}}}}}}' for i, r in enumerate(recent)]
    d = gql("gh-commits", "query($id:ID!){" + " ".join(parts) + "}", id=user_id)
    times = []
    for v in d.values():
        ref = (v or {}).get("defaultBranchRef")
        if ref:
            times += [parse_ts(n["authoredDate"]).astimezone(tz) for n in ref["target"]["history"]["nodes"]]
    return times


def fetch_stars(name):
    """Timestamps of every star on a repo, oldest first: the repo's 'AUM curve'."""
    out, cursor, page = [], None, 0
    while True:
        d = gql(f"gh-stars-{name}-{page}", """query($owner:String!,$name:String!,$cursor:String){repository(owner:$owner,name:$name){
          stargazers(first:100,after:$cursor,orderBy:{field:STARRED_AT,direction:ASC}){pageInfo{hasNextPage endCursor} edges{starredAt}}}}""",
                owner=USER, name=name, cursor=cursor)["repository"]["stargazers"]
        out += [parse_ts(e["starredAt"]) for e in d["edges"]]
        if not d["pageInfo"]["hasNextPage"] or page > 30:
            return out
        cursor, page = d["pageInfo"]["endCursor"], page + 1


# ---------------------------------------------------------------- markets
def fetch_chart(symbol, rng="6mo"):
    """Daily closes keyed by the exchange-local date, plus the live last price."""
    q = urllib.parse.quote(symbol)
    d = http_json(f"yf-{symbol}", f"https://query1.finance.yahoo.com/v8/finance/chart/{q}?range={rng}&interval=1d")["chart"]["result"][0]
    off = d["meta"].get("gmtoffset", 0)
    series = {}
    for ts, c in zip(d["timestamp"], d["indicators"]["quote"][0]["close"]):
        if c is not None:
            series[dt.datetime.fromtimestamp(ts + off, dt.timezone.utc).date()] = c
    last = d["meta"].get("regularMarketPrice")
    if last and series:
        series[max(series)] = last
    return dict(sorted(series.items()))


def fetch_deribit(currency):
    url = f"https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={currency}&kind=option"
    return http_json(f"deribit-{currency}", url)["result"]


def fetch_hyperliquid():
    body = json.dumps({"type": "metaAndAssetCtxs"}).encode()
    meta, ctxs = http_json("hyperliquid", "https://api.hyperliquid.xyz/info", body, {"Content-Type": "application/json"})
    return {u["name"]: c for u, c in zip(meta["universe"], ctxs)}
