"""Commands: JARVIS kaunsa kaam kaise karega. Naya kaam add karna ho to yahan add karo."""
import datetime
import os
import platform
import subprocess
import re
import webbrowser
from pathlib import Path

from . import config, internet
from . import skills_extra as extra
from . import agent as agent_mod
from .learner import Learner, subject_from
from . import builder
from . import audit
from . import selfimprove
from .plugins import PluginManager
from . import intent
from . import integrations as ig
from . import vision
from . import coder
from . import goals as goals_mod
from . import security
from . import project as project_mod
from . import versioning
from . import selfupgrade
from . import selfcode

APPS = {
    "notepad": {"Windows": "notepad", "Darwin": "open -a TextEdit", "Linux": "gedit"},
    "calculator": {"Windows": "calc", "Darwin": "open -a Calculator", "Linux": "gnome-calculator"},
    "chrome": {"Windows": "start chrome", "Darwin": "open -a 'Google Chrome'", "Linux": "google-chrome"},
    "vs code": {"Windows": "code", "Darwin": "code", "Linux": "code"},
    "paint": {"Windows": "mspaint", "Darwin": "", "Linux": ""},
    "edge": {"Windows": "start msedge", "Darwin": "", "Linux": ""},
    "word": {"Windows": "start winword", "Darwin": "", "Linux": ""},
    "excel": {"Windows": "start excel", "Darwin": "", "Linux": ""},
    "settings": {"Windows": "start ms-settings:", "Darwin": "", "Linux": ""},
    "command prompt": {"Windows": "start cmd", "Darwin": "", "Linux": ""},
}
PROCESSES = {"notepad": "notepad.exe", "calculator": "CalculatorApp.exe", "chrome": "chrome.exe",
             "vs code": "Code.exe", "paint": "mspaint.exe", "edge": "msedge.exe", "word": "WINWORD.EXE",
             "excel": "EXCEL.EXE", "spotify": "Spotify.exe", "whatsapp": "WhatsApp.exe",
             "command prompt": "cmd.exe"}
CLOSE_WORDS = ["close", "band kar", "band karo", "band kardo", "bandh", "quit", "kill"]
WEBSITES = {"youtube": "https://youtube.com", "google": "https://google.com",
            "gmail": "https://mail.google.com", "whatsapp": "https://web.whatsapp.com",
            "instagram": "https://instagram.com"}


TASK_WORDS = ["open", "kholo", "khol", "play", "chalao", "learn", "seekho", "sikho",
              "search", "google", "bhool jao", "forget everything", "likho", "likh do", "write", "type",
              "close", "band kar", "bandh", "lock", "screenshot", "whatsapp", "email", "find file",
              "research", "project", "pdf", "organize", "organise", "run command", "landing", "website", "banao"]
FOLDER_QUESTIONS = ["kaun sa folder", "kon sa folder", "which folder", "konsa folder", "kaunsa folder",
                    "folders open", "folder khula", "open folders"]
HOME = Path.home()
FOLDERS = {"download": HOME / "Downloads", "document": HOME / "Documents", "desktop": HOME / "Desktop",
           "picture": HOME / "Pictures", "photo": HOME / "Pictures", "music": HOME / "Music",
           "video": HOME / "Videos"}
NOTES_DIR = HOME / "Documents" / "JARVIS Notes"


def notepad_text(cmd):
    """'write X in notepad', 'notepad mein likho X', 'X notepad par likho' se X nikalo.
    Notepad me likhne ki baat hi nahi to None, text nahi mila to ""."""
    if "notepad" not in cmd or not any(w in cmd for w in ["likh", "write", "type"]):
        return None
    pats = [r"(?:write|type|likho|likh do)\s+(.+?)\s+(?:in|on|into)\s+(?:the\s+)?notepad",
            r"notepad\s+(?:me|mein|main|par|pe|pr)\s+(?:likho|likh do|write|type)\s+(.+)",
            r"(?:write|type)\s+(?:in|on|into)\s+notepad\s+(.+)",
            r"(.+?)\s+(?:write|type|likho|likh do)\s+(?:in|on|into)?\s*(?:the\s+)?notepad",
            r"(.+?)\s+notepad\s+(?:me|mein|main|par|pe|pr)\s+(?:likho|likh do|write)"]
    for p in pats:
        m = re.search(p, cmd)
        if m:
            text = m.group(1).strip(" ,.")
            if text not in ("kuch", "something", "ek kaam karo", "mujhe"):
                return text
    return ""


def open_path(path):
    if platform.system() == "Windows":
        os.startfile(str(path))
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_explorer_folders():
    """Windows par abhi khule File Explorer folders ke naam."""
    if platform.system() != "Windows":
        return []
    script = ("(New-Object -ComObject Shell.Application).Windows() | "
              "Where-Object { $_.FullName -like '*explorer.exe' } | ForEach-Object { $_.LocationName }")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True,
                         text=True, timeout=10, creationflags=0x08000000).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


QUESTION_WORDS = ["what", "who", "how", "why", "when", "where", "which", "kya", "kaun", "kon", "kaise", "kyu",
                  "kitna", "kitne", "kitni", "kab", "kahan", "batao", "bataiye", "explain", "ke bare", "ke baare",
                  "pata hai", "matlab", "meaning", "tell me"]


def is_question(cmd):
    return any(w in cmd for w in QUESTION_WORDS)


ACTION_RE = re.compile(r"\b(open|kholo|khol do|close|band kar\w*|play|chalao|likho|likh do|write|type|search|dhundo|"
                       r"research|organi[sz]e|screenshot|banao|bana do|learn|seekho|sikho|sikhna|seekhna|sikhana|padhna|whatsapp|"
                       r"email|mail|lock|click|delete|move|run command|install|download)\b")


def is_task(cmd):
    """Kya ye koi kaam hai? Sawaal ("google ads kaise chalate hain") task nahi hai."""
    if not ACTION_RE.search(cmd):
        return False
    return not (is_question(cmd) and not re.search(r"\b(karo|kar do|banao|kholo|open|start|sikho|seekho|bhejo|send)\b", cmd))


