"""Sunna aur bolna. Mic/speaker na mile to keyboard mode mein chalta hai."""
import asyncio
import json
import os
import queue
import sys
import tempfile
import time

from . import config
from .internet import internet_hai


def play_mp3(path):
    """MP3 bajao. Windows par built-in player (koi extra library nahi)."""
    if sys.platform == "win32":
        import ctypes
        mci = ctypes.windll.winmm.mciSendStringW
        mci("close jarvis", None, 0, None)
        err = mci(f'open "{path}" type mpegvideo alias jarvis', None, 0, None)
        if err != 0:
            print(f"[voice] MP3 player error {err}, dusri awaaz try kar raha hoon.")
            return False
        mci("play jarvis wait", None, 0, None)
        mci("close jarvis", None, 0, None)
        return True
    try:
        import pygame
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


def windows_speak(text):
    """Aakhri backup: Windows ki apni awaaz (PowerShell), koi library nahi chahiye."""
    if sys.platform != "win32":
        return
    import subprocess
    safe = text.replace("'", "''")
    script = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              "$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'en-IN' } | Select-Object -First 1; "
              "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }; "
              f"$s.Speak('{safe}')")
    subprocess.run(["powershell", "-NoProfile", "-Command", script], creationflags=0x08000000)


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
    def __init__(self, text_mode=False, on_say=None, on_said=None, typed=None):
        self.text_mode = text_mode
        self.typed = typed          # HUD ke type box se aane wale commands
        self.mic_ok = True
        self._threshold = None
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
        print(f"JARVIS: {text}")
        self.on_say(text)
        try:
            if self.text_mode:
                return
            if internet_hai() and self._edge_tts(text):
                return
            if self.engine:
                try:
                    self.engine.say(text)
                    self.engine.runAndWait()
                    return
                except Exception as e:
                    print(f"[voice] pyttsx3 error: {e}")
            windows_speak(text)
        finally:
            self.on_said()

    def _edge_tts(self, text):
        """Online ho to Microsoft ki natural Indian English awaaz (free, koi key nahi)."""
        try:
            import edge_tts
            self._n = getattr(self, "_n", 0) + 1
            path = os.path.join(tempfile.gettempdir(), f"jarvis_say_{self._n % 2}.mp3")
            asyncio.run(edge_tts.Communicate(text, config.TTS_VOICE).save(path))
            return play_mp3(path)
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

    def _record(self, timeout=4, phrase_limit=10):
        """Mic se ek vaakya record karta hai (pyaudio ke bina, sounddevice se).
        Chup rahe to None, warna 16kHz 16-bit mono raw bytes."""
        import numpy as np
        import sounddevice as sd
        rate, block = 16000, 1600                      # 0.1 second ke tukde
        with sd.InputStream(samplerate=rate, channels=1, dtype="int16", blocksize=block) as stream:
            def chunk():
                data, _ = stream.read(block)
                return data.tobytes(), float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))
            if self._threshold is None:                # pehli baar: kamre ka shor naapo
                levels = [chunk()[1] for _ in range(8)]
                self._threshold = max(sum(levels) / len(levels) * 2.5, 250.0)
            frames, started, silent = [], False, 0
            waited = 0.0
            while True:
                data, level = chunk()
                if not started:
                    waited += 0.1
                    frames = (frames + [data])[-3:]    # bolne se thoda pehle ka bhi rakho
                    if level > self._threshold:
                        started = True
                    elif waited > timeout:
                        return None
                    continue
                frames.append(data)
                silent = silent + 1 if level < self._threshold else 0
                if silent >= 6 or len(frames) > phrase_limit * 10:
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
