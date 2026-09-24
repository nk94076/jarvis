"""Intent/Goal Engine + Agent Orchestrator + Self-Evaluation.

Bada kaam ("research karo, uski landing page banao aur usko test karo") ek GOAL banta hai:
  1. PLAN: AI goal ko 2-6 steps mein todta hai, har step ko ek specialised agent milta hai
     (research, coder, browser, files, pc, web, skills, general). Pichhli galtiyon ke sabak plan mein jaate hain.
  2. EXECUTE: har step us agent ke tools ke saath chalta hai (Tool Registry se)
  3. EVALUATE: har step ka nateeja AI judge se jaancha jata hai; fail ho to feedback ke saath 1 baar dobara
  4. REPORT: goal ka final nateeja + score; galti hui to Failure Memory mein sabak
Goals JARVIS Data/goals.json mein save hote hain ("goals dikhao", "last goal ka status")."""
import json
import re
from datetime import datetime

from . import config, selfimprove

GOALS_FILE = config.DATA_DIR / "goals.json"
AGENTS = {
    "research": "internet research, reading webpages, deep research reports",
    "coder": "writing/running code, terminal commands, git, code review, project checks",
    "browser": "opening websites and controlling the browser",
    "files": "listing, reading, writing, moving, organising files and PDFs",
    "pc": "reading the screen, clicking, typing, keyboard shortcuts, any JARVIS command (apps, volume, etc.)",
    "web": "building landing pages / websites",
    "skills": "custom skills JARVIS has built",
    "general": "anything else (all tools)",
}
MULTI = re.compile(r"\b(aur phir|phir|uske baad|and then|then|after that|aur usko|aur uska|aur use|step by step|"
                   r"poora kaam|end to end)\b")


def is_goal(cmd):
    """Kai alag kaam ek ke baad ek? ("research karo, phir landing page banao aur test karo")"""
    if not MULTI.search(cmd):
        return False
    verbs = set(re.findall(r"\b(banao|bana do|likho|kholo|bhejo|test|check|research|find|dhundo|create|make|build|"
                           r"write|open|send|analy[sz]e|fix|summari[sz]e|save|padho|compare|deploy|download|upload)\b", cmd))
    return len(verbs) >= 2


def _json(text, default):
    m = re.search(r"[\[{].*[\]}]", text, re.S)
    try:
        return json.loads(m.group()) if m else default
    except ValueError:
        return default


class Orchestrator:
    def __init__(self, agent, llm):
        self.agent = agent                   # agent.Agent (tools chalata hai)
        self.llm = llm
        self.progress = lambda t: None

    # ---------- store ----------
    def _load(self):
        try:
            return json.loads(GOALS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, goals):
        GOALS_FILE.write_text(json.dumps(goals[-100:], ensure_ascii=False, indent=1), encoding="utf-8")

    def describe(self):
        goals = self._load()
        if not goals:
            return f"{config.USER_NAME}, I have not worked on any big goals yet."
        g = goals[-1]
        done = sum(1 for st in g["steps"] if st.get("passed"))
        return (f"{config.USER_NAME}, my last goal was: {g['goal']}. Status {g['status']}, {done} of {len(g['steps'])} "
                f"steps passed, score {g.get('score', '-')}. I have worked on {len(goals)} goals in total.")

    # ---------- plan ----------
    def plan(self, goal):
        lessons = selfimprove.lessons_for(goal)
        agents = "\n".join(f"- {k}: {v}" for k, v in AGENTS.items())
        raw = self.llm(
            f"You are the planner of JARVIS, a PC assistant. Break this goal into 2 to 6 concrete steps.\n"
            f"Goal: {goal}\nAvailable agents:\n{agents}\n"
            + (f"Lessons from past mistakes (follow them):\n- " + "\n- ".join(lessons) + "\n" if lessons else "")
            + 'Reply ONLY JSON: [{"agent": "research", "task": "...", "done_when": "..."}]')
        steps = [s for s in _json(raw, []) if isinstance(s, dict) and s.get("task")]
        for s in steps:
            if s.get("agent") not in AGENTS:
                s["agent"] = "general"
        return steps[:6] or [{"agent": "general", "task": goal, "done_when": "the goal is achieved"}]

    # ---------- evaluate ----------
    def evaluate(self, task, done_when, result):
        raw = self.llm(f"Task: {task}\nSuccess means: {done_when}\nResult: {result[:2500]}\n"
                       'Did the result achieve the task? Reply ONLY JSON: {"passed": true/false, "score": 0-100, '
                       '"reason": "short"}')
        v = _json(raw, {})
        score = int(v.get("score", 50)) if str(v.get("score", "")).isdigit() else 50
        passed = bool(v.get("passed", score >= 60)) and not result.startswith(("ERROR", "USER DENIED"))
        return passed, score, str(v.get("reason", ""))[:200]

    # ---------- run ----------
    def run(self, goal):
        from .agent import CATEGORIES, TOOLS
        s = config.USER_NAME
        record = {"goal": goal, "started": datetime.now().strftime("%Y-%m-%d %H:%M"), "status": "running", "steps": []}
        goals = self._load() + [record]
        self._save(goals)
        steps = self.plan(goal)
        self.progress(f"goal: {len(steps)} steps")
        context = ""
        for i, st in enumerate(steps, 1):
            if self.agent.stop is not None and self.agent.stop.is_set():
                record["status"] = "stopped"
                break
            tools = None if st["agent"] in ("general", "skills") and not CATEGORIES.get(st["agent"]) \
                else set(CATEGORIES.get(st["agent"], [])) | {"run_jarvis_command"}
            if tools is not None:
                tools &= set(TOOLS)
            self.progress(f"step {i}/{len(steps)} [{st['agent']}] {st['task'][:40]}")
            task = st["task"] + (f"\nResults of earlier steps:\n{context[-2000:]}" if context else "")
            result = self.agent.run(task, tools)
            passed, score, reason = self.evaluate(st["task"], st.get("done_when", ""), result)
            if not passed:                                # self-debugging: feedback ke saath ek aur koshish
                self.progress(f"step {i} retry: {reason[:40]}")
                result = self.agent.run(f"{task}\nYour previous attempt was not good enough because: {reason}. "
                                        f"Try a different approach.", tools)
                passed, score, reason = self.evaluate(st["task"], st.get("done_when", ""), result)
                if not passed:
                    selfimprove.add_lesson(st["task"], f"Step failed ({reason}). Next time plan it differently "
                                                       f"or use another agent than {st['agent']}.")
            record["steps"].append({**st, "result": result[:500], "passed": passed, "score": score, "reason": reason})
            context += f"\nStep {i} ({st['task']}): {result[:600]}"
            self._save(goals)
        scores = [x["score"] for x in record["steps"]]
        record["score"] = round(sum(scores) / len(scores)) if scores else 0
        if record["status"] == "running":
            record["status"] = "done" if all(x["passed"] for x in record["steps"]) else "partly done"
        record["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._save(goals)
        selfimprove.record(f"goal: {goal}", record["status"], ok=record["status"] == "done")
        summary = self.llm(f"Goal: {goal}\nStep results:\n{context[-3000:]}\n"
                           f"Give a 2-3 sentence spoken summary of what was done (Indian English, no markdown).")
        failed = [x["task"] for x in record["steps"] if not x["passed"]]
        tail = f" These steps did not fully work: {'; '.join(failed)[:200]}." if failed else ""
        return f"{s}, goal {record['status']} with a score of {record['score']}. {summary}{tail}"
