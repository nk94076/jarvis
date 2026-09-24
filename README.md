# JARVIS 🤖

Aapka personal voice assistant, Iron Man ke JARVIS jaisa.

![JARVIS HUD](docs/hud.png)

- **Iron Man HUD (v9):** tabs HOME / SYSTEMS / INTELLIGENCE / ANALYTICS / SETTINGS, date + ghadi, SYSTEM STATUS rings + live graphs, dhadakta arc reactor, WEATHER (temp, humidity, hawa, visibility), ACTIVITY LOG, SYSTEM PERFORMANCE graph, helmet character aur mic button (click karke type karo). SETTINGS tab mein safe mode aur brain mode ke button.
- **"Hey Jarvis" se ek baar jagao:** uske baad naam liye bina seedha baat karo. 90 second chup rahoge ya "so jao" bologe to standby.
- **Kaam par report:** open/play/learn/search jaise kaam par "Starting the task, Sir" aur "Task completed, Sir". Baatcheet par nahi.
- **Indian English awaaz:** online ho to `en-IN-PrabhatNeural`, offline ho to computer ki Indian English awaaz.

- **Paid API nahi:** dimaag (Ollama) aapke computer par chalta hai.
- **Offline + Online:** internet na ho to bhi baat karta hai. Internet ho to search, weather, YouTube bhi.
- **Internet se seekhta hai:** "seekho <topic>" bolo, wo padh kar notes bana lega aur yaad rakhega.
- **Batata hai kya seekha:** "kya seekha" bolo.
- **Memory:** `C:\Users\<aap>\JARVIS Data` mein save hoti hai, isliye naya version download karne par bhi nahi mitti.

## Windows par aasaan setup

1. **Python** (3.10 ya naya) install karo (python.org), aur **"Add python.exe to PATH"** tick karo.
2. **Ollama** install karo (ollama.com/download).
3. Is folder mein **`setup.bat`** par double-click karo.
4. Uske baad jab bhi chalana ho, **`JARVIS.bat`** par double-click karo.

Computer on hote hi JARVIS chalu karna ho: `Win + R` dabao, `shell:startup` likho, aur `JARVIS.bat` ka shortcut us folder mein daal do.

**`No module named 'pyttsx3'` jaisa error aaye:** `setup.bat` dobara chalao. Ab wo har library alag se install karta hai aur batata hai kaunsi fail hui. JARVIS ab `pyaudio` ke bina chalta hai, isliye Python 3.12, 3.13 ya 3.14 sab chalenge.

## 🧠 Smart dimaag (16 GB GPU/RAM)

**`upgrade_brain.bat`** par double-click karo. Ye `qwen2.5:14b` (lagbhag 9 GB) download karke `JARVIS Data\my_settings.py` mein set kar dega.
JARVIS dobara chalao, to HUD mein **BRAIN: qwen2.5:14b** dikhega.

- Model GPU mein 60 minute load rehta hai, isliye jawab tez aate hain (`KEEP_ALIVE`).
- Settings wala model install na ho to JARVIS jo sabse bada model install hai uspar chalta hai.
- Personality: insaan jaisi baat, Hinglish samajhna, pichhli baaton ka context, na pata ho to seedha bolna.

## 🧬 Self-Learning & Self-Upgrade (v6)

| Bolo | Kya hoga |
|---|---|
| `ek skill banao jo bitcoin ka price bataye` | JARVIS khud plugin likhta hai, sandbox mein test karta hai, fail ho to fix karke dobara (3 baar tak) |
| `kaun si skills hain meri` | Banayi hui skills aur versions |
| `improve skill bitcoin price taaki rupees mein bataye` | Naya version (test ke baad) |
| `rollback skill bitcoin price`, `disable skill ...`, `enable skill ...` | Version wapas / band / chalu |
| `python ka quiz lo`, `apna test lo` | Har chapter ka quiz, score; kamzor chapter dobara seekhta hai |
| `dashboard kholo` | Learning, scores, skills, success rate, failures, gaps ka page |
| `kya improve karna chahiye` | Jo kaam nahi kar paya uski list (gap analysis) aur suggestions |
| `audit adhookmedia.com` | SEO, speed, security, accessibility report |
| `learning list saaf karo`, `remove javascript from learning` | Pending learning list saaf |

