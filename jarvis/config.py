"""JARVIS ki settings. Yahan badlav karke JARVIS ko customize karo."""
from pathlib import Path

USER_NAME = "Sir"
OLLAMA_MODEL = "qwen2.5:3b"          # 16GB RAM ho to "llama3.1:8b"
VOSK_MODEL_DIR = "model"             # offline speech model ka folder
DATA_DIR = Path("data")              # memory aur knowledge yahan save hoti hai
MEMORY_FILE = DATA_DIR / "memory.json"
KNOWLEDGE_FILE = DATA_DIR / "knowledge.json"
MAX_HISTORY = 40                     # kitni purani baatein yaad rakhe

SYSTEM_PROMPT = f"""Tum JARVIS ho, {USER_NAME} ke personal AI assistant, bilkul Iron Man ke JARVIS jaise.
User ko '{USER_NAME}' bolo. Jawab chhote (1-3 line), bolne layak aur Hinglish mein do.
Markdown, emoji ya list mat use karo, kyunki jawab bol kar sunaya jayega."""
