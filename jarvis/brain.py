"""Dimaag: Ollama ka local model, baatcheet ki memory ke saath."""
import json
import re


def clean(text):
    """Bolne layak text: markdown (** ## ` -), 'Q:' jaisa kachra hatao."""
    text = re.sub(r"\*\*?Q:.*?(\*\*|$)", " ", text, flags=re.M)
    text = re.sub(r"[*#`_>]+", "", text)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.M)
    return re.sub(r"\s+", " ", text).strip()

from . import config


class Brain:
    def __init__(self):
        config.DATA_DIR.mkdir(exist_ok=True)
        self.history = []
        if config.MEMORY_FILE.exists():
            self.history = json.loads(config.MEMORY_FILE.read_text(encoding="utf-8"))

    def _chat(self, messages):
        try:
            from .llm_client import chat
            return chat(messages)["message"]["content"].strip()
        except Exception as e:
            return f"{config.USER_NAME}, my brain is offline. Please start Ollama. ({e})"

    def socho(self, sawaal, extra_context=""):
        """Baatcheet: history ke saath jawab deta hai aur memory save karta hai."""
        from datetime import datetime
        system = config.SYSTEM_PROMPT + datetime.now().strftime(
            "\nAaj %A, %d %B %Y hai aur abhi %I:%M %p baje hain. Kal (tomorrow) ka din isi se nikalo.")
        if extra_context:
            system += "\n\nYe jaankari tumne pehle seekhi hai, zaroorat ho to use karo:\n" + extra_context
        system += "\nSirf seedha jawab do. Sawaal dobara mat likho, 'Q:' ya headings mat banao."
        self.history.append({"role": "user", "content": sawaal})
        jawab = clean(self._chat([{"role": "system", "content": system}] + self.history[-config.CHAT_TURNS:]))
        self.history.append({"role": "assistant", "content": jawab})
        self.history = self.history[-config.MAX_HISTORY:]
        config.MEMORY_FILE.write_text(json.dumps(self.history, ensure_ascii=False, indent=1), encoding="utf-8")
        return jawab

    def ek_baar(self, prompt):
        """Bina history ke ek kaam (summary banana waghera)."""
        return self._chat([{"role": "user", "content": prompt}])

    def bhool_jao(self):
        self.history = []
        config.MEMORY_FILE.unlink(missing_ok=True)
