"""Main Brain + Agents.

- TOOLS: plugin system. Naya tool = ek function + @tool(...) decorator.
- Agent.run(task): Ollama model ko tools deta hai; model khud decide karta hai kaunsa tool kab chalana hai,
  jab tak kaam poora na ho (multi-step). Khatarnaak (risk="high") tools se pehle user se confirm karta hai.
- Agent.fast(cmd): aam commands (screen padho, click on X, research, pdf, git, terminal...) seedhe,
  bina model ke, taaki chhote model par bhi pakka chale.
Har tool call data/activity.log mein likha jata hai."""
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from . import config, internet, pc

HOME = Path.home()
REPORTS = HOME / "Documents" / "JARVIS Reports"
LOG_FILE = config.DATA_DIR / "activity.log"
ALIASES = {"downloads": HOME / "Downloads", "download": HOME / "Downloads", "documents": HOME / "Documents",
           "document": HOME / "Documents", "desktop": HOME / "Desktop", "pictures": HOME / "Pictures",
           "music": HOME / "Music", "videos": HOME / "Videos", "home": HOME}
DANGEROUS = ["format ", "rm -rf", "rd /s", "rmdir /s", "del /s", "del /q", "diskpart", "reg delete", "cipher /w",
             "shutdown", "mkfs", "bcdedit", "vssadmin", "remove-item -recurse", "takeown", "icacls"]

TOOLS = {}


def tool(name, description, params=None, risk="low"):
    """Plugin system: @tool se koi bhi function JARVIS ka tool ban jata hai."""
    def wrap(fn):
        TOOLS[name] = {"fn": fn, "risk": risk, "schema": {
            "type": "function",
            "function": {"name": name, "description": description, "parameters": {
                "type": "object",
                "properties": {k: {"type": v[0], "description": v[1]} for k, v in (params or {}).items()},
                "required": list(params or {}),
            }}}}
        return fn
    return wrap


def log(entry):
    config.DATA_DIR.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {entry}\n")


def resolve(path):
    """'downloads', 'downloads/report.pdf', 'C:\\x', 'jarvis' (project) -> Path."""
    p = str(path).strip().strip('"')
    low = p.lower()
    if low in config.PROJECTS:
        return Path(config.PROJECTS[low])
    first, _, rest = low.replace("\\", "/").partition("/")
    if first in ALIASES:
        return ALIASES[first] / p.replace("\\", "/").partition("/")[2] if rest else ALIASES[first]
    q = Path(p).expanduser()
    return q if q.is_absolute() else HOME / q


def llm(prompt, model=None):
    import ollama
    r = ollama.chat(model=model or config.AGENT_MODEL, messages=[{"role": "user", "content": prompt}])
    return r["message"]["content"].strip()


def find_named(name, exts=None):
    """Desktop/Documents/Downloads mein naam se file dhoondo."""
    words = name.lower().split()
    for base in [HOME / "Desktop", HOME / "Documents", HOME / "Downloads", HOME]:
        if not base.exists():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "AppData", ".git")]
            for f in files:
                fl = f.lower()
                if all(w in fl for w in words) and (not exts or fl.endswith(exts)):
                    return Path(root) / f
            if root.count(os.sep) - str(base).count(os.sep) > 4:
                dirs[:] = []
    return None


# ======================= TOOLS =======================
# ---- web / research ----
@tool("web_search", "Internet par search karke top results ka text lao", {"query": ("string", "kya search karna hai")})
def t_web_search(query):
    res = internet.search(query, max_results=6)
    return "\n".join(f"- {r.get('title')}: {r.get('body')} ({r.get('href')})" for r in res) or "no results"


