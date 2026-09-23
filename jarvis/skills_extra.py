"""Extra skills: volume, media, brightness, screenshot, battery, timer/reminder/alarm, calculator,
jokes, news, wikipedia, todo list, yaad rakhna, clipboard, typing, file dhoondhna, WhatsApp, email,
minimize, recycle bin, IP address, coin/dice, help.

Har skill ek function hai jo (cmd, s) leta hai aur jawab (str) ya None (meri skill nahi) lautata hai."""
import ast
import datetime
import json
import operator
import os
import platform
import random
import re
import socket
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote

from . import config, internet

WIN = platform.system() == "Windows"
HOME = Path.home()
TODO_FILE = config.DATA_DIR / "todo.json"
FACTS_FILE = config.DATA_DIR / "facts.json"
NO_WINDOW = 0x08000000


# ---------------- helpers ----------------
def _ps(script, timeout=15):
    """PowerShell chalao aur output lautao (sirf Windows)."""
    if not WIN:
        return ""
    return subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True,
                          text=True, timeout=timeout, creationflags=NO_WINDOW).stdout.strip()


def _keys(*vks, times=1):
    """Keyboard ki special keys dabao (volume, media, Win+D...)."""
    if not WIN:
        return
    import ctypes
    kb = ctypes.windll.user32.keybd_event
    for _ in range(times):
        for vk in vks:
            kb(vk, 0, 0, 0)
        for vk in reversed(vks):
            kb(vk, 0, 2, 0)
        time.sleep(0.02)


