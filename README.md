# JARVIS 🤖

Aapka personal voice assistant, Iron Man ke JARVIS jaisa.

- **Paid API nahi:** dimaag (Ollama) aapke computer par chalta hai.
- **Offline + Online:** internet na ho to bhi baat karta hai. Internet ho to search, weather, YouTube bhi.
- **Internet se seekhta hai:** "seekho <topic>" bolo, wo padh kar notes bana lega aur yaad rakhega.
- **Batata hai kya seekha:** "kya seekha" bolo.
- **Memory:** band karke dobara kholo, pichli baatein yaad rehti hain.

## Setup (ek baar)

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
   Windows par `pyaudio` fail ho to: `pip install pipwin` aur `pipwin install pyaudio`.
4. **Offline awaaz (optional):** https://alphacephei.com/vosk/models se
   `vosk-model-small-en-in-0.4` download karo, unzip karo, folder ka naam `model` rakho
   aur `main.py` ke saath rakho. Internet ho to Google speech apne aap use hoti hai.

## Chalao

```bash
python main.py          # awaaz se
python main.py --text   # keyboard se type karke
```

## Commands

| Bolo | Kya hoga |
|---|---|
| `seekho artificial intelligence` | Internet se padh kar notes banayega aur save karega |
| `kya seekha` | Seekhe hue topics batayega |
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
jarvis/voice.py      sunna aur bolna
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
    return "Sir, Tony Stark ne kaha: main Iron Man hoon. Maine kaha: aur main uska WiFi."
```
