"""JARVIS chalao:  python main.py         (awaaz se)
                python main.py --text  (keyboard se type karke)"""
import sys

from jarvis import config
from jarvis.brain import Brain
from jarvis.internet import internet_hai
from jarvis.knowledge import Knowledge
from jarvis.skills import Skills
from jarvis.voice import Voice


def main():
    voice = Voice(text_mode="--text" in sys.argv)
    brain = Brain()
    skills = Skills(brain, Knowledge(brain))
    mode = "online" if internet_hai() else "offline"
    voice.bolo(f"Namaste {config.USER_NAME}, JARVIS {mode} mode mein ready hai.")
    while True:
        cmd = voice.suno()
        if not cmd:
            continue
        try:
            jawab = skills.handle(cmd)
        except Exception as e:
            jawab = f"{config.USER_NAME}, ek gadbad hui: {e}"
        if jawab is None:
            voice.bolo(f"Alvida {config.USER_NAME}, apna khayal rakhiye.")
            break
        voice.bolo(jawab)


if __name__ == "__main__":
    main()
