"""JARVIS ki settings. Yahan badlav karke JARVIS ko customize karo."""
from pathlib import Path

VERSION = "5.4"

USER_NAME = "Sir"
OLLAMA_MODEL = "qwen2.5:3b"          # 16GB RAM ho to "llama3.1:8b"
VOSK_MODEL_DIR = "model"             # offline speech model ka folder
# Memory aur knowledge user ke home mein, taaki naya version download karne par bhi na mite
DATA_DIR = Path.home() / "JARVIS Data"
MEMORY_FILE = DATA_DIR / "memory.json"
KNOWLEDGE_FILE = DATA_DIR / "knowledge.json"
MAX_HISTORY = 40                     # kitni purani baatein yaad rakhe
WAKE_WORDS = ["jarvis", "jarvish", "jervis", "javis", "jarvees"]
TTS_VOICE = "en-IN-PrabhatNeural"    # online awaaz; ladki ki awaaz: "en-IN-NeerjaNeural"
SLEEP_AFTER = 90                     # itne second chup rahoge to JARVIS standby mein chala jayega
MIC_SENSITIVITY = 2.0                # kam = zyada sensitive (1.5 bahut sensitive, 3 kam)
MIC_PAUSE = 0.9                      # itne second ruko to JARVIS samjhega aapki baat khatam
STOP_WORDS = ["stop", "ruko", "rukiye", "ruk", "bas", "cancel", "chup", "rokiye", "roko"]
STOP_PHRASES = ["ruk jao", "bas karo", "band karo"]
# ---- Main Brain / Agents ----
AGENT_MODEL = OLLAMA_MODEL           # multi-step kaam ke liye; bada model behtar: "qwen2.5:7b" ya "llama3.1:8b"
AGENT_MAX_STEPS = 8                  # ek kaam mein zyada se zyada kitne tool steps
# Aapke coding projects: naam -> folder. "check my jarvis project" bolo
PROJECTS = {
    "jarvis": str(Path(__file__).resolve().parent.parent),
    # "website": r"C:\Users\Naveen\Projects\website",
}

# WhatsApp aur email ke liye apne contacts yahan likho (naam chhote aksharon mein)
CONTACTS = {
    # "mom": "+919876543210",
}
EMAILS = {
    # "boss": "boss@example.com",
}
SLEEP_WORDS = ["so jao", "sleep", "go to sleep", "standby", "chup ho jao"]

def _migrate_old_data():
    """Purane version ke 'data' folder se knowledge/facts/todo naye DATA_DIR mein le aao (ek baar)."""
    import shutil
    old = Path("data")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("knowledge.json", "facts.json", "todo.json", "activity.log"):
        if (old / name).exists() and not (DATA_DIR / name).exists():
            shutil.copy(old / name, DATA_DIR / name)


_migrate_old_data()

SYSTEM_PROMPT = f"""Tum JARVIS ho, {USER_NAME} ke personal AI assistant, bilkul Iron Man ke JARVIS jaise.
User ko '{USER_NAME}' bolo. User Hinglish mein bolega (jaise "kal kaun sa din hai"), use samjho. Reply in short (1-3 sentences), natural Indian English, like a polite Indian assistant.
Markdown, emoji ya list mat use karo, kyunki jawab bol kar sunaya jayega.
BAHUT ZAROORI: Tum sirf baat kar rahe ho, koi kaam khud nahi kar sakte. Kabhi mat bolo ki tumne kuch
khola, band kiya, likha ya chalaya ("Notepad closed", "Chat opened" jaisa kabhi nahi). Kaam alag system karta hai.
Agar user koi kaam kahe jo neeche list mein nahi hai, to saaf bolo ki ye abhi seekha nahi hai.
Agar user ki baat adhoori ya bematlab lage (jaise sirf "jar" ya "I am a"), to poocho ki dobara boliye.
Kaam jo system kar sakta hai: apps/websites kholna aur band karna, File Explorer aur folders kholna,
khule folders batana, Notepad mein likhna, laptop lock/sleep/shutdown, location, gaana chalana, volume,
brightness, media control, screenshot, battery, timer/reminder/alarm, calculator, jokes, news, todo list,
baatein yaad rakhna, clipboard, typing, file dhoondhna, WhatsApp/Gmail kholna, internet search, weather, seekhna.
Agar user inme se koi kaam maange aur tum tak pahunch gaya, to use sahi shabdon mein command dene ko kaho
(jaise "volume 50 karo", "remind me in 10 minutes to drink water"). "help" bolne par poori list milti hai."""


# ---- Aapki apni settings (update par nahi mitti) ----
# JARVIS Data\my_settings.py mein jo likhoge wo upar ki settings ko badal dega.
MY_SETTINGS = DATA_DIR / "my_settings.py"
if not MY_SETTINGS.exists():
    MY_SETTINGS.write_text('''# JARVIS ki aapki settings. Ye file update karne par nahi mitti.
# Jo line chahiye uske aage se # hatao aur apni value likho.

# USER_NAME = "Sir"
# OLLAMA_MODEL = "qwen2.5:3b"
# AGENT_MODEL = "qwen2.5:7b"
# MIC_SENSITIVITY = 2.0
# TTS_VOICE = "en-IN-PrabhatNeural"
# CONTACTS["mom"] = "+919876543210"
# EMAILS["boss"] = "boss@example.com"
# PROJECTS["website"] = r"C:\\Users\\Naveen\\Projects\\website"
''', encoding="utf-8")
try:
    exec(MY_SETTINGS.read_text(encoding="utf-8"), globals())
except Exception as _e:
    print(f"[config] my_settings.py mein galti: {_e}")
