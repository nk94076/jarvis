"""Coding Agent: "python mein ek program likho jo prime numbers nikale" -> code likhna, chalana,
error aaye to khud theek karke dobara chalana (3 baar). Python, JavaScript, PHP, Java, C, C++, Go, Rust, C#.
Language ka compiler/runtime PC par install hona chahiye (Python to hota hi hai).
Files: Documents/JARVIS Projects/code/"""
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from . import config

CODE_DIR = Path.home() / "Documents" / "JARVIS Projects" / "code"
LANGS = {  # naam: (extension, [run steps]) - {f} file, {d} folder, {e} exe
    "python": (".py", [[sys.executable, "{f}"]]),
    "javascript": (".js", [["node", "{f}"]]),
    "php": (".php", [["php", "{f}"]]),
    "java": (".java", [["java", "{f}"]]),
    "c++": (".cpp", [["g++", "{f}", "-o", "{e}"], ["{e}"]]),
    "c": (".c", [["gcc", "{f}", "-o", "{e}"], ["{e}"]]),
    "go": (".go", [["go", "run", "{f}"]]),
    "rust": (".rs", [["rustc", "{f}", "-o", "{e}"], ["{e}"]]),
    "c#": (".cs", [["dotnet-script", "{f}"]]),
    "bash": (".sh", [["bash", "{f}"]]),
}
ALIASES = {"js": "javascript", "node": "javascript", "cpp": "c++", "c plus plus": "c++", "golang": "go",
           "csharp": "c#", "c sharp": "c#", "py": "python"}


def detect_lang(text):
    t = text.lower()
    for a, l in ALIASES.items():
        if re.search(rf"\b{re.escape(a)}\b", t):
            return l
    for l in sorted(LANGS, key=len, reverse=True):
        if re.search(rf"(?<![\w+#]){re.escape(l)}(?![\w+#])", t):
            return l
    return "python"


def run_file(path, lang=None, stdin="", timeout=30):
    path = Path(path)
    lang = lang or next((l for l, (ext, _) in LANGS.items() if ext == path.suffix), "python")
    steps = LANGS[lang][1]
    exe = str(path.with_suffix(".exe" if sys.platform == "win32" else ""))
    out = ""
    for step in steps:
        cmd = [a.replace("{f}", str(path)).replace("{e}", exe).replace("{d}", str(path.parent)) for a in step]
        if not shutil.which(cmd[0]) and not Path(cmd[0]).exists():
            return False, f"'{cmd[0]}' is not installed, so I cannot run {lang} code on this PC."
        try:
            r = subprocess.run(cmd, cwd=path.parent, input=stdin, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, f"TIMEOUT after {timeout} seconds"
        out += r.stdout + r.stderr
        if r.returncode != 0:
            return False, out[-2500:]
    return True, out[-2500:]


def _code(text):
    m = re.search(r"```[\w+#-]*\s*(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def write_and_run(request, llm, progress=print):
    """Code likho -> chalao -> error to fix -> dobara (3 baar). Spoken reply lautata hai."""
    s = config.USER_NAME
    lang = detect_lang(request)
    ext = LANGS[lang][0]
    CODE_DIR.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^a-z0-9]+", "_", request.lower())[:40].strip("_") or "program"
    path = CODE_DIR / f"{name}_{datetime.now():%H%M%S}{ext}"
    if lang == "java":
        path = CODE_DIR / f"Main_{datetime.now():%H%M%S}" / "Main.java"
        path.parent.mkdir(parents=True, exist_ok=True)
    prompt = (f"Write a complete, runnable {lang} program for: {request}\nIt must run without user input and print "
              f"its result. {'Use class Main.' if lang == 'java' else ''} Reply with only the code in one code block.")
    code, output = "", ""
    for attempt in range(1, 4):
        progress(f"coder: {lang} attempt {attempt}")
        ask = prompt if attempt == 1 else (f"This {lang} program failed:\n```\n{code}\n```\nError/output:\n{output}\n"
                                           f"Fix it. Reply with only the full corrected code in one code block.")
        code = _code(llm(ask))
        path.write_text(code, encoding="utf-8")
        ok, output = run_file(path, lang)
        if ok:
            short = output.strip().splitlines()
            result = " ".join(short[-3:])[:250] if short else "no output"
            return (f"{s}, the {lang} program works{' after ' + str(attempt - 1) + ' fixes' if attempt > 1 else ''}. "
                    f"Output: {result}. It is saved in Documents, JARVIS Projects, code, as {path.name}.")
        if "is not installed" in output:
            return f"{s}, I wrote the code and saved it as {path.name}, but {output}"
    return f"Sorry {s}, the {lang} program still fails after 3 tries. The last error was: {output.strip()[-200:]}"


def test_file(path_text, llm):
    """'test karo calculator.py' -> chalao; fail ho to error samjhao."""
    from .agent import resolve
    p = resolve(path_text)
    if not p.exists():
        return f"{config.USER_NAME}, I could not find {path_text}."
    ok, out = run_file(p)
    if ok:
        return f"{config.USER_NAME}, {p.name} ran successfully. Output: {out.strip()[-200:] or 'nothing'}."
    return f"{config.USER_NAME}, {p.name} failed. " + llm(f"Explain this error in 2 simple sentences and how to fix it:\n{out}")
