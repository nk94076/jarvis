"""Computer-use Agent: screen dekh kar khud agla kadam tay karta hai jab tak kaam poora na ho.
"notepad kholo, usme hello likho aur save karo" jaise kaam jo kai clicks/keys maangte hain.

Har round: screen ka text (Windows OCR) -> AI ek action chunta hai -> JARVIS karta hai -> dobara dekhta hai.
Actions: click_text, type, key, scroll, open (JARVIS command), wait, done. 12 rounds tak.
'stop' bolne par ruk jata hai (agent.stop)."""
import json
import re
import time

from . import config, pc

MAX_STEPS = 12


def _screen_summary():
    lines = pc.ocr_screen()
    text = "\n".join(" ".join(w[0] for w in line) for line in lines if line)
    return text[:2500] or "(no text visible)"


def run(task, llm, stop=None):
    from .agent import AGENT
    history = []
    for step in range(1, MAX_STEPS + 1):
        if stop is not None and stop.is_set():
            return "Stopped."
        try:
            screen = _screen_summary()
        except Exception as e:
            return f"ERROR: cannot read the screen ({e}). Computer use works on Windows only."
        raw = llm(
            f"You control a Windows PC to finish this task: {task}\n"
            f"Text currently visible on screen (OCR):\n{screen}\n\nActions done so far:\n"
            + ("\n".join(history[-8:]) or "none")
            + '\n\nChoose the NEXT single action. Reply ONLY JSON like {"action": "click_text", "value": "Save"}.\n'
              "Actions: click_text (value = visible text to click), type (value = text), key (value = e.g. enter, "
              "ctrl+s, alt+tab, win), scroll (value = up/down), open (value = a JARVIS command like 'open notepad'), "
              'wait, done (value = short summary). Use "done" as soon as the task is finished.')
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            act = json.loads(m.group()) if m else {}
        except ValueError:
            act = {}
        a, v = str(act.get("action", "")).lower(), str(act.get("value", ""))
        if a == "done":
            return f"Done in {step - 1} steps: {v or 'task finished'}"
        try:
            if a == "click_text":
                out = pc.click_text(v)
            elif a == "type":
                out = pc.type_text(v)
            elif a == "key":
                out = pc.hotkey(v)
            elif a == "scroll":
                out = pc.scroll("up" if "up" in v else "down", 5)
            elif a == "open" and AGENT and AGENT.skills:
                out = AGENT.skills.handle(v)
            elif a == "wait":
                out = "waited"
            else:
                out = f"unknown action {a!r}"
        except Exception as e:
            out = f"error {e}"
        history.append(f"{step}. {a} {v!r} -> {str(out)[:100]}")
        time.sleep(1.2)                              # screen ko update hone do
    return f"I did {MAX_STEPS} steps but could not confirm the task finished. Steps: " + " | ".join(history[-4:])
