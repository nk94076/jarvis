"""Website Audit Agent: "audit adhookmedia.com" -> SEO, speed, security, accessibility, mobile checks + HTML report.
Sirf page ko padhta hai (koi attack/scan nahi)."""
import html
import re
import time
import webbrowser
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

from . import config

REPORTS = Path.home() / "Documents" / "JARVIS Reports"


def audit(url):
    import requests
    if not url.startswith("http"):
        url = "https://" + url
    t0 = time.time()
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (JARVIS audit)"})
    secs = time.time() - t0
    page = r.text
    low = page.lower()
    h = {k.lower(): v for k, v in r.headers.items()}
    checks = []                                          # (category, name, passed, detail)

    def add(cat, name, ok, detail=""):
        checks.append((cat, name, bool(ok), detail))

    title = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    title = html.unescape(title.group(1).strip()) if title else ""
    desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]*content=["\'](.*?)["\']', page, re.I)
    desc = desc.group(1) if desc else ""
    h1 = re.findall(r"<h1[\s>]", low)
    imgs = re.findall(r"<img\b[^>]*>", page, re.I)
    no_alt = [i for i in imgs if not re.search(r'\balt=["\'][^"\']+', i, re.I)]
    links = re.findall(r'<a\b[^>]*href=["\']([^"\'#]+)', page, re.I)
    scripts = len(re.findall(r"<script\b", low))
    css = len(re.findall(r'<link[^>]+stylesheet', low))

    # SEO
    add("SEO", "Page title", 10 <= len(title) <= 65, f"'{title[:70]}' ({len(title)} chars, best 10-65)")
    add("SEO", "Meta description", 50 <= len(desc) <= 160, f"{len(desc)} chars (best 50-160)")
    add("SEO", "Exactly one H1 heading", len(h1) == 1, f"found {len(h1)}")
    add("SEO", "Canonical link", 'rel="canonical"' in low or "rel='canonical'" in low)
    add("SEO", "Open Graph tags (social sharing)", 'property="og:' in low or "property='og:" in low)
    add("SEO", "Language set on <html>", re.search(r"<html[^>]+lang=", low) is not None)
    try:
        base = f"{urlparse(r.url).scheme}://{urlparse(r.url).netloc}"
        add("SEO", "robots.txt", requests.get(base + "/robots.txt", timeout=8).status_code == 200)
        add("SEO", "sitemap.xml", requests.get(base + "/sitemap.xml", timeout=8).status_code == 200)
    except Exception:
        pass
    # Performance
    size_kb = len(r.content) / 1024
    add("Performance", "Server response time", secs < 1.5, f"{secs:.2f} s (best under 1.5 s)")
    add("Performance", "HTML size", size_kb < 300, f"{size_kb:.0f} KB")
    add("Performance", "Compression (gzip/br)", h.get("content-encoding", "") in ("gzip", "br", "deflate"),
        h.get("content-encoding", "none"))
    add("Performance", "Not too many scripts", scripts <= 25, f"{scripts} script tags")
    add("Performance", "Browser caching header", "cache-control" in h, h.get("cache-control", "missing"))
    add("Performance", "Lazy-loaded images", not imgs or 'loading="lazy"' in low, f"{len(imgs)} images")
    # Security
    add("Security", "HTTPS", r.url.startswith("https://"), r.url)
    add("Security", "HSTS header", "strict-transport-security" in h)
    add("Security", "Content-Security-Policy header", "content-security-policy" in h)
    add("Security", "X-Frame-Options / frame-ancestors", "x-frame-options" in h or "frame-ancestors" in h.get("content-security-policy", ""))
    add("Security", "X-Content-Type-Options", h.get("x-content-type-options", "").lower() == "nosniff")
    add("Security", "Server version hidden", not re.search(r"\d", h.get("server", "") + h.get("x-powered-by", "")),
        (h.get("server", "") + " " + h.get("x-powered-by", "")).strip() or "hidden")
    mixed = re.findall(r'(?:src|href)=["\']http://', page, re.I)
    add("Security", "No mixed (http) content", not mixed, f"{len(mixed)} http resources")
    # Accessibility / UX
    add("Accessibility", "Images have alt text", not no_alt, f"{len(no_alt)} of {len(imgs)} images missing alt")
    add("Accessibility", "Mobile viewport tag", 'name="viewport"' in low or "name='viewport'" in low)
    add("Accessibility", "Form inputs have labels", low.count("<input") <= low.count("<label") + low.count("aria-label"),
        f"{low.count('<input')} inputs, {low.count('<label')} labels")
    add("UX", "Has links / navigation", len(links) >= 3, f"{len(links)} links")
    add("UX", "Favicon", "rel=\"icon\"" in low or "rel='icon'" in low or "shortcut icon" in low)

    score = round(100 * sum(c[2] for c in checks) / len(checks))
    fails = [c for c in checks if not c[2]]
    return {"url": r.url, "status": r.status_code, "score": score, "checks": checks, "fails": fails,
            "title": title, "time": secs, "css": css}


def report(url):
    s = config.USER_NAME
    try:
        res = audit(url)
    except Exception as e:
        return f"Sorry {s}, I could not open {url}. ({type(e).__name__})"
    e = html.escape
    rows = "".join(f"<tr class='{'ok' if ok else 'bad'}'><td>{e(cat)}</td><td>{e(n)}</td><td>{'✅' if ok else '❌'}</td>"
                   f"<td>{e(d)}</td></tr>" for cat, n, ok, d in res["checks"])
    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit {e(res['url'])}</title><style>body{{font-family:Segoe UI,system-ui;margin:0;padding:24px;background:#f8fafc;color:#0f172a}}
h1{{margin:0}} .score{{font-size:3rem;font-weight:800;color:{'#16a34a' if res['score'] >= 75 else '#ea580c' if res['score'] >= 50 else '#dc2626'}}}
table{{width:100%;border-collapse:collapse;background:#fff;margin-top:18px}} td,th{{padding:10px;border-bottom:1px solid #e2e8f0;text-align:left}}
tr.bad td{{background:#fff7ed}}</style></head><body><h1>Website Audit</h1><p>{e(res['url'])} · {date.today()}</p>
<div class="score">{res['score']}/100</div><p>{len(res['fails'])} things to fix out of {len(res['checks'])} checks.</p>
<table><tr><th>Area</th><th>Check</th><th>Result</th><th>Detail</th></tr>{rows}</table></body></html>"""
    REPORTS.mkdir(parents=True, exist_ok=True)
    host = urlparse(res["url"]).netloc.replace(":", "_")
    out = REPORTS / f"audit {host} {date.today()}.html"
    out.write_text(page, encoding="utf-8")
    webbrowser.open(out.as_uri())
    top = ", ".join(n for _, n, _, _ in res["fails"][:4])
    return (f"{s}, {host} scored {res['score']} out of 100. "
            + (f"Main things to fix: {top}. " if top else "Everything looks good. ")
            + "I have opened the full report and saved it in Documents, JARVIS Reports.")
