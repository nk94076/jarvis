"""Safe Self-Code-Upgrade: JARVIS apna khud ka code padh kar sudhaar propose karta hai.

"apna code upgrade karo taaki reminders hindi mein bhi samjhe" ->
  1. Relevant files dhoondhna (apna code padhna)
  2. AI se chhote, sateek badlav (find -> replace) likhwana
  3. Poore JARVIS ki ALAG COPY (staging) par badlav lagana + saare tests (selftest --skills)
  4. Fail? error AI ko dikhakar fix -> dobara test (3 baar tak)
  5. Pass -> badlav Notepad mein dikhana, aapse poochna; "yes" par hi asli JARVIS mein lagana
  6. Lagane se pehle backup; "self upgrade undo" = wapas pichla code
Suraksha: security.py, selftest.py, selfcode.py, sandbox.py kabhi nahi badle ja sakte."""
import difflib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from . import config

ROOT = Path(__file__).resolve().parent.parent
WORK = config.DATA_DIR / "selfcode"
PROTECTED = {"jarvis/security.py", "jarvis/selftest.py", "jarvis/selfcode.py", "jarvis/sandbox.py"}
SKIP = {".venv", "__pycache__", "model", ".git", "docs"}


def _code_files():
    return [p for p in ROOT.rglob("*.py") if not (set(p.relative_to(ROOT).parts) & SKIP)]


def _rel(p):
    return str(Path(p).relative_to(ROOT)).replace("\\", "/")


def find_files(request, limit=3):
    """Request se jude files (naam + andar ke shabd)."""
    words = [w for w in re.findall(r"[a-z]{4,}", request.lower())
             if w not in {"apna", "code", "upgrade", "karo", "taaki", "improve", "better", "khud", "your", "make", "that"}]
    scored = []
    for p in _code_files():
        if _rel(p) in PROTECTED:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore").lower()
        score = sum(text.count(w) for w in words) + 20 * sum(w in p.stem for w in words)
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]] or [ROOT / "jarvis" / "skills.py"]


def _staging():
    stage = WORK / "staging"
    if stage.exists():
        shutil.rmtree(stage, ignore_errors=True)
    shutil.copytree(ROOT, stage, ignore=shutil.ignore_patterns(*SKIP))
    return stage


def _apply(edits, base):
    """edits = [{"file": "jarvis/x.py", "find": "...", "replace": "..."}] ko base folder par lagao."""
    changed = {}
    for e in edits:
        rel = str(e.get("file", "")).replace("\\", "/").lstrip("./")
        if rel in PROTECTED or not rel.endswith(".py"):
            raise ValueError(f"not allowed to change {rel}")
        path = base / rel
        if not path.exists() or ".." in rel:
            raise ValueError(f"file not found: {rel}")
        text = changed.get(rel, path.read_text(encoding="utf-8"))
        find = e.get("find", "")
        if not find or text.count(find) != 1:
            raise ValueError(f"the 'find' text must appear exactly once in {rel}")
        changed[rel] = text.replace(find, e.get("replace", ""), 1)
    for rel, text in changed.items():
        (base / rel).write_text(text, encoding="utf-8")
    return list(changed)


def _test(stage):
    r = subprocess.run([sys.executable, "-m", "jarvis.selftest", "--skills"], cwd=stage, capture_output=True,
                       text=True, timeout=300)
    return r.returncode == 0, (r.stdout + r.stderr)[-1500:]


class SelfCoder:
    def __init__(self, llm, confirm, progress=print):
        self.llm, self.confirm, self.progress = llm, confirm, progress

    def propose(self, request, research=""):
        s = config.USER_NAME
        files = find_files(request)
        code = ""
        for p in files:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            code += f"\n===== FILE {_rel(p)} =====\n" + "\n".join(lines[:700])
        prompt = (f"You are improving the Python source code of JARVIS (a voice assistant) itself.\n"
                  f"Improvement requested: {request}\n" + (f"Useful knowledge:\n{research[:2500]}\n" if research else "")
                  + f"Relevant code:{code[:14000]}\n\n"
                  "Make the SMALLEST safe change that achieves it. Do not remove features. Keep the code style.\n"
                  'Reply ONLY JSON: {"summary": "one line", "edits": [{"file": "jarvis/...py", '
                  '"find": "exact existing code (unique, a few full lines)", "replace": "new code"}]}')
        last_error = ""
        for attempt in range(1, 4):
            self.progress(f"self-code: attempt {attempt}")
            ask = prompt if attempt == 1 else prompt + f"\n\nYour previous change failed:\n{last_error}\nFix it."
            m = re.search(r"\{.*\}", self.llm(ask), re.S)
            try:
                plan = json.loads(m.group()) if m else {}
            except ValueError:
                plan = {}
            edits = plan.get("edits") or []
            if not edits:
                last_error = "No valid JSON edits were given."
                continue
            stage = _staging()
            try:
                touched = _apply(edits, stage)
            except ValueError as e:
                last_error = str(e)
                continue
            ok, out = _test(stage)
            if not ok:
                last_error = "Tests failed:\n" + out
                continue
            return self._review_and_apply(plan.get("summary", request), touched, stage)
        from . import selfimprove
        selfimprove.add_lesson(f"self code upgrade: {request}", f"Could not make a passing change: {last_error[:200]}")
        return f"Sorry {s}, I tried 3 times but could not make a change that passes all my tests, so I changed nothing."

    def _review_and_apply(self, summary, touched, stage):
        s = config.USER_NAME
        diff = []
        for rel in touched:
            old = (ROOT / rel).read_text(encoding="utf-8").splitlines(keepends=True)
            new = (stage / rel).read_text(encoding="utf-8").splitlines(keepends=True)
            diff += difflib.unified_diff(old, new, f"current/{rel}", f"proposed/{rel}")
        WORK.mkdir(parents=True, exist_ok=True)
        dfile = WORK / f"proposal_{datetime.now():%Y-%m-%d_%H-%M-%S}.diff"
        dfile.write_text(f"# {summary}\n# Tests: PASSED\n\n" + "".join(diff), encoding="utf-8")
        if sys.platform == "win32":
            subprocess.Popen(["notepad", str(dfile)])
        added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
        removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
        if not self.confirm(f"{s}, my code change passed all tests. {summary}. It changes {len(touched)} file, "
                            f"{added} lines added and {removed} removed. I opened it in Notepad. Should I apply it?"):
            return f"Okay {s}, I did not change my code. The proposal is saved in JARVIS Data, selfcode."
        backup = WORK / "backups" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        for rel in touched:
            (backup / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, backup / rel)
            shutil.copy2(stage / rel, ROOT / rel)
        (backup / "summary.txt").write_text(summary, encoding="utf-8")
        from . import selfimprove
        selfimprove.record(f"self code upgrade: {summary}", "applied")
        return (f"Done {s}. I upgraded my own code: {summary}. Please restart me to use it. If anything goes wrong, "
                f"say: self upgrade undo.")


def undo():
    s = config.USER_NAME
    root = WORK / "backups"
    backups = sorted(root.iterdir()) if root.exists() else []
    if not backups:
        return f"{s}, there is no self upgrade to undo."
    last = backups[-1]
    for f in last.rglob("*.py"):
        shutil.copy2(f, ROOT / f.relative_to(last))
    shutil.rmtree(last)
    return f"Done {s}. I restored my code from before the last self upgrade. Please restart me."