@tool("read_webpage", "Kisi webpage ka text padho", {"url": ("string", "page ka URL")})
def t_read_webpage(url):
    import requests
    html = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"}).text
    html = re.sub(r"(?is)<(script|style|noscript|svg|header|footer|nav).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    import html as h
    return re.sub(r"\s+", " ", h.unescape(text)).strip()[:5000]


@tool("open_website", "Browser mein URL kholo", {"url": ("string", "website URL")})
def t_open_website(url):
    import webbrowser
    webbrowser.open(url if url.startswith("http") else "https://" + url)
    return f"opened {url}"


@tool("deep_research", "Kisi topic par kai websites padh kar detailed report banao aur save karo",
      {"topic": ("string", "research ka topic")})
def t_deep_research(topic):
    if not internet.internet_hai():
        return "internet nahi hai"
    results = internet.search(topic, max_results=6)
    wiki = internet.wikipedia_summary(topic, sentences=8)
    sources = [f"Wikipedia: {wiki}"] if wiki else []
    for r in results[:4]:
        try:
            sources.append(f"{r.get('title')} ({r.get('href')}): {t_read_webpage(r['href'])[:2500]}")
        except Exception:
            sources.append(f"{r.get('title')}: {r.get('body')}")
    report = llm(f"Topic: {topic}\n\nIn sources se ek saaf research report likho (simple English). Sections: "
                 f"Summary (3-4 lines), Key Points (bullets), Pros/Cons ya Opportunities (agar lagu ho), "
                 f"Conclusion. Sirf sources ki baat likho.\n\n" + "\n\n".join(sources)[:14000])
    REPORTS.mkdir(parents=True, exist_ok=True)
    f = REPORTS / f"{re.sub(r'[^a-zA-Z0-9 ]', '', topic)[:50].strip()} {datetime.date.today()}.md"
    links = "\n".join(f"- {r.get('href')}" for r in results)
    f.write_text(f"# {topic}\n\n{report}\n\n## Sources\n{links}\n", encoding="utf-8")
    return f"REPORT SAVED: {f}\n\n{report[:1500]}"


# ---- screen / mouse / keyboard ----
@tool("read_screen", "Screen par abhi jo text dikh raha hai wo padho")
def t_read_screen():
    return pc.read_screen()[:4000]


@tool("click_text", "Screen par likhe kisi text/button par click karo", {"text": ("string", "button ya text")})
def t_click_text(text):
    return pc.click_text(text)


@tool("mouse_click", "Screen ke x,y par click karo", {"x": ("integer", "x"), "y": ("integer", "y")})
def t_mouse_click(x, y):
    return pc.click(x, y)


@tool("scroll", "Page upar/neeche scroll karo", {"direction": ("string", "up ya down")})
def t_scroll(direction):
    return pc.scroll(direction, 6)


@tool("press_keys", "Keyboard shortcut dabao, jaise ctrl+t, alt+tab, enter", {"keys": ("string", "keys")})
def t_press_keys(keys):
    return pc.hotkey(keys)


@tool("type_text", "Jis jagah cursor hai wahan text type karo", {"text": ("string", "text")}, risk="medium")
def t_type_text(text):
    return pc.type_text(text)


@tool("browser_action", "Browser control: new_tab, close_tab, next_tab, previous_tab, back, forward, refresh, "
      "address_bar, reopen_tab, bookmark, history, downloads, zoom_in, zoom_out, find",
      {"action": ("string", "action ka naam")})
def t_browser(action):
    return pc.browser(action)


# ---- files ----
@tool("list_folder", "Folder ki files dekho (downloads, documents, desktop ya path)", {"path": ("string", "folder")})
def t_list_folder(path):
    p = resolve(path)
    items = sorted(p.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:40]
    return "\n".join(f"{'[DIR] ' if i.is_dir() else ''}{i.name}" for i in items) or "(khali)"


@tool("read_file", "Text/code file padho", {"path": ("string", "file path")})
def t_read_file(path):
    return resolve(path).read_text(encoding="utf-8", errors="ignore")[:6000]


@tool("write_file", "File mein text likho (nayi file ya overwrite)", {"path": ("string", "file"),
      "content": ("string", "text")}, risk="high")
def t_write_file(path, content):
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"written {p}"


@tool("create_folder", "Naya folder banao", {"path": ("string", "folder path")})
def t_create_folder(path):
    p = resolve(path)
    p.mkdir(parents=True, exist_ok=True)
    return f"created {p}"


@tool("move_file", "File/folder move ya rename karo", {"source": ("string", "kahan se"),
      "destination": ("string", "kahan")}, risk="high")
def t_move_file(source, destination):
    import shutil
    return f"moved to {shutil.move(str(resolve(source)), str(resolve(destination)))}"


@tool("delete_file", "File ko Recycle Bin mein bhejo", {"path": ("string", "file")}, risk="high")
def t_delete_file(path):
    p = resolve(path)
    if sys.platform == "win32":
        ps = ("Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::"
              f"{'DeleteDirectory' if p.is_dir() else 'DeleteFile'}('{str(p)}','OnlyErrorDialogs','SendToRecycleBin')")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], creationflags=pc.NO_WINDOW)
        return f"sent to recycle bin: {p}"
    return "delete sirf Windows par (Recycle Bin ke saath)"


