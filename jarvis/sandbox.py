"""Code Execution Sandbox: JARVIS ka banaya/likha code alag process mein, alag temp folder mein,
time limit ke saath, aur API keys/passwords wale environment variables hata kar chalata hai.
(Ye poori virtual machine jitna band nahi hai, par galti se PC ko nuksan hone ke khatre ko kaafi kam karta hai.)"""
import os
import subprocess
import sys
import tempfile

SECRET_HINTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASS", "AUTH")


def clean_env():
    env = {k: v for k, v in os.environ.items() if not any(h in k.upper() for h in SECRET_HINTS)}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run(cmd, cwd=None, stdin="", timeout=30):
    """cmd (list) ko sandbox mein chalao. (returncode, stdout+stderr) lautata hai; -1 = timeout/start fail."""
    own_tmp = cwd is None
    tmp = tempfile.mkdtemp(prefix="jarvis_sbx_") if own_tmp else cwd
    try:
        r = subprocess.run(cmd, cwd=tmp, input=stdin, capture_output=True, text=True, timeout=timeout,
                           env=clean_env(), creationflags=0x08000000 if sys.platform == "win32" else 0)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return -1, f"TIMEOUT: took more than {timeout} seconds"
    except FileNotFoundError as e:
        return -1, f"NOT INSTALLED: {e}"
    finally:
        if own_tmp:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


def run_python(code, timeout=30):
    """Python code ka tukda sandbox mein."""
    with tempfile.TemporaryDirectory(prefix="jarvis_sbx_") as tmp:
        path = os.path.join(tmp, "snippet.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        return run([sys.executable, path], cwd=tmp, timeout=timeout)
