"""Learning Agent: "python learn karna start karo" -> internet se poora subject seekhna, background mein.

1. Subject ka syllabus (10-12 chapters) banata hai
2. Har chapter: Wikipedia + web search + 2 webpages padh kar notes, knowledge mein save
3. Progress data/learning.json mein; JARVIS band ho jaye to agli baar wahi se aage seekhta hai
4. Knowledge kabhi apne aap delete nahi hoti, sirf aapke kehne par (confirm ke saath)
"""
import json
import re
import threading
import time
from datetime import datetime

from . import config, internet

LEARN_FILE = config.DATA_DIR / "learning.json"
LEARN_FILLER = ["ek kaam karo", "ek kam karo", "internet se", "google se", "learn karna start karo", "learn karna",
                "sikhna start karo", "seekhna start karo", "start karo", "shuru karo", "learn", "seekhna",
                "sikhna", "seekho", "sikho", "sikhao", "sikhana", "seekhao", "seekh lo", "sikh lo", "karo", "kar do", "start", "sab kuch", "poora",
                "pura", "complete", "detail mein", "achhe se", "about", "ke bare mein", "ke baare mein", "please",
                "jarvis", "language", "mujhe", "tum", "tumhe", "apne aap", "khud", "se", "ko", "the", "to"]


def subject_from(cmd):
    """'internet se python learn karna start karo' -> 'python'"""
    text = re.split(r"\s+(?:aur|and then|phir|then)\s+", cmd)[0]
    for w in sorted(LEARN_FILLER, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(w)}\b", " ", text)
    return " ".join(text.split())


class Learner:
    def __init__(self, knowledge, llm):
        self.knowledge = knowledge
        self.llm = llm                          # llm(prompt) -> text
        self.notify = print
        self.lock = threading.Lock()
        self.thread = None
        self.stop_flag = threading.Event()
        self.state = self._load()

    # ---------- state ----------
    def _load(self):
        try:
            return json.loads(LEARN_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"queue": [], "subjects": {}}

    def _save(self):
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        LEARN_FILE.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")

    def busy(self):
        return self.thread is not None and self.thread.is_alive()

    # ---------- commands ----------
    def start(self, subject):
        s = config.USER_NAME
        subject = subject.strip()
        if not subject:
            return f"What should I learn, {s}?"
        with self.lock:
            subj = self.state["subjects"].get(subject)
            if subj and subj.get("done_all"):
                return f"{s}, I have already learnt {subject}. Say 'upgrade yourself' to refresh it with the latest information."
            if subject not in self.state["queue"]:
                self.state["queue"].append(subject)
            self._save()
        self._run_background()
        ahead = len(self.state["queue"]) - 1
        extra = f" It is number {ahead + 1} in my learning list." if ahead else ""
        return (f"Okay {s}, I have started learning {subject} from the internet in the background. "
                f"You can keep talking to me. I will tell you when I finish.{extra}")

    def upgrade(self):
        """Seekhe hue subjects ko taaza karo + adhoore poore karo."""
        s = config.USER_NAME
        with self.lock:
            for name, subj in self.state["subjects"].items():
                subj["done"] = []
                subj["done_all"] = False
                if name not in self.state["queue"]:
                    self.state["queue"].append(name)
            self._save()
        if not self.state["queue"]:
            return (f"{s}, I have not learnt any subject yet. Tell me what to learn, like: "
                    f"learn Python. Then I will upgrade my knowledge.")
        self._run_background()
        return (f"Okay {s}, I am upgrading myself. I will re-learn {', '.join(self.state['queue'])} "
                f"with the latest information from the internet in the background.")

    def stop(self):
        self.stop_flag.set()
        return f"Okay {config.USER_NAME}, I have paused learning. Say 'resume learning' to continue."

    def resume(self):
        """JARVIS start hone par: adhoori learning wapas shuru."""
        if self.state["queue"]:
            self._run_background()
            return True
        return False

    def status(self):
        s = config.USER_NAME
        parts = []
        for name, subj in self.state["subjects"].items():
            total, done = len(subj.get("syllabus", [])), len(subj.get("done", []))
            parts.append(f"{name}: {'complete' if subj.get('done_all') else f'{done} of {total} chapters'}")
        if not parts:
            return f"{s}, I have not started learning any subject yet."
        now = f" Right now I am learning {self.state['queue'][0]}." if self.busy() and self.state["queue"] else ""
        return f"{s}, " + ". ".join(parts) + "." + now

    # ---------- background kaam ----------
    def _run_background(self):
        if self.busy():
            return
        self.stop_flag.clear()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        while self.state["queue"] and not self.stop_flag.is_set():
            if not internet.internet_hai():
                time.sleep(30)                  # internet aane ka intezaar
                continue
            subject = self.state["queue"][0]
            try:
                finished = self._learn_subject(subject)
            except Exception as e:
                print(f"[learn] {subject}: {e}")
                time.sleep(10)
                continue
            if finished:
                with self.lock:
                    self.state["queue"].pop(0)
                    self._save()
                n = len(self.state["subjects"][subject]["done"])
                self.notify(f"{config.USER_NAME}, I have finished learning {subject}. I learnt {n} chapters "
                            f"and saved everything in my memory. Ask me anything about {subject}.")

    def _syllabus(self, subject):
        raw = self.llm(f"Make a learning syllabus for '{subject}' for a beginner to advanced learner. "
                       f"Give exactly 10 short chapter titles, one per line, no numbering, no extra text.")
        chapters = [re.sub(r"^[\s\d.)*#-]+", "", line).strip() for line in raw.splitlines()]
        chapters = [c for c in chapters if 2 < len(c) < 80][:12]
        if len(chapters) < 4:                   # model ne gadbad ki: web se chapters
            res = internet.search(f"{subject} tutorial topics", max_results=8)
            chapters = ["introduction"] + [r.get("title", "")[:60] for r in res if r.get("title")]
        return chapters

    def _learn_subject(self, subject):
        with self.lock:
            subj = self.state["subjects"].setdefault(subject, {"started": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                                               "syllabus": [], "done": []})
        if not subj["syllabus"]:
            subj["syllabus"] = self._syllabus(subject)
            self._save()
        for chapter in subj["syllabus"]:
            if self.stop_flag.is_set():
                return False
            if chapter in subj["done"]:
                continue
            self._learn_chapter(subject, chapter)
            with self.lock:
                subj["done"].append(chapter)
                self._save()
        subj["done_all"] = True
        subj["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._save()
        return True

    def _learn_chapter(self, subject, chapter):
        from .agent import t_read_webpage
        query = f"{subject} {chapter}"
        texts, sources = [], []
        wiki = internet.wikipedia_summary(query, sentences=6)
        if wiki:
            texts.append(wiki)
        for r in internet.search(query + " tutorial", max_results=5):
            texts.append(r.get("body", ""))
            if r.get("href"):
                sources.append(r["href"])
        for url in sources[:2]:
            try:
                texts.append(t_read_webpage(url)[:3000])
            except Exception:
                pass
        notes = self.llm(f"Subject: {subject}. Chapter: {chapter}.\nIn sources se is chapter ke clear study notes "
                         f"likho (simple English): main concepts, short examples (code ho to chhota code), aur "
                         f"yaad rakhne wale points. 150-300 words.\n\n" + "\n\n".join(texts)[:9000])
        with self.lock:
            self.knowledge.add(f"{subject}: {chapter}", notes, sources)
