# JARVIS 🤖

Aapka personal voice assistant, Iron Man ke JARVIS jaisa.

![JARVIS HUD](docs/hud.png)

- **Iron Man HUD:** beech mein arc reactor heartbeat ki tarah dhadakta hai, saath mein ghadi, CPU/RAM/Disk, weather aur activity log.
- **"Hey Jarvis" se ek baar jagao:** uske baad naam liye bina seedha baat karo. 90 second chup rahoge ya "so jao" bologe to standby.
- **Kaam par report:** open/play/learn/search jaise kaam par "Starting the task, Sir" aur "Task completed, Sir". Baatcheet par nahi.
- **Indian English awaaz:** online ho to `en-IN-PrabhatNeural`, offline ho to computer ki Indian English awaaz.

- **Paid API nahi:** dimaag (Ollama) aapke computer par chalta hai.
- **Offline + Online:** internet na ho to bhi baat karta hai. Internet ho to search, weather, YouTube bhi.
- **Internet se seekhta hai:** "seekho <topic>" bolo, wo padh kar notes bana lega aur yaad rakhega.
- **Batata hai kya seekha:** "kya seekha" bolo.
- **Memory:** band karke dobara kholo, pichli baatein yaad rehti hain.

## Windows par aasaan setup

1. **Python** (3.10 ya naya) install karo (python.org), aur **"Add python.exe to PATH"** tick karo.
2. **Ollama** install karo (ollama.com/download).
3. Is folder mein **`setup.bat`** par double-click karo.
4. Uske baad jab bhi chalana ho, **`JARVIS.bat`** par double-click karo.

Computer on hote hi JARVIS chalu karna ho: `Win + R` dabao, `shell:startup` likho, aur `JARVIS.bat` ka shortcut us folder mein daal do.

**`No module named 'pyttsx3'` jaisa error aaye:** `setup.bat` dobara chalao. Ab wo har library alag se install karta hai aur batata hai kaunsi fail hui. JARVIS ab `pyaudio` ke bina chalta hai, isliye Python 3.12, 3.13 ya 3.14 sab chalenge.

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

## Folder structure

```
main.py              shuru karne ki file
jarvis/config.py     naam, model, personality (yahan customize karo)
jarvis/hud.py        Iron Man jaisa screen (arc reactor, character)
jarvis/voice.py      sunna aur bolna (Indian English)
jarvis/brain.py      Ollama dimaag + memory
jarvis/knowledge.py  internet se seekhna, notes save karna
jarvis/skills.py     saare commands (naya kaam yahan add karo)
jarvis/internet.py   search, weather, wikipedia
data/                memory.json aur knowledge.json (apne aap banta hai)
```

## Naya kaam kaise sikhayein

`jarvis/skills.py` ke `handle()` mein ek naya `if` jodo:

```python
if "joke" in cmd:
    return "Sir, why did the computer go to the doctor? Because it had a virus."
```
