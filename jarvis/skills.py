"""Commands: JARVIS kaunsa kaam kaise karega. Naya kaam add karna ho to yahan add karo."""
import datetime
import os
import platform
import subprocess
import webbrowser

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
              "search", "google", "bhool jao", "forget everything"]


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

    def handle(self, cmd):
        """Jawab (str) lautata hai. None matlab band ho jao."""
        s = config.USER_NAME
        if any(w in cmd for w in ["bye", "exit", "band ho", "goodbye"]):
            return None

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
