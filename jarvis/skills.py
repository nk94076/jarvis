"""Commands: JARVIS kaunsa kaam kaise karega. Naya kaam add karna ho to yahan add karo."""
import datetime
import os
import platform
import subprocess
import re
import webbrowser
from pathlib import Path

from . import config, internet

APPS = {
    "notepad": {"Windows": "notepad", "Darwin": "open -a TextEdit", "Linux": "gedit"},
    "calculator": {"Windows": "calc", "Darwin": "open -a Calculator", "Linux": "gnome-calculator"},
    "chrome": {"Windows": "start chrome", "Darwin": "open -a 'Google Chrome'", "Linux": "google-chrome"},
    "vs code": {"Windows": "code", "Darwin": "code", "Linux": "code"},
}
WEBSITES = {"youtube": "https://youtube.com", "google": "https://google.com",
            "gmail": "https://mail.google.com", "whatsapp": "https://web.whatsapp.com",
            "instagram": "https://instagram.com"}


TASK_WORDS = ["open", "kholo", "khol", "play", "chalao", "learn", "seekho", "sikho",
              "search", "google", "bhool jao", "forget everything", "likho", "likh do", "write", "type"]
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
        return self.brain.socho(cmd, extra_context=self.knowledge.context(cmd))
