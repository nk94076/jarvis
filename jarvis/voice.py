"""Sunna aur bolna. Mic/speaker na mile to keyboard mode mein chalta hai."""
import asyncio
import json
import os
import queue
import re
import threading
import sys
import tempfile
import time

from . import config
from .internet import internet_hai


def play_mp3(path, stop=None):
    """MP3 bajao. Windows par built-in player (koi extra library nahi). stop set ho to beech mein ruk jao."""
    if sys.platform == "win32":
        import ctypes
        mci = ctypes.windll.winmm.mciSendStringW
        mci("close jarvis", None, 0, None)
        err = mci(f'open "{path}" type mpegvideo alias jarvis', None, 0, None)
        if err != 0:
            print(f"[voice] MP3 player error {err}, dusri awaaz try kar raha hoon.")
            return False
        mci("play jarvis", None, 0, None)
        buf = ctypes.create_unicode_buffer(32)
        while True:
            time.sleep(0.05)
            mci("status jarvis mode", buf, 32, None)
            if buf.value != "playing":
                break
            if stop is not None and stop.is_set():
                mci("stop jarvis", None, 0, None)
                break
        mci("close jarvis", None, 0, None)
        return True
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            if stop is not None and stop.is_set():
                pygame.mixer.music.stop()
                break
            pygame.time.wait(50)
        pygame.mixer.music.unload()
        return True
    except Exception:
        return False


def windows_speak(text, stop=None):
    """Aakhri backup: Windows ki apni awaaz (PowerShell), koi library nahi chahiye."""
    if sys.platform != "win32":
        return
    import subprocess
    safe = text.replace("'", "''")
    script = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              "$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'en-IN' } | Select-Object -First 1; "
              "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }; "
              f"$s.Speak('{safe}')")
    proc = subprocess.Popen(["powershell", "-NoProfile", "-Command", script], creationflags=0x08000000)
    while proc.poll() is None:
        if stop is not None and stop.is_set():
            proc.kill()
            break
        time.sleep(0.05)


def find_vosk_model():
    """'model' folder, ya uske andar ka folder (unzip karne par aksar ek level andar chala jaata hai)."""
    base = config.VOSK_MODEL_DIR
    if not os.path.isdir(base):
        raise FileNotFoundError(f"'{base}' folder nahi mila (optional hai)")
    for root, dirs, files in os.walk(base):
        if "am" in dirs or "conf" in dirs:
            return root
    raise FileNotFoundError(f"'{base}' folder mein Vosk model nahi mila")


