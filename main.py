"""JARVIS chalao:
    python main.py           Iron Man HUD screen + awaaz (default)
    python main.py --cli     bina screen ke, sirf awaaz
    python main.py --text    keyboard se type karke (mic ke bina test karne ke liye)

Kaise kaam karta hai: JARVIS standby mein sunta rehta hai. "Hey Jarvis" bolo to wo jaag jata hai,
phir naam liye bina seedha baat karo. Kaam (open/play/learn/search) par "Starting the task" aur
"Task completed" bolta hai. SLEEP_AFTER second chup rahoge ya "so jao" bologe to standby."""
import queue
import sys
import threading
import time

from jarvis import config, internet
from jarvis.brain import Brain
from jarvis.knowledge import Knowledge
from jarvis.skills import Skills, is_task
from jarvis.voice import Voice


class NoHUD:
    def post(self, kind, value=None):
        pass


def wake_word_ke_baad(text):
    """Wake word mila to uske baad ka command lautata hai ("" agar sirf naam bola). Nahi mila to None."""
    for w in config.WAKE_WORDS:
        if w in text:
            return text.split(w, 1)[1].strip(" ,.!?")
    return None


def jarvis_loop(hud, text_mode, stop, typed=None):
    voice = Voice(text_mode=text_mode, typed=typed,
                  on_say=lambda t: (hud.post("state", "speak"), hud.post("say", t)),
                  on_said=lambda: hud.post("said"))
    brain = Brain()
    knowledge = Knowledge(brain)
    skills = Skills(brain, knowledge)
    s = config.USER_NAME

    online = internet.internet_hai()
    hud.post("info", {"mode": "ONLINE" if online else "OFFLINE", "brain": config.OLLAMA_MODEL,
                      "voice": "MIC + KEYBOARD" if voice.mic_ok and not text_mode else "KEYBOARD",
                      "learnt": str(len(knowledge.items))})
    if online:
        try:
            hud.post("weather", internet.mausam_hud())
        except Exception:
            pass
    voice.bolo(f"Hello {s}, JARVIS is online. Say Hey Jarvis to wake me up."
               if online else f"Hello {s}, JARVIS is ready in offline mode. Say Hey Jarvis to wake me up.")
    hud.post("state", "sleep")

    active = False          # "Hey Jarvis" ke baad True; chup rehne par wapas False
    last_talk = 0.0

    def so_jao(msg=None):
        nonlocal active
        active = False
        if msg:
            voice.bolo(msg)
        hud.post("state", "sleep")

    while not stop.is_set():
        text = voice.suno(max_wait=5)
        if not text:
            if active and time.time() - last_talk > config.SLEEP_AFTER:
                so_jao(f"Going to standby, {s}. Say Hey Jarvis whenever you need me.")
            continue

        cmd = wake_word_ke_baad(text)
        if not active:
            if cmd is None:
                continue                        # standby: sirf "Hey Jarvis" par jaago
            active = True
            last_talk = time.time()
            hud.post("state", "listen")
            if not cmd:
                voice.bolo(f"Yes {s}? I am listening.")
                hud.post("state", "listen")
                continue
        elif cmd is None:
            cmd = text                          # active hai, to naam lene ki zaroorat nahi
        elif not cmd:
            voice.bolo(f"Yes {s}?")
            hud.post("state", "listen")
            last_talk = time.time()
            continue
        last_talk = time.time()

        if any(w in cmd for w in config.SLEEP_WORDS):
            so_jao(f"Okay {s}, going to standby. Say Hey Jarvis to wake me up.")
            continue

        hud.post("log", cmd)
        task = is_task(cmd)
        if task:
            voice.bolo(f"Starting the task, {s}.")
        hud.post("state", "work")
        try:
            jawab = skills.handle(cmd)
        except Exception as e:
            jawab = f"Sorry {s}, something went wrong: {e}"

        if jawab is None:
            voice.bolo(f"Goodbye {s}. Take care.")
            hud.post("quit")
            return
        voice.bolo(jawab)
        if task:
            voice.bolo(f"Task completed, {s}.")
        hud.post("info", {"learnt": str(len(knowledge.items)),
                          "mode": "ONLINE" if internet.internet_hai() else "OFFLINE"})
        hud.post("state", "listen")
        last_talk = time.time()


def main():
    print(f"J.A.R.V.I.S. v{config.VERSION}")
    text_mode = "--text" in sys.argv
    stop = threading.Event()
    if "--cli" in sys.argv or text_mode and "--gui" not in sys.argv:
        jarvis_loop(NoHUD(), text_mode, stop)
        return
    from jarvis.hud import HUD
    typed = queue.Queue()

    def on_command(text):
        # type kiye command ke liye "Jarvis" bolna zaroori nahi
        if wake_word_ke_baad(text.lower()) is None:
            text = "jarvis " + text
        typed.put(text)

    hud = HUD(on_close=stop.set, on_command=on_command)
    threading.Thread(target=jarvis_loop, args=(hud, text_mode, stop, typed), daemon=True).start()
    hud.run()


if __name__ == "__main__":
    main()