def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _save(path, data):
    config.DATA_DIR.mkdir(exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _num(cmd):
    m = re.search(r"\d+", cmd)
    return int(m.group()) if m else None


def _has(cmd, *words):
    return any(w in cmd for w in words)


# ---------------- volume aur media ----------------
VK_MUTE, VK_VDOWN, VK_VUP = 0xAD, 0xAE, 0xAF
VK_NEXT, VK_PREV, VK_PLAYPAUSE = 0xB0, 0xB1, 0xB3


def volume(cmd, s):
    if not _has(cmd, "volume", "awaaz", "aawaz", "sound", "mute"):
        return None
    if _has(cmd, "unmute"):
        _keys(VK_MUTE)
        return f"Unmuted, {s}."
    if _has(cmd, "mute") and not _has(cmd, "unmute"):
        _keys(VK_MUTE)
        return f"Muted, {s}."
    n = _num(cmd)
    if n is not None and _has(cmd, "set", "karo", "kar do", "par", "pe", "to", "percent"):
        _keys(VK_VDOWN, times=50)               # 0 par le jao
        _keys(VK_VUP, times=max(0, min(100, n)) // 2)
        return f"Volume set to {n} percent, {s}."
    if _has(cmd, "up", "badha", "increase", "zyada", "tez", "high"):
        _keys(VK_VUP, times=5)
        return f"Volume increased, {s}."
    if _has(cmd, "down", "kam", "ghata", "decrease", "low", "dheere"):
        _keys(VK_VDOWN, times=5)
        return f"Volume decreased, {s}."
    return None


def media(cmd, s):
    if _has(cmd, "next song", "next video", "agla gaana", "agla song", "skip song"):
        _keys(VK_NEXT)
        return f"Next track, {s}."
    if _has(cmd, "previous song", "previous video", "pichla gaana", "pichla song", "last song"):
        _keys(VK_PREV)
        return f"Previous track, {s}."
    if cmd in ("pause", "resume", "play") or _has(cmd, "pause song", "pause music", "pause video",
                                                   "gaana roko", "resume song", "resume music", "resume video"):
        _keys(VK_PLAYPAUSE)
        return f"Done, {s}."
    return None


def brightness(cmd, s):
    if not _has(cmd, "brightness", "roshni", "chamak"):
        return None
    if not WIN:
        return f"{s}, brightness control works on Windows laptops only."
    cur = _ps("(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness")
    try:
        cur = int(cur.split()[0])
    except (ValueError, IndexError):
        return f"Sorry {s}, I cannot change brightness on this screen."
    n = _num(cmd)
    if n is None:
        if _has(cmd, "up", "badha", "increase", "zyada", "high"):
            n = cur + 20
        elif _has(cmd, "down", "kam", "ghata", "decrease", "low"):
            n = cur - 20
        else:
            return f"{s}, brightness is {cur} percent."
    n = max(0, min(100, n))
    _ps(f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{n})")
    return f"Brightness set to {n} percent, {s}."


# ---------------- system ----------------
def screenshot(cmd, s):
    if not _has(cmd, "screenshot", "screen shot", "ss lo", "screen capture"):
        return None
    from PIL import ImageGrab
    folder = HOME / "Pictures" / "JARVIS Screenshots"
    folder.mkdir(parents=True, exist_ok=True)
    f = folder / datetime.datetime.now().strftime("screenshot_%Y-%m-%d_%H-%M-%S.png")
    ImageGrab.grab(all_screens=True).save(f)
    return f"Screenshot saved in Pictures, JARVIS Screenshots, {s}."


def battery(cmd, s):
    if not _has(cmd, "battery", "charging", "charge"):
        return None
    import psutil
    b = psutil.sensors_battery()
    if not b:
        return f"{s}, I cannot find a battery. This looks like a desktop."
    plug = "and charging" if b.power_plugged else "and not charging"
    left = ""
    if not b.power_plugged and b.secsleft and b.secsleft > 0:
        left = f" About {b.secsleft // 3600} hours {b.secsleft % 3600 // 60} minutes left."
    return f"{s}, battery is at {b.percent:.0f} percent {plug}.{left}"


def system_status(cmd, s):
    if not _has(cmd, "system status", "cpu", "ram", "memory usage", "pc kaisa", "laptop kaisa", "system kaisa"):
        return None
    import psutil
    disk = psutil.disk_usage("C:\\" if WIN else "/")
    return (f"{s}, CPU usage is {psutil.cpu_percent(interval=0.5):.0f} percent, RAM is "
            f"{psutil.virtual_memory().percent:.0f} percent used, and disk is {disk.percent:.0f} percent full.")


def ip_address(cmd, s):
    if not _has(cmd, "ip address", "my ip", "mera ip", "ip kya"):
        return None
    try:
        sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sk.connect(("8.8.8.8", 80))
        local = sk.getsockname()[0]
        sk.close()
    except OSError:
        local = "not connected"
    public = ""
    if internet.internet_hai():
        try:
            import requests
            public = f" Public IP is {requests.get('https://api.ipify.org', timeout=6).text}."
        except Exception:
            pass
    return f"{s}, your local IP is {local}.{public}"


def windows_control(cmd, s):
    if _has(cmd, "minimize all", "minimise all", "show desktop", "desktop dikhao", "sab minimize"):
        _keys(0x5B, 0x44)                       # Win + D
        return f"Showing desktop, {s}."
    if _has(cmd, "switch window", "window badlo", "next window"):
        _keys(0x12, 0x09)                       # Alt + Tab
        return f"Switched window, {s}."
    if _has(cmd, "sleep mode", "laptop ko sula", "hibernate"):
        if WIN:
            subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return f"Putting the laptop to sleep, {s}."
    return None


# ---------------- time wale kaam ----------------
UNITS = {"sec": 1, "second": 1, "seconds": 1, "min": 60, "minute": 60, "minutes": 60, "mins": 60,
         "hour": 3600, "hours": 3600, "ghanta": 3600, "ghante": 3600}


def _duration(cmd):
    m = re.search(r"(\d+)\s*(seconds?|sec|minutes?|mins?|hours?|ghant[ae])", cmd)
    if not m:
        return None, cmd
    unit = m.group(2)
    secs = int(m.group(1)) * next(v for k, v in UNITS.items() if unit.startswith(k))
    return secs, cmd.replace(m.group(0), " ")


class Timers:
    def __init__(self):
        self.notify = print

    def _later(self, secs, msg):
        t = threading.Timer(secs, lambda: self.notify(msg))
        t.daemon = True                         # JARVIS band ho to timer bhi band
        t.start()

    def handle(self, cmd, s):
        # alarm 6:30 am
        m = re.search(r"alarm\D*(\d{1,2})(?:[:. ](\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?", cmd)
        if m:
            h, mi = int(m.group(1)), int(m.group(2) or 0)
            ap = (m.group(3) or "").replace(".", "")
            if ap == "pm" and h < 12:
                h += 12
            if ap == "am" and h == 12:
                h = 0
            now = datetime.datetime.now()
            at = now.replace(hour=h % 24, minute=mi, second=0, microsecond=0)
            if at <= now:
                at += datetime.timedelta(days=1)
            self._later((at - now).total_seconds(), f"{s}, wake up! It is {at:%I:%M %p}. This is your alarm.")
            return f"Alarm set for {at:%I:%M %p}, {s}."
        if not _has(cmd, "timer", "remind", "yaad dila", "reminder", "baad bata"):
            return None
        secs, rest = _duration(cmd)
        if not secs:
            return f"{s}, please tell me the time too, like: remind me in 10 minutes to drink water."
        for w in ["remind me", "set a", "set", "timer", "reminder", "yaad dilana", "yaad dila do", "yaad dila",
                  "baad bata dena", "baad", "in ", "after", "laga do", "lagao", "ka", "ke liye", "to "]:
            rest = rest.replace(w, " ")
        what = " ".join(rest.split())
        msg = f"{s}, reminder: {what}." if what else f"{s}, your timer is done."
        self._later(secs, msg)
        mins = secs // 60
        when = f"{mins} minutes" if mins else f"{secs} seconds"
        return f"Okay {s}, I will remind you in {when}."


# ---------------- maths aur masti ----------------
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Pow: operator.pow, ast.Mod: operator.mod, ast.USub: operator.neg}


def _safe_eval(expr):
    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in OPS:
            return OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in OPS:
            return OPS[type(n.op)](ev(n.operand))
        raise ValueError
    return ev(ast.parse(expr, mode="eval").body)


def calculator(cmd, s):
    if not (_has(cmd, "calculate", "kitna hota", "kitne hote", "kitna hai", "what is", "plus", "minus",
                 "multiply", "divide", "into", "times", "square", "percent of")
            and re.search(r"\d", cmd)):
        return None
    e = cmd
    m = re.search(r"(\d+(?:\.\d+)?)\s*percent of\s*(\d+(?:\.\d+)?)", e)
    if m:
        v = float(m.group(1)) * float(m.group(2)) / 100
        return f"{s}, that is {v:g}."
    for a, b in [("square root of", "SQRT"), ("squared", "**2"), ("square of", "SQ"), ("multiplied by", "*"),
                 ("multiply", "*"), ("divided by", "/"), ("divide", "/"), ("into", "*"), ("times", "*"),
                 ("plus", "+"), ("minus", "-"), ("x", "*"), ("guna", "*"), ("bata", "/"), ("power", "**")]:
        e = e.replace(a, f" {b} ")
    e = re.sub(r"SQRT\s*(\d+(?:\.\d+)?)", r"(\1**0.5)", e)
    e = re.sub(r"SQ\s*(\d+(?:\.\d+)?)", r"(\1**2)", e)
    e = "".join(re.findall(r"[\d.+\-*/()% ]+", e)).strip()
    if not re.search(r"\d\s*[-+*/%]", e) and "**" not in e:
        return None
    try:
        v = _safe_eval(e)
    except Exception:
        return None
    v = round(v, 4)
    return f"{s}, the answer is {v:g}."


JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "Teacher asked, why are you late? Student said, sir, the sign said school ahead, go slow.",
    "I told my computer I needed a break. It said, no problem, I will go to sleep.",
    "Why did the scarecrow win an award? Because he was outstanding in his field.",
    "My WiFi and I have a lot in common. We both lose connection when things get serious.",
    "Why was the maths book sad? It had too many problems.",
    "Papa asked, beta, result kya aaya? I said, server down hai papa.",
]
QUOTES = [
    "The best way to predict the future is to create it.",
    "Dream is not that which you see while sleeping, it is something that does not let you sleep. A P J Abdul Kalam.",
    "Arise, awake, and stop not till the goal is reached. Swami Vivekananda.",
    "Sometimes you gotta run before you can walk. Tony Stark.",
    "Success is not final, failure is not fatal. It is the courage to continue that counts.",
]


