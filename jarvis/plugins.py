"""Skill Builder: JARVIS khud nayi skills (plugins) likhta, test karta aur sambhalta hai.

"ek skill banao jo bitcoin ka price bataye" ->
  1. AI plugin code likhta hai (NAME, DESCRIPTION, TRIGGERS, run(cmd), TESTS)
  2. Safety scan: delete/format/registry jaisa khatarnaak code ho to aapse poochta hai
  3. Sandbox: alag Python process, temp folder, time limit, TESTS chalata hai
  4. Fail? Error AI ko wapas deta hai -> fix -> dobara test (3 baar tak)
  5. Pass -> JARVIS Data/skills/<name>/v1.py, enable. Har improvement = naya version, rollback ho sakta hai
Core JARVIS code kabhi nahi badalta; plugins alag files hain aur alag process mein chalte hain."""
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from . import config

SKILLS_DIR = config.DATA_DIR / "skills"
RISKY = ["shutil.rmtree", "os.remove", "os.unlink", "os.rmdir", "rmdir", "subprocess", "os.system", "ctypes",
         "winreg", "format c", "del /", "rm -rf", "eval(", "exec(", "__import__", "keyboard", "pynput", "smtplib",
         "shutdown", "os.kill", "Path.unlink", ".unlink(", "send2trash"]
TEMPLATE = '''NAME = "short_snake_case_name"
DESCRIPTION = "one line: what this skill does"
TRIGGERS = ["phrase the user will say", "hinglish phrase too"]   # lowercase words/phrases

def run(cmd: str) -> str:
    """cmd = what the user said (lowercase). Return a short spoken reply in Indian English."""
    ...

TESTS = [("example user command", "text expected somewhere in the reply, or empty string")]'''

RUNNER = r'''
import importlib.util, json, sys, traceback, signal
spec = importlib.util.spec_from_file_location("plugin", sys.argv[1])
out = {"ok": False}
try:
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    if sys.argv[2] == "test":
        for name in ("NAME", "DESCRIPTION", "TRIGGERS", "run", "TESTS"):
            assert hasattr(m, name), f"missing {name}"
        assert isinstance(m.TRIGGERS, list) and m.TRIGGERS, "TRIGGERS must be a non-empty list"
        results = []
        for cmd, expect in m.TESTS[:5]:
            r = str(m.run(cmd))
            passed = bool(r.strip()) and (not expect or expect.lower() in r.lower())
            results.append({"cmd": cmd, "reply": r[:300], "expect": expect, "passed": passed})
        out = {"ok": all(x["passed"] for x in results) and bool(results), "results": results,
               "meta": {"name": m.NAME, "description": m.DESCRIPTION, "triggers": [t.lower() for t in m.TRIGGERS]}}
    else:
        out = {"ok": True, "reply": str(m.run(sys.argv[3]))}
except Exception:
    out = {"ok": False, "error": traceback.format_exc()[-1500:]}
print("@@RESULT@@" + json.dumps(out))
'''


def _sandbox(path, mode, cmd="", timeout=30):
    """Plugin ko alag Python process mein, temp folder mein, time limit ke saath chalao."""
    from . import sandbox
    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(tmp) / "runner.py"
        runner.write_text(RUNNER, encoding="utf-8")
        code, out = sandbox.run([sys.executable, str(runner), str(path), mode, cmd], cwd=tmp, timeout=timeout)
    m = re.search(r"@@RESULT@@(.*)", out)
    if not m:
        return {"ok": False, "error": out[-1500:] or "no output"}
    return json.loads(m.group(1))


