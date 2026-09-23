"""Internet wale kaam: check, search, weather, wikipedia. Sab free, koi API key nahi."""
import socket


def internet_hai():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2).close()
        return True
    except OSError:
        return False


def search(query, max_results=5):
    """DuckDuckGo se search. [{title, body, href}] lautata hai."""
    try:
        from ddgs import DDGS
        return list(DDGS().text(query, max_results=max_results))
    except Exception as e:
        print(f"[internet] Search fail: {e}")
        return []


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
