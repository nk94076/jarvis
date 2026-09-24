"""Self-Upgrade Engine: JARVIS apni kamiyan (capability gaps) khud dhoondh kar door karta hai.

"apni kamiyan door karo" / "self upgrade engine chalao":
  1. Gap analysis: jo kaam aapne maange par JARVIS nahi kar paya (Failure Memory se)
  2. Har gap ke liye aapse poochta hai -> Skill Builder se nayi skill (research -> code -> sandbox test -> fix loop)
  3. Git branch par banti hai; poore JARVIS ka Regression Test chalta hai
  4. Test pass -> skill rakhi (merge); fail -> skill band + branch hata do (rollback)
Core JARVIS code nahi badalta; sirf plugin skills."""
import json
from collections import Counter

from . import config, selfimprove, versioning


def gaps(limit=3):
    d, _ = selfimprove.summary()
    counts = Counter(g["cmd"].strip().lower() for g in d["gaps"][-150:])
    return [cmd for cmd, _ in counts.most_common(limit)]


def run(plugins, confirm, progress=print):
    s = config.USER_NAME
    todo = gaps()
    if not todo:
        return f"{s}, I have no recorded missing capabilities right now. When I fail at something you ask, I will remember it."
    built, skipped, failed = [], [], []
    for req in todo:
        if not confirm(f"{s}, you asked me '{req}' and I could not do it. Should I build a skill for it?"):
            skipped.append(req)
            continue
        branch = versioning.start_branch("upgrade")
        progress(f"self-upgrade: building '{req[:40]}'")
        before = {m["name"] for m in plugins.list()}
        reply = plugins.create(req)
        new = [m for m in plugins.list() if m["name"] not in before]
        ok = bool(new) and regression_ok()
        if not ok and new:
            for m in new:
                plugins.set_enabled(m["name"], False)
        versioning.finish_branch(branch, keep=ok)
        (built if ok else failed).append(req)
        if ok:
            _clear_gap(req)
        else:
            selfimprove.add_lesson(req, f"Self-upgrade could not build a working skill: {reply[:150]}")
    parts = []
    if built:
        parts.append(f"I built and tested new skills for: {', '.join(built)}")
    if failed:
        parts.append(f"I could not build: {', '.join(failed)}")
    if skipped:
        parts.append(f"skipped: {', '.join(skipped)}")
    return f"{s}, self-upgrade finished. " + "; ".join(parts) + "."


def regression_ok():
    """Poore JARVIS ka regression test (jarvis.selftest) alag process mein."""
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-m", "jarvis.selftest", "--skills"], cwd=root, capture_output=True, text=True, timeout=300)
    return r.returncode == 0


def _clear_gap(cmd):
    d, _ = selfimprove.summary()
    d["gaps"] = [g for g in d["gaps"] if g["cmd"].strip().lower() != cmd]
    selfimprove.STATS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