@tool("organize_folder", "Folder ki files ko type ke hisaab se sub-folders mein lagao (Images, Documents...)",
      {"path": ("string", "folder, jaise downloads")}, risk="high")
def t_organize(path):
    import shutil
    kinds = {"Images": (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"), "Videos": (".mp4", ".mkv", ".mov", ".avi"),
             "Documents": (".pdf", ".docx", ".doc", ".txt", ".pptx", ".xlsx", ".csv"), "Music": (".mp3", ".wav", ".m4a"),
             "Archives": (".zip", ".rar", ".7z"), "Programs": (".exe", ".msi")}
    p, moved = resolve(path), 0
    for f in p.iterdir():
        if f.is_file():
            for k, exts in kinds.items():
                if f.suffix.lower() in exts:
                    (p / k).mkdir(exist_ok=True)
                    shutil.move(str(f), str(p / k / f.name))
                    moved += 1
    return f"organized {moved} files in {p}"


# ---- pdf ----
@tool("read_pdf", "PDF file ka text padho (naam ya path)", {"name": ("string", "pdf ka naam ya path")})
def t_read_pdf(name):
    p = resolve(name) if (os.sep in name or "/" in name or name.lower().endswith(".pdf")) else None
    if not p or not p.exists():
        p = find_named(name.replace(".pdf", ""), (".pdf",))
    if not p:
        return f"'{name}' naam ki PDF nahi mili"
    from pypdf import PdfReader
    reader = PdfReader(str(p))
    text = "\n".join((pg.extract_text() or "") for pg in reader.pages[:40])
    return f"PDF: {p.name}, {len(reader.pages)} pages\n{text[:8000]}"


# ---- terminal / git / code ----
@tool("run_terminal", "Terminal/CMD command chalao aur output lao", {"command": ("string", "command"),
      "folder": ("string", "kis folder mein (project naam ya path), khali = home")}, risk="high")
def t_terminal(command, folder=""):
    if any(d in command.lower() for d in DANGEROUS):
        return "BLOCKED: ye command khatarnaak hai, JARVIS ise nahi chalayega"
    cwd = resolve(folder) if folder else HOME
    r = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=120)
    return (r.stdout + r.stderr).strip()[-4000:] or f"(done, exit code {r.returncode})"


def _git(repo, *args):
    r = subprocess.run(["git", *args], cwd=resolve(repo), capture_output=True, text=True, timeout=60)
    return (r.stdout + r.stderr).strip()


@tool("git_status", "Git project ka status, branch aur last commits", {"repo": ("string", "project naam ya path")})
def t_git_status(repo):
    return (f"BRANCH: {_git(repo, 'branch', '--show-current')}\nSTATUS:\n{_git(repo, 'status', '--short') or 'clean'}"
            f"\nLAST COMMITS:\n{_git(repo, 'log', '--oneline', '-5')}")


@tool("git_pull", "Git project ko GitHub se update (pull) karo", {"repo": ("string", "project")}, risk="medium")
def t_git_pull(repo):
    return _git(repo, "pull")


@tool("git_diff", "Git project mein kya badla (diff) dekho", {"repo": ("string", "project")})
def t_git_diff(repo):
    return (_git(repo, "diff", "HEAD~1", "--stat") + "\n" + _git(repo, "diff", "HEAD~1"))[:6000]


@tool("review_code", "Code file ko bugs ke liye check karo aur sudhaar batao", {"path": ("string", "file")})
def t_review_code(path):
    p = resolve(path)
    code = p.read_text(encoding="utf-8", errors="ignore")
    numbered = "\n".join(f"{i + 1}: {line}" for i, line in enumerate(code.splitlines()[:400]))
    return llm(f"File {p.name} ko bugs ke liye review karo. Har bug: line number, kya galat hai, fix kaise karein. "
               f"Sirf asli bugs, chhota rakho. Bug na mile to 'No obvious bugs' likho.\n\n{numbered}")


@tool("check_project", "Poora project check karo: git status, naye changes, syntax errors, code review, aur report",
      {"repo": ("string", "project naam ya path")})
