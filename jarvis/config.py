"""JARVIS ki settings. Yahan badlav karke JARVIS ko customize karo."""
from pathlib import Path

VERSION = "4.0"

USER_NAME = "Sir"
OLLAMA_MODEL = "qwen2.5:3b"          # 16GB RAM ho to "llama3.1:8b"
VOSK_MODEL_DIR = "model"             # offline speech model ka folder
DATA_DIR = Path("data")              # memory aur knowledge yahan save hoti hai
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
# WhatsApp aur email ke liye apne contacts yahan likho (naam chhote aksharon mein)
CONTACTS = {
    # "mom": "+919876543210",
}
EMAILS = {
    # "boss": "boss@example.com",
}
SLEEP_WORDS = ["so jao", "sleep", "go to sleep", "standby", "chup ho jao"]

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