def fun(cmd, s):
    if _has(cmd, "joke", "chutkula", "hasao", "funny"):
        return random.choice(JOKES)
    if _has(cmd, "quote", "motivat", "inspire", "motivation"):
        return random.choice(QUOTES)
    words = set(cmd.split())
    if words & {"toss", "coin", "sikka"}:
        return f"{s}, it is {random.choice(['heads', 'tails'])}."
    if words & {"dice", "pasa"} or "roll a" in cmd:
        return f"{s}, you got {random.randint(1, 6)}."
    m = re.search(r"random number(?:\D+(\d+)\D+(\d+))?", cmd)
    if m:
        lo, hi = (int(m.group(1)), int(m.group(2))) if m.group(1) else (1, 100)
        return f"{s}, your number is {random.randint(min(lo, hi), max(lo, hi))}."
    return None


# ---------------- internet se ----------------
def news(cmd, s):
    if not _has(cmd, "news", "khabar", "headlines", "samachar"):
        return None
    if not internet.internet_hai():
        return f"{s}, I need internet for the news."
    import requests
    import xml.etree.ElementTree as ET
    topic = re.sub(r".*(?:news|khabar|headlines|samachar)\s*(?:about|on|of|ki|ke)?\s*", "", cmd).strip()
    url = ("https://news.google.com/rss/search?q=" + quote(topic) if topic else "https://news.google.com/rss") \
        + ("&" if topic else "?") + "hl=en-IN&gl=IN&ceid=IN:en"
    root = ET.fromstring(requests.get(url, timeout=10).content)
    titles = [i.findtext("title", "").rsplit(" - ", 1)[0] for i in root.iter("item")][:5]
    if not titles:
        return f"Sorry {s}, I could not get the news right now."
    return f"{s}, here are the top headlines. " + ". ".join(f"{n}. {t}" for n, t in enumerate(titles, 1)) + "."


