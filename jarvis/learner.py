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
IDEAS_FILE = config.DATA_DIR / "ideas.json"


def load_ideas():
    try:
        return json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
LEARN_FILLER = ["ek kaam karo", "ek kam karo", "internet se", "google se", "learn karna start karo", "learn karna",
                "sikhna start karo", "seekhna start karo", "start karo", "shuru karo", "learn", "seekhna",
                "sikhna", "seekho", "sikho", "sikhao", "sikhana", "seekhao", "seekh lo", "sikh lo", "karo", "kar do", "start", "sab kuch", "poora",
                "pura", "complete", "detail mein", "achhe se", "about", "ke bare mein", "ke baare mein", "please",
                "jarvis", "language", "languages", "mujhe", "tum", "tumhe", "apne aap", "khud", "se", "ko", "the", "to",
                "bare mein", "baare mein", "bare me", "bare", "baare", "mein", "me", "ke", "ka", "ki", "padhna",
                "padho", "padh lo", "batao", "bata do", "mujhe batao", "sikhana", "seekhana", "internet", "access",
                "maine kaha hai", "maine kaha", "pura", "sab", "kuch", "karna", "hai", "please"]


NOT_SUBJECT = {"tum", "tumne", "tumhe", "aap", "main", "mai", "mein", "i", "am", "ok", "now", "rahoge", "karoge",
               "band", "bare", "baare", "li", "liya", "sad", "hai", "ho", "kya", "agar", "tab", "bhi", "dun", "do"}


def valid_subject(subject):
    """'python', 'google ads', 'machine learning' theek; 'bare mein', 'i am sad learning javascript' nahi."""
    words = subject.lower().split()
    if not words or len(words) > 5:
        return False
    return not (set(words) & NOT_SUBJECT)


def subject_words(part):
    text = part
    for w in sorted(LEARN_FILLER, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(w)}\b", " ", text)
    return text.split()


def subject_from(cmd):
    """'internet se python learn karna start karo' -> 'python'"""
    parts = re.split(r"\s+(?:aur|and then|and|phir|then|uske baad)\s+", cmd)
    verb = re.compile(r"learn|seekh|sikh|padhna|padho")
    text = next((p for p in parts if verb.search(p) and subject_words(p)), parts[0])
    for w in sorted(LEARN_FILLER, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(w)}\b", " ", text)
    return " ".join(text.split())


