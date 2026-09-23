# JARVIS 🤖

Aapka personal voice assistant, Iron Man ke JARVIS jaisa.

![JARVIS HUD](docs/hud.png)

- **Iron Man HUD:** beech mein arc reactor heartbeat ki tarah dhadakta hai, saath mein ghadi, CPU/RAM/Disk, weather aur activity log.
- **Sirf naam se jaagta hai:** "Jarvis" bolo, to chhota robot "Yes Sir?" bolega, kaam karega, phir "Task done, Sir." bolega.
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

Har command se pehle **"Jarvis"** bolo, jaise *"Jarvis, open YouTube"*. Sirf "Jarvis" bolo to wo "Yes Sir?" bol kar command ka intezaar karega.
`F11` se full screen hota hai, `Esc` se band.

## Commands

| Bolo | Kya hoga |
|---|---|
| `learn artificial intelligence` / `seekho ...` | Internet se padh kar notes banayega aur save karega |
| `what have you learnt` / `kya seekha` | Seekhe hue topics batayega |
| `notes artificial intelligence` | Us topic ke notes sunayega |
| `time` / `date` | Samay / tareekh |
| `open youtube`, `notepad kholo` | Website / app kholega |
| `weather in delhi` | Live mausam (online) |
| `play arijit singh` | YouTube par gaana (online) |
| `search iron man 4` | Internet se dhoondh kar jawab (online) |
| `bhool jao` | Baatcheet ki memory mitayega |
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