def who_is(cmd, s):
    m = re.search(r"(?:who is|who was|tell me about|what is the meaning of)\s+(.+)", cmd) or \
        re.search(r"(.+?)\s+(?:kaun hai|kaun tha|kaun thi|kon hai|ke bare mein batao|ke baare mein batao|kya hota hai)", cmd)
    if not m or not internet.internet_hai():
        return None
    topic = m.group(1).strip(" ?")
    text = internet.wikipedia_summary(topic, sentences=2)
    return f"{text}" if text else None


def website(cmd, s):
    """'open amazon', 'open github.com', 'youtube par X search karo', 'google par X search karo'."""
    m = re.search(r"youtube (?:par|pe|on)\s+(.+?)\s+(?:search|dhundo|dhoondo|chalao|lagao)", cmd) or \
        re.search(r"search\s+(.+?)\s+on youtube", cmd)
    if m:
        webbrowser.open("https://www.youtube.com/results?search_query=" + quote(m.group(1)))
        return f"Searching {m.group(1)} on YouTube, {s}."
    m = re.search(r"google (?:par|pe|on)\s+(.+?)\s+(?:search|dhundo|dhoondo)", cmd) or \
        re.search(r"search\s+(.+?)\s+on google", cmd)
    if m:
        webbrowser.open("https://www.google.com/search?q=" + quote(m.group(1)))
        return f"Searching {m.group(1)} on Google, {s}."
    m = re.search(r"(?:open|kholo|khol do)\s+([a-z0-9-]+\.(?:com|in|org|net|io|co\.in|ai|dev))", cmd) or \
        re.search(r"([a-z0-9-]+\.(?:com|in|org|net|io|co\.in|ai|dev))\s+(?:kholo|khol do|open)", cmd)
    if m:
        webbrowser.open("https://" + m.group(1))
        return f"Opening {m.group(1)}, {s}."
    return None