def t_check_project(repo):
    root = resolve(repo)
    if not root.exists():
        return f"project '{repo}' nahi mila. config.py mein PROJECTS mein naam aur path jodo."
    parts = [f"# Project report: {root.name} ({datetime.date.today()})"]
    if (root / ".git").exists():
        parts.append("## Git\n" + t_git_status(str(root)))
        changed = [f for f in _git(str(root), "diff", "--name-only", "HEAD~3").splitlines() if f.strip()]
    else:
        changed = []
    if not changed:
        changed = [str(f.relative_to(root)) for f in sorted(root.rglob("*.py"), key=lambda f: f.stat().st_mtime,
                   reverse=True) if ".venv" not in f.parts][:5]
    errors = []
    for f in root.rglob("*.py"):
        if ".venv" in f.parts or "site-packages" in f.parts:
            continue
        r = subprocess.run([sys.executable, "-m", "py_compile", str(f)], capture_output=True, text=True)
        if r.returncode:
            errors.append(r.stderr.strip()[-400:])
    parts.append("## Syntax check\n" + ("\n".join(errors) if errors else "Sab Python files compile ho rahi hain."))
    for f in [c for c in changed if c.endswith((".py", ".js", ".ts", ".java", ".php", ".go"))][:3]:
        if (root / f).exists():
            parts.append(f"## Review: {f}\n" + t_review_code(str(root / f)))
    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"project {root.name} {datetime.date.today()}.md"
    out.write_text("\n\n".join(parts), encoding="utf-8")
    return f"REPORT SAVED: {out}\n\n" + "\n\n".join(parts)[:3000]


@tool("run_jarvis_command", "JARVIS ki koi bhi seedhi command chalao: apps kholna/band karna, volume, screenshot, "
      "timer, notepad, whatsapp, weather, todo, etc.", {"command": ("string", "jaise 'open notepad', 'volume 50 karo'")})
def t_jarvis_command(command):
    return AGENT.skills.handle(command) if AGENT and AGENT.skills else "skills not ready"


# ======================= AGENT =======================
AGENT_PROMPT = """You are JARVIS, the main brain of a personal AI assistant on the user's Windows PC.
Break the user's task into steps and use the tools to actually do it. Call one tool at a time, read its result,
then decide the next step. When the task is done, reply with a short spoken summary (2-4 sentences, Indian English,
no markdown). If a report was saved, mention it. Never claim you did something unless a tool result confirms it.
Today is {today}. Known projects: {projects}. Folders: downloads, documents, desktop, pictures."""


