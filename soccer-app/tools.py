"""
Shared tool functions for web_search, team_form, and get_fixtures.
Imported by both app.py and multi_agent.py.
"""

import re, html as html_mod
from datetime import date
import requests as _req
from urllib.parse import quote

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
}
_TSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"

_ESPN_LEAGUES = {
    "champions league":  "uefa.champions",
    "europa league":     "uefa.europa",
    "conference league": "uefa.europa.conf",
    "premier league":    "eng.1",
    "la liga":           "esp.1",
    "bundesliga":        "ger.1",
    "serie a":           "ita.1",
    "ligue 1":           "fra.1",
    "eredivisie":        "ned.1",
    "primeira liga":     "por.1",
}


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


# ── Web search ────────────────────────────────────────────────────────────────

def _ddg_search(query: str, max_results: int) -> list:
    url = "https://html.duckduckgo.com/html/?q=" + quote(query)
    r = _req.get(url, headers=_HEADERS, timeout=12)
    if r.status_code != 200:
        return []
    titles   = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', r.text, re.DOTALL)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</div>', r.text, re.DOTALL)
    urls     = re.findall(r'class="result__url"[^>]*>(.*?)</a>', r.text, re.DOTALL)
    out = []
    for i, (t, s) in enumerate(zip(titles[:max_results], snippets[:max_results])):
        out.append({"title": _strip_tags(t), "url": _strip_tags(urls[i]) if i < len(urls) else "", "snippet": _strip_tags(s)})
    return out


def _gnews_search(query: str, max_results: int) -> list:
    rss = "https://news.google.com/rss/search?q=" + quote(query) + "&hl=en-US&gl=US&ceid=US:en"
    r = _req.get(rss, headers=_HEADERS, timeout=12)
    r.raise_for_status()
    items = re.findall(r"<item>(.*?)</item>", r.text, re.DOTALL)
    out = []
    for item in items[:max_results]:
        m = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
        title = html_mod.unescape(_strip_tags(m.group(1))) if m else ""
        src_m = re.search(r" - ([^-]+)$", title)
        src = src_m.group(1).strip() if src_m else ""
        if src:
            title = title[:title.rfind(f" - {src}")].strip()
        if title:
            out.append({"title": title, "url": src, "snippet": src})
    return out


def web_search(query: str, max_results: int = 6) -> str:
    try:
        results = _ddg_search(query, max_results) or _gnews_search(query, max_results)
        if not results:
            return "No results found."
        return "\n\n---\n\n".join(
            f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
            for r in results
        )
    except Exception as e:
        return f"Search error: {e}"


# ── Team form (TheSportsDB) ───────────────────────────────────────────────────

def team_form(team_name: str) -> str:
    try:
        r = _req.get(f"{_TSDB_BASE}/searchteams.php?t={quote(team_name)}", timeout=10)
        r.raise_for_status()
        teams = r.json().get("teams") or []
        if not teams:
            return f"Team '{team_name}' not found in TheSportsDB."
        team      = teams[0]
        team_id   = team.get("idTeam")
        team_full = team.get("strTeam", team_name)
        league    = team.get("strLeague", "")

        r2 = _req.get(f"{_TSDB_BASE}/eventslast.php?id={team_id}", timeout=10)
        r2.raise_for_status()
        events = (r2.json().get("results") or [])[:5]
        if not events:
            return f"No recent events for {team_full}."

        lines, scored_list, conceded_list = [f"{team_full} ({league}) — last {len(events)}:"], [], []
        for ev in events:
            h, a   = ev.get("strHomeTeam", ""), ev.get("strAwayTeam", "")
            sh, sa = ev.get("intHomeScore", "?"), ev.get("intAwayScore", "?")
            is_h   = h.lower() == team_full.lower()
            sc, co = (int(sh), int(sa)) if is_h else (int(sa), int(sh))
            scored_list.append(sc); conceded_list.append(co)
            res  = "W" if sc > co else ("D" if sc == co else "L")
            side = "H" if is_h else "A"
            lines.append(f"  [{ev.get('dateEvent','')}] {res}({side}) {h} {sh}-{sa} {a}  [{ev.get('strLeague','')}]")
        lines.append(f"  Avg scored: {sum(scored_list)/len(scored_list):.1f}/game  |  Avg conceded: {sum(conceded_list)/len(conceded_list):.1f}/game")
        return "\n".join(lines)
    except Exception as e:
        return f"TheSportsDB error for '{team_name}': {e}"


# ── Fixtures (ESPN → TheSportsDB → web search) ────────────────────────────────

def _espn_fixtures(slug: str) -> list:
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"
    r = _req.get(url, timeout=10); r.raise_for_status()
    today = date.today().isoformat()
    out = []
    for ev in r.json().get("events", []):
        if ev.get("date", "")[:10] != today:
            continue
        comps = ev.get("competitions", [{}])[0]
        teams = comps.get("competitors", [])
        home = next((t["team"]["displayName"] for t in teams if t.get("homeAway") == "home"), "?")
        away = next((t["team"]["displayName"] for t in teams if t.get("homeAway") == "away"), "?")
        out.append({"home": home, "away": away,
                    "status": ev.get("status", {}).get("type", {}).get("description", "Scheduled"),
                    "time": ev.get("date", "")[:16].replace("T", " ")})
    return out


def get_fixtures(competition: str = "") -> str:
    today = date.today().isoformat()
    ck = competition.lower().strip()
    slug = next((s for n, s in _ESPN_LEAGUES.items() if n in ck or ck in n), None)
    if slug:
        try:
            ms = _espn_fixtures(slug)
            if ms:
                return f"{competition} fixtures ({today}):\n" + "\n".join(
                    f"  {m['home']} vs {m['away']}  {m['time']} UTC  [{m['status']}]" for m in ms)
        except Exception:
            pass
    try:
        r = _req.get(f"{_TSDB_BASE}/eventsday.php?d={today}&s=Soccer", timeout=10)
        events = r.json().get("events") or []
        if ck:
            events = [e for e in events if ck in e.get("strLeague", "").lower()]
        if events:
            by: dict = {}
            for ev in events:
                by.setdefault(ev.get("strLeague", "Other"), []).append(
                    f"  {ev.get('strHomeTeam')} vs {ev.get('strAwayTeam')}  {ev.get('strTime','')}")
            return f"Fixtures on {today}:\n" + "\n".join(f"\n{lg}:\n" + "\n".join(ms) for lg, ms in by.items())
    except Exception:
        pass
    return f"Structured data unavailable.\n\n{web_search(f'{competition} fixtures today {today}', 5)}"
