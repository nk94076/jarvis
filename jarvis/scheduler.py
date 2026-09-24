"""Scheduled Automation + Notifications.
"har roz subah 9 baje news sunao", "every weekday at 6 pm battery batao", "schedules dikhao", "schedule 2 hatao".
Tay samay par command chalti hai, jawab bolta hai aur Windows notification dikhata hai."""
import json
import re
import subprocess
import sys
import threading
import time
from datetime import datetime

from . import config

FILE = config.DATA_DIR / "schedules.json"
DAYS = {"daily": range(7), "weekdays": range(5), "weekends": (5, 6)}


def notify(title, text):
    """Windows notification (tray balloon). Koi library nahi."""
    if sys.platform != "win32":
        return
    t, m = title.replace("'", "''"), text.replace("'", "''")[:240]
    ps = ("Add-Type -AssemblyName System.Windows.Forms; $n = New-Object System.Windows.Forms.NotifyIcon; "
          "$n.Icon = [System.Drawing.SystemIcons]::Information; $n.Visible = $true; "
          f"$n.ShowBalloonTip(8000, '{t}', '{m}', 'Info'); Start-Sleep 9; $n.Dispose()")
    subprocess.Popen(["powershell", "-NoProfile", "-Command", ps], creationflags=0x08000000)


def parse(cmd):
    """-> (time 'HH:MM', days, command) ya None"""
    if not re.search(r"\b(har roz|roz|daily|every day|everyday|har din|every weekday|weekdays|har subah|har shaam|"
                     r"every morning|every evening|weekend)\b", cmd):
        return None
    m = re.search(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|baje)?", cmd)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap == "pm" and h < 12 or (re.search(r"shaam|evening|raat|night", cmd) and h < 12):
        h += 12
    days = "weekdays" if re.search(r"weekday", cmd) else "weekends" if "weekend" in cmd else "daily"
    task = cmd
    for w in [r"har roz", r"\broz\b", "daily", "every day", "everyday", "har din", "every weekday", "weekdays",
              "weekends", "weekend", "har subah", "har shaam", "every morning", "every evening", r"\bsubah\b",
              r"\bshaam\b", r"\braat\b", r"\bat\b", r"\bko\b", r"\bpe\b", r"\bpar\b", m.group(0)]:
        task = re.sub(w, " ", task)
    task = " ".join(task.split())
    return (f"{h % 24:02d}:{mi:02d}", days, task) if task else None


class Scheduler:
    def __init__(self, run_command, say):
        self.run_command = run_command        # cmd -> reply
        self.say = say
        self.items = self._load()
        threading.Thread(target=self._loop, daemon=True).start()

    def _load(self):
        try:
            return json.loads(FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self):
        FILE.write_text(json.dumps(self.items, ensure_ascii=False, indent=1), encoding="utf-8")

    def add(self, cmd):
        p = parse(cmd)
        if not p:
            return None
        at, days, task = p
        self.items.append({"time": at, "days": days, "command": task, "last": ""})
        self._save()
        return f"Okay {config.USER_NAME}, every {'day' if days == 'daily' else days[:-1]} at {at} I will: {task}."

    def describe(self):
        if not self.items:
            return f"{config.USER_NAME}, you have no scheduled tasks."
        return f"{config.USER_NAME}, your schedules: " + "; ".join(
            f"{i + 1}. {x['time']} {x['days']}: {x['command']}" for i, x in enumerate(self.items)) + "."

    def remove(self, n):
        if 1 <= n <= len(self.items):
            x = self.items.pop(n - 1)
            self._save()
            return f"Removed the schedule: {x['command']}, {config.USER_NAME}."
        return f"{config.USER_NAME}, there is no schedule number {n}."

    def _loop(self):
        while True:
            now = datetime.now()
            key = now.strftime("%Y-%m-%d")
            for x in list(self.items):
                if x["time"] == now.strftime("%H:%M") and x["last"] != key and now.weekday() in DAYS[x["days"]]:
                    x["last"] = key
                    self._save()
                    try:
                        reply = self.run_command(x["command"]) or "done"
                    except Exception as e:
                        reply = f"The scheduled task '{x['command']}' failed: {e}"
                    notify("JARVIS", reply)
                    self.say(reply)
            time.sleep(20)
