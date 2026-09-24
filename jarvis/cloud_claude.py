"""Cloud dimaag: Claude (Anthropic API). Sabse samajhdaar, par paid.

Setup: JARVIS Data/my_settings.py mein
    ANTHROPIC_API_KEY = "sk-ant-..."
    BRAIN_MODE = "auto"        # internet ho to cloud, na ho to local
    CLOUD_PROVIDER = "claude"
"""
from . import config

_client = None


def available():
    return bool(getattr(config, "ANTHROPIC_API_KEY", ""))


def chat(messages):
    """messages: [{"role": "system"/"user"/"assistant", "content": str}] -> reply text."""
    global _client
    import anthropic
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    convo = [{"role": m["role"], "content": m["content"]} for m in messages
             if m["role"] in ("user", "assistant") and m.get("content")]
    while convo and convo[0]["role"] != "user":          # pehla message user ka hona chahiye
        convo.pop(0)
    # Refusal par server khud dusre model par chala deta hai (fallbacks="default")
    response = _client.beta.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4000,
        system=system or anthropic.NOT_GIVEN,
        messages=convo,
        output_config={"effort": "low"},                 # baatcheet: tez aur sasta
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        return f"Sorry {config.USER_NAME}, I can't help with that one."
    return "".join(b.text for b in response.content if b.type == "text").strip()
