"""Sunna aur bolna. Mic/speaker na mile to keyboard mode mein chalta hai."""
import asyncio
import json
import os
import queue
import tempfile

from . import config
from .internet import internet_hai


class Voice:
    def __init__(self, text_mode=False, on_say=None, on_said=None):
        self.text_mode = text_mode
        self.on_say = on_say or (lambda text: None)
        self.on_said = on_said or (lambda: None)
        self.engine = None
        self.vosk = None
        if text_mode:
            return
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            # Indian English awaaz dhoondo (Windows: Heera/Ravi, Linux: en-in)
            for v in self.engine.getProperty("voices"):
                info = f"{v.id} {v.name} {getattr(v, 'languages', '')}".lower()
                if any(k in info for k in ("en-in", "en_in", "india", "heera", "ravi")):
                    self.engine.setProperty("voice", v.id)
                    break
            self.engine.setProperty("rate", 175)
        except Exception as e:
            print(f"[voice] Speaker nahi mila ({e}), sirf text dikhega.")
        try:
            from vosk import KaldiRecognizer, Model
            self.vosk = KaldiRecognizer(Model(config.VOSK_MODEL_DIR), 16000)
        except Exception as e:
            print(f"[voice] Vosk model nahi mila ({e}). Online Google speech use hogi.")

    def bolo(self, text):
        print(f"JARVIS: {text}")
        self.on_say(text)
        try:
            if self.text_mode:
                return
            if internet_hai() and self._edge_tts(text):
                return
            if self.engine:
                self.engine.say(text)
                self.engine.runAndWait()
        finally:
            self.on_said()

    def _edge_tts(self, text):
        """Online ho to Microsoft ki natural Indian English awaaz (free, koi key nahi)."""
        try:
            import edge_tts
            import pygame
            path = os.path.join(tempfile.gettempdir(), "jarvis_say.mp3")
            asyncio.run(edge_tts.Communicate(text, config.TTS_VOICE).save(path))
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(50)
            pygame.mixer.music.unload()
            return True
        except Exception:
            return False

    def suno(self):
        if self.text_mode:
            try:
                return input("Aap: ").strip().lower()
            except EOFError:
                return "bye"
        if internet_hai():
            text = self._google()
            if text is not None:
                return text
        if self.vosk:
            return self._vosk()
        return input("Aap (type karo): ").strip().lower()

    def _google(self):
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as mic:
                print("Sun raha hoon (online)...")
                r.adjust_for_ambient_noise(mic, duration=0.5)
                audio = r.listen(mic, phrase_time_limit=10)
            text = r.recognize_google(audio, language="en-IN").lower()
            print(f"Aap: {text}")
            return text
        except Exception:
            return None

    def _vosk(self):
        import sounddevice as sd
        q = queue.Queue()
        print("Sun raha hoon (offline)...")
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                               channels=1, callback=lambda d, f, t, s: q.put(bytes(d))):
            while True:
                if self.vosk.AcceptWaveform(q.get()):
                    text = json.loads(self.vosk.Result()).get("text", "")
                    if text:
                        print(f"Aap: {text}")
                        return text.lower()