- **Order vs sawaal:** "kya tum ... sakte ho", "...rahoge?" jaise vaakyon par JARVIS pehle samajhta hai ki aap kaam bol rahe ho ya sawaal pooch rahe ho.
- Skills `JARVIS Data\skills` mein alag files hain; JARVIS apna core code kabhi khud nahi badalta.
- **`update.bat`** pehle backup banata hai, update ke baad regression test chalata hai, fail ho to purana version khud wapas lata hai. **`rollback.bat`** se kabhi bhi pichla version.

## 🚀 Phase 2 & 3 (v7)

| Bolo | Kya hoga | Setup chahiye? |
|---|---|---|
| `python mein program likho jo ...` (JavaScript, PHP, Java, C++, Go, Rust bhi) | Code likhta, chalata, error aaye to khud fix (3 baar) | Language install honi chahiye |
| `run calculator.py`, `test karo app.js` | File chala kar result / error samjhata hai | – |
| `har roz subah 9 baje news sunao`, `schedules dikhao`, `schedule 1 hatao` | Tay samay par kaam + Windows notification | – |
| `camera se dekho kya dikh raha hai`, `screen ko dekho`, `photo beach dekho` | Vision model se dekh kar batata hai | `upgrade_brain.bat` (vision model) |
| `gate cctv dekho` | CCTV camera ki photo le kar batata hai | `CAMERAS` |
| `check my email`, `naye mails batao` | Unread emails ki summary | Gmail App Password |
| `send email to nk94076 at gmail dot com subject hi message kal milte hain` | Confirm karke bhejta hai | Gmail App Password |
| `aaj ki meetings batao`, `add meeting with rahul kal 4 baje` | Calendar padhna / event page | Calendar iCal link |
| `github repos`, `github issues of jarvis`, `clone github jarvis`, `commit my jarvis project` | GitHub | GitHub token |
| `shop database mein kitne users hain` | Sirf-padhne wali SQL query | `DATABASES` |
| `web server status check karo` | SSH se server status | `SERVERS` |
| `bedroom ki light on karo`, `hall ka ac 24 par set karo` | Smart home | Home Assistant |
| `cloud brain on karo` / `local brain on karo` / `auto brain` | Claude/Gemini aur local ke beech switch | API key |
| **Phone se JARVIS** | Console mein dikhe address ko phone ke browser mein kholo, PIN daalo, "Add to Home screen" | Same WiFi |

### Phase 2 setup (sab `JARVIS Data\my_settings.py` mein)

- **Gmail:** Google Account → Security → 2-Step Verification on → "App passwords" → naya password banao.
  `GMAIL_ADDRESS = "aap@gmail.com"` aur `GMAIL_APP_PASSWORD = "abcd efgh ijkl mnop"`
- **Calendar:** calendar.google.com → Settings → apna calendar → "Secret address in iCal format" copy karo.
  `CALENDAR_ICS_URL = "https://calendar.google.com/calendar/ical/.../basic.ics"`
- **GitHub:** github.com → Settings → Developer settings → Personal access tokens → Fine-grained token (repo read/write).
  `GITHUB_TOKEN = "github_pat_..."` aur `GITHUB_USER = "nk94076"`
- **Cloud AI (optional):** Claude: console.anthropic.com se key → `ANTHROPIC_API_KEY = "sk-ant-..."`, `BRAIN_MODE = "auto"`.
  Gemini (free tier): aistudio.google.com se key → `GEMINI_API_KEY = "..."`, `CLOUD_PROVIDER = "gemini"`, `BRAIN_MODE = "auto"`.
- **Database:** `DATABASES = {"shop": "sqlite:///C:/data/shop.db"}` (MySQL: `pip install pymysql`, Postgres: `pip install psycopg2-binary`).
- **Server:** `SERVERS = {"web": {"host": "1.2.3.4", "user": "root", "key": r"C:\Users\me\.ssh\id_rsa"}}`
- **Smart home:** Home Assistant install karo → Profile → Long-lived access token.
  `HOME_ASSISTANT_URL = "http://homeassistant.local:8123"`, `HOME_ASSISTANT_TOKEN = "..."`
