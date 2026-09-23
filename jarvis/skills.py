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
              "research", "project", "pdf", "organize", "organise", "run command"]
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


def is_task(cmd):
    """Kya ye koi kaam hai (sirf baatcheet ya sawaal nahi)?"""
    return any(w in cmd for w in TASK_WORDS)


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

    def write_notepad(self, text):
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        f = NOTES_DIR / datetime.datetime.now().strftime("note_%Y-%m-%d_%H-%M-%S.txt")
        f.write_text(text + "\n", encoding="utf-8")
        if platform.system() == "Windows":
            subprocess.Popen(["notepad", str(f)])
        else:
            open_path(f)
        return f"Done {config.USER_NAME}, I have written it in Notepad and saved it in Documents, JARVIS Notes."

    def handle(self, cmd):
        """Jawab (str) lautata hai. None matlab band ho jao."""
        s = config.USER_NAME
        if any(w in cmd for w in ["bye", "exit", "band ho", "goodbye"]):
            return None

        # ---- pichla adhoora kaam ----
        if self.pending == "notepad":
            self.pending = None
            return self.write_notepad(cmd)

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

        # ---- seekhna ----
        if cmd.startswith(("seekho", "sikho", "learn")):
            topic = _after(cmd, "seekho", "sikho", "learn", "about").removeprefix("about").strip()
            return self.knowledge.seekho(topic) if topic else f"What should I learn, {s}?"
        if any(w in cmd for w in ["kya seekha", "kya sikha", "what did you learn", "what have you learned", "what have you learnt"]):
            return self.knowledge.kya_seekha()
        if cmd.startswith(("notes", "seekha hua batao")):
            return self.knowledge.batao(_after(cmd, "notes", "batao"))
        if any(w in cmd for w in ["bhool jao", "forget everything"]):
            self.brain.bhool_jao()
            return f"Done {s}, I have cleared our conversation memory."

        # ---- basic ----
        day = day_answer(cmd, s)
        if day:
            return day
        if "time" in cmd or "samay" in cmd or "baje" in cmd:
            return datetime.datetime.now().strftime(f"{s}, the time is %I:%M %p.")

        # ---- apps aur websites ----
        if any(w in cmd for w in ["open", "kholo", "khol"]):
            for name, url in WEBSITES.items():
                if name in cmd:
                    webbrowser.open(url)
                    return f"Opening {name}, {s}."
            for name, cmds in APPS.items():
                if name in cmd:
                    subprocess.Popen(cmds[platform.system()], shell=True)
                    return f"{name} is open, {s}."
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
            query = _after(cmd, "search", "google") or cmd
            results = internet.search(query)
            info = "\n".join(r.get("body", "") for r in results)
            return self.brain.socho(f"Internet se mili jaankari:\n{info}\n\nIs se jawab do: {cmd}")

        if "shutdown" in cmd:
            return f"{s}, for safety I don't shut down the system myself. Please do it manually."

        # ---- baaki sab: baatcheet, seekhi hui jaankari ke saath ----
        if agent_mod.needs_agent(cmd):
            return self.agent.run(cmd)          # multi-step: Main Brain tools ke saath
        context = "\n\n".join(c for c in [extra.facts_text(), self.knowledge.context(cmd)] if c)
        return self.brain.socho(cmd, extra_context=context)
