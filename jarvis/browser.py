"""Browser Agent (Playwright): asli Chrome/Chromium ko JARVIS khud chalata hai.
open, click (text se), form bharna, text padhna, screenshot, scroll, aur poori website TEST
(desktop + mobile screenshot, console errors, toote links, load time).

Setup (ek baar): pip install playwright   aur   python -m playwright install chromium
(setup.bat ye khud karta hai). Login yaad rehte hain: profile JARVIS Data/browser_profile mein.
Playwright ek hi thread se chalta hai, isliye saare kaam ek alag "browser thread" par line se hote hain."""
import queue
import re
import threading
import time
from datetime import datetime
from pathlib import Path

from . import config

PROFILE = config.DATA_DIR / "browser_profile"
SHOTS = Path.home() / "Pictures" / "JARVIS Screenshots"


class _Worker:
    def __init__(self):
        self.q = queue.Queue()
        self.page = None
        self.ctx = None
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        pw = None
        while True:
            fn, box, done = self.q.get()
            try:
                if self.page is None or self.page.is_closed():
                    from playwright.sync_api import sync_playwright
                    if pw is None:
                        pw = sync_playwright().start()
                    PROFILE.mkdir(parents=True, exist_ok=True)
                    kw = {"headless": not getattr(config, "BROWSER_VISIBLE", True), "viewport": {"width": 1366, "height": 800}}
                    if getattr(config, "BROWSER_EXECUTABLE", ""):
                        kw["executable_path"] = config.BROWSER_EXECUTABLE
                    try:
                        self.ctx = pw.chromium.launch_persistent_context(str(PROFILE), channel="chrome", **kw)
                    except Exception:
                        self.ctx = pw.chromium.launch_persistent_context(str(PROFILE), **kw)
                    self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
                box["value"] = fn(self)
            except Exception as e:
                box["error"] = f"{type(e).__name__}: {str(e)[:300]}"
            done.set()

    def do(self, fn, timeout=90):
        box, done = {}, threading.Event()
        self.q.put((fn, box, done))
        if not done.wait(timeout):
            return "ERROR: browser took too long"
        if "error" in box:
            msg = box["error"]
            if "No module named 'playwright'" in msg or "Executable doesn't exist" in msg:
                return ("ERROR: Playwright is not installed. Run: pip install playwright  and then  "
                        "python -m playwright install chromium  (setup.bat does it).")
            return "ERROR: " + msg
        return box.get("value")


_W = None


def _w():
    global _W
    if _W is None:
        _W = _Worker()
    return _W


def _url(u):
    u = u.strip()
    if not re.match(r"https?://", u):
        u = ("https://" + u) if "." in u else "https://www.google.com/search?q=" + u.replace(" ", "+")
    return u


# ---------------- actions ----------------
def open_url(url):
    def f(w):
        w.page.goto(_url(url), wait_until="domcontentloaded", timeout=45000)
        return f"opened {w.page.url} (title: {w.page.title()[:80]})"
    return _w().do(f)


def click(text):
    def f(w):
        p = w.page
        for loc in (p.get_by_role("button", name=re.compile(re.escape(text), re.I)),
                    p.get_by_role("link", name=re.compile(re.escape(text), re.I)),
                    p.get_by_text(re.compile(re.escape(text), re.I))):
            if loc.count():
                loc.first.click(timeout=8000)
                p.wait_for_load_state("domcontentloaded")
                return f"clicked '{text}', now on {p.url}"
        return f"could not find '{text}' on the page"
    return _w().do(f)


def fill(field, value):
    """field = label / placeholder / name (jaise 'email', 'Full name', 'search')"""
    def f(w):
        p = w.page
        rx = re.compile(re.escape(field), re.I)
        for loc in (p.get_by_label(rx), p.get_by_placeholder(rx), p.locator(f"[name*='{field}' i]"),
                    p.get_by_role("textbox", name=rx)):
            if loc.count():
                loc.first.fill(value, timeout=8000)
                return f"filled '{field}'"
        return f"could not find a field called '{field}'"
    return _w().do(f)


