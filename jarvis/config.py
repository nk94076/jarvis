"""JARVIS ki settings. Yahan badlav karke JARVIS ko customize karo."""
from pathlib import Path

VERSION = "3.1"

USER_NAME = "Sir"
OLLAMA_MODEL = "qwen2.5:3b"          # 16GB RAM ho to "llama3.1:8b"
VOSK_MODEL_DIR = "model"             # offline speech model ka folder
DATA_DIR = Path("data")              # memory aur knowledge yahan save hoti hai
MEMORY_FILE = DATA_DIR / "memory.json"
KNOWLEDGE_FILE = DATA_DIR / "knowledge.json"
MAX_HISTORY = 40                     # kitni purani baatein yaad rakhe
WAKE_WORDS = ["jarvis", "jarvish", "jervis", "javis", "jarvees"]
TTS_VOICE = "en-IN-PrabhatNeural"    # online awaaz; ladki ki awaaz: "en-IN-NeerjaNeural"

SYSTEM_PROMPT = f"""Tum JARVIS ho, {USER_NAME} ke personal AI assistant, bilkul Iron Man ke JARVIS jaise.
User ko '{USER_NAME}' bolo. Reply in short (1-3 sentences), natural Indian English, like a polite Indian assistant.
Markdown, emoji ya list mat use karo, kyunki jawab bol kar sunaya jayega."""
