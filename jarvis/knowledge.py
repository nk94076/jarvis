"""Seekhna: internet se topic padh kar notes banana, save karna, aur baad mein yaad karna."""
import json
import re
from datetime import datetime

from . import config, internet


def _words(text):
    return set(w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2)


class Knowledge:
    def __init__(self, brain):
        self.brain = brain
        config.DATA_DIR.mkdir(exist_ok=True)
        self.items = []
        if config.KNOWLEDGE_FILE.exists():
            self.items = json.loads(config.KNOWLEDGE_FILE.read_text(encoding="utf-8"))

    def _save(self):
        config.KNOWLEDGE_FILE.write_text(json.dumps(self.items, ensure_ascii=False, indent=1), encoding="utf-8")

    def seekho(self, topic):
        """Internet se topic ke baare mein padhta hai aur notes save karta hai."""
        if not internet.internet_hai():
            return f"{config.USER_NAME}, I need internet to learn new things."
        texts = []
        wiki = internet.wikipedia_summary(topic)
        if wiki:
            texts.append(wiki)
        results = internet.search(topic)
        texts += [r.get("body", "") for r in results]
        if not any(texts):
            return f"Sorry {config.USER_NAME}, I could not find anything about {topic}."
        raw = "\n".join(texts)[:6000]
        notes = self.brain.ek_baar(
            f"Neeche di gayi jaankari se '{topic}' ke 5-7 sabse zaroori points "
            f"simple Indian English mein likho, har point nayi line par:\n\n{raw}")
        self.items = [i for i in self.items if i["topic"] != topic]
        self.items.append({
            "topic": topic,
            "notes": notes,
            "sources": [r.get("href", "") for r in results if r.get("href")],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        self._save()
        pehli_line = notes.splitlines()[0] if notes else ""
        return f"{config.USER_NAME}, I have learnt about {topic}. {pehli_line}"

    def add(self, topic, notes, sources=()):
        """Research ya kisi aur jagah se aayi jaankari knowledge mein jodo."""
        self.items = [i for i in self.items if i["topic"] != topic]
        self.items.append({"topic": topic, "notes": notes, "sources": list(sources),
                           "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
        self._save()

    def kya_seekha(self):
        if not self.items:
            return f"{config.USER_NAME}, I have not learnt anything yet. Just say learn, and the topic name."
        topics = ", ".join(i["topic"] for i in self.items[-10:])
        return f"I have {len(self.items)} topics in my memory. Recent ones are: {topics}."

    def batao(self, topic):
        item = self.dhoondo(topic, limit=1)
        return item[0]["notes"] if item else f"I have not learnt about {topic} yet."

    def dhoondo(self, query, limit=2):
        """Sawaal se milte-julte seekhe hue topics."""
        q = _words(query)
        scored = []
        for item in self.items:
            score = len(q & _words(item["topic"])) * 3 + len(q & _words(item["notes"]))
            if score:
                scored.append((score, item))
        scored.sort(key=lambda s: -s[0])
        return [i for _, i in scored[:limit]]

    def context(self, query):
        return "\n\n".join(f"{i['topic']}:\n{i['notes'][:1500]}" for i in self.dhoondo(query, limit=3))
