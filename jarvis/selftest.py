"""Regression test: update ke baad check karo ki purane features chal rahe hain.
Chalao: python -m jarvis.selftest   (exit code 0 = sab theek)"""
import compileall
import importlib
import os
import sys
from pathlib import Path

os.environ["JARVIS_SELFTEST"] = "1"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CHECKS = [("what is the time", "time is"), ("calculate 25 into 4", "100"), ("kal kaun sa din hai", "tomorrow"),
          ("what can you do", "open"), ("toss a coin", "it is"), ("15 percent of 200", "30")]


def main():
    failed = []
    if not compileall.compile_dir(str(ROOT / "jarvis"), quiet=1) or not compileall.compile_file(str(ROOT / "main.py"), quiet=1):
        failed.append("syntax error in code")
    for mod in ["config", "brain", "knowledge", "learner", "skills", "skills_extra", "agent", "pc", "builder",
                "plugins", "selfimprove", "audit", "internet", "voice"]:
        try:
            importlib.import_module(f"jarvis.{mod}")
        except Exception as e:
            failed.append(f"import jarvis.{mod}: {type(e).__name__}: {e}")
    if not failed:
        from jarvis import agent, skills
        from jarvis.brain import Brain
        from jarvis.knowledge import Knowledge
        agent.llm = lambda prompt, model=None: "ok"
        Brain._chat = lambda self, messages: "ok"
        b = Brain()
        s = skills.Skills(b, Knowledge(b))
        for cmd, expect in CHECKS:
            try:
                out = s.handle(cmd) or ""
                if expect.lower() not in out.lower():
                    failed.append(f"'{cmd}' -> '{out[:80]}' (expected '{expect}')")
            except Exception as e:
                failed.append(f"'{cmd}' crashed: {type(e).__name__}: {e}")
    if failed:
        print("SELFTEST FAILED:")
        for f in failed:
            print("  -", f)
        return 1
    print(f"SELFTEST OK: {len(CHECKS)} feature checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
