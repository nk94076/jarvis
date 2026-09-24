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


def cloud_provider():
    """Is waqt cloud use karna hai? To module lautao, warna None."""
    mode = getattr(config, "BRAIN_MODE", "local")
    if mode == "local":
        return None
    from . import cloud_claude, cloud_gemini
    prov = cloud_gemini if config.CLOUD_PROVIDER == "gemini" else cloud_claude
    if not prov.available():
        return None
    if mode == "auto":
        from .internet import internet_hai
        if not internet_hai():
            return None
    return prov


def chat(messages, model=None, tools=None, max_tokens=None):
    """Tools wale (agent) calls hamesha local; baaki: cloud (agar set hai) warna local."""
    if not tools:
        prov = cloud_provider()
        if prov:
            try:
                return {"message": {"content": prov.chat(messages, max_tokens) if max_tokens else prov.chat(messages)}}
            except Exception as e:
                print(f"[brain] Cloud AI fail ({type(e).__name__}: {str(e)[:120]}), local dimaag use kar raha hoon.")
    import ollama
    kwargs = {"model": pick(model or config.OLLAMA_MODEL), "messages": messages, "keep_alive": config.KEEP_ALIVE,
              "options": {"temperature": config.TEMPERATURE, "num_ctx": max(config.CONTEXT_SIZE, 16384 if max_tokens else 0),
                          **({"num_predict": max_tokens} if max_tokens else {})}}
    if tools:
        kwargs["tools"] = tools
    r = ollama.chat(**kwargs)
    content = r["message"]["content"] if isinstance(r, dict) else (r.message.content or "")
    if not tools and has_foreign_script(content):
        # Qwen kabhi kabhi Chinese mein bolne lagta hai: saaf nirdesh ke saath ek baar dobara
        kwargs["messages"] = messages + [{"role": "user", "content":
                                          "Your last answer switched to Chinese/another script. Answer again ONLY in "
                                          "English or Hinglish (Hindi written in English letters). No Chinese characters."}]
        r2 = ollama.chat(**kwargs)
        c2 = r2["message"]["content"] if isinstance(r2, dict) else (r2.message.content or "")
        clean_text = c2 if not has_foreign_script(c2) else strip_foreign(c2)
        return {"message": {"content": clean_text}}
    return r


def has_foreign_script(text):
    """Chinese/Japanese/Korean akshar (5 se zyada) hain?"""
    return sum(1 for ch in text or "" if "\u3040" <= ch <= "\u30ff" or "\u3400" <= ch <= "\u9fff"
               or "\uac00" <= ch <= "\ud7af") > 5


def strip_foreign(text):
    import re
    parts = re.split(r"(?<=[.!?。！？])\s*", text)
    kept = [p for p in parts if not has_foreign_script(p) and not re.search(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]", p)]
    return " ".join(kept).strip() or "Sorry, please ask me again."
