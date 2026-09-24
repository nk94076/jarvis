"""Project Understanding Agent: poora code project scan karke samajhna, aur uske baare mein sawaalon ke jawab.
"understand my website project", "jarvis project mein voice kahan handle hoti hai".
Samajh Project Memory (knowledge: "project: <naam> overview") mein save hoti hai."""
import json
import os
import re
from collections import Counter
from pathlib import Path

from . import config

SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", ".next", "vendor", ".idea", ".vscode",
        "target", "bin", "obj", "coverage"}
CODE_EXT = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "React TSX", ".jsx": "React JSX",
            ".php": "PHP", ".java": "Java", ".kt": "Kotlin", ".go": "Go", ".rs": "Rust", ".cs": "C#", ".cpp": "C++",
            ".c": "C", ".rb": "Ruby", ".swift": "Swift", ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
            ".vue": "Vue", ".dart": "Dart", ".sql": "SQL", ".sh": "Shell", ".bat": "Batch"}
MARKERS = {"package.json": "Node.js", "requirements.txt": "Python pip", "pyproject.toml": "Python project",
           "composer.json": "PHP Composer", "pom.xml": "Java Maven", "build.gradle": "Gradle", "go.mod": "Go modules",
           "Cargo.toml": "Rust Cargo", "Dockerfile": "Docker", "docker-compose.yml": "Docker Compose",
           "manage.py": "Django", "artisan": "Laravel", "next.config.js": "Next.js", "vite.config.js": "Vite",
           "angular.json": "Angular", "pubspec.yaml": "Flutter", "wp-config.php": "WordPress"}
ENTRY = ["main.py", "app.py", "manage.py", "index.js", "server.js", "app.js", "index.php", "main.go", "src/main.rs",
         "src/index.js", "src/main.ts", "src/App.jsx", "src/App.tsx", "index.html"]


def _root(name):
    from .agent import resolve
    return resolve(name)


def scan(root):
    files, langs = [], Counter()
    for dirpath, dirs, fnames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        for f in fnames:
            p = Path(dirpath) / f
            files.append(p)
            if p.suffix in CODE_EXT:
                langs[CODE_EXT[p.suffix]] += 1
        if len(files) > 20000:
            break
    rel = lambda p: str(p.relative_to(root)).replace("\\", "/")  # noqa: E731
    markers = sorted({v for k, v in MARKERS.items() if (root / k).exists()})
    deps = []
    if (root / "package.json").exists():
        try:
            pj = json.loads((root / "package.json").read_text(encoding="utf-8"))
            deps = list(pj.get("dependencies", {}))[:25]
        except ValueError:
            pass
    elif (root / "requirements.txt").exists():
        deps = [re.split(r"[<>=\[ ]", ln)[0] for ln in (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.startswith("#")][:25]
    top = sorted({rel(p).split("/")[0] + ("/" if "/" in rel(p) else "") for p in files})[:40]
    readme = next((p for p in files if p.name.lower().startswith("readme") and p.parent == root), None)
    return {"root": str(root), "files": len(files), "languages": dict(langs.most_common(8)), "stack": markers,
            "dependencies": deps, "top_level": top, "entry_points": [e for e in ENTRY if (root / e).exists()],
            "readme": readme.read_text(encoding="utf-8", errors="ignore")[:1500] if readme else "",
            "biggest": [rel(p) for p in sorted((p for p in files if p.suffix in CODE_EXT), key=lambda p: p.stat().st_size,
                                               reverse=True)[:8]]}


def understand(name, llm, knowledge=None):
    root = _root(name)
    if not root.exists():
        return f"{config.USER_NAME}, I could not find the {name} project. Add it to PROJECTS in my_settings.py."
    info = scan(root)
    snippets = ""
    for e in info["entry_points"][:2]:
        snippets += f"\n--- {e} ---\n" + (root / e).read_text(encoding="utf-8", errors="ignore")[:1500]
    summary = llm(f"Explain this software project for its owner in 6-8 short lines: what it does, tech stack, "
                  f"structure (main folders), entry points, and how to run it.\nFacts: {json.dumps(info)[:5000]}\n{snippets}")
    if knowledge is not None:
        knowledge.add(f"project: {root.name} overview", summary + "\n\nFACTS: " + json.dumps(info)[:3000], [])
    langs = ", ".join(info["languages"]) or "no code files"
    return (f"{config.USER_NAME}, {root.name} has {info['files']} files, mostly {langs}"
            + (f", using {', '.join(info['stack'])}" if info["stack"] else "") + f". {summary[:500]}")


def ask(name, question, llm):
    """Project ke baare mein sawaal: relevant files dhoondh kar AI se jawab."""
    root = _root(name)
    if not root.exists():
        return f"{config.USER_NAME}, I could not find the {name} project."
    words = [w for w in re.findall(r"[a-z]{3,}", question.lower())
             if w not in {"project", "mein", "kahan", "kaha", "hota", "hoti", "kaise", "where", "what", "does", "the", "handle"}]
    hits = []
    for dirpath, dirs, fnames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        for f in fnames:
            p = Path(dirpath) / f
            if p.suffix not in CODE_EXT or p.stat().st_size > 400_000:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore").lower()
            score = sum(text.count(w) for w in words) + 5 * sum(w in f.lower() for w in words)
            if score:
                hits.append((score, p, text))
    hits.sort(key=lambda h: -h[0])
    ctx = ""
    for _, p, text in hits[:4]:
        lines = text.splitlines()
        keep = [f"{i + 1}: {lines[i]}" for i in range(len(lines)) if any(w in lines[i] for w in words)][:30]
        ctx += f"\n--- {p.relative_to(root)} ---\n" + "\n".join(keep)
    if not ctx:
        return f"{config.USER_NAME}, I could not find anything about that in {root.name}."
    return llm(f"Project {root.name}. Question: {question}\nRelevant code lines:\n{ctx[:6000]}\n"
               f"Answer in 2-4 spoken sentences and name the file(s).")
