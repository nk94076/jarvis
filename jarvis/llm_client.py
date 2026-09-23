"""Saare AI (Ollama) calls yahan se: model GPU mein load rakhta hai (tez jawab), aur agar settings wala
model install nahi hai to jo model install hai us par chala deta hai (JARVIS band nahi hota)."""
from . import config

_installed = None
_warned = set()


def installed_models():
    global _installed
    if _installed is None:
        try:
            import ollama
            res = ollama.list()
            models = res.get("models", []) if isinstance(res, dict) else getattr(res, "models", [])
            _installed = [(m.get("model") or m.get("name")) if isinstance(m, dict) else (m.model or "") for m in models]
        except Exception:
            _installed = []
    return _installed


def pick(model):
    """Maanga hua model install hai to wahi, warna sabse bada install hua model."""
    have = installed_models()
    if not have:
        return model
    names = {h.split(":latest")[0] for h in have} | set(have)
    if model in names or f"{model}:latest" in names:
        return model
    size = lambda n: float(next((p[:-1] for p in n.replace("-", ":").split(":") if p.endswith("b") and p[:-1].replace(".", "").isdigit()), 0))  # noqa: E731
    best = max(have, key=size)
    if model not in _warned:
        print(f"[brain] '{model}' install nahi hai, abhi '{best}' use kar raha hoon. "
              f"Behtar dimaag ke liye upgrade_brain.bat chalao.")
        _warned.add(model)
    return best


def chat(messages, model=None, tools=None):
    import ollama
    kwargs = {"model": pick(model or config.OLLAMA_MODEL), "messages": messages, "keep_alive": config.KEEP_ALIVE,
              "options": {"temperature": config.TEMPERATURE, "num_ctx": config.CONTEXT_SIZE}}
    if tools:
        kwargs["tools"] = tools
    return ollama.chat(**kwargs)
