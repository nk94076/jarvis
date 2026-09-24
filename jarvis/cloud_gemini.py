"""Cloud dimaag: Google Gemini (free tier milta hai, limit ke saath).

Setup: aistudio.google.com par free API key banao, phir JARVIS Data/my_settings.py mein
    GEMINI_API_KEY = "AIza..."
    BRAIN_MODE = "auto"
    CLOUD_PROVIDER = "gemini"
"""
import requests

from . import config


def available():
    return bool(getattr(config, "GEMINI_API_KEY", ""))


def chat(messages):
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in messages if m["role"] in ("user", "assistant") and m.get("content")]
    body = {"contents": contents}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent",
                      params={"key": config.GEMINI_API_KEY}, json=body, timeout=60)
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts).strip()
