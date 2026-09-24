"""Website Builder: "gym ke liye html landing page banao" -> sundar, responsive landing page.

AI sirf content (headline, features, FAQ...) JSON mein likhta hai; design ek pakka template hai,
isliye chhote model se bhi page kabhi toot'ta nahi. Rang bol sakte ho: "red/blue/green/purple/orange/dark".
File: Documents/JARVIS Projects/<topic>/index.html"""
import html
import json
import re
import webbrowser
from datetime import date
from pathlib import Path

from . import config

PROJECTS_DIR = Path.home() / "Documents" / "JARVIS Projects"
THEMES = {
    "blue": ("#2563eb", "#06b6d4"), "red": ("#dc2626", "#f97316"), "green": ("#16a34a", "#84cc16"),
    "purple": ("#7c3aed", "#ec4899"), "orange": ("#ea580c", "#facc15"), "pink": ("#db2777", "#a855f7"),
    "teal": ("#0d9488", "#22d3ee"), "black": ("#111827", "#6b7280"), "gold": ("#b45309", "#f59e0b"),
}
COLOR_WORDS = {"neela": "blue", "laal": "red", "lal": "red", "hara": "green", "baingani": "purple",
               "narangi": "orange", "gulabi": "pink", "kala": "black", "sunehra": "gold"}
FILLER = ["ek kaam karo", "ek kam karo", "jarvis", "mujhe", "muje", "mere liye", "html", "css", "mein", "me", "ek",
          "landing page", "landing", "website", "web page", "webpage", "page", "site", "banao", "bana do", "banado",
          "create", "make", "build", "chahiye", "chaiye", "karo", "kar do", "please", "for", "ke liye", "ka", "ki",
          "ke", "a", "an", "the", "on", "about", "topic", "naam", "hai", "theme", "color", "colour", "rang", "wali",
          "wala", "dark", "light", "and", "aur", "with", "se", "par", "pe", "do", "de"]
WANTS = re.compile(r"(landing\s*page|website|web\s*page|webpage|html page|html)")
MAKE = re.compile(r"(bana|create|make|build|chahiye|chaiye|design|generate)")


def wants_page(cmd):
    return bool(WANTS.search(cmd) and MAKE.search(cmd))


def topic_from(cmd):
    text = cmd
    for w in list(THEMES) + list(COLOR_WORDS):
        text = re.sub(rf"\b{w}\b", " ", text)
    for w in sorted(FILLER, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(w)}\b", " ", text)
    return " ".join(text.split())


def theme_from(cmd, topic):
    for w, t in COLOR_WORDS.items():
        if re.search(rf"\b{w}\b", cmd):
            return THEMES[t]
    for t in THEMES:
        if re.search(rf"\b{t}\b", cmd):
            return THEMES[t]
    names = list(THEMES)
    return THEMES[names[sum(map(ord, topic)) % 6]]


def default_content(topic):
    T = topic.title()
    return {
        "brand": T, "headline": f"The smarter way to enjoy {topic}",
        "subheadline": f"Everything you need for {topic}, in one place. Simple, fast and made for you.",
        "cta": "Get Started",
        "features": [{"title": t, "text": f"{t} designed around {topic}, so you get better results with less effort."}
                     for t in ["Easy to start", "Expert support", "Great value", "Fast results", "Trusted quality",
                               "Made for you"]],
        "steps": [{"title": "Sign up", "text": "Tell us what you need in a minute."},
                  {"title": "Get a plan", "text": f"We prepare the best {topic} plan for you."},
                  {"title": "Enjoy results", "text": "Start and see the difference."}],
        "testimonials": [{"name": "Rahul S.", "text": f"Best {topic} experience I have had. Highly recommended!"},
                         {"name": "Priya M.", "text": "Simple, professional and really helpful team."},
                         {"name": "Amit K.", "text": "Great value for money. I will come back again."}],
        "faq": [{"q": f"What is {T}?", "a": f"{T} helps you get the best out of {topic} with a simple process."},
                {"q": "How do I start?", "a": "Click Get Started and fill the short form. We will contact you."},
                {"q": "Is there any support?", "a": "Yes, our team is available to help you every day."},
                {"q": "How much does it cost?", "a": "We have plans for every budget. Contact us for details."}],
        "about": f"We are passionate about {topic} and help people get real results with a friendly, expert team.",
    }


