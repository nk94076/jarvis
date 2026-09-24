"""Security / Permission Layer: har tool call yahan se guzarta hai.

Policy (upar wala jeet'ta hai):
  1. config.PERMISSIONS = {"run_terminal": "deny", "write_file": "ask", "web_search": "allow"}
  2. SAFE MODE on ("safe mode on karo") -> medium aur high dono par poochna
  3. Default risk se: low = allow, medium = allow (log), high = ask
Har faisla audit log (JARVIS Data/audit.log) mein likha jata hai."""
import datetime
import json

from . import config

AUDIT = config.DATA_DIR / "audit.log"
DEFAULT = {"low": "allow", "medium": "allow", "high": "ask"}
_safe_mode = False


def set_safe_mode(on):
    global _safe_mode
    _safe_mode = on
    return (f"Safe mode is {'on. I will ask before every medium or high risk action' if on else 'off'}, "
            f"{config.USER_NAME}.")


def policy(tool, risk):
    custom = (getattr(config, "PERMISSIONS", {}) or {}).get(tool)
    if custom in ("allow", "ask", "deny"):
        return custom
    if _safe_mode and risk in ("medium", "high"):
        return "ask"
    return DEFAULT.get(risk, "ask")


def audit(tool, args, decision, source="agent"):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(AUDIT, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {source:8} {decision:7} {tool} "
                f"{json.dumps(args, ensure_ascii=False)[:200]}\n")


def check(tool, risk, args, confirm, source="agent"):
    """True = chalao. confirm(question) -> bool (awaaz se yes/no)."""
    decision = policy(tool, risk)
    if decision == "ask":
        detail = ", ".join(f"{k}: {str(v)[:60]}" for k, v in args.items())
        ok = bool(confirm(f"{config.USER_NAME}, should I {tool.replace('_', ' ')}? {detail}"))
        decision = "allowed" if ok else "denied"
    audit(tool, args, decision, source)
    return decision in ("allow", "allowed")


def describe():
    custom = getattr(config, "PERMISSIONS", {}) or {}
    rules = ", ".join(f"{k} {v}" for k, v in custom.items()) or "no custom rules"
    return (f"{config.USER_NAME}, safe mode is {'on' if _safe_mode else 'off'}. Low and medium risk tools run directly, "
            f"high risk tools ask you first. Custom rules: {rules}. Every decision is in the audit log.")
