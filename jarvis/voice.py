"""Sunna aur bolna. Mic/speaker na mile to keyboard mode mein chalta hai."""
import asyncio
import json
import os
import queue
import tempfile
import time

from . import config
from .internet import internet_hai


class Voice:
    def __init__(self, text_mode=False, on_say=None, on_said=None, typed=None):
        self.text_mode = text_mode
        self.typed = typed          # HUD ke type box se aane wale commands
        self.mic_ok = True
        self._rec = None
        self._calibrated = False
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
            print(f"[voice] Awaaz band: {e}. Fix: setup.bat dobara chalao (pyttsx3 install hoga).")
        try:
            from vosk import KaldiRecognizer, Model
            self.vosk = KaldiRecognizer(Model(config.VOSK_MODEL_DIR), 16000)
        except Exception as e:
            print(f"[voice] Offline sunna band ({e}). Internet par Google speech chalegi.")

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
        """Ek command lautata hai: mic se, ya HUD ke type box se (jo pehle aaye)."""
        if self.text_mode and self.typed is None:
            try:
                return input("Aap: ").strip().lower()
            except EOFError:
                return "bye"
        while True:
            if self.typed is not None and not self.typed.empty():
                return self.typed.get().strip().lower()
            text = None
            if not self.text_mode and self.mic_ok:
                if internet_hai():
                    text = self._google()
                elif self.vosk:
                    text = self._vosk(timeout=4)
                else:
                    time.sleep(0.3)
            elif self.typed is not None:
                try:
                    return self.typed.get(timeout=0.5).strip().lower()
                except queue.Empty:
                    pass
            else:
                return input("Aap (type karo): ").strip().lower()
            if text:
                return text

    def _google(self):
        try:
            import speech_recognition as sr
        except ImportError:
            print("[voice] SpeechRecognition install nahi hai. setup.bat dobara chalao.")
            self.mic_ok = False
            return None
        try:
            if self._rec is None:
                self._rec = sr.Recognizer()
                self._rec.dynamic_energy_threshold = True
            with sr.Microphone() as mic:
                if not self._calibrated:
                    self._rec.adjust_for_ambient_noise(mic, duration=0.8)
                    self._calibrated = True
                audio = self._rec.listen(mic, timeout=4, phrase_time_limit=10)
            text = self._rec.recognize_google(audio, language="en-IN").lower()
            print(f"Aap: {text}")
            return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except (OSError, AttributeError) as e:
            print(f"[voice] Mic nahi mila ({e}). HUD ke box mein type karo.")
            self.mic_ok = False
            return None
        except Exception:
            return None

    def _vosk(self, timeout=4):
        import sounddevice as sd
        q = queue.Queue()
        deadline = time.time() + timeout
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16",
                               channels=1, callback=lambda d, f, t, s: q.put(bytes(d))):
            # chup ho to timeout par wapas; bol rahe ho to vaakya poora hone do
            while time.time() < deadline or json.loads(self.vosk.PartialResult()).get("partial"):
                try:
                    data = q.get(timeout=0.5)
                except queue.Empty:
                    continue
                if self.vosk.AcceptWaveform(data):
                    text = json.loads(self.vosk.Result()).get("text", "")
                    if text:
                        print(f"Aap: {text}")
                        return text.lower()
                if time.time() > deadline + 10:
                    break
        return None