class Agent:
    def __init__(self, skills=None):
        self.skills = skills
        self.confirm = lambda question: False      # main.py voice se confirm lagata hai
        self.progress = lambda text: None           # HUD log
        self.stop = None

    # ---------- tool chalana (permission ke saath) ----------
    def call(self, name, args):
        t = TOOLS.get(name)
        if not t:
            return f"unknown tool {name}"
        if t["risk"] == "high":
            detail = ", ".join(f"{k}: {str(v)[:80]}" for k, v in args.items())
            if not self.confirm(f"{config.USER_NAME}, should I {name.replace('_', ' ')}? {detail}"):
                log(f"DENIED {name} {args}")
                self.denied = True
                return "USER DENIED this action. Do not retry it."
        self.progress(f"{name} {json.dumps(args, ensure_ascii=False)[:60]}")
        log(f"TOOL {name} {json.dumps(args, ensure_ascii=False)[:300]}")
        try:
            result = str(t["fn"](**args))
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as e:              # kisi tool ki galti se JARVIS crash na ho
            result = f"ERROR: {type(e).__name__}: {e}"
        log(f"  -> {result[:200]!r}")
        return result

    # ---------- multi-step agent loop ----------
    def run(self, task):
        import ollama
        s = config.USER_NAME
        messages = [{"role": "system", "content": AGENT_PROMPT.format(
            today=datetime.date.today(), projects=", ".join(config.PROJECTS) or "none")},
            {"role": "user", "content": task}]
        schemas = [t["schema"] for t in TOOLS.values()]
        log(f"TASK {task}")
        for _ in range(config.AGENT_MAX_STEPS):
            if self.stop is not None and self.stop.is_set():
                return f"Stopped, {s}."
            try:
                r = ollama.chat(model=config.AGENT_MODEL, messages=messages, tools=schemas)
            except Exception as e:
                return f"{s}, my brain is offline. Please start Ollama. ({e})"
            msg = r["message"]
            calls = msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", None)
            content = (msg.get("content") if isinstance(msg, dict) else msg.content) or ""
            messages.append({"role": "assistant", "content": content, "tool_calls": calls or []})
            if not calls:
                return content.strip() or f"Done, {s}."
            for c in calls:
                fn = c["function"] if isinstance(c, dict) else c.function
                name = fn["name"] if isinstance(fn, dict) else fn.name
                args = fn["arguments"] if isinstance(fn, dict) else fn.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                messages.append({"role": "tool", "content": self.call(name, args or {})[:4000], "tool_name": name})
        return f"{s}, I did {config.AGENT_MAX_STEPS} steps. Please check the activity log for details."

    # ---------- seedhe commands (bina model ke) ----------
    def fast(self, cmd):
        self.denied = False
        out = self._fast(cmd)
        return f"Okay {config.USER_NAME}, cancelled." if out and self.denied else out

    def _fast(self, cmd):
        s = config.USER_NAME

        def after(pattern):
            m = re.search(pattern, cmd)
            return m.group(1).strip(" .?") if m else None

        if re.search(r"start (button|menu)|windows (button|key|menu)", cmd):
            self.call("press_keys", {"keys": "win"})
            return f"Opened the Start menu, {s}."
        if re.search(r"(read|padho|padh do).*(screen)|screen (par|pe) kya|what.*on (my )?screen", cmd):
            text = self.call("read_screen", {})
            lines = [line for line in text.splitlines() if len(line) > 3][:8]
            return f"{s}, I can see: " + ". ".join(lines)[:300]
        x = after(r"^(.+?)\s+(?:par|pe) click(?: karo| kar do)?$") or after(r"(?:click on|click karo)\s+(.+)")
        if x:
            return f"{s}, " + self.call("click_text", {"text": x})
        x = after(r"^(?:press|dabao)\s+(.+)") or after(r"(.+?)\s+dabao$")
        if x and re.fullmatch(r"[a-z0-9+ ]+", x):
            return f"Done, {s}. " + self.call("press_keys", {"keys": x.replace(" plus ", "+").replace(" ", "")})
        if re.search(r"scroll (down|neeche|niche)|neeche scroll", cmd):
            return self.call("scroll", {"direction": "down"}) and f"Scrolled down, {s}."
        if re.search(r"scroll (up|upar)|upar scroll", cmd):
            return self.call("scroll", {"direction": "up"}) and f"Scrolled up, {s}."
        for words, action in [(("new tab", "naya tab"), "new_tab"), (("close tab", "tab band"), "close_tab"),
                              (("next tab", "agla tab"), "next_tab"), (("previous tab", "pichla tab"), "previous_tab"),
                              (("go back", "peeche jao", "wapas jao"), "back"), (("go forward", "aage jao"), "forward"),
                              (("refresh", "reload"), "refresh"), (("zoom in",), "zoom_in"), (("zoom out",), "zoom_out"),
                              (("reopen tab", "band tab kholo"), "reopen_tab"), (("bookmark",), "bookmark")]:
            if any(w in cmd for w in words):
                self.call("browser_action", {"action": action})
                return f"Done, {s}."
        if "research" in cmd:
            if any(w in cmd for w in ["kiya hai", "kya research", "yaad", "remember", "kiya tha"]):
                return self.skills.knowledge.kya_seekha() if self.skills else None
            topic = research_topic(cmd)
            if topic:
                out = self.call("deep_research", {"topic": topic})
                if out.startswith("REPORT SAVED"):
                    report = out.split("\n\n", 1)[1]
                    if self.skills:
                        self.skills.knowledge.add(topic, report, [])
                    from .brain import clean
                    summary = clean(re.sub(r"(?im)^#+.*$", "", report))[:350]
                    return (f"{s}, research on {topic} is complete. I have saved it in my memory and in Documents, "
                            f"JARVIS Reports. {summary}")
                return out
        if re.search(r"\bpdf\b|p d f", cmd) and re.search(r"read|padh|open|khol|summar|batao|sunao|dikhao", cmd):
            name = pdf_name(cmd)
            path = find_pdf(name)
            if not path:
                return f"Sorry {s}, I could not find a PDF named {name or 'that'} in Desktop, Documents or Downloads."
            if re.search(r"open|khol|dikhao", cmd) and sys.platform == "win32":
                os.startfile(str(path))
            if re.search(r"read|padh|summar|batao|sunao", cmd):
                text = self.call("read_pdf", {"name": str(path)})
                if text.startswith("PDF:"):
                    return f"{s}, I found {path.name}. " + llm(
                        f"Is PDF ki 4-5 line ki simple summary do (spoken English, no markdown):\n{text}")
                return text
            return f"Opening {path.name}, {s}."
        x = after(r"(?:check|analyze|analyse)\s+(?:my\s+)?(.+?)\s+project") or after(r"(?:mera|my)\s+(.+?)\s+project\s+check")
        if x:
            out = self.call("check_project", {"repo": x})
            if out.startswith("REPORT SAVED"):
                return llm("Is project report ko 3-4 line mein bolkar batao (Indian English, no markdown), "
                           "bugs aur syntax errors par focus:\n" + out)[:700] + f" The full report is in Documents, JARVIS Reports, {s}."
            return out
        x = after(r"git status (?:of |for )?(.+)") or after(r"(.+?)\s+(?:ka|ki) git status")
        if x:
            return f"{s}, " + self.call("git_status", {"repo": x}).replace("\n", ". ")[:600]
        x = after(r"(?:run command|command chalao|cmd mein chalao|terminal mein chalao|run)\s+(.+)")
        if x and cmd.startswith(("run command", "command chalao", "cmd", "terminal", "run ")):
            return f"{s}, output: " + self.call("run_terminal", {"command": x, "folder": ""})[:500]
        x = after(r"(?:organize|organise|saaf karo|arrange)\s+(?:my\s+)?(\w+)\s*(?:folder)?")
        if x and x in ALIASES:
            return f"{s}, " + self.call("organize_folder", {"path": x})
        x = after(r"(?:review|check)\s+(?:the\s+)?code\s+(?:of\s+|in\s+)?(.+)")
        if x:
            return self.call("review_code", {"path": x})[:800]
        return None