def _extract_code(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


class PluginManager:
    def __init__(self, llm):
        self.llm = llm
        self.confirm = lambda q: False
        self.progress = lambda t: None
        self.on_change = lambda: None            # Tool Registry sync
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- store ----------
    def _meta_path(self, name):
        return SKILLS_DIR / name / "meta.json"

    def _meta(self, name):
        try:
            return json.loads(self._meta_path(name).read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save_meta(self, meta):
        self._meta_path(meta["name"]).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    def list(self):
        out = []
        for d in sorted(SKILLS_DIR.iterdir()) if SKILLS_DIR.exists() else []:
            m = self._meta(d.name)
            if m:
                out.append(m)
        return out

    def find(self, text):
        text = text.lower().replace(" ", "_")
        for m in self.list():
            if m["name"] in text or text in m["name"]:
                return m
        return None

    # ---------- banana / sudharna ----------
    def _write_and_test(self, request, base_code=None, feedback=""):
        """AI se code likhwao -> safety -> sandbox test -> fail ho to fix (3 baar). (code, result) ya (None, error)."""
        if base_code:
            prompt = (f"Improve this JARVIS skill plugin. Change requested: {feedback}\nKeep the same format.\n\n"
                      f"```python\n{base_code}\n```\nReply with ONLY the full python code.")
        else:
            prompt = (f"Write a JARVIS skill plugin in Python for this request: {request}\n"
                      f"Rules: Python standard library + 'requests' + 'webbrowser' only. No API keys. "
                      f"Handle errors and always return a short friendly string. Use free public endpoints "
                      f"without keys if internet data is needed. Keep it under 80 lines.\n"
                      f"Use EXACTLY this format:\n```python\n{TEMPLATE}\n```\nReply with ONLY the python code.")
        last_error = ""
        for attempt in range(1, 4):
            self.progress(f"skill builder: attempt {attempt}")
            ask = prompt if attempt == 1 else (prompt + f"\n\nYour previous code failed with this error, fix it:\n"
                                                        f"{last_error}\n\nPrevious code:\n```python\n{code}\n```")
            code = _extract_code(self.llm(ask))
            risky = [r for r in RISKY if r.lower() in code.lower()]
            if risky and not self.confirm(f"{config.USER_NAME}, this new skill uses risky things: "
                                          f"{', '.join(risky[:3])}. Should I allow it?"):
                return None, "You did not allow the risky code, so I stopped."
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(code)
            result = _sandbox(f.name, "test")
            Path(f.name).unlink(missing_ok=True)
            if result.get("ok"):
                return code, result
            last_error = result.get("error") or json.dumps(result.get("results", []), ensure_ascii=False)[:1500]
        return None, last_error

    def create(self, request):
        s = config.USER_NAME
        code, result = self._write_and_test(request)
        if not code and str(result).startswith("You did not allow"):
            return f"Okay {s}. {result}"
        if not code:
            from . import selfimprove
            selfimprove.record(f"build skill: {request}", "", ok=False, error=f"skill build failed: {result}")
            return (f"Sorry {s}, I tried 3 times but could not build a working skill for that. "
                    f"I have saved the error in my failure memory.")
        meta = result["meta"]
        name = re.sub(r"[^a-z0-9_]", "", meta["name"].lower())[:40] or "skill"
        if self._meta(name):
            name = f"{name}_{datetime.now():%H%M%S}"
        folder = SKILLS_DIR / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "v1.py").write_text(code, encoding="utf-8")
        self._save_meta({"name": name, "description": meta["description"], "triggers": meta["triggers"],
                         "version": 1, "versions": [1], "enabled": True, "request": request,
                         "created": datetime.now().strftime("%Y-%m-%d %H:%M"), "uses": 0, "fails": 0})
        from . import versioning
        versioning.commit(f"new skill {name}: {request[:60]}")
        self.on_change()
        example = meta["triggers"][0]
        return (f"{s}, I have built and tested a new skill called {name.replace('_', ' ')}. All tests passed. "
                f"Try saying: {example}.")

    def improve(self, name, feedback):
        s = config.USER_NAME
        meta = self.find(name)
        if not meta:
            return f"{s}, I could not find a skill named {name}."
        from . import versioning
        base = (SKILLS_DIR / meta["name"] / f"v{meta['version']}.py").read_text(encoding="utf-8")
        branch = versioning.start_branch(meta["name"])        # sudhaar alag branch par
        code, result = self._write_and_test(meta["request"], base_code=base, feedback=feedback or "make it better")
        if not code:
            versioning.finish_branch(branch, keep=False)
            return f"Sorry {s}, the improved version failed its tests, so I kept version {meta['version']}."
        v = max(meta["versions"]) + 1
        (SKILLS_DIR / meta["name"] / f"v{v}.py").write_text(code, encoding="utf-8")
        meta.update(version=v, versions=meta["versions"] + [v], triggers=result["meta"]["triggers"])
        self._save_meta(meta)
        versioning.finish_branch(branch, keep=True)
        self.on_change()
        return f"{s}, {meta['name'].replace('_', ' ')} is upgraded to version {v} and all tests passed."

    def rollback(self, name):
        meta = self.find(name)
        if not meta or len(meta["versions"]) < 2 or meta["version"] == min(meta["versions"]):
            return f"{config.USER_NAME}, there is no older version to go back to."
        older = [v for v in meta["versions"] if v < meta["version"]]
        meta["version"] = max(older)
        self._save_meta(meta)
        return f"Done {config.USER_NAME}, {meta['name'].replace('_', ' ')} is back to version {meta['version']}."

    def set_enabled(self, name, on):
        meta = self.find(name)
        if not meta:
            return f"{config.USER_NAME}, I could not find that skill."
        meta["enabled"] = on
        self._save_meta(meta)
        return f"{meta['name'].replace('_', ' ')} is {'enabled' if on else 'disabled'}, {config.USER_NAME}."

    def run_all_tests(self):
        """Regression: har enabled skill ke apne TESTS sandbox mein. [(name, ok, error)]"""
        out = []
        for meta in self.list():
            if meta.get("enabled"):
                res = _sandbox(SKILLS_DIR / meta["name"] / f"v{meta['version']}.py", "test")
                out.append((meta["name"], bool(res.get("ok")), res.get("error") or ""))
        return out

    def describe(self):
        items = self.list()
        if not items:
            return f"{config.USER_NAME}, I have not built any custom skills yet. Say: ek skill banao jo ..."
        return f"{config.USER_NAME}, I have built {len(items)} skills: " + "; ".join(
            f"{m['name'].replace('_', ' ')} version {m['version']}{'' if m['enabled'] else ' (disabled)'}" for m in items) + "."

    # ---------- chalana ----------
    def match(self, cmd):
        """Kisi plugin ka trigger cmd mein hai? Sandbox mein chala kar jawab. Nahi to None."""
        for meta in self.list():
            if meta["enabled"] and any(t and t in cmd for t in meta["triggers"]):
                path = SKILLS_DIR / meta["name"] / f"v{meta['version']}.py"
                res = _sandbox(path, "run", cmd)
                meta["uses"] = meta.get("uses", 0) + 1
                if not res.get("ok"):
                    meta["fails"] = meta.get("fails", 0) + 1
                    self._save_meta(meta)
                    from . import selfimprove
                    selfimprove.record(cmd, "", ok=False, error=f"skill {meta['name']}: {res.get('error', '')[-200:]}")
                    return (f"Sorry {config.USER_NAME}, my {meta['name'].replace('_', ' ')} skill failed. "
                            f"Say 'improve skill {meta['name'].replace('_', ' ')}' and I will fix it.")
                self._save_meta(meta)
                return res["reply"]
        return None