def open_any_site(cmd, s):
    """Jab koi app/website list mein na ho: 'open flipkart' -> flipkart.com."""
    m = re.search(r"(?:open|kholo|khol do)\s+([a-z0-9]+)$", cmd) or re.search(r"^([a-z0-9]+)\s+(?:kholo|khol do|open karo)$", cmd)
    if not m or m.group(1) in ("it", "this", "that", "karo", "do"):
        return None
    site = m.group(1)
    webbrowser.open(f"https://www.{site}.com")
    return f"Opening {site} dot com, {s}."


# ---------------- aapka data ----------------
def todo(cmd, s):
    if not _has(cmd, "todo", "to do", "to-do", "task list", "kaam ki list"):
        return None
    items = _load(TODO_FILE, [])
    m = re.search(r"(?:add|daalo|jodo|likho)\s+(.+?)\s+(?:to|in|mein|me)\s+(?:my\s+)?(?:todo|to do|to-do|task list|kaam ki list)", cmd) or \
        re.search(r"(?:todo|to do|to-do|task|kaam ki)(?:\s+list)?\s+(?:mein|me|main|par)\s+(.+?)\s+(?:add|daalo|jodo|likho)", cmd)
    if m:
        items.append(m.group(1).strip())
        _save(TODO_FILE, items)
        return f"Added to your todo list, {s}. You have {len(items)} items."
    if _has(cmd, "clear", "saaf", "delete all", "khali"):
        _save(TODO_FILE, [])
        return f"Your todo list is cleared, {s}."
    m = re.search(r"(?:remove|done|complete|hatao|ho gaya)\D*(\d+)", cmd)
    if m and 0 < int(m.group(1)) <= len(items):
        done = items.pop(int(m.group(1)) - 1)
        _save(TODO_FILE, items)
        return f"Removed {done} from your list, {s}."
    if not items:
        return f"{s}, your todo list is empty."
    return f"{s}, you have {len(items)} things to do. " + ". ".join(f"{n}. {t}" for n, t in enumerate(items, 1)) + "."


def facts_text():
    facts = _load(FACTS_FILE, [])
    return "User ke baare mein yaad rakhi baatein: " + "; ".join(facts) if facts else ""


def memory(cmd, s):
    m = re.search(r"(?:remember that|remember|yaad rakho ki|yaad rakhna ki|yaad rakho|yaad rakhna)\s+(.+)", cmd) or \
        re.search(r"(.+?)\s+(?:yaad rakhna|yaad rakho)$", cmd)
    if m and not _has(cmd, "kya yaad", "what do you remember"):
        facts = _load(FACTS_FILE, [])
        facts.append(m.group(1).strip())
        _save(FACTS_FILE, facts)
        return f"Okay {s}, I will remember that."
    if _has(cmd, "kya yaad hai", "what do you remember", "what you remember", "mere baare mein kya pata"):
        facts = _load(FACTS_FILE, [])
        if not facts:
            return f"{s}, you have not told me anything to remember yet."
        return f"{s}, I remember that " + ", and ".join(facts) + "."
    if _has(cmd, "forget what i told", "yaad wali baatein bhool", "facts bhool"):
        _save(FACTS_FILE, [])
        return f"Done {s}, I have forgotten those things."
    return None


# ---------------- clipboard, typing, files ----------------
def clipboard(cmd, s):
    if _has(cmd, "clipboard mein kya", "clipboard me kya", "what is in clipboard", "what's in my clipboard", "read clipboard"):
        text = _ps("Get-Clipboard -Raw")
        return f"{s}, your clipboard says: {text[:300]}" if text else f"{s}, your clipboard is empty."
    m = re.search(r"^copy\s+(.+)", cmd) or re.search(r"(.+?)\s+copy (?:karo|kar do)$", cmd)
    if m:
        _ps("Set-Clipboard -Value '" + m.group(1).replace("'", "''") + "'")
        return f"Copied to clipboard, {s}."
    return None


def type_text(cmd, s):
    if "notepad" in cmd:
        return None
    m = re.search(r"^type\s+(.+)", cmd) or re.search(r"(.+?)\s+type (?:karo|kar do)$", cmd)
    if not m:
        return None
    text = re.sub(r"([+^%~(){}\[\]])", r"{\1}", m.group(1))
    time.sleep(0.5)
    _ps("$w = New-Object -ComObject WScript.Shell; $w.SendKeys('" + text.replace("'", "''") + "')")
    return f"Typed it, {s}."


