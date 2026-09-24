"""Phone se JARVIS (Android/iPhone): ghar ke WiFi par phone ke browser mein JARVIS kholo.
PC ka address aur PIN JARVIS shuru hote hi console aur HUD log mein dikhta hai.
Phone par page "Add to Home screen" kar lo, app jaisa icon ban jayega.
Sirf ghar ke WiFi (LAN) par chalta hai; PIN ke bina koi command nahi chalti."""
import json
import random
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config

PIN_FILE = config.DATA_DIR / "phone_pin.txt"

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#01080f"><title>JARVIS</title><link rel="manifest" href="/manifest.json">
<style>body{margin:0;font-family:system-ui;background:#01080f;color:#bdf8ff;display:flex;flex-direction:column;height:100vh}
header{padding:14px;text-align:center;color:#19e6ff;letter-spacing:6px;font-weight:800}
#log{flex:1;overflow:auto;padding:12px}.m{margin:8px 0;padding:10px 14px;border-radius:14px;max-width:85%}
.me{background:#0b8fae;color:#fff;margin-left:auto}.jv{background:#03141f;border:1px solid #0a4a5e}
form{display:flex;gap:8px;padding:10px;border-top:1px solid #0a4a5e}
input{flex:1;padding:14px;border-radius:24px;border:1px solid #0a4a5e;background:#03141f;color:#fff;font-size:16px}
button{border:0;border-radius:24px;padding:0 18px;background:#19e6ff;color:#01080f;font-weight:700;font-size:16px}
#core{width:70px;height:70px;border-radius:50%;margin:6px auto;background:radial-gradient(#e8feff,#0b8fae 60%,#01080f 70%);
box-shadow:0 0 30px #19e6ff;animation:b 1.3s infinite}@keyframes b{10%{transform:scale(1.08)}25%{transform:scale(1)}35%{transform:scale(1.05)}}
</style></head><body><header>J.A.R.V.I.S.</header><div id="core"></div><div id="log"></div>
<form id="f"><input id="t" placeholder="Type or tap 🎤" autocomplete="off"><button type="button" id="mic">🎤</button><button>➤</button></form>
<script>
let pin = localStorage.getItem('jpin') || prompt('JARVIS PIN (PC par dikh raha hai)');
localStorage.setItem('jpin', pin);
const log = document.getElementById('log');
function add(t, c){const d=document.createElement('div');d.className='m '+c;d.textContent=t;log.appendChild(d);log.scrollTop=1e9;}
function speak(t){try{const u=new SpeechSynthesisUtterance(t);u.lang='en-IN';speechSynthesis.speak(u);}catch(e){}}
async function send(text){ if(!text) return; add(text,'me');
  const r = await fetch('/api/cmd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin,text})});
  const j = await r.json(); if(r.status==401){localStorage.removeItem('jpin'); add('Wrong PIN. Reload the page.','jv'); return;}
  add(j.reply,'jv'); speak(j.reply); }
document.getElementById('f').onsubmit = e => { e.preventDefault(); const t=document.getElementById('t'); send(t.value); t.value=''; };
document.getElementById('mic').onclick = () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!SR){ add('Voice not supported here: use the mic on your keyboard.','jv'); return; }
  const r = new SR(); r.lang='en-IN'; r.onresult = e => send(e.results[0][0].transcript);
  r.onerror = () => add('Voice needs HTTPS in this browser: use the mic on your keyboard instead.','jv'); r.start(); };
add('Hello! Tell me what to do.','jv');
</script></body></html>"""
MANIFEST = json.dumps({"name": "JARVIS", "short_name": "JARVIS", "start_url": "/", "display": "standalone",
                       "background_color": "#01080f", "theme_color": "#01080f",
                       "icons": [{"src": "https://em-content.zobj.net/source/google/387/robot_1f916.png",
                                  "sizes": "144x144", "type": "image/png"}]})


def get_pin():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if getattr(config, "PHONE_PIN", ""):
        return str(config.PHONE_PIN)
    if not PIN_FILE.exists():
        PIN_FILE.write_text(f"{random.randint(0, 999999):06d}", encoding="utf-8")
    return PIN_FILE.read_text(encoding="utf-8").strip()


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def start(handle, on_command=lambda text: None):
    """Background server. handle(text) -> reply. Address aur PIN lautata hai."""
    pin = get_pin()
    fails = {}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/manifest.json":
                return self._send(200, MANIFEST)
            self._send(200, PAGE, "text/html")

        def do_POST(self):
            ip = self.client_address[0]
            if fails.get(ip, (0, 0))[0] >= 5 and time.time() - fails[ip][1] < 300:
                return self._send(429, json.dumps({"reply": "Too many wrong PINs. Try after 5 minutes."}))
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except ValueError:
                return self._send(400, json.dumps({"reply": "bad request"}))
            if str(body.get("pin", "")) != pin:
                fails[ip] = (fails.get(ip, (0, 0))[0] + 1, time.time())
                return self._send(401, json.dumps({"reply": "Wrong PIN"}))
            fails.pop(ip, None)
            text = str(body.get("text", "")).strip().lower()[:500]
            on_command(text)
            try:
                reply = handle(text) or "Okay."
            except Exception as e:
                reply = f"Sorry, something went wrong: {e}"
            self._send(200, json.dumps({"reply": reply}))

    port = getattr(config, "PHONE_PORT", 8765)
    try:
        srv = ThreadingHTTPServer(("0.0.0.0", port), H)
    except OSError as e:
        return None, f"phone server not started ({e})"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://{local_ip()}:{port}  PIN {pin}"
