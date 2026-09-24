"""Phase 2/3 integrations. Har ek ke liye JARVIS Data/my_settings.py mein ek baar setting daalni hoti hai
(README mein step-by-step). Setting na ho to JARVIS batata hai kya karna hai.

- Gmail: IMAP/SMTP + Google "App Password"        (GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
- Calendar: Google Calendar ka "secret iCal link"  (CALENDAR_ICS_URL); naya event -> prefilled Google Calendar page
- GitHub: personal access token                      (GITHUB_TOKEN, GITHUB_USER)
- Database: SQLite / MySQL / PostgreSQL               (DATABASES = {"shop": "sqlite:///C:/data/shop.db"})
- Server (SSH): paramiko                               (SERVERS = {"web": {"host": .., "user": .., "key": ..}})
- Smart home: Home Assistant REST API                  (HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN)
"""
import datetime
import email as email_lib
import re
import subprocess
import webbrowser
from email.header import decode_header
from urllib.parse import quote

from . import config

S = lambda: config.USER_NAME  # noqa: E731


def _setting(name):
    return getattr(config, name, None)


def _missing(what, how):
    return f"{S()}, {what} is not set up yet. {how} The steps are in the README, section Phase 2 setup."


# ======================= GMAIL =======================
def _dec(v):
    out = ""
    for part, enc in decode_header(v or ""):
        out += part.decode(enc or "utf-8", errors="ignore") if isinstance(part, bytes) else part
    return out


def gmail_unread(limit=5, llm=None):
    if not (_setting("GMAIL_ADDRESS") and _setting("GMAIL_APP_PASSWORD")):
        return _missing("Gmail", "Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD in my_settings.py.")
    import imaplib
    box = imaplib.IMAP4_SSL("imap.gmail.com")
    box.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
    box.select("INBOX", readonly=True)
    _, data = box.search(None, "UNSEEN")
    ids = data[0].split()
    if not ids:
        box.logout()
        return f"{S()}, you have no unread emails."
    mails = []
    for i in reversed(ids[-limit:]):
        _, msg = box.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)] BODY.PEEK[TEXT]<0.600>)")
        raw = b"".join(p[1] for p in msg if isinstance(p, tuple))
        m = email_lib.message_from_bytes(raw)
        sender = re.sub(r"<.*?>", "", _dec(m.get("From"))).strip().strip('"')
        mails.append({"from": sender, "subject": _dec(m.get("Subject")),
                      "text": re.sub(r"\s+", " ", raw.decode("utf-8", errors="ignore"))[-400:]})
    box.logout()
    head = f"{S()}, you have {len(ids)} unread emails. "
    if llm:
        return head + llm("Summarise these emails for a spoken briefing, 1 short line each, most important first, "
                          "plain English, no markdown:\n" + "\n".join(f"From {m['from']}: {m['subject']}. {m['text']}"
                                                                     for m in mails))
    return head + " ".join(f"From {m['from']}: {m['subject']}." for m in mails)


def gmail_send(to, subject, body):
    if not (_setting("GMAIL_ADDRESS") and _setting("GMAIL_APP_PASSWORD")):
        return _missing("Gmail", "Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD in my_settings.py.")
    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"], msg["To"], msg["Subject"] = config.GMAIL_ADDRESS, to, subject
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        s.send_message(msg)
    return f"Email sent to {to}, {S()}."


# ======================= CALENDAR =======================
def _ics_events():
    import requests
    text = requests.get(config.CALENDAR_ICS_URL, timeout=15).text.replace("\r\n ", "").replace("\n ", "")
    events = []
    for block in text.split("BEGIN:VEVENT")[1:]:
        get = lambda k: (re.search(rf"^{k}[^:\n]*:(.*)$", block, re.M) or [None, ""])[1].strip()  # noqa: E731
        start = get("DTSTART")
        m = re.match(r"(\d{8})(?:T(\d{4}))?", start)
        if not m:
            continue
        d = datetime.datetime.strptime(m.group(1) + (m.group(2) or "0000"), "%Y%m%d%H%M")
        if start.endswith("Z"):                              # UTC -> local
            d = d.replace(tzinfo=datetime.timezone.utc).astimezone().replace(tzinfo=None)
        events.append({"start": d, "all_day": not m.group(2), "title": get("SUMMARY").replace("\\,", ",")})
    return events


