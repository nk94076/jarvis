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
from jarvis.voice import Voice, is_stop


class NoHUD:
    def post(self, kind, value=None):
        pass


KNOWN_SINGLE = {"time", "date", "weather", "mausam", "location", "hello", "hi", "thanks", "thank",
                "shukriya", "bye", "yes", "no", "haan", "nahi", "lock", "shutdown", "restart"}


def wake_word_ke_baad(text):
    """Wake word mila to uske baad ka command lautata hai ("" agar sirf naam bola). Nahi mila to None."""
    for w in config.WAKE_WORDS:
        if w in text:
            return text.split(w, 1)[1].strip(" ,.!?")
    return None


def jarvis_loop(hud, text_mode, stop, typed=None, interrupt=None):
    interrupt = interrupt or threading.Event()   # "stop" bolne/likhne par set hota hai
    voice = Voice(text_mode=text_mode, typed=typed, stop=interrupt,
                  on_say=lambda t: (hud.post("state", "speak"), hud.post("say", t)),
                  on_said=lambda: hud.post("said"))
    voice.on_level = lambda level: hud.post("level", level)
    brain = Brain()
    knowledge = Knowledge(brain)
    skills = Skills(brain, knowledge)
    skills.timers.notify = lambda msg: (hud.post("log", "⏰ " + msg), voice.bolo(msg))

    def confirm(question):
        """Khatarnaak kaam se pehle: bolo, jawab suno (yes/haan = ok)."""
        voice.paused = True
        try:
            voice.bolo(question + " Say yes or no.")
            for _ in range(3):
                ans = voice.suno(max_wait=10)
                if ans:
                    hud.post("log", f"confirm: {ans}")
                    return bool(set(ans.split()) & {"yes", "haan", "ha", "han", "ok", "okay", "confirm", "kar", "karo"})
            return False
        finally:
            voice.paused = False

    skills.agent.confirm = confirm
    skills.agent.progress = lambda text: hud.post("log", "⚙ " + text)
    skills.agent.stop = interrupt
    skills.orchestrator.progress = lambda text: hud.post("log", "🎯 " + text)

    def hud_data():
        """INTELLIGENCE / ANALYTICS / SETTINGS tabs ke liye."""
        from jarvis import selfimprove, security
        from jarvis.agent import TOOLS
        d, rate = selfimprove.summary()
        st = skills.learner.state
        goals = skills.orchestrator._load()
        return {"brain_mode": config.BRAIN_MODE, "safe_mode": security.safe_mode(),
                "learning": ", ".join(st.get("queue", [])[:3]) or "nothing",
                "subjects": ", ".join(skills.learner.learnt_subjects())[:60] or "-",
                "skills": str(len(skills.plugins.list())), "tools": str(len(TOOLS)),
                "goal": (f"{goals[-1]['goal'][:40]} ({goals[-1]['status']})" if goals else "-"),
                "total": d["total"], "rate": f"{rate:.0f}%", "failed": d["failed"], "gaps": len(d["gaps"]),
                "by_day": d["by_day"]}

    if hasattr(hud, "provider"):
        from jarvis import security, selfimprove as _si
        hud.provider = hud_data

        def set_mode(m):
            config.BRAIN_MODE = m
            hud.post("info", {"brain": brain_label()})
        hud.actions.update({
            "safe_mode": lambda: security.set_safe_mode(not security.safe_mode()),
            "brain_local": lambda: set_mode("local"), "brain_auto": lambda: set_mode("auto"),
            "brain_cloud": lambda: set_mode("cloud"), "learning_stop": skills.learner.stop,
            "dashboard": lambda: _si.dashboard(skills.learner, skills.knowledge, skills.plugins)})
    from jarvis.scheduler import Scheduler, notify
    skills.scheduler = Scheduler(skills.handle, lambda msg: (hud.post("log", "⏰ " + msg[:50]), voice.bolo(msg)))
    if getattr(config, "PHONE_APP", True):
        from jarvis import remote
        _, phone = remote.start(skills.handle, on_command=lambda t: hud.post("log", "📱 " + t))
        print(f"[phone] Phone se JARVIS: {phone}")
        hud.post("log", "📱 " + phone)
    skills.plugins.confirm = confirm
    skills.plugins.progress = lambda text: hud.post("log", "🛠 " + text)
    skills.learner.notify = lambda msg: (hud.post("log", "📚 " + msg[:60]),
                                         hud.post("info", {"learnt": knowledge_info()}), voice.bolo(msg))
    s = config.USER_NAME

    def brain_label():
        from jarvis.llm_client import cloud_provider
        prov = cloud_provider()
        return (config.CLAUDE_MODEL if prov.__name__.endswith("claude") else config.GEMINI_MODEL) if prov \
            else config.OLLAMA_MODEL

    def knowledge_info():
        from jarvis.skills_extra import FACTS_FILE, _load
        return f"{len(knowledge.items)} topics, {len(_load(FACTS_FILE, []))} facts"

    online = internet.internet_hai()
    hud.post("info", {"mode": "ONLINE" if online else "OFFLINE", "brain": brain_label(),
                      "voice": "MIC + KEYBOARD" if voice.mic_ok and not text_mode else "KEYBOARD",
                      "learnt": knowledge_info()})
    if online:
        try:
            hud.post("weather", internet.weather_full())
        except Exception:
            pass
    voice.bolo(f"Hello {s}, JARVIS is online. Say Hey Jarvis to wake me up."
               if online else f"Hello {s}, JARVIS is ready in offline mode. Say Hey Jarvis to wake me up.")
    if skills.learner.resume():
        voice.bolo(f"{s}, I am continuing my pending learning: {', '.join(skills.learner.state['queue'])}.")
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
                print('   (standby: pehle "Hey Jarvis" bolo, phir command)')
                hud.post("log", "Standby: say Hey Jarvis first")
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
        if is_stop(cmd):
            interrupt.clear()
            continue                            # kuch chal hi nahi raha, bas chup raho

        if len(cmd.split()) == 1 and cmd not in KNOWN_SINGLE and not is_task(cmd) and not skills.pending:
            voice.bolo(f"Sorry {s}, I did not catch that. Please say it again.")
            continue                            # "jar", "internet" jaisa adhoora sunaai diya

        hud.post("log", cmd)
        interrupt.clear()
        done = threading.Event()
        threading.Thread(target=voice.listen_for_stop, args=(done,), daemon=True).start()

        task = is_task(cmd)
        if task:
            voice.bolo(f"Starting the task, {s}.")
        hud.post("state", "work")

        result = {}

        def kaam():
            try:
                result["jawab"] = skills.handle(cmd)
            except Exception as e:
                result["jawab"] = f"Sorry {s}, something went wrong: {e}"

        worker = threading.Thread(target=kaam, daemon=True)
        worker.start()
        while worker.is_alive() and not interrupt.is_set():
            worker.join(0.1)

        if not interrupt.is_set():
            jawab = result.get("jawab", "")
            if jawab is None:
                done.set()
                voice.bolo(f"Goodbye {s}. Take care.")
                hud.post("quit")
                return
            voice.bolo(jawab)
            if task:
                voice.bolo(f"Task completed, {s}.")
        done.set()
        if interrupt.is_set():
            interrupt.clear()
            hud.post("said")
            voice.bolo(f"Okay {s}, stopped.")
        hud.post("info", {"learnt": knowledge_info(),
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
    interrupt = threading.Event()

    def on_command(text):
        if is_stop(text):
            interrupt.set()                 # type box mein "stop" = turant ruko
            return
        # type kiye command ke liye "Jarvis" bolna zaroori nahi
        if wake_word_ke_baad(text.lower()) is None:
            text = "jarvis " + text
        typed.put(text)

    hud = HUD(on_close=stop.set, on_command=on_command, on_stop=interrupt.set)
    threading.Thread(target=jarvis_loop, args=(hud, text_mode, stop, typed, interrupt), daemon=True).start()
    hud.run()


if __name__ == "__main__":
    main()