def fill_form(fields, submit=None):
    """fields = {"name": "Naveen", "email": "x@y.com"}; submit = button text."""
    out = [fill(k, v) for k, v in fields.items()]
    if submit:
        out.append(click(submit))
    return "; ".join(out)


def press(key):
    return _w().do(lambda w: (w.page.keyboard.press(key), f"pressed {key}")[1])


def read_text(limit=4000):
    def f(w):
        t = w.page.inner_text("body", timeout=15000)
        return f"PAGE {w.page.url}: " + re.sub(r"\s+", " ", t)[:limit]
    return _w().do(f)


def screenshot(full=True):
    def f(w):
        SHOTS.mkdir(parents=True, exist_ok=True)
        path = SHOTS / f"browser_{datetime.now():%Y-%m-%d_%H-%M-%S}.png"
        w.page.screenshot(path=str(path), full_page=full)
        return str(path)
    return _w().do(f)


def scroll(direction="down"):
    return _w().do(lambda w: (w.page.mouse.wheel(0, 700 if direction == "down" else -700), f"scrolled {direction}")[1])


def test_website(url):
    """Browser Testing: load time, console errors, toote links/images, desktop+mobile screenshot."""
    def f(w):
        p = w.page
        errors, failed = [], []
        p.on("console", lambda m: errors.append(m.text[:150]) if m.type == "error" else None)
        p.on("requestfailed", lambda r: failed.append(r.url[:120]))
        t0 = time.time()
        resp = p.goto(_url(url), wait_until="load", timeout=60000)
        load = time.time() - t0
        status = resp.status if resp else 0
        SHOTS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        p.screenshot(path=str(SHOTS / f"test_desktop_{stamp}.png"), full_page=True)
        links = p.eval_on_selector_all("a[href]", "els => [...new Set(els.map(e => e.href).filter(h => h.startsWith('http')))].slice(0, 25)")
        broken_imgs = p.eval_on_selector_all("img", "els => els.filter(i => i.complete && i.naturalWidth === 0).map(i => i.src).slice(0, 10)")
        dead = []
        for link in links:
            try:
                r = w.ctx.request.head(link, timeout=8000)
                if r.status >= 400:
                    dead.append(f"{link} ({r.status})")
            except Exception:
                dead.append(f"{link} (no response)")
        p.set_viewport_size({"width": 390, "height": 844})
        p.reload(wait_until="load")
        overflow = p.evaluate("document.documentElement.scrollWidth > window.innerWidth + 5")
        p.screenshot(path=str(SHOTS / f"test_mobile_{stamp}.png"), full_page=True)
        p.set_viewport_size({"width": 1366, "height": 800})
        return {"status": status, "load": round(load, 2), "console_errors": errors[:8], "failed_requests": failed[:8],
                "dead_links": dead, "broken_images": broken_imgs, "mobile_overflow": overflow,
                "screens": f"Pictures/JARVIS Screenshots/test_*_{stamp}.png"}
    res = _w().do(f, timeout=240)
    if isinstance(res, str):
        return res
    problems = []
    if res["status"] >= 400:
        problems.append(f"page returned HTTP {res['status']}")
    if res["load"] > 4:
        problems.append(f"slow load ({res['load']} s)")
    if res["console_errors"]:
        problems.append(f"{len(res['console_errors'])} JavaScript errors")
    if res["dead_links"]:
        problems.append(f"{len(res['dead_links'])} broken links")
    if res["broken_images"]:
        problems.append(f"{len(res['broken_images'])} broken images")
    if res["mobile_overflow"]:
        problems.append("page is wider than a phone screen")
    s = config.USER_NAME
    verdict = "Everything passed." if not problems else "Problems: " + "; ".join(problems) + "."
    return (f"{s}, website test done. Loaded in {res['load']} seconds. {verdict} Desktop and mobile screenshots are "
            f"saved in Pictures, JARVIS Screenshots.")


def close():
    return _w().do(lambda w: (w.ctx.close(), setattr(w, "page", None), "browser closed")[2])
