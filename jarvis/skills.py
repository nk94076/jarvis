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
            return self.knowledge.seekho(topic) if topic else f"{s}, kya seekhun?"
        if any(w in cmd for w in ["kya seekha", "kya sikha", "what did you learn", "what have you learned"]):
            return self.knowledge.kya_seekha()
        if cmd.startswith(("notes", "seekha hua batao")):
            return self.knowledge.batao(_after(cmd, "notes", "batao"))
        if any(w in cmd for w in ["bhool jao", "forget everything"]):
            self.brain.bhool_jao()
            return f"{s}, maine baatcheet ki memory mita di."

        # ---- basic ----
        if "time" in cmd or "samay" in cmd:
            return datetime.datetime.now().strftime(f"{s}, abhi %I:%M %p baje hain.")
        if "date" in cmd or "tareekh" in cmd:
            return datetime.date.today().strftime(f"{s}, aaj %d %B %Y hai.")

        # ---- apps aur websites ----
        if any(w in cmd for w in ["open", "kholo", "khol"]):
            for name, url in WEBSITES.items():
                if name in cmd:
                    webbrowser.open(url)
                    return f"{name} khol raha hoon, {s}."
            for name, cmds in APPS.items():
                if name in cmd:
                    subprocess.Popen(cmds[platform.system()], shell=True)
                    return f"{name} khol diya, {s}."

        # ---- online kaam ----
        online_words = ["weather", "mausam", "play", "chalao", "search", "news", "khabar", "google"]
        if any(w in cmd for w in online_words):
            if not internet.internet_hai():
                return f"{s}, iske liye internet chahiye. Abhi main offline hoon."
            if "weather" in cmd or "mausam" in cmd:
                return internet.mausam(_after(cmd, " in ", " of "))
            if "play" in cmd or "chalao" in cmd:
                song = cmd.replace("play", "").replace("chalao", "").strip()
                try:
                    import pywhatkit
                    pywhatkit.playonyt(song)
                except Exception:
                    webbrowser.open(f"https://www.youtube.com/results?search_query={song}")
                return f"{song} chala raha hoon, {s}."
            query = _after(cmd, "search", "google") or cmd
            results = internet.search(query)
            info = "\n".join(r.get("body", "") for r in results)
            return self.brain.socho(f"Internet se mili jaankari:\n{info}\n\nIs se jawab do: {cmd}")

        if "shutdown" in cmd:
            return f"{s}, suraksha ke liye shutdown khud nahi karta. Pehle confirm karke khud karein."

        # ---- baaki sab: baatcheet, seekhi hui jaankari ke saath ----
        return self.brain.socho(cmd, extra_context=self.knowledge.context(cmd))
