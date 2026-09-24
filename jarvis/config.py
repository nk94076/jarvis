"""JARVIS ki settings. Yahan badlav karke JARVIS ko customize karo."""
from pathlib import Path

VERSION = "9.10"

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
AGENT_MODEL = OLLAMA_MODEL
# ---- Cloud AI (optional) ----
BRAIN_MODE = "local"                 # "local" (sirf Ollama), "auto" (internet ho to cloud), "cloud"
CLOUD_PROVIDER = "claude"            # "claude" ya "gemini"
ANTHROPIC_API_KEY = ""               # my_settings.py mein daalo, yahan nahi
CLAUDE_MODEL = "claude-opus-5"
GEMINI_API_KEY = ""
GEMINI_MODEL = "gemini-2.5-flash"
CHAT_TURNS = 16                      # baatcheet ke kitne pichhle messages AI ko dikhein
KEEP_ALIVE = "60m"                   # model itni der GPU/RAM mein load rahe (tez jawab)
TEMPERATURE = 0.6                    # kam = seedha, zyada = creative
CONTEXT_SIZE = 8192                  # kitna lamba context yaad rakhe           # multi-step kaam ke liye; bada model behtar: "qwen2.5:7b" ya "llama3.1:8b"
AGENT_MAX_STEPS = 8
PASS_SCORE = 60                      # self-test mein isse kam score = chapter dobara seekho                  # ek kaam mein zyada se zyada kitne tool steps
# Aapke coding projects: naam -> folder. "check my jarvis project" bolo
PROJECTS = {
    "jarvis": str(Path(__file__).resolve().parent.parent),
    # "website": r"C:\Users\Naveen\Projects\website",
}

# ---- Vision / camera ----
VISION_MODEL = "qwen2.5vl:7b"        # camera/screen/photo dekhne wala model
WEBCAM_INDEX = 0
CAMERAS = {}                         # CCTV: {"gate": "rtsp://user:pass@192.168.1.20:554/stream1"}
# ---- Phase 2 integrations (my_settings.py mein bharo) ----
GMAIL_ADDRESS = ""
GMAIL_APP_PASSWORD = ""
CALENDAR_ICS_URL = ""
GITHUB_TOKEN = ""
GITHUB_USER = ""
DATABASES = {}                       # {"shop": "sqlite:///C:/data/shop.db", "crm": "mysql://user:pass@host/db"}
SERVERS = {}                         # {"web": {"host": "1.2.3.4", "user": "root", "key": r"C:\Users\me\.ssh\id_rsa"}}
HOME_ASSISTANT_URL = ""              # "http://homeassistant.local:8123"
HOME_ASSISTANT_TOKEN = ""
PERMISSIONS = {}                     # {"run_terminal": "deny", "pw_click": "ask", "web_search": "allow"}
BROWSER_EXECUTABLE = ""              # khali = Playwright ka Chromium / aapka Chrome
BROWSER_VISIBLE = True               # Browser Agent ka Chrome dikhe (False = chhupa hua)
PHONE_APP = True                     # phone se JARVIS (ghar ka WiFi)
PHONE_PORT = 8765
PHONE_PIN = ""                       # khali = apne aap bana dega

# WhatsApp aur email ke liye apne contacts yahan likho (naam chhote aksharon mein)
CONTACTS = {
    # "mom": "+919876543210",
}
EMAILS = {
    # "boss": "boss@example.com",
}
# Mic aksar ye shabd galat sunta hai: galat -> sahi (apne shabd my_settings.py mein jodo)
SPEECH_FIXES = {"paidal": "python", "payton": "python", "pithon": "python", "paython": "python",
                "jarwis": "jarvis", "service": "jarvis", "jar vis": "jarvis", "java script": "javascript",
                "php ": "php ", "you tube": "youtube", "what's app": "whatsapp", "note pad": "notepad",
                "g mail": "gmail", "chat gpt": "chatgpt", "bnao": "banao", "banado": "bana do"}
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

def build_system_prompt():
    """JARVIS ki personality. my_settings.py ke baad dobara banti hai (USER_NAME wagairah ke liye)."""
    n = USER_NAME
    return f"""You are JARVIS, the personal AI assistant of {n}, like JARVIS from Iron Man: warm, witty, loyal and sharp.
Talk like a real, smart human friend, not like a robot or a search engine.
LANGUAGE: reply ONLY in English or Hinglish (Hindi in English letters). NEVER use Chinese, Japanese or any other script.

How you talk:
- Address the user as '{n}' now and then, not in every sentence.
- The user speaks Hinglish (Hindi + English, often with speech-recognition mistakes). Understand the MEANING,
  not the exact words. Guess sensibly from context: "cal kaun sa din hai" means "what day is tomorrow".
- Reply in natural Indian English, short like spoken conversation: 1-3 sentences normally. Give more detail only
  when asked to explain. Never use markdown, lists, headings, emojis or links: your reply is spoken aloud.
- Use common sense and the recent conversation. "usko", "wo wala", "it", "that" refer to what was just discussed.
- If the request is truly unclear or looks misheard (like just "jar" or "I am a"), ask one short question instead
  of guessing. If you do not know something, say so honestly. Never invent facts, names or numbers.
- Have a personality: be encouraging, a little humorous when it fits, and give your honest opinion when asked.
- Remember what the user tells you about themselves and use it naturally.

What you can and cannot do:
- You are only the talking brain. A separate system performs actions. NEVER say you opened, closed, clicked,
  wrote, sent or played something ("Notepad closed", "Chat opened" is forbidden).
- The system can: open/close apps and websites, Google/YouTube search, File Explorer and folders, Notepad,
  screen reading and clicking on text, browser tabs, volume, brightness, music, screenshots, battery, storage,
  timers, reminders, alarms, calculator, news, weather, todo list, remembering facts, clipboard, typing,
  finding files and PDFs, WhatsApp/Gmail, lock/sleep/shutdown, research reports, learning subjects from the
  internet, landing pages, project code checks and terminal commands.
- If the user asks for one of these and it reached you, tell them the exact words to say, for example
  "Just say: volume 50 karo". "help" lists everything."""





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
SYSTEM_PROMPT = build_system_prompt()