def keep_awake(on):
    """Windows: learning chalte waqt system sleep roko (display off ho sakta hai)."""
    import sys
    if sys.platform != "win32":
        return
    import ctypes
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))


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
            state = json.loads(LEARN_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"queue": [], "subjects": {}}
        bad = [q for q in state.get("queue", []) if not valid_subject(q)]     # purana kachra hatao
        if bad:
            state["queue"] = [q for q in state["queue"] if q not in bad]
            for q in bad:
                state.get("subjects", {}).pop(q, None)
        return state

    def _save(self):
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        LEARN_FILE.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")

    def busy(self):
        return self.thread is not None and self.thread.is_alive()

    # ---------- commands ----------
    def notes_count(self, subject):
        return sum(1 for i in self.knowledge.items if i["topic"].startswith(subject + ":"))

    def learnt_subjects(self):
        """Poore seekhe subjects (refresh chal raha ho tab bhi, ya notes memory mein hon)."""
        return [n for n, x in self.state.get("subjects", {}).items()
                if x.get("done_all") or x.get("learnt_once") or self.notes_count(n) >= max(len(x.get("syllabus", [])), 5)]

    def clear_queue(self):
        with self.lock:
            n = len(self.state["queue"])
            self.state["queue"] = []
            self._save()
        self.stop_flag.set()
        return f"Done {config.USER_NAME}, I removed {n} pending subjects. Everything already learnt is still saved."

    def remove(self, subject):
        with self.lock:
            hit = [q for q in self.state["queue"] if subject in q or q in subject]
            self.state["queue"] = [q for q in self.state["queue"] if q not in hit]
            self._save()
        if not hit:
            return f"{config.USER_NAME}, {subject} is not in my learning list."
        return f"Removed {', '.join(hit)} from my learning list, {config.USER_NAME}."

    def start(self, subject):
        s = config.USER_NAME
        subject = subject.strip()
        if not valid_subject(subject):
            return f"{s}, I am not sure what to learn. Say it clearly, for example: learn Python."
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
                if subj.get("done_all"):
                    subj["learnt_once"] = True         # refresh ke dauraan bhi "seekha hua" gina jaye
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
            if subj.get("done_all"):
                state = "complete"
            elif subj.get("learnt_once") or self.notes_count(name) >= max(total, 5):
                state = f"learnt, refreshing {done} of {total} chapters"
            else:
                state = f"{done} of {total} chapters"
            parts.append(f"{name}: {state}")
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
        keep_awake(True)                         # seekhte waqt PC sleep mein na jaye (screen band ho sakti hai)
        try:
            self._work()
        finally:
            keep_awake(False)

    def _work(self):
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
                self._apply_idea(subject)
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
            score = self._quiz_chapter(subject, chapter)
            if score < config.PASS_SCORE:                 # kamzor: aur gehraai se dobara seekho
                self._learn_chapter(subject, chapter, deep=True)
                score = max(score, self._quiz_chapter(subject, chapter))
            with self.lock:
                subj.setdefault("scores", {})[chapter] = score
                subj["done"].append(chapter)
                self._save()
        subj["done_all"] = True
        subj["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        scores = subj.get("scores", {})
        subj["score"] = round(sum(scores.values()) / len(scores)) if scores else None
        self._save()
        return True

    # ---------- seekha hua apne upar lagana ----------
    def _apply_idea(self, subject):
        """Subject seekhne ke baad: is gyaan se JARVIS ka code kaise behtar ho? Idea ideas.json mein (lagana aap approve karte ho)."""
        notes = "\n".join(i["notes"][:500] for i in self.knowledge.items if i["topic"].startswith(subject + ":"))[:4000]
        idea = self.llm(f"You are JARVIS, a Python voice assistant for a Windows PC (voice commands, learning, browser, "
                        f"skills, marketing research). You just learnt '{subject}'. Notes:\n{notes}\n\n"
                        "Suggest ONE small, concrete improvement to your OWN behaviour or code that uses this knowledge "
                        "(one sentence, starting with a verb). If this subject cannot improve you, reply exactly NONE.").strip()
        if not idea or idea.upper().startswith("NONE") or len(idea) > 400:
            return
        ideas = load_ideas()
        ideas.append({"subject": subject, "idea": idea, "status": "pending", "time": datetime.now().strftime("%Y-%m-%d %H:%M")})
        IDEAS_FILE.write_text(json.dumps(ideas[-100:], ensure_ascii=False, indent=1), encoding="utf-8")

    # ---------- self test ----------
    def _quiz_chapter(self, subject, chapter):
        """Notes se 3 sawaal banao, apni knowledge se jawab do, khud grade karo. 0-100."""
        item = next((i for i in self.knowledge.items if i["topic"] == f"{subject}: {chapter}"), None)
        if not item:
            return 0
        try:
            raw = self.llm(f"From these study notes make 3 short quiz questions with their correct answers. Reply ONLY "
                           f'JSON: [{{"q": "...", "a": "..."}}]\n\n{item["notes"][:3000]}')
            qa = json.loads(re.search(r"\[.*\]", raw, re.S).group())[:3]
        except Exception:
            return 50
        scores = []
        for pair in qa:
            q, a = str(pair.get("q", "")), str(pair.get("a", ""))
            if not q:
                continue
            ctx = self.knowledge.context(f"{subject} {q}")
            ans = self.llm(f"Answer in 1-2 sentences using only this knowledge.\n{ctx[:3000]}\n\nQuestion: {q}")
            grade = self.llm(f"Question: {q}\nCorrect answer: {a}\nStudent answer: {ans}\n"
                             f"How correct is the student answer from 0 to 100? Reply with only the number.")
            m = re.search(r"\d+", grade)
            scores.append(min(100, int(m.group())) if m else 50)
        return round(sum(scores) / len(scores)) if scores else 50

    def self_test(self, subject=None):
        """'python ka test do' -> har chapter ka quiz; kamzor chapters background mein dobara seekho."""
        s = config.USER_NAME
        subjects = [subject] if subject in self.state["subjects"] else list(self.state["subjects"])
        if not subjects:
            return f"{s}, I have not learnt any subject yet, so there is nothing to test."
        report, weak_total = [], 0
        for name in subjects:
            subj = self.state["subjects"][name]
            scores = {c: self._quiz_chapter(name, c) for c in subj.get("done", [])}
            subj["scores"] = scores
            weak = [c for c, v in scores.items() if v < config.PASS_SCORE]
            weak_total += len(weak)
            if weak:
                subj["done"] = [c for c in subj["done"] if c not in weak]
                subj["done_all"] = False
                if name not in self.state["queue"]:
                    self.state["queue"].append(name)
            avg = round(sum(scores.values()) / len(scores)) if scores else 0
            subj["score"] = avg
            report.append(f"{name} scored {avg} percent" + (f", weak in {', '.join(weak[:3])}" if weak else ""))
        self._save()
        if weak_total:
            self._run_background()
        tail = " I am re-learning the weak chapters now." if weak_total else " No weak chapters."
        return f"{s}, test done. " + "; ".join(report) + "." + tail

    def _learn_chapter(self, subject, chapter, deep=False):
        from .agent import t_read_webpage
        query = f"{subject} {chapter}" + (" explained with examples" if deep else "")
        texts, sources = [], []
        wiki = internet.wikipedia_summary(query, sentences=6)
        if wiki:
            texts.append(wiki)
        for r in internet.search(query + " tutorial", max_results=5):
            texts.append(r.get("body", ""))
            if r.get("href"):
                sources.append(r["href"])
        for url in sources[:4 if deep else 2]:
            try:
                texts.append(t_read_webpage(url)[:3000])
            except Exception:
                pass
        notes = self.llm(f"Subject: {subject}. Chapter: {chapter}.\nIn sources se is chapter ke clear study notes "
                         f"likho (simple English): main concepts, short examples (code ho to chhota code), aur "
                         f"yaad rakhne wale points. 150-300 words.\n\n" + "\n\n".join(texts)[:9000])
        with self.lock:
            self.knowledge.add(f"{subject}: {chapter}", notes, sources)