- **CCTV:** `CAMERAS = {"gate": "rtsp://user:pass@192.168.1.20:554/stream1"}`
- **Phone PIN badalna:** `PHONE_PIN = "4321"`; band karna: `PHONE_APP = False`

## 🧠 Core Architecture (v8)

```
Voice / Phone / Type box
   ↓
Intent + Goal Engine ── order? sawaal? kai kaam ek saath (goal)?
   ↓
Agent Orchestrator ── plan (2-6 steps) → har step sahi agent → Self-Evaluation → retry → report
   ↓                    ↑ Failure Memory ke sabak plan mein
Tool Registry (36+ tools, category + risk) ── research · coder · browser · files · pc · web · skills
   ↓
Security Layer (allow / ask / deny, safe mode, audit log) → Sandbox (alag process, time limit, secrets hataye)
```

| Bolo | Module |
|---|---|
| `electric cars par research karo phir landing page banao aur usko test karo` | Goal Engine + Orchestrator + Self-Evaluation |
| `goals dikhao` | Goal status / history |
| `tools list dikhao` | Tool Registry |
| `safe mode on karo`, `permissions batao` | Security layer (`PERMISSIONS` in my_settings) |
| `test website adhookmedia.com` | Browser Agent (Playwright): speed, JS errors, broken links/images, mobile layout, screenshots |
| `browser agent adhookmedia.com kholo aur contact form mein naam Naveen bharo` | Browser Agent (real Chrome: open, click, fill, read) |
| `computer use: notepad kholo, hello likho aur save karo` | Computer-use Agent (screen padh kar khud kadam) |
| `understand my jarvis project`, `jarvis project mein voice kahan handle hoti hai` | Project Understanding + Project Memory |
| `apni kamiyan door karo` | Self-Upgrade Engine: gaps → skill → regression test → keep/rollback |
| `skill history dikhao`, `undo last skill change` | Git version/branch system (Git install ho to) |

## 🧬 Khud ko smart banana (v9.1)

| Bolo | Kya hoga |
|---|---|
| `internet se seekho aur khud ko smart banao` | Seekha gyaan internet se taaza + jo kaam nahi kar paya uski skills + (aapse poochkar) apne code ka ek sudhaar |
| `python ke bare mein internet se seekho aur khud ko smart banao` | Python seekhna shuru + baaki upar wala |
| `apna code upgrade karo taaki reminders hindi mein bhi samjhe` | **Safe Self-Code-Upgrade**: apna code padhta hai → badlav alag copy par → saare tests → fail ho to khud fix (3 baar) → Notepad mein badlav dikhata hai → **aapke "yes" par hi** lagata hai (backup ke saath) |
| `self upgrade undo` | Pichla code wapas |

Suraksha: `security.py`, `selftest.py`, `sandbox.py` aur `selfcode.py` ko JARVIS kabhi nahi badal sakta.

## 🔄 Update kaise karein

- **`update.bat`** par double-click karo, ya JARVIS se bolo **"code update karo"**. Naya version download ho jayega.
- Aapki memory, knowledge aur settings `C:\Users\<aap>\JARVIS Data` mein safe rehti hain.
- Apni settings (naam, contacts, projects, model) **`JARVIS Data\my_settings.py`** mein likho. Ye update par nahi mitti.

## 🌐 Website Builder (v9.8: jo aap bolo wahi)

- `mere chai shop ke liye dark brown theme wali website banao jisme menu, timing aur contact form ho`
  → AI aapki baat ke hisaab se **poora naya design** likhta hai (template nahi), browser mein khol kar JS errors aur
  mobile layout jaanchta hai, galti ho to khud theek karta hai.
- `page mein pricing section jodo`, `rang blue karo`, `header mein logo lagao` → pichhle page mein badlav (purana version `index_v1.html`...)
- `page undo` → pichla version

## 🌐 Website Builder (purana template)

Bolo: *"gym ke liye HTML landing page banao"*, *"coffee shop ki website banao red color mein"*.
JARVIS content likhta hai, sundar responsive page banata hai, browser mein kholta hai aur
`Documents\JARVIS Projects\<topic>\index.html` mein save karta hai. Rang: red, blue, green, purple, orange, pink, teal, black, gold.

