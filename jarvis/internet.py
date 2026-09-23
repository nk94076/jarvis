"""Internet wale kaam: check, search, weather, wikipedia. Sab free, koi API key nahi."""
import socket


def internet_hai():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2).close()
        return True
    except OSError:
        return False


def search(query, max_results=5):
    """Web search: pehle ddgs, fail ho to DuckDuckGo HTML, phir Wikipedia search. [{title, body, href}]"""
    try:
        from ddgs import DDGS
        res = list(DDGS().text(query, max_results=max_results))
        if res:
            return res
    except Exception:
        pass
    try:
        return _ddg_html(query, max_results) or _wiki_search(query, max_results)
    except Exception as e:
        print(f"[internet] Search fail: {e}")
        return []


def _ddg_html(query, n):
    import html
    import re
    import requests
    page = requests.post("https://html.duckduckgo.com/html/", data={"q": query}, timeout=10,
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}).text
    strip = lambda t: html.unescape(re.sub(r"<[^>]+>", "", t)).strip()  # noqa: E731
    links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.S)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', page, re.S)
    out = []
    for i, (href, title) in enumerate(links[:n]):
        m = re.search(r"uddg=([^&]+)", href)
        if m:
            from urllib.parse import unquote
            href = unquote(m.group(1))
        out.append({"title": strip(title), "body": strip(snippets[i]) if i < len(snippets) else "", "href": href})
    return out


def _wiki_search(query, n):
    import requests
    r = requests.get("https://en.wikipedia.org/w/api.php", timeout=10, params={
        "action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": n})
    import re
    return [{"title": x["title"], "body": re.sub(r"<[^>]+>", "", x["snippet"]),
             "href": "https://en.wikipedia.org/wiki/" + x["title"].replace(" ", "_")}
            for x in r.json().get("query", {}).get("search", [])]


def wikipedia_summary(topic, sentences=5):
    try:
        import wikipedia
        return wikipedia.summary(topic, sentences=sentences, auto_suggest=True)
    except Exception:
        return ""


def mausam(shehar=""):
    import requests
    return requests.get(f"https://wttr.in/{shehar}?format=3", timeout=8).text.strip()


def mausam_hud(shehar=""):
    """HUD ke liye (temperature, 'City · Condition')."""
    import requests
    raw = requests.get(f"https://wttr.in/{shehar}?format=%t|%C|%l", timeout=8).text.strip()
    temp, cond, place = (raw.split("|") + ["", "", ""])[:3]
    return temp.replace("+", ""), f"{place.split(',')[0].strip()} · {cond.strip()}"