def calendar_day(offset=0):
    if not _setting("CALENDAR_ICS_URL"):
        return _missing("Google Calendar", "Add CALENDAR_ICS_URL (your calendar's secret address in iCal format).")
    day = datetime.date.today() + datetime.timedelta(days=offset)
    todays = sorted((e for e in _ics_events() if e["start"].date() == day), key=lambda e: e["start"])
    label = "today" if offset == 0 else "tomorrow" if offset == 1 else day.strftime("%A")
    if not todays:
        return f"{S()}, you have nothing on your calendar {label}."
    items = [f"{'all day' if e['all_day'] else e['start'].strftime('%I:%M %p')} {e['title']}" for e in todays]
    return f"{S()}, {label} you have {len(items)} events: " + "; ".join(items) + "."


def calendar_add(title, when_text=""):
    """Google Calendar ka 'naya event' page, title aur time bhar kar (save aap karte ho)."""
    now = datetime.datetime.now()
    m = re.search(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|baje)?", when_text)
    start = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
    if m:
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        if (m.group(3) == "pm" or (m.group(3) == "baje" and h < 8)) and h < 12:
            h += 12
        start = now.replace(hour=h % 24, minute=mi, second=0, microsecond=0)
    if re.search(r"\b(kal|tomorrow)\b", when_text):
        start += datetime.timedelta(days=1)
    end = start + datetime.timedelta(hours=1)
    fmt = "%Y%m%dT%H%M%S"
    webbrowser.open("https://calendar.google.com/calendar/render?action=TEMPLATE&text=" + quote(title)
                    + f"&dates={start:{fmt}}/{end:{fmt}}")
    return f"{S()}, I have opened Google Calendar with '{title}' at {start:%I:%M %p, %d %B}. Press save to add it."