RESEARCH_FILLER = ["ek kaam karo", "ek kam karo", "google se", "internet se", "web se", "deep research",
                   "research", "karo", "kar do", "karke", "ke bare mein", "ke baare mein", "ke bare me", "about",
                   "on", "par", "pe", "please", "jarvis", "detail mein", "achhe se", "puri", "poori"]
PDF_STOP = {"pdf", "p", "d", "f", "read", "padho", "padh", "kar", "karo", "do", "open", "kholo", "khol", "usko",
            "use", "isko", "aur", "batao", "bata", "folder", "downloads", "download", "documents", "desktop", "mein",
            "me", "main", "ek", "pada", "padi", "hai", "from", "the", "in", "file", "summary", "summarize", "ki",
            "ka", "ke", "wali", "naam", "named", "my", "mera", "meri", "se", "and", "it", "please", "sunao", "ko",
            "dikhao", "of", "a", "jo", "hua", "hui", "rakha", "rakhi", "wala"}


def research_topic(cmd):
    """'ek kaam karo affiliate marketing ke bare mein google se research karo aur memory mein store karo'
    -> 'affiliate marketing'"""
    parts = re.split(r"\s+(?:aur|and then|and|phir|then|uske baad)\s+", cmd)
    part = next((p for p in parts if "research" in p), cmd)
    for w in sorted(RESEARCH_FILLER, key=len, reverse=True):
        part = re.sub(rf"\b{re.escape(w)}\b", " ", part)
    return " ".join(part.split())


def pdf_name(cmd):
    return " ".join(w for w in re.findall(r"[a-z0-9]+", cmd) if w not in PDF_STOP)


def find_pdf(name):
    """Desktop/Documents/Downloads/OneDrive mein PDF dhoondo; naam thoda alag ho tab bhi (fuzzy)."""
    import difflib
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    pdfs = []
    for base in [HOME / "Downloads", HOME / "Desktop", HOME / "Documents", HOME / "OneDrive"]:
        if not base.exists():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "AppData")]
            pdfs += [Path(root) / f for f in files if f.lower().endswith(".pdf")]
            if len(pdfs) > 3000:
                break
    if not pdfs:
        return None
    if not key:                                   # naam nahi bola: sabse nayi PDF
        return max(pdfs, key=lambda p: p.stat().st_mtime)

    def score(p):
        stem = re.sub(r"[^a-z0-9]", "", p.stem.lower())
        if key in stem:
            return 2 + len(key) / max(len(stem), 1)
        return difflib.SequenceMatcher(None, key, stem).ratio()
    best = max(pdfs, key=score)
    return best if score(best) >= 0.55 else None


AGENT = None
AGENT_WORDS = ["karo", "kar do", "and then", "phir", "uske baad", "check", "analyze", "analyse", "find", "dhundo",
               "compare", "download", "folder", "file", "project", "report", "fill", "login", "research", "summarize"]


def needs_agent(cmd):
    """Lamba/multi-step kaam lagta hai? Tab Main Brain (tools ke saath) ko do."""
    return len(cmd.split()) >= 5 and any(w in cmd for w in AGENT_WORDS)
