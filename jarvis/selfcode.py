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
            return self._review_and_apply(plan.get("summary", request), touched, stage, edits)
        from . import selfimprove
        selfimprove.add_lesson(f"self code upgrade: {request}", f"Could not make a passing change: {last_error[:200]}")
        return f"Sorry {s}, I tried 3 times but could not make a change that passes all my tests, so I changed nothing."

    def _review_and_apply(self, summary, touched, stage, edits=()):
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
        save_patch(summary, edits, backup.name)
        try:
            share_to_github(quiet=True)                   # developer ko automatic dikhe (token ho to)
        except Exception as e:
            print(f"[selfcode] GitHub par share nahi hua: {e}")
        from . import selfimprove
        selfimprove.record(f"self code upgrade: {summary}", "applied")
        return (f"Done {s}. I upgraded my own code: {summary}. Please restart me to use it. If anything goes wrong, "
                f"say: self upgrade undo.")


PATCHES = WORK / "patches.json"


def load_patches():
    try:
        return json.loads(PATCHES.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_patch(summary, edits, backup_name):
    """Har laga hua sudhaar patch ki tarah save: update ke baad dobara lagane ke liye."""
    WORK.mkdir(parents=True, exist_ok=True)
    items = load_patches() + [{"summary": summary, "edits": list(edits), "backup": backup_name,
                               "time": datetime.now().strftime("%Y-%m-%d %H:%M")}]
    PATCHES.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def reapply_all():
    """update.bat ke baad: JARVIS ke apne sudhaar naye code par dobara. (applied, already, conflicts)"""
    applied, already, conflicts = [], [], []
    for p in load_patches():
        ok_all, todo = True, []
        for e in p["edits"]:
            rel = str(e.get("file", "")).replace("\\", "/")
            path = ROOT / rel
            if rel in PROTECTED or not path.exists():
                ok_all = False
                break
            text = path.read_text(encoding="utf-8")
            if e.get("replace") and e["replace"] in text:
                continue                               # pehle se laga hua
            if text.count(e.get("find", "")) != 1:
                ok_all = False                         # mera naya code wahi hissa badal chuka: takraav
                break
            todo.append((path, e))
        if not ok_all:
            conflicts.append(p["summary"])
            continue
        if not todo:
            already.append(p["summary"])
            continue
        for path, e in todo:
            path.write_text(path.read_text(encoding="utf-8").replace(e["find"], e["replace"], 1), encoding="utf-8")
        applied.append(p["summary"])
    return applied, already, conflicts


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
    items = [p for p in load_patches() if p.get("backup") != last.name]   # undo kiya patch dobara na lage
    PATCHES.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"Done {s}. I restored my code from before the last self upgrade. Please restart me."


if __name__ == "__main__":                            # update.bat: python -m jarvis.selfcode --reapply
    if "--reapply" in sys.argv:
        a, al, c = reapply_all()
        print(f"   JARVIS ke apne sudhaar: {len(a)} dobara lagaye, {len(al)} pehle se the, {len(c)} takraaye (chhode)")
        for x in c:
            print("     chhoda (naye code se takraav):", x)


# ======================= Developer ke saath sharing =======================
SHARE_BRANCH = "jarvis-self-upgrades"
SHARE_PATH = "self_patches/patches.json"


def export_patches():
    """Saare self-upgrades ek readable file mein (developer ko bhejne ke liye)."""
    s = config.USER_NAME
    items = load_patches()
    if not items:
        return f"{s}, I have not made any code changes to myself yet, so there is nothing to export."
    out_dir = Path.home() / "Documents" / "JARVIS Reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    md = [f"# JARVIS self-upgrades (version {config.VERSION}, {datetime.now():%Y-%m-%d %H:%M})\n"]
    for i, p in enumerate(items, 1):
        md.append(f"## {i}. {p['summary']}  ({p['time']})")
        for e in p["edits"]:
            md.append(f"File: `{e.get('file')}`\n```diff")
            md += [f"- {ln}" for ln in str(e.get("find", "")).splitlines()]
            md += [f"+ {ln}" for ln in str(e.get("replace", "")).splitlines()]
            md.append("```")
    md.append("\n<details><summary>patches.json</summary>\n\n```json\n" + json.dumps(items, ensure_ascii=False, indent=1)
              + "\n```\n</details>")
    path = out_dir / "jarvis_self_changes.md"
    path.write_text("\n".join(md), encoding="utf-8")
    if sys.platform == "win32":
        subprocess.Popen(["notepad", str(path)])
    return (f"{s}, I exported {len(items)} self-upgrades to Documents, JARVIS Reports, jarvis_self_changes.md. "
            f"You can send this file to the developer.")


def share_to_github(quiet=False):
    """patches.json ko GitHub repo ki alag branch par bhejo, taaki developer naya code push karne se pehle dekh sake."""
    import base64
    s = config.USER_NAME
    token, repo = getattr(config, "GITHUB_TOKEN", ""), getattr(config, "JARVIS_REPO", "")
    if not (token and repo):
        return None if quiet else (f"{s}, to share my changes automatically, add GITHUB_TOKEN in my_settings.py. "
                                   f"Or say: apne badlav export karo.")
    import requests
    api = f"https://api.github.com/repos/{repo}"
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    ref = requests.get(f"{api}/git/ref/heads/{SHARE_BRANCH}", headers=h, timeout=20)
    if ref.status_code == 404:                           # branch pehli baar banao
        base = requests.get(f"{api}/git/ref/heads/{config.JARVIS_BASE_BRANCH}", headers=h, timeout=20)
        base.raise_for_status()
        requests.post(f"{api}/git/refs", headers=h, timeout=20, json={
            "ref": f"refs/heads/{SHARE_BRANCH}", "sha": base.json()["object"]["sha"]}).raise_for_status()
    cur = requests.get(f"{api}/contents/{SHARE_PATH}", headers=h, params={"ref": SHARE_BRANCH}, timeout=20)
    body = {"message": f"JARVIS self-upgrades ({len(load_patches())} patches, v{config.VERSION})",
            "content": base64.b64encode(json.dumps(load_patches(), ensure_ascii=False, indent=1).encode()).decode(),
            "branch": SHARE_BRANCH}
    if cur.status_code == 200:
        body["sha"] = cur.json()["sha"]
    requests.put(f"{api}/contents/{SHARE_PATH}", headers=h, json=body, timeout=30).raise_for_status()
    return f"{s}, I shared my {len(load_patches())} self-upgrades on GitHub branch {SHARE_BRANCH} for the developer."