def ai_content(topic, llm):
    prompt = (f"Write landing page content for: {topic}. Reply with ONLY valid JSON, no other text, with keys: "
              '"brand" (short name), "headline" (max 8 words), "subheadline" (1 sentence), "cta" (2-3 words), '
              '"features" (list of 6 objects with "title" and "text"), "steps" (list of 3 objects with "title" and '
              '"text"), "testimonials" (list of 3 objects with "name" (Indian name) and "text"), '
              '"faq" (list of 4 objects with "q" and "a"), "about" (2 sentences). Simple English.')
    base = default_content(topic)
    try:
        raw = llm(prompt)
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group())
    except Exception:
        return base
    for k, v in base.items():                       # jo AI ne sahi nahi diya wahan default
        got = data.get(k)
        if isinstance(v, str):
            base[k] = got if isinstance(got, str) and got.strip() else v
        elif isinstance(got, list) and got and all(isinstance(i, dict) for i in got):
            keys = list(v[0])
            clean = [i for i in got if all(isinstance(i.get(x), str) and i.get(x) for x in keys)]
            if len(clean) >= min(3, len(v)):
                base[k] = clean[:len(v)]
    return base


def render(c, colors):
    e = lambda t: html.escape(str(t))  # noqa: E731
    p1, p2 = colors
    feats = "".join(f'<div class="card"><div class="icon">{"✦★◆●▲■"[i % 6]}</div><h3>{e(f["title"])}</h3>'
                    f'<p>{e(f["text"])}</p></div>' for i, f in enumerate(c["features"]))
    steps = "".join(f'<div class="step"><span>{i + 1}</span><h3>{e(s["title"])}</h3><p>{e(s["text"])}</p></div>'
                    for i, s in enumerate(c["steps"]))
    tests = "".join(f'<figure class="card quote"><blockquote>“{e(t["text"])}”</blockquote>'
                    f'<figcaption>— {e(t["name"])}</figcaption></figure>' for t in c["testimonials"])
    faqs = "".join(f'<details><summary>{e(f["q"])}</summary><p>{e(f["a"])}</p></details>' for f in c["faq"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(c["brand"])} | {e(c["headline"])}</title>
<meta name="description" content="{e(c["subheadline"])}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root {{ --p1: {p1}; --p2: {p2}; --ink: #0f172a; --muted: #64748b; --bg: #f8fafc; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; }}
body {{ font-family: Poppins, system-ui, sans-serif; color: var(--ink); background: var(--bg); line-height: 1.6; }}
a {{ color: inherit; text-decoration: none; }}
.wrap {{ width: min(1120px, 92%); margin: auto; }}
nav {{ position: sticky; top: 0; z-index: 10; background: rgba(255,255,255,.85); backdrop-filter: blur(10px);
       border-bottom: 1px solid #e2e8f0; }}
nav .wrap {{ display: flex; align-items: center; justify-content: space-between; height: 64px; }}
.logo {{ font-weight: 800; font-size: 1.3rem; background: linear-gradient(90deg, var(--p1), var(--p2));
        -webkit-background-clip: text; background-clip: text; color: transparent; }}
nav ul {{ display: flex; gap: 28px; list-style: none; font-size: .95rem; }}
.btn {{ display: inline-block; padding: 12px 26px; border-radius: 999px; font-weight: 600; color: #fff;
       background: linear-gradient(90deg, var(--p1), var(--p2)); box-shadow: 0 8px 24px -8px var(--p1);
       transition: transform .2s; border: 0; cursor: pointer; font: inherit; }}
.btn:hover {{ transform: translateY(-2px); }}
.btn.ghost {{ background: transparent; color: var(--p1); box-shadow: inset 0 0 0 2px var(--p1); }}
.hero {{ padding: 110px 0 90px; text-align: center; position: relative; overflow: hidden; }}
.hero::before {{ content: ""; position: absolute; inset: 0; z-index: -1;
                background: radial-gradient(circle at 30% 40%, color-mix(in srgb, var(--p1) 22%, transparent), transparent 60%),
                            radial-gradient(circle at 70% 50%, color-mix(in srgb, var(--p2) 22%, transparent), transparent 60%); }}
.badge {{ display: inline-block; padding: 6px 16px; border-radius: 999px; background: #fff; font-size: .85rem;
         color: var(--p1); box-shadow: 0 2px 10px rgba(0,0,0,.06); margin-bottom: 22px; }}
h1 {{ font-size: clamp(2.2rem, 5vw, 3.8rem); line-height: 1.15; font-weight: 800; max-width: 820px; margin: auto; }}
.hero p {{ color: var(--muted); font-size: 1.15rem; max-width: 620px; margin: 20px auto 34px; }}
.hero .actions {{ display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; }}
section {{ padding: 80px 0; }}
.title {{ text-align: center; margin-bottom: 48px; }}
.title h2 {{ font-size: clamp(1.7rem, 3.5vw, 2.4rem); font-weight: 800; }}
.title p {{ color: var(--muted); }}
.grid {{ display: grid; gap: 22px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }}
.card {{ background: #fff; border-radius: 18px; padding: 28px; box-shadow: 0 10px 30px -18px rgba(15,23,42,.35);
        transition: transform .2s, box-shadow .2s; }}
.card:hover {{ transform: translateY(-4px); box-shadow: 0 18px 40px -20px var(--p1); }}
.icon {{ width: 46px; height: 46px; border-radius: 12px; display: grid; place-items: center; color: #fff;
        background: linear-gradient(135deg, var(--p1), var(--p2)); margin-bottom: 16px; font-size: 1.2rem; }}
.card h3 {{ margin-bottom: 6px; }}
.card p {{ color: var(--muted); }}
.steps {{ display: grid; gap: 22px; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); counter-reset: s; }}
.step {{ text-align: center; padding: 20px; }}
.step span {{ display: inline-grid; place-items: center; width: 54px; height: 54px; border-radius: 50%;
             font-weight: 800; color: #fff; background: linear-gradient(135deg, var(--p1), var(--p2)); margin-bottom: 14px; }}
.step p {{ color: var(--muted); }}
.alt {{ background: #fff; }}
.quote blockquote {{ font-style: italic; margin-bottom: 14px; }}
.quote figcaption {{ font-weight: 600; color: var(--p1); }}
.about {{ display: grid; gap: 40px; grid-template-columns: 1fr 1fr; align-items: center; }}
.about .art {{ aspect-ratio: 4/3; border-radius: 24px; background: linear-gradient(135deg, var(--p1), var(--p2));
              display: grid; place-items: center; color: #fff; font-size: 3rem; font-weight: 800; }}
.about p {{ color: var(--muted); font-size: 1.1rem; margin: 14px 0 24px; }}
details {{ background: #fff; border-radius: 14px; padding: 18px 22px; margin-bottom: 12px;
          box-shadow: 0 6px 20px -16px rgba(15,23,42,.4); }}
summary {{ cursor: pointer; font-weight: 600; }}
details p {{ color: var(--muted); margin-top: 10px; }}
.faq {{ max-width: 760px; margin: auto; }}
.cta {{ text-align: center; color: #fff; border-radius: 28px; padding: 60px 24px;
       background: linear-gradient(135deg, var(--p1), var(--p2)); }}
.cta h2 {{ font-size: clamp(1.7rem, 3.5vw, 2.4rem); }}
.cta form {{ display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 26px; }}
.cta input {{ padding: 13px 18px; border-radius: 999px; border: 0; min-width: 240px; font: inherit; }}
.cta .btn {{ background: #fff; color: var(--p1); }}
footer {{ padding: 36px 0; text-align: center; color: var(--muted); font-size: .9rem; }}
@media (max-width: 760px) {{ nav ul {{ display: none; }} .about {{ grid-template-columns: 1fr; }} .hero {{ padding-top: 70px; }} }}
</style>
</head>
<body>
<nav><div class="wrap"><a href="#" class="logo">{e(c["brand"])}</a>
<ul><li><a href="#features">Features</a></li><li><a href="#how">How it works</a></li>
<li><a href="#reviews">Reviews</a></li><li><a href="#faq">FAQ</a></li></ul>
<a href="#contact" class="btn">{e(c["cta"])}</a></div></nav>

<header class="hero"><div class="wrap">
<span class="badge">✨ Welcome to {e(c["brand"])}</span>
<h1>{e(c["headline"])}</h1>
<p>{e(c["subheadline"])}</p>
<div class="actions"><a href="#contact" class="btn">{e(c["cta"])}</a><a href="#features" class="btn ghost">Learn more</a></div>
</div></header>

<section id="features"><div class="wrap">
<div class="title"><h2>Why choose {e(c["brand"])}</h2><p>Everything you need, nothing you don't.</p></div>
<div class="grid">{feats}</div></div></section>

<section id="how" class="alt"><div class="wrap">
<div class="title"><h2>How it works</h2><p>Get started in three simple steps.</p></div>
<div class="steps">{steps}</div></div></section>

<section><div class="wrap about">
<div class="art">{e(c["brand"][:2].upper())}</div>
<div><h2>About {e(c["brand"])}</h2><p>{e(c["about"])}</p><a href="#contact" class="btn">{e(c["cta"])}</a></div>
</div></section>

<section id="reviews" class="alt"><div class="wrap">
<div class="title"><h2>What people say</h2></div>
<div class="grid">{tests}</div></div></section>

<section id="faq"><div class="wrap faq">
<div class="title"><h2>Frequently asked questions</h2></div>{faqs}</div></section>

<section id="contact"><div class="wrap"><div class="cta">
<h2>Ready to get started?</h2><p>Leave your email and we will get back to you.</p>
<form onsubmit="event.preventDefault(); this.innerHTML='<p>Thank you! We will contact you soon.</p>'">
<input type="email" placeholder="Your email" required><button class="btn" type="submit">{e(c["cta"])}</button>
</form></div></div></section>

<footer>© {date.today().year} {e(c["brand"])}. All rights reserved. · Made with JARVIS</footer>
</body>
</html>
"""


def build(cmd, llm, open_browser=True):
    """Page banao, save karo, browser mein kholo. (path, spoken reply) lautata hai."""
    s = config.USER_NAME
    topic = topic_from(cmd)
    if not topic:
        return None, f"{s}, what should the landing page be about? Say for example: landing page for a gym."
    content = ai_content(topic, llm)
    page = render(content, theme_from(cmd, topic))
    folder = PROJECTS_DIR / re.sub(r"[^a-zA-Z0-9 -]", "", topic).strip().title()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "index.html"
    path.write_text(page, encoding="utf-8")
    if open_browser:
        webbrowser.open(path.as_uri())
    return path, (f"{s}, your landing page for {topic} is ready. I have opened it in the browser and saved it in "
                  f"Documents, JARVIS Projects, {folder.name}.")


# ======================= CUSTOM PAGE: jo aap bolo wahi =======================
LAST_FILE = config.DATA_DIR / "last_page.txt"
DESIGN_RULES = """Rules:
- ONE complete HTML file: <!DOCTYPE html> ... </html>. All CSS inside <style>, all JS inside <script>. No build tools.
- Follow the user's request EXACTLY: their sections, order, text, colours, style, language, fonts, mood.
  Do not add a generic template look; design it specifically for this request.
- Modern, polished, responsive (mobile first, works at 360px and 1440px), semantic HTML, accessible (alt text, labels).
- Real, specific content for the topic (no lorem ipsum). Images: use https://picsum.photos/seed/<word>/1200/800 or
  inline SVG; icons as inline SVG or emoji. Google Fonts allowed.
- Smooth small animations/hover effects are welcome. Forms should work client-side (show a thank-you message).
Reply with ONLY the HTML in one ```html code block."""


def _extract_html(text):
    m = re.search(r"```(?:html)?\s*(<!DOCTYPE.*?</html>)\s*```", text, re.S | re.I) or \
        re.search(r"(<!DOCTYPE.*</html>)", text, re.S | re.I) or re.search(r"(<html.*</html>)", text, re.S | re.I)
    return m.group(1).strip() if m else ""


def _check_html(page_html, path):
    """Problems ki list: toota HTML, JS errors, khali page. Browser (Playwright) ho to usme khol kar."""
    problems = []
    low = page_html.lower()
    for tag in ("<body", "</body>", "</html>", "<style"):
        if tag not in low:
            problems.append(f"missing {tag}")
    if len(re.sub(r"<[^>]+>", "", page_html)) < 300:
        problems.append("page has almost no visible text")
    try:
        from . import browser
        res = browser._w().do(lambda w: _probe(w, path), timeout=60)
        if isinstance(res, dict):
            problems += [f"JavaScript error: {e}" for e in res["errors"][:5]]
            if res["overflow"]:
                problems.append("page is wider than a phone screen (horizontal scroll on mobile)")
            if res["text"] < 200:
                problems.append("page shows almost no text in the browser")
    except Exception:
        pass
    return problems


def _probe(w, path):
    p = w.page
    errors = []
    p.on("pageerror", lambda e: errors.append(str(e)[:150]))
    p.set_viewport_size({"width": 390, "height": 844})
    p.goto(Path(path).as_uri(), wait_until="load", timeout=30000)
    overflow = p.evaluate("document.documentElement.scrollWidth > window.innerWidth + 5")
    text = len(p.inner_text("body"))
    p.set_viewport_size({"width": 1366, "height": 800})
    return {"errors": errors, "overflow": overflow, "text": text}


def _gen(prompt, chat):
    r = chat([{"role": "user", "content": prompt}], max_tokens=12000)
    return _extract_html(r["message"]["content"])


def build_custom(cmd, chat=None, open_browser=True):
    """Aapki baat ke hisaab se poora naya page. 2 baar tak khud jaanch-sudhaar. Fail ho to template."""
    from .llm_client import chat as default_chat
    chat = chat or default_chat
    s = config.USER_NAME
    topic = topic_from(cmd) or "website"
    words = [w for w in topic.split() if w not in {"mere", "meri", "mera", "jisme", "jismein", "jis", "ho", "hai", "aur",
                                                    "brown", "dark", "light", "theme", "menu", "timing", "style", "wali"}]
    name = " ".join(words[:3]) or "website"
    folder = PROJECTS_DIR / re.sub(r"[^a-zA-Z0-9 -]", "", name).strip().title()[:40]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "index.html"
    page = _gen(f"Build this web page for the user.\nUser's request (may be Hinglish): {cmd}\n\n{DESIGN_RULES}", chat)
    for _ in range(2):
        if not page:
            break
        path.write_text(page, encoding="utf-8")
        problems = _check_html(page, path)
        if not problems:
            break
        fixed = _gen(f"This HTML page has problems: {'; '.join(problems)}.\nFix them and keep everything else the same.\n"
                     f"User's original request: {cmd}\n\n```html\n{page[:30000]}\n```\n\n{DESIGN_RULES}", chat)
        page = fixed or page
    if not page:                                  # AI achha HTML nahi likh paya: template backup
        from .agent import llm
        p, msg = build(cmd, llm, open_browser)
        LAST_FILE.write_text(str(p), encoding="utf-8")
        return msg + " (I used my basic template because the AI could not write a custom page this time.)"
    path.write_text(page, encoding="utf-8")
    LAST_FILE.write_text(str(path), encoding="utf-8")
    if open_browser:
        webbrowser.open(path.as_uri())
    return (f"{s}, I designed a custom page exactly as you asked and opened it. It is saved in Documents, JARVIS "
            f"Projects, {folder.name}. Tell me any change, like: page mein pricing section jodo, or colour blue karo.")


EDIT_WORDS = re.compile(r"\b(page|website|site|landing)\b.*\b(jodo|add|badlo|change|hatao|remove|karo|kar do|bada|chhota|"
                        r"lagao|update|replace|fix|theek)\b|\b(pricing|header|footer|section|button|colou?r|rang|font|logo|"
                        r"menu|navbar|image|photo)\b.*\b(jodo|add|badlo|change|hatao|remove|lagao|karo|kar do)\b")


def wants_edit(cmd):
    return LAST_FILE.exists() and bool(EDIT_WORDS.search(cmd)) and not MAKE.search(cmd.replace("kar do", ""))


def edit_page(cmd, chat=None, open_browser=True):
    """Pichhle page mein badlav: purana version index_v1.html... ke roop mein sambhal kar."""
    from .llm_client import chat as default_chat
    chat = chat or default_chat
    s = config.USER_NAME
    path = Path(LAST_FILE.read_text(encoding="utf-8").strip())
    if not path.exists():
        return f"{s}, I could not find the last page. Ask me to make a new one."
    old = path.read_text(encoding="utf-8")
    n = len(list(path.parent.glob("index_v*.html"))) + 1
    (path.parent / f"index_v{n}.html").write_text(old, encoding="utf-8")
    page = _gen(f"Change this web page as the user asks. Keep everything else exactly the same.\nChange (may be "
                f"Hinglish): {cmd}\n\n```html\n{old[:30000]}\n```\n\n{DESIGN_RULES}", chat)
    if not page:
        return f"Sorry {s}, I could not make that change. The page is unchanged."
    path.write_text(page, encoding="utf-8")
    if open_browser:
        webbrowser.open(path.as_uri())
    return (f"Done {s}, I changed the page and opened it. The old version is saved as index_v{n}.html. "
            f"Say 'page undo' to go back.")


def undo_page():
    s = config.USER_NAME
    if not LAST_FILE.exists():
        return f"{s}, there is no page to undo."
    path = Path(LAST_FILE.read_text(encoding="utf-8").strip())
    versions = sorted(path.parent.glob("index_v*.html"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    if not versions:
        return f"{s}, there is no older version of this page."
    versions[-1].replace(path)
    webbrowser.open(path.as_uri())
    return f"Done {s}, the page is back to the previous version."