class Voice:
    def __init__(self, text_mode=False, on_say=None, on_said=None, typed=None, stop=None):
        self.text_mode = text_mode
        self.stop = stop or threading.Event()   # set ho to bolna/kaam turant band
        self.typed = typed          # HUD ke type box se aane wale commands
        self.mic_ok = True
        self._noise = None
        self.on_level = lambda level: None
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
            from vosk import KaldiRecognizer, Model, SetLogLevel
            SetLogLevel(-1)
            self.vosk = KaldiRecognizer(Model(find_vosk_model()), 16000)
        except Exception as e:
            print(f"[voice] Offline sunna band ({e}). Internet par Google speech chalegi.")

    def bolo(self, text):
        if self.stop.is_set():
            return
        print(f"JARVIS: {text}")
        self.on_say(text)
        try:
            if self.text_mode:
                return
            if internet_hai() and self._edge_tts(text):
                return
            if self.engine:
                try:
                    # vaakya-vaakya bolo taaki "stop" par beech mein ruk sake
                    for part in re.split(r"(?<=[.!?])\s+", text):
                        if self.stop.is_set():
                            break
                        self.engine.say(part)
                        self.engine.runAndWait()
                    return
                except Exception as e:
                    print(f"[voice] pyttsx3 error: {e}")
            windows_speak(text, self.stop)
        finally:
            self.on_said()

    def _edge_tts(self, text):
        """Online ho to Microsoft ki natural Indian English awaaz (free, koi key nahi)."""
        try:
            import edge_tts
            self._n = getattr(self, "_n", 0) + 1
            path = os.path.join(tempfile.gettempdir(), f"jarvis_say_{self._n % 2}.mp3")
            asyncio.run(edge_tts.Communicate(text, config.TTS_VOICE).save(path))
            return play_mp3(path, self.stop)
        except Exception as e:
            if not getattr(self, "_edge_warned", False):
                print(f"[voice] Online awaaz nahi chali ({e}). Offline awaaz use hogi.")
                self._edge_warned = True
            return False

    def suno(self, max_wait=None):
        """Ek command lautata hai: mic se, ya HUD ke type box se (jo pehle aaye).
        max_wait second tak kuch na mile to "" lautata hai."""
        deadline = time.time() + max_wait if max_wait else None
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
                online = internet_hai()
                if online or self.vosk:
                    text = self._listen(online)
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
            if deadline and time.time() > deadline:
                return ""

    def _record(self, timeout=4, phrase_limit=12, learn=True):
        """Mic se ek vaakya record karta hai (pyaudio ke bina, sounddevice se).
        Kamre ka shor lagatar naapta rehta hai, isliye normal awaaz mein bolna kaafi hai.
        Chup rahe to None, warna 16kHz 16-bit mono raw bytes."""
        import numpy as np
        import sounddevice as sd
        rate, block = 16000, 1600                      # 0.1 second ke tukde
        with sd.InputStream(samplerate=rate, channels=1, dtype="int16", blocksize=block) as stream:
            def chunk():
                data, _ = stream.read(block)
                level = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))
                self.on_level(level)
                return data.tobytes(), level

            if self._noise is None:                    # pehli baar: 0.5s kamre ka shor
                self._noise = max(float(np.median([chunk()[1] for _ in range(5)])), 30.0)
                print(f"[mic] Shor ka level {self._noise:.0f}. Normal awaaz mein bolo.")

            def start_level():
                return min(max(self._noise * config.MIC_SENSITIVITY, self._noise + 100, 120), 2500)

            frames, started, silent, waited = [], False, 0, 0.0
            while True:
                data, level = chunk()
                if not started:
                    waited += 0.1
                    frames = (frames + [data])[-5:]    # bolne se 0.5s pehle ka bhi rakho
                    if level > start_level():
                        started = True
                        continue
                    if learn:                          # chuppi mein shor ka level update karo
                        self._noise = 0.95 * self._noise + 0.05 * max(level, 30.0)
                    if waited > timeout:
                        return None
                    continue
                frames.append(data)
                end_level = max(self._noise * 1.3, self._noise + 50)
                silent = silent + 1 if level < end_level else 0
                if silent >= config.MIC_PAUSE * 10 or len(frames) > phrase_limit * 10:
                    return b"".join(frames)

    def _listen(self, online):
        try:
            raw = self._record()
        except Exception as e:
            print(f"[voice] Mic nahi mila ({e}). HUD ke box mein type karo.")
            self.mic_ok = False
            return None
        if not raw:
            return None
        text = ""
        if online:
            try:
                import speech_recognition as sr
                audio = sr.AudioData(raw, 16000, 2)
                text = sr.Recognizer().recognize_google(audio, language="en-IN")
            except Exception:
                text = ""
        if not text and self.vosk:
            self.vosk.AcceptWaveform(raw)
            text = json.loads(self.vosk.FinalResult()).get("text", "")
        if text:
            print(f"Aap: {text}")
            return text.lower()
        return None

    def listen_for_stop(self, done):
        """Kaam ya bolne ke dauraan chupke se suno; "stop/ruko/bas" suna to self.stop set karo."""
        if self.text_mode or not self.mic_ok:
            return
        while not done.is_set() and not self.stop.is_set():
            try:
                raw = self._record(timeout=1, phrase_limit=3, learn=False)
            except Exception:
                return
            if not raw or done.is_set():
                continue
            text = ""
            try:
                if internet_hai():
                    import speech_recognition as sr
                    text = sr.Recognizer().recognize_google(sr.AudioData(raw, 16000, 2), language="en-IN")
                elif self.vosk:
                    self.vosk.AcceptWaveform(raw)
                    text = json.loads(self.vosk.FinalResult()).get("text", "")
            except Exception:
                text = ""
            if is_stop(text):
                print(f"Aap: {text}  [STOP]")
                self.stop.set()


def is_stop(text):
    """Sirf chhota "stop/ruko/bas" jaisa vaakya (lambe vaakya jaise "notepad band karo" stop nahi hain)."""
    words = re.findall(r"[a-z]+", text.lower())
    if not words or len(words) > 3:
        return False
    return bool(set(words) & set(config.STOP_WORDS)) or " ".join(words) in config.STOP_PHRASES