![Landing page example](docs/landing-example.png)

## 📚 Learning Agent

| Bolo | Kya hoga |
|---|---|
| `internet se python learn karna start karo`, `php seekho`, `mujhe react sikhao` | Background mein poora subject (10 chapters) internet se seekhta hai |
| `learning status`, `kya kya seekha` | Kitna seekha |
| `learning band karo` / `resume learning` | Rokna / aage seekhna (JARVIS dobara chalane par apne aap aage seekhta hai) |
| `khud ko upgrade kar lo` | Seekhe hue subjects ko taaza jaankari se dobara seekhta hai |
| `python mein loops kya hote hain` | Seekhe hue notes se jawab |
| `memory delete karo` | Sab gyaan mitata hai, **sirf "yes" bolne par** |

## Setup (manual, ek baar)

1. **Python 3.10+** install karo (python.org, "Add to PATH" tick karna).
2. **Ollama** install karo (ollama.com), phir:
   ```bash
   ollama pull qwen2.5:3b
   ```
   16GB RAM ho to `llama3.1:8b` lo aur `jarvis/config.py` mein `OLLAMA_MODEL` badlo.
3. **Libraries:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Offline awaaz (optional):** https://alphacephei.com/vosk/models se
   `vosk-model-small-en-in-0.4` download karo, unzip karo, folder ka naam `model` rakho
   aur `main.py` ke saath rakho. Internet ho to Google speech apne aap use hoti hai.

## Chalao

```bash
python main.py              # HUD screen + awaaz
python main.py --cli        # bina screen ke
python main.py --text       # type karke test karo
python main.py --text --gui # screen ke saath, sirf type karke
```

HUD mein neeche ek **type box** bhi hai: command likho aur Enter dabao (usme "Jarvis" likhna zaroori nahi).

Pehle **"Hey Jarvis"** bolo. Uske baad seedha bolo: *"open YouTube"*, *"kal kaun sa din hai"*. Chup rahoge to 90 second baad standby (`config.py` mein `SLEEP_AFTER`).
`F11` se full screen hota hai, `Esc` se band.

## Commands

| Bolo | Kya hoga |
|---|---|
| `learn artificial intelligence` / `seekho ...` | Internet se padh kar notes banayega aur save karega |
| `what have you learnt` / `kya seekha` | Seekhe hue topics batayega |
| `notes artificial intelligence` | Us topic ke notes sunayega |
| `time kya hua hai`, `kal kaun sa din hai`, `aaj ki date` | Samay / din / tareekh |
| `stop` / `ruko` / `bas` (bolte ya kaam karte waqt bhi), ya `Ctrl+Space` | Turant ruk jata hai |
| `my name is Naveen write on notepad`, `notepad mein likho ...` | Notepad mein likh kar `Documents\JARVIS Notes` mein save |
| `open file explorer`, `open downloads/documents/desktop` | File Explorer / folder kholega |
| `kaun sa folder open hai` | Khule hue folders ke naam batayega |
| `so jao` / `sleep` | Standby (phir "Hey Jarvis" se jagao) |
| `open youtube`, `notepad kholo` | Website / app kholega |
| `weather in delhi` | Live mausam (online) |
| `play arijit singh` | YouTube par gaana (online) |
| `search iron man 4` | Internet se dhoondh kar jawab (online) |
| `bhool jao` | Baatcheet ki memory mitayega |
| `volume up/down`, `volume 40 karo`, `mute` | Volume |
| `next song`, `pause`, `resume` | Music/video control |
| `brightness 60`, `brightness badhao` | Screen brightness |
| `take a screenshot` | `Pictures\JARVIS Screenshots` mein save |
| `battery kitni hai`, `system status`, `my ip address` | System jaankari |
| `remind me in 10 minutes to drink water`, `5 minute ka timer`, `alarm 6:30 am` | Reminder / timer / alarm |
| `calculate 25 into 4`, `15 percent of 200`, `square root of 144` | Calculator |
| `tell me a joke`, `motivation do`, `toss a coin`, `roll a dice` | Masti |
| `news`, `cricket ki news`, `who is elon musk` | News / Wikipedia |
| `add buy milk to my todo list`, `todo list batao`, `remove 1 from todo` | Todo list |
| `remember that my birthday is 5 may`, `tumhe kya yaad hai` | Yaad rakhna |
| `copy hello`, `clipboard mein kya hai`, `type hello sir` | Clipboard / typing |
| `find file resume` | Desktop/Documents/Downloads mein file dhoondh kar kholna |
| `send whatsapp message to mom I will be late` | WhatsApp (contacts `config.py` mein) |
| `email to boss about leave` | Gmail compose |
| `open flipkart`, `open github.com`, `youtube par X search karo` | Koi bhi website |
| `close chrome`, `mera laptop band` (lock), `sleep mode`, `shutdown` (confirm ke saath) | PC control |
| `empty recycle bin` (confirm ke saath), `minimize all` | Windows |
| `where am i` | Location (internet se, lagbhag) |
| `what can you do` / `help` | Saari skills ki list |
| `bye` | Band |
| Kuch bhi aur | Normal baatcheet; seekhi hui jaankari bhi use karta hai |