def find_file(cmd, s):
    m = re.search(r"(?:find|search|dhundo|dhoondo|open)\s+(?:the\s+)?file\s+(?:named\s+)?(.+)", cmd) or \
        re.search(r"(.+?)\s+(?:naam ki|wali)\s+file\s+(?:dhundo|dhoondo|kholo|open karo)", cmd)
    if not m:
        return None
    words = m.group(1).split()
    seen = 0
    for base in [HOME / "Desktop", HOME / "Documents", HOME / "Downloads", HOME / "Pictures", HOME / "Videos"]:
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "AppData")]
            for f in files:
                seen += 1
                if all(w in f.lower() for w in words):
                    path = Path(root) / f
                    if WIN:
                        os.startfile(str(path))
                    return f"Found and opened {f}, {s}."
                if seen > 60000:
                    return f"Sorry {s}, I could not find that file quickly."
    return f"Sorry {s}, I could not find a file named {' '.join(words)}."


# ---------------- WhatsApp aur email ----------------
def whatsapp(cmd, s):
    if "whatsapp" not in cmd or not _has(cmd, "message", "msg", "bhejo", "send"):
        return None
    for name, number in config.CONTACTS.items():
        if name in cmd:
            text = re.split(rf"\b{name}\b", cmd, 1)[1]
            text = re.sub(r"^\s*(?:ko|to|that|ki|ke)\s+", "", text)
            text = re.sub(r"\s*(?:bhejo|send karo|send kar do|send)\s*$", "", text).strip()
            webbrowser.open(f"https://wa.me/{number.lstrip('+')}?text={quote(text)}")
            return f"{s}, I have opened WhatsApp with the message for {name}. Please press send."
    return (f"{s}, I do not have that contact. Add the name and number in config.py under CONTACTS, "
            f"like mom and her number.")


def email(cmd, s):
    if not _has(cmd, "email", "e-mail", "mail likho", "gmail compose"):
        return None
    to = ""
    for name, addr in config.EMAILS.items():
        if name in cmd:
            to = addr
    m = re.search(r"(?:subject|about|ke bare mein|ke baare mein)\s+(.+)", cmd)
    subject = m.group(1) if m else ""
    webbrowser.open(f"https://mail.google.com/mail/?view=cm&fs=1&to={quote(to)}&su={quote(subject)}")
    return f"Opened Gmail compose{' for ' + to if to else ''}, {s}. Write your message and press send."


# ---------------- recycle bin (confirm ke saath) ----------------
def recycle_bin(cmd, s, skills):
    if not _has(cmd, "recycle bin", "recycle", "kachra"):
        return None
    if _has(cmd, "empty", "khali", "saaf", "clear"):
        skills.pending = "recycle"
        return f"{s}, this will permanently delete everything in the recycle bin. Say yes to confirm."
    if WIN:
        subprocess.Popen("start shell:RecycleBinFolder", shell=True)
    return f"Opening recycle bin, {s}."


def help_text(cmd, s):
    if not _has(cmd, "what can you do", "kya kya kar sakte", "help", "tumhari skills", "your skills", "features"):
        return None
    return (f"{s}, I can open and close apps and websites, open folders and File Explorer, write in Notepad, "
            "control volume, music and brightness, take screenshots, tell battery and system status, set timers, "
            "reminders and alarms, calculate, tell jokes, news, weather and time, search Google, YouTube and "
            "Wikipedia, keep a todo list, remember things about you, read and copy clipboard, type for you, "
            "find files, open WhatsApp and Gmail, lock, sleep or shut down the laptop, and learn new topics "
            "from the internet.")


# Order matters: pehle specific, baad mein general
SIMPLE = [help_text, memory, todo, screenshot, battery, system_status, ip_address, windows_control,
          volume, brightness, media, calculator, fun, news, whatsapp, email, clipboard, type_text,
          find_file, website, who_is]
