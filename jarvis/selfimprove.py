"""Self-Improvement: har command ka record, failure memory, capability gaps, suggestions aur dashboard.

- record(cmd, reply, ok, error): har command ke baad
- Gap: jab user ne koi KAAM maanga (action verb) par koi skill nahi mili aur baat AI chat tak gayi
- suggestions(): sabse zyada fail/gap wale kaam -> "ye seekhna/banana chahiye"
- dashboard(): Learning + skills + metrics ka HTML page, browser mein"""
import html
import json
import os
import webbrowser
from collections import Counter
from datetime import datetime

from . import config

STATS_FILE = config.DATA_DIR / "stats.json"
DASHBOARD = config.DATA_DIR / "dashboard.html"


def _load():
    try:
        return json.loads(STATS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"total": 0, "ok": 0, "failed": 0, "failures": [], "gaps": [], "by_day": {}}


def _save(d):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def record(cmd, reply, ok=True, error=None, gap=False):
    if os.environ.get("JARVIS_SELFTEST"):
        return
    d = _load()
    d["total"] += 1
    d["ok" if ok and not gap else "failed"] += 1
    day = datetime.now().strftime("%Y-%m-%d")
    d["by_day"][day] = d["by_day"].get(day, 0) + 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if error:
        d["failures"] = (d["failures"] + [{"time": now, "cmd": cmd, "error": str(error)[:300]}])[-200:]
    if gap:
        d["gaps"] = (d["gaps"] + [{"time": now, "cmd": cmd, "reply": str(reply)[:200]}])[-200:]
    _save(d)


def looks_like_gap(cmd, reply):
    """Action maanga tha par jawab 'nahi kar sakta' type ka?"""
    r = str(reply).lower()
    return any(p in r for p in ["i can't", "i cannot", "i am not able", "i'm not able", "not able to", "unable to",
                                "i don't have the ability", "not sure", "have not learnt", "not a task i can"])


def suggestions(limit=5):
    d = _load()
    s = config.USER_NAME
    gaps = Counter(" ".join(g["cmd"].split()[:4]) for g in d["gaps"][-100:])
    fails = Counter(f["error"].split(":")[0] for f in d["failures"][-100:])
    out = []
    for cmd, n in gaps.most_common(limit):
        out.append(f"you asked '{cmd}' {n} time{'s' if n > 1 else ''} and I could not do it; I can build a skill for it")
    for err, n in fails.most_common(2):
        out.append(f"the error '{err}' happened {n} times")
    if not out:
        return f"{s}, I have no failures or missing skills recorded yet. Everything is working fine."
    return f"{s}, here is what I should improve: " + "; ".join(out) + ". Say 'ek skill banao jo ...' to build one."


def summary():
    d = _load()
    rate = 100 * d["ok"] / d["total"] if d["total"] else 100
    return d, rate


def dashboard(learner=None, knowledge=None, plugins=None, open_browser=True):
    d, rate = summary()
    e = html.escape
    rows_learn = ""
    if learner:
        for name, subj in learner.state.get("subjects", {}).items():
            total, done = len(subj.get("syllabus", [])), len(subj.get("done", []))
            scores = subj.get("scores", {})
            avg = round(sum(scores.values()) / len(scores)) if scores else "-"
            weak = ", ".join(c for c, v in scores.items() if v < 60) or "-"
            status = "Complete" if subj.get("done_all") else f"{done}/{total}"
            rows_learn += f"<tr><td>{e(name)}</td><td>{status}</td><td>{avg}</td><td>{e(weak)}</td></tr>"
    rows_skill = ""
    if plugins:
        for p in plugins.list():
            rows_skill += (f"<tr><td>{e(p['name'])}</td><td>v{p['version']}</td><td>{'✅' if p['enabled'] else '⛔'}</td>"
                           f"<td>{e(p.get('description', ''))}</td></tr>")
    gaps = "".join(f"<li>{e(g['time'])}: {e(g['cmd'])}</li>" for g in reversed(d["gaps"][-10:])) or "<li>None</li>"
    fails = "".join(f"<li>{e(f['time'])}: {e(f['cmd'])} <small>{e(f['error'])}</small></li>"
                    for f in reversed(d["failures"][-10:])) or "<li>None</li>"
    topics = len(knowledge.items) if knowledge else 0
    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JARVIS Dashboard</title><style>
body{{font-family:Segoe UI,system-ui,sans-serif;background:#01080f;color:#bdf8ff;margin:0;padding:24px}}
h1{{color:#19e6ff;letter-spacing:4px}} h2{{color:#19e6ff;border-bottom:1px solid #0a4a5e;padding-bottom:6px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px}}
.kpi{{background:#03141f;border:1px solid #0a4a5e;border-radius:10px;padding:16px}}
.kpi b{{display:block;font-size:2rem;color:#fff}} table{{width:100%;border-collapse:collapse;background:#03141f}}
td,th{{border:1px solid #0a4a5e;padding:8px;text-align:left}} th{{color:#19e6ff}} small{{color:#6fb}}
section{{margin-top:26px}} li{{margin:4px 0}}</style></head><body>
<h1>J.A.R.V.I.S. DASHBOARD</h1><p>Updated {datetime.now():%d %b %Y, %I:%M %p}</p>
<div class="kpis"><div class="kpi">Commands<b>{d['total']}</b></div><div class="kpi">Success rate<b>{rate:.0f}%</b></div>
<div class="kpi">Knowledge topics<b>{topics}</b></div><div class="kpi">Custom skills<b>{len(plugins.list()) if plugins else 0}</b></div>
<div class="kpi">Failures<b>{d['failed']}</b></div></div>
<section><h2>📚 Learning</h2><table><tr><th>Subject</th><th>Progress</th><th>Quiz score</th><th>Weak chapters</th></tr>
{rows_learn or '<tr><td colspan=4>Nothing yet. Say: learn Python</td></tr>'}</table></section>
<section><h2>🛠️ Skills built by JARVIS</h2><table><tr><th>Skill</th><th>Version</th><th>Status</th><th>What it does</th></tr>
{rows_skill or '<tr><td colspan=4>None yet. Say: ek skill banao jo ...</td></tr>'}</table></section>
<section><h2>🔍 Missing capabilities (gaps)</h2><ul>{gaps}</ul></section>
<section><h2>🐛 Recent failures</h2><ul>{fails}</ul></section>
<section><h2>💡 Suggestions</h2><p>{e(suggestions())}</p></section></body></html>"""
    DASHBOARD.write_text(page, encoding="utf-8")
    if open_browser:
        webbrowser.open(DASHBOARD.as_uri())
    return DASHBOARD


# ---------------- Failure memory -> lessons ----------------
LESSONS_FILE = config.DATA_DIR / "lessons.json"


def add_lesson(task, lesson):
    """Galti se seekha sabak, taaki agli baar wahi galti na ho."""
    try:
        items = json.loads(LESSONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        items = []
    items = (items + [{"time": datetime.now().strftime("%Y-%m-%d %H:%M"), "task": task[:200], "lesson": lesson[:300]}])[-300:]
    LESSONS_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def lessons_for(task, limit=4):
    """Is kaam se milte-julte pichhle sabak (plan banate waqt AI ko diye jaate hain)."""
    try:
        items = json.loads(LESSONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    words = set(w for w in task.lower().split() if len(w) > 3)
    scored = sorted(((len(words & set(i["task"].lower().split())), i) for i in items), key=lambda x: -x[0])
    return [i["lesson"] for n, i in scored if n][:limit]
