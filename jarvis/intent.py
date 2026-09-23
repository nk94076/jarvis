"""Intent check: ye ORDER hai (kuch karo) ya SAWAAL/BAATCHEET (sirf jawab do)?

Keyword se kaam chunne mein galti hoti thi: "band kar dun to bhi tum sikhate rahoge?" ko "seekho" ka order
maan liya. Ab sawaal jaise vaakyon par pehle AI se poochte hain. AI na mile to seedhe niyam (rules) se."""
import json
import re

from . import config

# Ye shabd hon to vaakya shayad sawaal/baat hai, order nahi
QUESTIONY = re.compile(
    r"\?|\b(rahoge|rahogi|karoge|karogi|sakoge|paoge|hoge|ho gaya kya|kya tum|kya aap|tum .{0,40}(sakte|sakti) ho|"
    r"can you|could you|will you|would you|do you|did you|are you|have you|agar|if i|if you|kyun|kyu|why|"
    r"kaise|how do|how does|what if|matlab|sikh li|seekh li|sikh liya|seekh liya|seekha|sikha|sikhate|seekhte)\b")
DIRECT = re.compile(r"\b(karo|kar do|kardo|kholo|khol do|band karo|chalao|bhejo|likho|banao|bana do|seekho|sikho|"
                    r"dikhao|batao|sunao|lagao|hatao|please|open|close|play|start|stop|search|send|write|make|create|"
                    r"learn|turn|set|show|tell me)\b")


def ambiguous(cmd):
    """Sawaal jaisa lagta hai? Tab hi AI se check karna padega."""
    return bool(QUESTIONY.search(cmd))


def classify(cmd):
    """'action' ya 'question'. Pehle AI, AI na chale to rules."""
    try:
        from .llm_client import chat
        r = chat([{"role": "user", "content":
                   "You route voice commands for an assistant called JARVIS. The user speaks Hinglish.\n"
                   "Decide if this message is an ACTION (the user wants JARVIS to do something now, e.g. "
                   "'kya tum notepad khol sakte ho' = please open notepad) or a QUESTION/CHAT (asking about JARVIS, "
                   "hypothetical, opinion, information, e.g. 'band kar dun to bhi tum sikhate rahoge' = question).\n"
                   f'Message: "{cmd}"\nReply ONLY JSON: {{"type": "action" or "question"}}'}],
                 model=config.OLLAMA_MODEL)
        text = r["message"]["content"]
        m = re.search(r"\{.*\}", text, re.S)
        kind = json.loads(m.group()).get("type", "") if m else text
        if "question" in str(kind).lower():
            return "question"
        if "action" in str(kind).lower():
            return "action"
    except Exception:
        pass
    # AI nahi mila: seedha order-shabd (karo/kholo/open) ho aur "agar/kya tum...?" na ho to action
    if re.search(r"\b(agar|if i|if you|what if|kyun|kyu|why)\b|\?$", cmd):
        return "question"
    return "action" if DIRECT.search(cmd) and not re.search(r"\b(rahoge|karoge|sakoge|hoge|sikh li|seekh li)\b", cmd) \
        else "question"