# ======================= GITHUB =======================
def _gh(path, method="GET", **kw):
    import requests
    r = requests.request(method, "https://api.github.com" + path, timeout=20, headers={
        "Authorization": f"Bearer {config.GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}, **kw)
    r.raise_for_status()
    return r.json()


def github(cmd, llm=None):
    if not _setting("GITHUB_TOKEN"):
        return _missing("GitHub", "Add GITHUB_TOKEN (a personal access token) in my_settings.py.")
    if re.search(r"\b(repos|repositories|projects)\b", cmd):
        repos = _gh("/user/repos?sort=updated&per_page=8")
        return f"{S()}, your latest repositories are: " + ", ".join(r["name"] for r in repos) + "."
    repo = _find_repo(cmd)
    if not repo:
        return f"{S()}, which repository? Say for example: github issues of jarvis."
    if "issue" in cmd:
        m = re.search(r"(?:create|new|banao|kholo)\s+(?:an?\s+)?issue\s+(?:in\s+\S+\s+)?(?:that|ki|:)?\s*(.+)", cmd)
        if m:
            it = _gh(f"/repos/{repo}/issues", "POST", json={"title": m.group(1)[:120]})
            return f"{S()}, I created issue number {it['number']} in {repo}."
        issues = [i for i in _gh(f"/repos/{repo}/issues?state=open&per_page=8") if "pull_request" not in i]
        if not issues:
            return f"{S()}, {repo} has no open issues."
        return f"{S()}, {repo} has {len(issues)} open issues: " + "; ".join(f"{i['number']}: {i['title']}" for i in issues) + "."
    if re.search(r"\b(pr|prs|pull request|pull requests)\b", cmd):
        prs = _gh(f"/repos/{repo}/pulls?state=open&per_page=8")
        if not prs:
            return f"{S()}, {repo} has no open pull requests."
        return f"{S()}, open pull requests: " + "; ".join(f"{p['number']}: {p['title']}" for p in prs) + "."
    if re.search(r"commit|changes|activity|kya badla", cmd):
        cs = _gh(f"/repos/{repo}/commits?per_page=5")
        return f"{S()}, latest commits in {repo}: " + "; ".join(c["commit"]["message"].splitlines()[0] for c in cs) + "."
    if re.search(r"clone|download", cmd):
        from pathlib import Path
        dest = Path.home() / "Documents" / "JARVIS Projects" / repo.split("/")[1]
        r = subprocess.run(["git", "clone", f"https://github.com/{repo}.git", str(dest)], capture_output=True, text=True)
        if r.returncode:
            return f"Sorry {S()}, clone failed: {r.stderr.strip()[-150:]}"
        config.PROJECTS[repo.split("/")[1].lower()] = str(dest)
        return f"{S()}, I cloned {repo} into Documents, JARVIS Projects. Say 'check my {repo.split('/')[1]} project' to analyse it."
    info = _gh(f"/repos/{repo}")
    return (f"{S()}, {repo}: {info.get('description') or 'no description'}. {info['stargazers_count']} stars, "
            f"{info['open_issues_count']} open issues, last updated {info['pushed_at'][:10]}.")


def _find_repo(cmd):
    user = _setting("GITHUB_USER") or ""
    m = re.search(r"([\w.-]+/[\w.-]+)", cmd)
    if m and "/" in m.group(1):
        return m.group(1)
    try:
        for r in _gh("/user/repos?per_page=100&sort=updated"):
            if r["name"].lower() in cmd or r["name"].lower().replace("-", " ") in cmd:
                return r["full_name"]
    except Exception:
        pass
    words = [w for w in cmd.split() if w not in ("github", "issues", "issue", "of", "in", "ke", "ki", "repo", "show", "my")]
    return f"{user}/{words[-1]}" if user and words else None


def git_commit_push(repo_path, message):
    """Local project: sab changes commit + push (confirm main.py karwata hai)."""
    run = lambda *a: subprocess.run(["git", *a], cwd=repo_path, capture_output=True, text=True)  # noqa: E731
    if not run("status", "--porcelain").stdout.strip():
        return f"{S()}, there is nothing new to commit."
    run("add", "-A")
    c = run("commit", "-m", message)
    if c.returncode:
        return f"Sorry {S()}, commit failed: {c.stderr.strip()[-150:]}"
    p = run("push")
    return f"{S()}, committed and pushed." if p.returncode == 0 else f"{S()}, committed, but push failed: {p.stderr.strip()[-150:]}"


# ======================= DATABASE =======================
def database(cmd, llm):
    dbs = _setting("DATABASES") or {}
    if not dbs:
        return _missing("Database", 'Add DATABASES = {"shop": "sqlite:///C:/path/shop.db"} in my_settings.py.')
    name = next((n for n in dbs if n in cmd), next(iter(dbs)))
    url = dbs[name]
    conn, schema = _db_connect(url)
    question = re.sub(r"\b(database|db|mein|me|se|batao|query)\b", " ", cmd)
    sql = llm(f"Database schema:\n{schema}\n\nWrite ONE read-only SQL SELECT query that answers: {question}\n"
              f"Reply with only the SQL, no explanation.")
    sql = re.sub(r"```(sql)?", "", sql).strip().rstrip(";")
    if not re.match(r"(?is)^\s*(select|with)\b", sql) or re.search(r"(?i)\b(insert|update|delete|drop|alter|create|truncate)\b", sql):
        return f"Sorry {S()}, I only run read-only queries. I got: {sql[:120]}"
    cur = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchmany(20)
    cols = [d[0] for d in cur.description or []]
    conn.close()
    table = "; ".join(", ".join(f"{c}={v}" for c, v in zip(cols, r)) for r in rows[:10])
    return llm(f"Question: {question}\nSQL result rows: {table or 'no rows'}\nAnswer in 1-2 spoken sentences.")


def _db_connect(url):
    if url.startswith("sqlite:///"):
        import sqlite3
        conn = sqlite3.connect(url[len("sqlite:///"):])
        tables = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall()
        return conn, "\n".join(t[1] for t in tables)[:6000]
    if url.startswith(("mysql://", "postgres://", "postgresql://")):
        from urllib.parse import urlparse
        u = urlparse(url)
        if u.scheme == "mysql":
            import pymysql
            conn = pymysql.connect(host=u.hostname, port=u.port or 3306, user=u.username, password=u.password,
                                   database=u.path.lstrip("/"))
            q = "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = DATABASE()"
        else:
            import psycopg2
            conn = psycopg2.connect(url)
            q = "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema='public'"
        cur = conn.cursor()
        cur.execute(q)
        return conn, "\n".join(f"{t}.{c} {d}" for t, c, d in cur.fetchall())[:6000]
    raise ValueError("unsupported database url")


# ======================= SERVER (SSH) =======================
SAFE_SERVER = {"status": "uptime; df -h / | tail -1; free -m | sed -n 2p",
               "disk": "df -h", "memory": "free -m", "uptime": "uptime",
               "logs": "journalctl -n 20 --no-pager 2>/dev/null || tail -n 20 /var/log/syslog"}


def server(cmd, confirm):
    servers = _setting("SERVERS") or {}
    if not servers:
        return _missing("Server access", 'Add SERVERS = {"web": {"host": "1.2.3.4", "user": "root", "key": r"C:\\Users\\me\\.ssh\\id_rsa"}}.')
    name = next((n for n in servers if n in cmd), next(iter(servers)))
    srv = servers[name]
    m = re.search(r"(?:run|chalao)\s+(.+?)\s+(?:on|par|pe)\s+", cmd + " on ")
    key = next((k for k in SAFE_SERVER if k in cmd), None)
    command = SAFE_SERVER[key] if key else (m.group(1) if m else SAFE_SERVER["status"])
    if not key and not confirm(f"{S()}, should I run '{command}' on server {name}?"):
        return f"Okay {S()}, cancelled."
    import paramiko
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(srv["host"], port=srv.get("port", 22), username=srv["user"], key_filename=srv.get("key"),
              password=srv.get("password"), timeout=15)
    _, out, err = c.exec_command(command, timeout=60)
    text = (out.read() + err.read()).decode("utf-8", errors="ignore").strip()
    c.close()
    return f"{S()}, server {name} says: {text[-600:]}"


# ======================= SMART HOME (Home Assistant) =======================
def smart_home(cmd):
    url, token = _setting("HOME_ASSISTANT_URL"), _setting("HOME_ASSISTANT_TOKEN")
    if not (url and token):
        return _missing("Smart home", "Install Home Assistant, then add HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN.")
    import requests
    h = {"Authorization": f"Bearer {token}"}
    states = requests.get(url.rstrip("/") + "/api/states", headers=h, timeout=10).json()
    words = set(re.findall(r"[a-z0-9]+", cmd))

    def score(e):
        name = (e["attributes"].get("friendly_name") or e["entity_id"]).lower()
        return len(words & set(re.findall(r"[a-z0-9]+", name)))
    want_domain = "climate" if re.search(r"\bac\b|thermostat|temperature|temp", cmd) else \
        "light" if re.search(r"light|lamp|batti|bulb", cmd) else "fan" if "fan" in cmd or "pankha" in cmd else None
    cands = [e for e in states if not want_domain or e["entity_id"].startswith(want_domain + ".")]
    if not cands:
        return f"{S()}, I could not find that device in Home Assistant."
    ent = max(cands, key=score)
    eid, domain = ent["entity_id"], ent["entity_id"].split(".")[0]
    name = ent["attributes"].get("friendly_name", eid)
    num = re.search(r"(\d{2})", cmd)
    if domain == "climate" and num:
        svc, data = "climate/set_temperature", {"entity_id": eid, "temperature": int(num.group(1))}
        done = f"set {name} to {num.group(1)} degrees"
    elif re.search(r"\b(off|band|bandh|bujha)\b", cmd):
        svc, data, done = "homeassistant/turn_off", {"entity_id": eid}, f"turned off {name}"
    elif re.search(r"\b(on|chalu|jala|laga|start)\b", cmd):
        svc, data, done = "homeassistant/turn_on", {"entity_id": eid}, f"turned on {name}"
    else:
        return f"{S()}, {name} is {ent['state']}."
    requests.post(url.rstrip("/") + f"/api/services/{svc}", headers=h, json=data, timeout=10).raise_for_status()
    return f"Done {S()}, I {done}."