def day_answer(cmd, s):
    """'aaj/kal/parso kaun sa din hai', 'what is the date tomorrow' jaise sawaal. Match na ho to None."""
    words = set(cmd.replace("?", " ").split())
    if not words & {"date", "tareekh", "tarikh", "din", "day", "dinank"}:
        return None
    offset, label = 0, "today"
    if words & {"yesterday"} or "kal tha" in cmd or "kal kya tha" in cmd:
        offset, label = -1, "yesterday"
    elif words & {"parso", "parson"}:
        offset, label = 2, "the day after tomorrow"
    elif words & {"tomorrow", "kal", "cal", "call"}:
        offset, label = 1, "tomorrow"
    d = datetime.date.today() + datetime.timedelta(days=offset)
    verb = "was" if offset < 0 else ("is" if offset == 0 else "will be")
    return f"{s}, {label} {verb} {d:%A}, {d.day} {d:%B %Y}."


def _after(cmd, *words):
    for w in words:
        if w in cmd:
            return cmd.split(w, 1)[1].strip()
    return ""


class Skills:
    def __init__(self, brain, knowledge):
        self.brain = brain
        self.knowledge = knowledge
        self.pending = None     # jaise "notepad": agla vaakya notepad mein likhna hai
        self.timers = extra.Timers()
        self.agent = agent_mod.Agent(self)
        agent_mod.AGENT = self.agent
        self.learner = Learner(knowledge, lambda prompt: agent_mod.llm(prompt))
        self.plugins = PluginManager(lambda prompt: agent_mod.llm(prompt))
        self.plugins.on_change = lambda: agent_mod.registry_sync(self.plugins)
        agent_mod.registry_sync(self.plugins)
        self.orchestrator = goals_mod.Orchestrator(self.agent, agent_mod.llm)
        self.route = ""
        self.scheduler = None       # main.py lagata hai
        import threading
        self.lock = threading.RLock()   # awaaz, phone aur schedules ek saath na takrayein

    def core_modules(self, cmd):
        """Goal engine, tool registry, security, browser/computer-use, project understanding, self-upgrade, git."""
        s = config.USER_NAME
        llm = agent_mod.llm
        if re.search(r"(goals?|last goal)\s+(dikhao|batao|status|list)|show (my )?goals|goal ka status", cmd):
            return self.orchestrator.describe()
        if re.search(r"(tools?|tool registry)\s+(list|dikhao|batao)|kaun se tools|what tools", cmd):
            return agent_mod.registry_describe()
        m = re.search(r"safe mode\s+(on|off|chalu|band)", cmd)
        if m:
            return security.set_safe_mode(m.group(1) in ("on", "chalu"))
        if re.search(r"permissions? (batao|dikhao|list)|security (status|batao)|what can you do without asking", cmd):
            return security.describe()
        if re.search(r"skill history|skills? ka history|version history", cmd):
            return versioning.history()
        if re.search(r"undo (last )?skill change|skill change undo", cmd):
            return versioning.undo_last()
        if re.search(r"(self|code) upgrade undo|undo (self|code) upgrade|pichla code wapas", cmd):
            return selfcode.undo()
        m = re.search(r"(?:apna|apne|your|khud ka|khud ke)\s+code\s+(?:ko\s+)?(?:upgrade|improve|sudhaar|sudhar|better|update|behtar)\w*"
                      r"\s*(?:karo|kar do|karke)?\s*(?:taaki|taki|jisse|jis se|jisase|so that|ki|:)?\s*(.*)", cmd)
        if m:
            if len(m.group(1).split()) < 2:
                return self.self_review()               # kya sudhaarna hai? khud check karke chuno
            return self.selfcoder().propose(m.group(1))
        if re.search(r"(core|apna|apne|khud ka|khud ke|tumhara)\s+(core\s+)?code\s+(ko\s+)?(check|review|dekho|padho|analy[sz]e)", cmd) \
                and not re.search(r"smart|sikh|seekh", cmd):
            return self.self_review()
        if re.search(r"(seekha|sikha|seekhi|sikhi|learnt|learned|learning)\s+(hua|hui|cheezein|cheeze|things|knowledge)?\s*"
                     r"(apply|lagao|use karo|apne upar)|apply (your |my )?(learnings?|knowledge)|khud (par|pe|per) apply", cmd):
            return self.apply_learnings()
        if re.search(r"(kya kya|kitne|which|what)\s+(upgrade|upgrades|sudhaar|improvement)|upgrade (list|history)|"
                     r"kya (upgrade|seekha|badla) (hua|hue|kiya)|changelog", cmd):
            return self.upgrade_history()
        if re.search(r"(khud ko|apne aap ko|yourself)\s+(smart|smarter|intelligent|behtar|better)|smart bano|smarter bano|"
                     r"internet.{0,60}(upgrade|smart|improve|behtar)", cmd):
            return self.smart_upgrade(cmd)
        if re.search(r"apni kamiyan|kamiyan door|self.?upgrade engine|fix your gaps|upgrade your (skills|capabilities)|"
                     r"jo nahi kar paye (wo|woh) seekho", cmd):
            return selfupgrade.run(self.plugins, self.agent.confirm, self.agent.progress)
        m = re.search(r"(?:test|check)\s+(?:the\s+)?website\s+(\S+)|website\s+(\S+)\s+(?:ko\s+)?test|(\S+\.\S+)\s+(?:ko\s+)?test karo", cmd)
        if m:
            return self.agent.call("test_website", {"url": m.group(1) or m.group(2) or m.group(3)})
        m = re.search(r"(?:computer use|khud (?:se )?(?:screen par |pc par )?karo|screen par khud)\s*[:,]?\s*(.+)", cmd)
        if m:
            return self.agent.call("computer_use", {"task": m.group(1)})
        m = re.search(r"(?:understand|samjho|analy[sz]e)\s+(?:my\s+|the\s+)?(\w+)\s+project|(\w+)\s+project\s+(?:ko\s+)?samjho", cmd)
        if m:
            return project_mod.understand(m.group(1) or m.group(2), llm, self.knowledge)
        m = re.search(r"(\w+)\s+project\s+(?:mein|me|in)\s+(.+)", cmd)
        if m and m.group(1).lower() in config.PROJECTS and re.search(r"kahan|kaha|kaise|where|how|kya|which|what", cmd):
            return project_mod.ask(m.group(1), m.group(2), llm)
        m = re.search(r"(?:browser|chrome)\s+(?:agent|mein|me)\s+(.+)", cmd)
        if m and not re.search(r"search", cmd):
            return self.orchestrator.agent.run(m.group(1), set(agent_mod.CATEGORIES.get("browser", [])))
        return None

    def capability_answer(self, cmd):
        """'kya tum internet access kar sakte ho' jaise sawaal: jawab code se (AI kabhi galat bol deta tha)."""
        s = config.USER_NAME
        can = re.search(r"(kar )?(sakte|sakoge|sakta) ho|can you|are you able|kya tum|kya aap", cmd)
        if not can or re.search(r"search|dhundo|dhoondo|kholo|open|play|chalao|bhejo|send|likho|batao|bataiye|"
                                r"weather|news|price", cmd):
            return None                                   # ye asal mein kaam maanga hai, sirf sawaal nahi
        if re.search(r"\b(internet|net|online|web|google)\b", cmd):
            status = "and I am connected right now" if internet.internet_hai() else "but right now there is no internet connection"
            return (f"Yes {s}, I can use the internet, {status}. I can search Google, read websites, do research, get "
                    f"news and weather, learn subjects, and control a real browser.")
        if re.search(r"(khud|apne aap|yourself|self).{0,40}(sikh|seekh|learn|upgrade|smart|improve)|self learning|"
                     r"(sikh|seekh|learn).{0,30}(khud|apne aap)", cmd):
            return (f"Yes {s}. I can learn subjects from the internet and test myself, build new skills for things I "
                    f"could not do, and check and improve my own code with your permission. Just say: internet se "
                    f"seekho aur khud ko smart banao.")
        return None

    def apply_learnings(self):
        """Seekhe subjects se bane ideas ek-ek karke: batao -> "yes" -> safe self-code-upgrade."""
        from .learner import load_ideas, IDEAS_FILE
        import json as _json
        s = config.USER_NAME
        ideas = load_ideas()
        pending = [i for i in ideas if i["status"] == "pending"]
        if not pending:
            done = [n for n, x in self.learner.state.get("subjects", {}).items() if x.get("done_all")]
            if not done:
                return (f"{s}, I have not finished learning any subject yet, so there is nothing to apply. "
                        f"When I finish a subject I will think how to use it to improve myself.")
            tried = {i["subject"] for i in ideas}
            fresh = [d for d in done if d not in tried]
            if not fresh:
                return (f"{s}, I have already applied or offered ideas from everything I have learnt so far. "
                        f"When I finish new subjects I will have new ideas.")
            for subj in fresh[-3:]:
                self.learner._apply_idea(subj)
            ideas = load_ideas()
            pending = [i for i in ideas if i["status"] == "pending"]
            if not pending:
                return f"{s}, I thought about what I learnt, but found nothing that can improve my own code right now."
        results = []
        for item in pending[:3]:
            if not self.agent.confirm(f"{s}, from {item['subject']} I learnt this idea: {item['idea'][:200]}. Should I apply it to myself?"):
                item["status"] = "skipped"
                continue
            out = self.selfcoder().propose(item["idea"])
            item["status"] = "applied" if out.startswith("Done") else "failed"
            results.append(f"{item['subject']}: {item['status']}")
        for it in ideas:
            for p in pending:
                if it["idea"] == p["idea"]:
                    it["status"] = p["status"]
        IDEAS_FILE.write_text(_json.dumps(ideas, ensure_ascii=False, indent=1), encoding="utf-8")
        left = sum(1 for i in ideas if i["status"] == "pending")
        return (f"{s}, " + ("; ".join(results) + ". " if results else "I did not apply anything. ")
                + (f"{left} more ideas are waiting. " if left else "")
                + "Restart me to use any applied changes.")

    def upgrade_history(self):
        """'kya kya upgrade hue hain': code sudhaar, banayi skills, seekhe subjects."""
        s = config.USER_NAME
        parts = []
        root = selfcode.WORK / "backups"
        ups = [(b / "summary.txt").read_text(encoding="utf-8") for b in sorted(root.iterdir())
               if (b / "summary.txt").exists()] if root.exists() else []
        parts.append(f"{len(ups)} code upgrades" + (f": {'; '.join(ups[-3:])}" if ups else ""))
        sk = self.plugins.list()
        parts.append(f"{len(sk)} new skills" + (f": {', '.join(m['name'].replace('_', ' ') for m in sk[-4:])}" if sk else ""))
        subj = [n for n, x in self.learner.state.get("subjects", {}).items() if x.get("done_all")]
        parts.append(f"{len(subj)} subjects learnt" + (f": {', '.join(subj[-5:])}" if subj else ""))
        q = self.learner.state.get("queue", [])
        if q:
            parts.append(f"now learning {', '.join(q[:3])}")
        return f"{s}, my upgrades so far: " + ". ".join(parts) + ". My version is " + config.VERSION + "."

    def self_review(self):
        """Apna code check karo -> sabse zaroori chhota sudhaar chuno -> (permission ke saath) lagao."""
        s = config.USER_NAME
        report = self.agent.call("check_project", {"repo": "jarvis"})
        if not report.startswith("REPORT SAVED"):
            return report
        idea = agent_mod.llm("This is a code check report of JARVIS, a voice assistant. Pick the ONE most valuable, "
                             "small and safe improvement and write it as one clear sentence (what to change and "
                             "where). If there is nothing important, reply exactly: NOTHING.\n\n" + report[:6000]).strip()
        if not idea or idea.upper().startswith("NOTHING"):
            return f"{s}, I checked my core code. No syntax errors and nothing important to fix. The report is in Documents, JARVIS Reports."
        if not self.agent.confirm(f"{s}, I checked my code. The most useful fix is: {idea[:200]}. Should I try it?"):
            return f"Okay {s}. I checked my code and saved the report in Documents, JARVIS Reports. I did not change anything."
        return self.selfcoder().propose(idea[:300])

    def selfcoder(self):
        return selfcode.SelfCoder(agent_mod.llm, self.agent.confirm, self.agent.progress)

    def smart_upgrade(self, cmd):
        """'internet se seekho aur khud ko smart banao': gyaan taaza + kamiyon ki skills + apne code ka ek sudhaar."""
        s = config.USER_NAME
        report = []
        topic = re.search(r"(.+?)\s+(?:ke bare mein|ke baare mein|about)\b", cmd)
        topic = subject_from(topic.group(1)) if topic else ""
        if topic and len(topic.split()) <= 4 and topic not in ("khud", "apne"):
            report.append(self.learner.start(topic).split(".")[0] + ".")
        elif self.learner.state.get("queue"):
            self.learner.resume()
            report.append(f"I am already learning {', '.join(self.learner.state['queue'][:3])} from the internet.")
        elif self.learner.state.get("subjects"):
            self.learner.upgrade()
            report.append("I am refreshing everything I have learnt with the latest information from the internet.")
        else:
            report.append("I have not learnt any subject yet, so tell me a topic to learn, like: learn python.")
        if selfupgrade.gaps():
            report.append(selfupgrade.run(self.plugins, self.agent.confirm, self.agent.progress))
        lessons = selfimprove.lessons_for("self code upgrade skill goal step failed", limit=3)
        d, _ = selfimprove.summary()
        recent = [f["error"] for f in d["failures"][-5:]]
        if re.search(r"internet|research|news|trend|latest|naye features|analytics", cmd) and internet.internet_hai():
            out = self.agent.call("deep_research", {"topic": "latest features and ideas for personal AI voice assistants"})
            if out.startswith("REPORT SAVED"):
                ideas = agent_mod.llm("From this research, list 3 short new feature ideas a Windows voice assistant could add, "
                                      "one line each, spoken style:\n" + out[:5000])
                self.knowledge.add("ideas: new assistant features", out.split("\n\n", 1)[-1][:4000], [])
                report.append("I researched the latest assistant features. Ideas I could add: " + " ".join(ideas.split())[:350]
                              + ". Say 'ek skill banao jo ...' for any of them.")
        if re.search(r"\bcode\b", cmd) or not (lessons or recent):
            report.append(self.self_review())             # "core code check karo ... smart banao"
        elif self.agent.confirm(f"{s}, should I also read my own code and try to fix my most common mistake?"):
            idea = agent_mod.llm("From these recent problems of a voice assistant, write ONE small, concrete code "
                                 "improvement request (one sentence):\n" + "\n".join(lessons + recent))
            report.append(self.selfcoder().propose(idea.strip()[:300]))
        return f"{s}, " + " ".join(report)

    def phase2(self, cmd):
        """Gmail, Calendar, GitHub, Git, Database, Server, Smart home, Vision, Coding, Schedules, Cloud brain."""
        s = config.USER_NAME
        llm = agent_mod.llm
        confirm = self.agent.confirm
        # ---- schedules ----
        if self.scheduler:
            if re.search(r"(my |meri |sab )?schedules? (dikhao|batao|list)|show (my )?schedules|what are my schedules", cmd):
                return self.scheduler.describe()
            m = re.search(r"(?:schedule|shedule)\s+(\d+)\s+(?:hatao|delete|remove|band)|(?:delete|remove)\s+schedule\s+(\d+)", cmd)
            if m:
                return self.scheduler.remove(int(m.group(1) or m.group(2)))
            added = self.scheduler.add(cmd)
            if added:
                return added
        # ---- cloud / local brain ----
        m = re.search(r"(cloud|local|auto)\s+(brain|dimaag|mode)\s*(on|chalu|karo|use karo)?", cmd)
        if m:
            config.BRAIN_MODE = {"cloud": "cloud", "local": "local", "auto": "auto"}[m.group(1)]
            from .llm_client import cloud_provider
            note = "" if config.BRAIN_MODE == "local" or cloud_provider() else \
                " But no cloud API key is set, so I will keep using the local brain."
            return f"Okay {s}, brain mode is now {config.BRAIN_MODE}.{note}"
        # ---- gmail ----
        if re.search(r"(unread|new|naye|naya|kitne)\s+(e-?mails?|mails?)|(e-?mails?|mails?|inbox)\s+(check|padho|dekho|batao|read|sunao)|"
                     r"check (my )?(e-?mail|mail|inbox)|read (my )?(e-?mails?|mails?)", cmd):
            return ig.gmail_unread(llm=llm)
        m = re.search(r"(?:send|bhejo)\b.*?(?:e-?mail|mail)", cmd)
        if m and getattr(config, "GMAIL_APP_PASSWORD", "") and re.search(r"\b(message|body)\b", cmd):
            to = extra.spoken_email(cmd) or next((a for n, a in config.EMAILS.items() if n in cmd), "")
            sub = re.search(r"subject\s+(?:is\s+)?(.+?)(?:\s+(?:message|body)\b|$)", cmd)
            body = re.search(r"(?:message|body)\s+(?:is\s+)?(.+)", cmd)
            if to and body and confirm(f"{s}, send email to {to}: {body.group(1)[:80]}?"):
                return ig.gmail_send(to, sub.group(1) if sub else "Message from JARVIS", body.group(1))
        # ---- calendar ----
        m = re.search(r"(?:add|daalo|create|set|lagao)\s+(?:a\s+|ek\s+)?(?:meeting|event|appointment)\s+(.+)|"
                      r"calendar (?:mein|me|par|pe) (.+?) (?:add|daalo|dalo)", cmd)
        if m:
            text = m.group(1) or m.group(2)
            title = re.sub(r"\b(at|on|kal|tomorrow|aaj|today|\d{1,2}([:.]\d{2})?\s*(am|pm|baje)?)\b", " ", text)
            title = " ".join(title.split()).title() or "Meeting"
            if title.lower().startswith(("with ", "se ")):
                title = "Meeting " + title
            return ig.calendar_add(title, text)
        if re.search(r"\b(calendar|meetings?|events?|appointments?)\b", cmd) and not re.search(r"\b(add|create|daalo)\b", cmd):
            return ig.calendar_day(1 if re.search(r"\b(kal|tomorrow)\b", cmd) else 0)
        # ---- github / git ----
        if "github" in cmd:
            return ig.github(cmd, llm)
        m = re.search(r"(?:commit|push)\s+(?:and push\s+)?(?:my\s+|the\s+)?(\w+)\s+project|(\w+)\s+project\s+(?:ko\s+)?(?:commit|push)", cmd)
        if m:
            name = m.group(1) or m.group(2)
            path = config.PROJECTS.get(name)
            if not path:
                return f"{s}, I do not know the {name} project. Add it to PROJECTS in my_settings.py."
            if not confirm(f"{s}, should I commit and push all changes in the {name} project?"):
                return f"Okay {s}, cancelled."
            return ig.git_commit_push(path, f"Update from JARVIS {datetime.datetime.now():%Y-%m-%d %H:%M}")
        # ---- database / server / smart home ----
        if re.search(r"\b(database|db)\b", cmd):
            return ig.database(cmd, llm)
        if re.search(r"\b(server|ssh)\b", cmd):
            return ig.server(cmd, confirm)
        if re.search(r"\b(lights?|batti|bulb|lamp|fan|pankha|ac|thermostat|geyser|tv)\b", cmd) and \
                re.search(r"\b(on|off|band|chalu|jala|bujha|set|karo|kar do|\d{2})\b", cmd):
            return ig.smart_home(cmd)
        # ---- vision ----
        if re.search(r"\b(cctv|gate camera|door camera)\b", cmd):
            return vision.cctv(cmd, cmd)
        if re.search(r"camera\s+(se\s+|mein\s+)?(dekho|dekh|look|check)|what do you see|kya dikh raha|mujhe dekho|look at me|"
                     r"camera (on|kholo) (karo )?(aur|and)", cmd):
            return vision.look_camera(cmd)
        if re.search(r"screen\s+(ko\s+)?(dekho|dekh kar|analy[sz]e)|look at (my )?screen|screen par kya ho raha|explain (my|the) screen", cmd):
            return vision.look_screen(cmd)
        m = re.search(r"(?:image|photo|picture|tasveer|pic)\s+(.+?)\s+(?:dekho|analy[sz]e|describe|batao|mein kya hai)|"
                      r"(?:analy[sz]e|describe|dekho)\s+(?:the\s+|my\s+)?(?:image|photo|picture|pic)\s+(.+)", cmd)
        if m:
            return vision.look_image((m.group(1) or m.group(2)).strip(), cmd)
        # ---- coding ----
        if re.search(r"(program|code|script|function)\s+(likho|likh do|banao|bana do|write)|write (a |an |me a )?(\w+ )?(program|code|script)|"
                     r"(program|code) (likh|bana)", cmd):
            return coder.write_and_run(cmd, llm, progress=self.agent.progress)
        m = re.search(r"(?:run|test|chalao|test karo)\s+(?:the\s+)?(?:file\s+)?([\w./\\: -]+\.(?:py|js|php|java|cpp|c|go|rs|sh))", cmd)
        if m:
            return coder.test_file(m.group(1), llm)
        return None

    def self_upgrade(self, cmd):
        """Skill Builder, self-test, dashboard, suggestions, audit. Match na ho to None."""
        s = config.USER_NAME
        m = re.search(r"(?:skill|feature|capability|tool)\s+(?:banao|bana do|create karo|build karo|sikho)\s+(?:jo|ki|that|to)?\s*(.*)|"
                      r"(?:create|build|make)\s+(?:a\s+)?(?:new\s+)?(?:skill|tool)\s+(?:that|to|for|which)?\s*(.*)|"
                      r"(?:ek\s+)?(?:nayi|naya|new)\s+skill\s+(?:banao|bana do)?\s*(?:jo|ki)?\s*(.*)", cmd)
        if m:
            request = next((g for g in m.groups() if g), "").strip()
            if len(request.split()) < 2:
                return f"{s}, what should the new skill do? Say for example: ek skill banao jo bitcoin ka price bataye."
            return self.plugins.create(request)
        if re.search(r"(kaun si|konsi|kya kya|list|meri|your|all)\s+skills|skills (list|dikhao|batao)", cmd):
            return self.plugins.describe()
        m = re.search(r"(?:improve|upgrade|better|sudhaaro|sudharo)\s+(?:skill\s+)?(.+?)(?:\s+skill)?(?:\s+(?:so that|taaki|ki)\s+(.+))?$", cmd)
        if m and "skill" in cmd:
            return self.plugins.improve(m.group(1).replace("skill", "").strip(), m.group(2) or "")
        m = re.search(r"rollback\s+(?:skill\s+)?(.+)", cmd)
        if m and "skill" in cmd:
            return self.plugins.rollback(m.group(1).replace("skill", "").strip())
        m = re.search(r"(disable|enable|band karo|chalu karo)\s+(?:skill\s+)?(.+)|skill\s+(.+?)\s+(disable|enable|band karo|chalu karo)", cmd)
        if m and "skill" in cmd:
            name = (m.group(2) or m.group(3) or "").replace("skill", "").strip()
            return self.plugins.set_enabled(name, (m.group(1) or m.group(4)) in ("enable", "chalu karo"))
        if re.search(r"dashboard", cmd):
            selfimprove.dashboard(self.learner, self.knowledge, self.plugins)
            return f"Opening my dashboard, {s}."
        if re.search(r"kya improve|what should you improve|suggestion|kya nahi kar (sakte|paye|paya)|kamiyan batao|\bkami\b|gap analysis|"
                     r"what can't you do|weakness", cmd):
            return selfimprove.suggestions()
        if re.search(r"(self test|apna test|quiz|test (do|lo|karo)|exam)", cmd) and not re.search(r"website|code|project", cmd):
            subject = next((n for n in self.learner.state["subjects"] if n in cmd), None)
            return self.learner.self_test(subject)
        m = re.search(r"audit\s+(?:karo\s+)?(?:of\s+|website\s+)?([a-z0-9.-]+\.[a-z]{2,}(?:/\S*)?)|([a-z0-9.-]+\.[a-z]{2,})\s+(?:ka|ki)\s+audit", cmd)
        if m:
            return audit.report(m.group(1) or m.group(2))
        return None

    def handle(self, cmd):
        """handle ke upar record: success / failure / capability gap (self-improvement ke liye)."""
        self.route = ""
        try:
            with self.lock:
                reply = self._handle(cmd)
        except Exception as e:
            selfimprove.record(cmd, "", ok=False, error=f"{type(e).__name__}: {e}")
            raise
        if reply is not None:
            gap = self.route == "chat" and is_task(cmd) and selfimprove.looks_like_gap(cmd, reply)
            selfimprove.record(cmd, reply, ok=not reply.startswith(("Sorry", "ERROR")), gap=gap)
        return reply

    def learn_many(self, text):
        """'seekho: python, php, hindi language, google ads' -> sab learning list mein."""
        from .learner import valid_subject
        s = config.USER_NAME
        items = [" ".join(p.split()) for p in re.split(r",|;|\n|\baur\b|\band\b", text)]
        good = [p for p in items if p and valid_subject(p)]
        bad = [p for p in items if p and not valid_subject(p)]
        if not good:
            return f"{s}, I could not understand the list. Separate subjects with commas, like: seekho: python, php, java."
        for g in good:
            self.learner.start(g)
        msg = (f"Okay {s}, I have added {len(good)} subjects to my learning list and started learning them one by one "
               f"in the background: {', '.join(good[:8])}{' and more' if len(good) > 8 else ''}. "
               f"Say 'learning status' any time to check progress.")
        if bad:
            msg += f" I skipped these because they were not clear subjects: {', '.join(bad[:5])}."
        return msg

    def learning(self, cmd):
        """Seekhne se jude saare commands. Match na ho to None."""
        s = config.USER_NAME
        if re.search(r"(stop|band|pause|ruk)\w*\s+(learning|seekhna|sikhna)|(learning|seekhna|sikhna)\s+(band|stop|roko|pause)", cmd):
            return self.learner.stop()
        if re.search(r"resume learning|continue learning|seekhna (jaari|continue|wapas)|learning (resume|continue|wapas)", cmd):
            return (f"Resuming learning, {s}." if self.learner.resume()
                    else f"{s}, there is nothing pending to learn.")
        if re.search(r"upgrade (yourself|karo|kar lo|karlo)|khud ko upgrade|apne aap ko upgrade|self upgrade", cmd):
            return self.learner.upgrade()
        if re.search(r"learning status|kya seekh rahe|kya sikh rahe|kitna seekha|kitna sikha|kya kya seekha|kya kya sikha|"
                     r"kya seekha|kya sikha|what did you learn|what have you learn|what are you learning", cmd):
            return self.learner.status() + " " + self.knowledge.kya_seekha()
        if cmd.startswith(("notes", "seekha hua batao")):
            return self.knowledge.batao(_after(cmd, "notes", "batao"))
        if re.search(r"(learning list|seekhne ki list|learning queue)\s*(saaf|clear|khali|delete)|clear (the )?learning (list|queue)", cmd):
            return self.learner.clear_queue()
        m = re.search(r"(?:remove|hatao|hata do|delete)\s+(.+?)\s+(?:from|se)\s+(?:the\s+)?(?:learning|list)|"
                      r"(.+?)\s+(?:ko\s+)?learning (?:list )?se (?:hatao|hata do|remove karo)", cmd)
        if m:
            return self.learner.remove((m.group(1) or m.group(2)).strip())
        m = re.search(r"(?:seekho|sikho|seekh lo|sikh lo|learn|sikhna hai|seekhna hai|padho)\s*(?:ye sab|sab)?\s*[:\-]\s*(.+)", cmd)
        if m and ("," in m.group(1) or ";" in m.group(1)):
            return self.learn_many(m.group(1))
        if re.search(r"\b(seekho|sikho|sikhao|seekhao|seekh lo|sikh lo|learn karo|learn kar lo|learn karna (start|shuru)|"
                     r"(seekhna|sikhna|sikhana|seekhana|padhna|learning) (start|shuru)|start learning|learn about)\b|^learn\s", cmd):
            subject = subject_from(cmd)
            if not subject:
                return f"{s}, what should I learn? Say for example: learn Python."
            return self.learner.start(subject)
        return None

    def write_notepad(self, text):
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        f = NOTES_DIR / datetime.datetime.now().strftime("note_%Y-%m-%d_%H-%M-%S.txt")
        f.write_text(text + "\n", encoding="utf-8")
        if platform.system() == "Windows":
            subprocess.Popen(["notepad", str(f)])
        else:
            open_path(f)
        return f"Done {config.USER_NAME}, I have written it in Notepad and saved it in Documents, JARVIS Notes."

    def jarvis_facts(self):
        """JARVIS apne baare mein sach bataye (sawaal: 'band kar dun to bhi seekhoge?')."""
        q = self.learner.state.get("queue", [])
        online = internet.internet_hai()
        return ("Facts about yourself (JARVIS), always answer consistently with these: "
                f"You are {'CONNECTED to the internet right now' if online else 'OFFLINE right now (no internet)'}. "
                "YES, you can use the internet: Google/web search, reading websites, deep research reports, news, "
                "weather, Wikipedia, learning whole subjects, controlling a real browser (Playwright) and testing "
                "websites. YES, you can learn by yourself and upgrade yourself: learn whole subjects from the internet "
                "and test yourself with quizzes ('python seekho'), build new skills for things you could not do "
                "('apni kamiyan door karo'), and safely improve your own code after the user approves "
                "('apna code upgrade karo taaki ...', 'internet se seekho aur khud ko smart banao'). "
                f"Learning status right now: {self.learner.status()} "
                "Your name comes from J.A.R.V.I.S. (Just A Rather Very Intelligent System), Tony Stark's AI assistant "
                "in the Iron Man movies, voiced by Paul Bettany; it later became Vision. If the user asks about "
                "Tony Stark's JARVIS ('uska AI Jarvis'), answer about that movie AI, not about the user. "
                "You are male: in Hindi/Hinglish always use masculine forms (kar sakta hoon, main karta hoon). "
                "Learning runs in the background only while JARVIS is running. "
                "If the user closes JARVIS, learning pauses and automatically continues from the same chapter "
                "next time JARVIS starts. Nothing learnt is lost; memory is deleted only if the user says "
                "'memory delete karo' and confirms. "
                + (f"Currently pending to learn: {', '.join(q)}." if q else "Nothing is pending to learn."))

    def _handle(self, cmd):
        """Jawab (str) lautata hai. None matlab band ho jao."""
        s = config.USER_NAME
        if any(w in cmd for w in ["bye", "exit", "goodbye"]) or cmd.strip() in ("band ho jao", "jarvis band ho jao"):
            return None
        helped = extra.help_text(cmd, s) or self.capability_answer(cmd)   # apne baare mein pakke jawab
        if helped:
            return helped
        # sawaal jaisa vaakya? pehle samjho ki ye order hai ya sawaal (koi adhoora kaam pending na ho tab)
        if not self.pending and intent.ambiguous(cmd) and intent.classify(cmd) == "question":
            return self.chat(cmd)

        # ---- pichla adhoora kaam ----
        if self.pending == "notepad":
            self.pending = None
            return self.write_notepad(cmd)

        if self.pending == "wipe":
            self.pending = None
            if any(w in cmd.split() for w in ["yes", "haan", "ha", "han", "confirm"]):
                self.knowledge.items = []
                self.knowledge._save()
                self.learner.state = {"queue": [], "subjects": {}}
                self.learner._save()
                extra._save(extra.FACTS_FILE, [])
                self.brain.bhool_jao()
                return f"Done {s}. I have deleted all my memory and knowledge."
            return f"Okay {s}, your memory is safe. Nothing was deleted."

        # ---- memory delete: sirf aapke kehne par, confirm ke saath ----
        if re.search(r"(memory|knowledge|yaadasht|gyaan)\s+(delete|clear|saaf|mita)|delete (all )?(memory|knowledge)|"
                     r"sab kuch bhool jao|forget everything", cmd):
            self.pending = "wipe"
            return (f"{s}, this will delete everything I have learnt and remembered. "
                    f"Are you sure? Say yes to delete.")

        # ---- apna code update (update.bat) ----
        if self.pending == "code_update":
            self.pending = None
            if any(w in cmd.split() for w in ["yes", "haan", "ha", "han", "confirm"]):
                bat = Path(__file__).resolve().parent.parent / "update.bat"
                if platform.system() == "Windows" and bat.exists():
                    subprocess.Popen(["cmd", "/c", "start", "", str(bat)], cwd=str(bat.parent))
                    return f"{s}, the update window is open. When it finishes, close me and start JARVIS again."
                return f"{s}, please run update.bat from the JARVIS folder."
            return f"Okay {s}, no update."
        if re.search(r"(code|software|version|jarvis)\s+(update|updte)|update (your )?(code|software|version)|naya version", cmd) \
                and not re.search(r"taaki|so that|apna code|apne code|khud ka code|improve", cmd):
            self.pending = "code_update"
            return f"{s}, should I download the latest version of my code? Your memory will stay safe. Say yes or no."

        # ---- kai kaam ek saath -> Goal Engine + Orchestrator (pehle, taaki "test karo" jaise hisse na bhatkein) ----
        if goals_mod.is_goal(cmd):
            return self.orchestrator.run(cmd)

        # ---- self-upgrade: skill builder, self-test, dashboard, audit ----
        jawab = self.self_upgrade(cmd)
        if jawab:
            return jawab

        # ---- core: goals, registry, security, browser, computer use, project, self-upgrade ----
        jawab = self.core_modules(cmd)
        if jawab:
            return jawab

        # ---- Phase 2/3: gmail, calendar, github, db, server, smart home, vision, coding, schedules ----
        jawab = self.phase2(cmd)
        if jawab:
            return jawab

        # ---- JARVIS ki khud banayi skills (aapki banwayi skill built-in se pehle) ----
        jawab = self.plugins.match(cmd)
        if jawab:
            return jawab

        # ---- website / landing page banana ----
        if builder.wants_page(cmd):
            return builder.build(cmd, agent_mod.llm)[1]

        # ---- seekhna ----
        jawab = self.learning(cmd)
        if jawab:
            return jawab

        # ---- notepad mein likhna ----
        note = notepad_text(cmd)
        if note is not None:
            if note:
                return self.write_notepad(note)
            self.pending = "notepad"
            return f"Sure {s}, what should I write in Notepad?"

        # ---- confirm wale kaam ----
        if self.pending in ("shutdown", "restart"):
            action, self.pending = self.pending, None
            if any(w in cmd.split() for w in ["yes", "haan", "ha", "han", "confirm", "kar", "karo"]):
                if platform.system() == "Windows":
                    subprocess.Popen(f"shutdown /{'s' if action == 'shutdown' else 'r'} /t 15", shell=True)
                return f"Okay {s}, the laptop will {action} in 15 seconds. Save your work."
            return f"Okay {s}, cancelled."

        if self.pending == "recycle":
            self.pending = None
            if any(w in cmd.split() for w in ["yes", "haan", "ha", "han", "confirm"]):
                extra._ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
                return f"Recycle bin is empty now, {s}."
            return f"Okay {s}, cancelled."

        # ---- app band karna ----
        if any(w in cmd for w in CLOSE_WORDS):
            for name, proc in PROCESSES.items():
                if name in cmd:
                    if platform.system() != "Windows":
                        return f"{s}, closing apps works on Windows only."
                    res = subprocess.run(["taskkill", "/IM", proc], capture_output=True, creationflags=0x08000000)
                    if res.returncode != 0:
                        return f"{s}, {name} was not open."
                    return f"Closing {name}, {s}."

        # ---- laptop: lock / shutdown / restart ----
        if "shutdown" in cmd or "shut down" in cmd or "restart" in cmd:
            self.pending = "restart" if "restart" in cmd else "shutdown"
            return f"{s}, are you sure you want to {self.pending} the laptop? Say yes or no."
        if "lock" in cmd or ("laptop" in cmd and ("band" in cmd or "off" in cmd)):
            if platform.system() == "Windows":
                import ctypes
                ctypes.windll.user32.LockWorkStation()
            return f"Locking the laptop, {s}."

        # ---- location ----
        if any(w in cmd for w in ["location", "kahan hoon", "kaha hoon", "where am i", "kahan hu", "kaha hu"]):
            if not internet.internet_hai():
                return f"{s}, I need internet to find your location."
            import requests
            d = requests.get("https://ipinfo.io/json", timeout=8).json()
            return (f"{s}, as per your internet connection you are near {d.get('city', 'unknown city')}, "
                    f"{d.get('region', '')}, {d.get('country', '')}. This is approximate, not GPS.")

        # ---- PC / screen / browser / research / pdf / git (seedhe) ----
        jawab = self.agent.fast(cmd)
        if jawab:
            return jawab

        # ---- extra skills (volume, timer, calculator, news...) ----
        jawab = self.timers.handle(cmd, s) or extra.recycle_bin(cmd, s, self)
        if jawab:
            return jawab
        for skill in extra.SIMPLE:
            jawab = skill(cmd, s)
            if jawab:
                return jawab

        # ---- file explorer aur folders ----
        if any(q in cmd for q in FOLDER_QUESTIONS):
            names = open_explorer_folders()
            if not names:
                return f"{s}, no folder is open in File Explorer right now."
            return f"{s}, these folders are open: " + ", ".join(names) + "."
        if any(w in cmd for w in ["file explorer", "explorer", "my computer", "this pc", "file manager"]):
            if platform.system() == "Windows":
                subprocess.Popen("explorer")
            else:
                open_path(HOME)
            return f"Opening File Explorer, {s}."
        if any(w in cmd for w in ["open", "kholo", "khol"]):
            for key, path in FOLDERS.items():
                if key in cmd:
                    open_path(path)
                    return f"Opening your {path.name} folder, {s}."

        if cmd.strip() in ("bhool jao", "baatein bhool jao", "chat bhool jao"):
            self.brain.bhool_jao()
            return f"Done {s}, I have cleared our chat history. Everything I have learnt is still safe."

        # ---- basic ----
        day = day_answer(cmd, s)
        if day:
            return day
        if "time" in cmd or "samay" in cmd or "baje" in cmd:
            return datetime.datetime.now().strftime(f"{s}, the time is %I:%M %p.")

        # ---- apps aur websites ----
        if any(w in cmd for w in ["open", "kholo", "khol"]):
            for name, cmds in APPS.items():          # pehle apps ("google chrome" = Chrome app)
                if name in cmd:
                    subprocess.Popen(cmds[platform.system()], shell=True)
                    return f"{name} is open, {s}."
            for name, url in WEBSITES.items():
                if name in cmd:
                    webbrowser.open(url)
                    return f"Opening {name}, {s}."
            jawab = extra.open_any_site(cmd, s)
            if jawab:
                return jawab

        # ---- online kaam ----
        online_words = ["weather", "mausam", "play", "chalao", "search", "news", "khabar", "google"]
        if any(w in cmd for w in online_words):
            if not internet.internet_hai():
                return f"Sorry {s}, I need internet for this. I am offline right now."
            if "weather" in cmd or "mausam" in cmd:
                return internet.mausam(_after(cmd, " in ", " of "))
            if "play" in cmd or "chalao" in cmd:
                song = cmd.replace("play", "").replace("chalao", "").strip()
                try:
                    import pywhatkit
                    pywhatkit.playonyt(song)
                except Exception:
                    webbrowser.open(f"https://www.youtube.com/results?search_query={song}")
                return f"Playing {song} on YouTube, {s}."
            q = extra.search_query(cmd) if re.search(r"search|dhundo|dhoondo|look up", cmd) else None
            if q:
                webbrowser.open("https://www.google.com/search?q=" + extra.quote(q))
                return f"Searching {q} on Google, {s}."

        if "shutdown" in cmd:
            return f"{s}, for safety I don't shut down the system myself. Please do it manually."

        # ---- baaki sab: baatcheet, seekhi hui jaankari ke saath ----
        self.route = "chat"
        if agent_mod.needs_agent(cmd):
            return self.agent.run(cmd)          # multi-step: Main Brain tools ke saath
        return self.chat(cmd)

    def chat(self, cmd):
        """Baatcheet: yaad rakhi baatein + seekha gyaan + (sawaal ho to) internet."""
        self.route = "chat"
        context = [extra.facts_text(), self.knowledge.context(cmd), self.jarvis_facts()]
        if is_question(cmd) and internet.internet_hai():   # sawaal hai to internet se taaza jaankari
            web = internet.search(cmd, max_results=5)
            if web:
                context.append("Internet se abhi mili jaankari (isi par jawab do):\n" +
                               "\n".join(f"- {r.get('title')}: {r.get('body')}" for r in web))
            else:
                context.append("Internet par is baare mein kuch nahi mila. Agar pakka nahi pata to saaf bolo "
                               "'I am not sure about this', andaza mat lagao.")
        return self.brain.socho(cmd, extra_context="\n\n".join(c for c in context if c))