## 🧠 Main Brain aur Agents (v5)

Lamba ya kai step wala kaam bolo, to Main Brain use steps mein todta hai aur tools chalata hai, jab tak kaam poora na ho.
Jaise: *"downloads folder check karo aur files ko organize kar do"*.

| Bolo | Agent | Kya hoga |
|---|---|---|
| `screen par kya likha hai` | 👁️ Vision | Windows OCR se screen padhega |
| `submit par click karo`, `click on sign in` | 🖱️ PC | Screen par wo text dhoondh kar click |
| `press ctrl+t`, `scroll down` | ⌨️ PC | Keyboard / mouse |
| `new tab`, `close tab`, `go back`, `refresh`, `zoom in` | 🌐 Browser | Chrome/Edge control |
| `research karo electric cars in india` | 🔎 Research | Kai websites padh kar report, `Documents\JARVIS Reports` mein |
| `read pdf invoice`, `invoice pdf ki summary` | 📄 PDF | PDF dhoondh kar summary |
| `organize my downloads folder` | 📂 File | Files ko Images/Documents/Videos... mein lagata hai (confirm) |
| `check my jarvis project` | 💻 Coding | Git status, syntax check, code review, report |
| `git status of jarvis`, `review code main.py` | 🐙 Git / Coding | |
| `run command ipconfig` | 🖥️ Terminal | Confirm ke baad chalata hai; khatarnaak commands block |

- **Permission system:** file likhna/move/delete, terminal, organize jaise kaam se pehle JARVIS poochta hai: *"Say yes or no"*.
- **Activity log:** har tool call `data\activity.log` mein likha jata hai.
- **Projects:** `config.py` mein `PROJECTS` mein apne projects ka naam aur folder jodo.
- **Behtar dimaag:** 16GB RAM ho to `ollama pull qwen2.5:7b` karke `config.py` mein `AGENT_MODEL = "qwen2.5:7b"` karo. Multi-step kaam kaafi behtar honge.
- **Naya tool (plugin):** `jarvis/agent.py` mein `@tool(...)` laga kar ek function likho, Main Brain use apne aap use karne lagega.

## Folder structure

```
main.py              shuru karne ki file
jarvis/config.py     naam, model, personality (yahan customize karo)
jarvis/hud.py        Iron Man jaisa screen (arc reactor, character)
jarvis/voice.py      sunna aur bolna (Indian English)
jarvis/brain.py      Ollama dimaag + memory
jarvis/knowledge.py  internet se seekhna, notes save karna
jarvis/skills.py     seedhe commands
jarvis/skills_extra.py  volume, timer, calculator, news, todo...
jarvis/agent.py      Main Brain, tools/plugins, agents, permission system
jarvis/pc.py         mouse, keyboard, screen OCR, browser keys
jarvis/internet.py   search, weather, wikipedia
data/                memory.json aur knowledge.json (apne aap banta hai)
```

## Naya kaam kaise sikhayein

`jarvis/skills.py` ke `handle()` mein ek naya `if` jodo:

```python
if "joke" in cmd:
    return "Sir, why did the computer go to the doctor? Because it had a virus."
```
