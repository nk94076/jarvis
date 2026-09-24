"""Git Version/Branch System: JARVIS ki banayi skills (JARVIS Data/skills) ek git repo mein.
- Har nayi skill / sudhaar = ek commit ("skill history")
- Sudhaar pehle alag branch par ("try/<skill>"), tests pass -> main mein merge, fail -> branch hata do
- "skill history dikhao", "undo last skill change" (git revert)
Git install na ho (git-scm.com) to ye chupchaap band rehta hai; file versions (v1.py, v2.py) phir bhi chalte hain."""
import shutil
import subprocess

from . import config

REPO = config.DATA_DIR / "skills"


def available():
    return shutil.which("git") is not None


def _git(*args):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=30,
                       creationflags=0x08000000 if __import__("sys").platform == "win32" else 0)
    return r.returncode, (r.stdout + r.stderr).strip()


def ensure_repo():
    if not available():
        return False
    REPO.mkdir(parents=True, exist_ok=True)
    if not (REPO / ".git").exists():
        _git("init", "-b", "main")
        _git("config", "user.name", "JARVIS")
        _git("config", "user.email", "jarvis@localhost")
        _git("add", "-A")
        _git("commit", "--allow-empty", "-m", "JARVIS skills repository")
    return True


def commit(message):
    if not ensure_repo():
        return None
    _git("add", "-A")
    code, out = _git("commit", "-m", message)
    return out if code == 0 else None


def start_branch(name):
    """Sudhaar ke liye naya branch. Branch ka naam lautata hai (ya None)."""
    if not ensure_repo():
        return None
    commit("auto-save before experiment")
    branch = f"try/{name}"
    _git("checkout", "-B", branch)
    return branch


def finish_branch(branch, keep):
    """keep=True: main mein merge; False: branch ke badlav hata kar main par wapas."""
    if not branch or not available():
        return
    if keep:
        commit(f"{branch}: tests passed")
        _git("checkout", "main")
        _git("merge", "--no-ff", "-m", f"merge {branch}", branch)
    else:
        _git("checkout", "-f", "main")
    _git("branch", "-D", branch)


def history(limit=6):
    if not available() or not (REPO / ".git").exists():
        return f"{config.USER_NAME}, version history needs Git. Install it from git-scm.com."
    _, out = _git("log", "--oneline", f"-{limit}")
    items = [ln.split(" ", 1)[1] for ln in out.splitlines() if " " in ln]
    return f"{config.USER_NAME}, recent skill changes: " + "; ".join(items) + "." if items else "No history yet."


def undo_last():
    if not available() or not (REPO / ".git").exists():
        return f"{config.USER_NAME}, undo needs Git."
    code, out = _git("revert", "--no-edit", "HEAD")
    return f"Done {config.USER_NAME}, I undid the last skill change." if code == 0 else f"Could not undo: {out[-150:]}"
