"""Vision Agent: camera, screen, photo aur CCTV ko 'dekh' kar batana. Local vision model (Ollama) se, free.
Setup: `ollama pull qwen2.5vl:7b` (16 GB GPU ke liye) - upgrade_brain.bat ye bhi karta hai.
CCTV: my_settings.py mein CAMERAS = {"gate": "rtsp://user:pass@192.168.1.20:554/stream1"}"""
import base64
import os
import tempfile
from pathlib import Path

from . import config


def _ask(image_path, question):
    from .llm_client import pick
    import ollama
    with open(image_path, "rb") as f:
        img = base64.b64encode(f.read()).decode()
    r = ollama.chat(model=pick(config.VISION_MODEL), keep_alive=config.KEEP_ALIVE, messages=[{
        "role": "user", "images": [img],
        "content": f"{question}\nAnswer in 1-3 short spoken sentences in simple Indian English, no markdown."}])
    return r["message"]["content"].strip()


def _grab_camera(source=0):
    import cv2
    cap = cv2.VideoCapture(source)
    for _ in range(8):                    # camera ko roshni adjust karne do
        ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError("camera se photo nahi mili")
    path = os.path.join(tempfile.gettempdir(), "jarvis_camera.jpg")
    cv2.imwrite(path, frame)
    return path


def look_camera(question="What do you see?"):
    try:
        path = _grab_camera(config.WEBCAM_INDEX)
    except Exception as e:
        return f"Sorry {config.USER_NAME}, I could not use the camera. ({e}) Is opencv-python installed and the camera free?"
    return _ask(path, question)


def look_screen(question="Describe what is on the screen."):
    from PIL import ImageGrab
    path = os.path.join(tempfile.gettempdir(), "jarvis_screen_v.png")
    img = ImageGrab.grab()
    img.thumbnail((1600, 1600))
    img.save(path)
    return _ask(path, question)


def look_image(name, question="Describe this image."):
    from .agent import HOME
    p = Path(name)
    if not p.exists():
        for base in [HOME / "Pictures", HOME / "Downloads", HOME / "Desktop", HOME / "Documents"]:
            hits = [f for f in base.rglob("*") if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
                    and all(w in f.stem.lower() for w in name.lower().split())] if base.exists() else []
            if hits:
                p = max(hits, key=lambda f: f.stat().st_mtime)
                break
    if not p.exists():
        return f"Sorry {config.USER_NAME}, I could not find an image named {name}."
    return f"{p.name}: " + _ask(str(p), question)


def cctv(name, question="Is anyone there? Describe what you see."):
    cams = getattr(config, "CAMERAS", {}) or {}
    if not cams:
        return (f"{config.USER_NAME}, no CCTV cameras are set up. Add CAMERAS with your camera's RTSP link in "
                f"my_settings.py.")
    key = next((k for k in cams if k in name), next(iter(cams)))
    try:
        path = _grab_camera(cams[key])
    except Exception as e:
        return f"Sorry {config.USER_NAME}, I could not connect to the {key} camera. ({e})"
    return f"{key} camera: " + _ask(path, question)
