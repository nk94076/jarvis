"""J.A.R.V.I.S. HUD (v9 design): tabs (HOME / SYSTEMS / INTELLIGENCE / ANALYTICS / SETTINGS), date + clock,
SYSTEM STATUS rings with live sparklines, heartbeat arc reactor, WEATHER, ACTIVITY LOG (live), SYSTEM PERFORMANCE
graph, helmet character with speech bubble + waveform, and a mic button (click = type a command).

Layout 1600x900 virtual, har window size par fit. Dusre thread se sirf hud.post(...) call karo."""
import datetime
import math
import queue
import time
import tkinter as tk
from collections import deque

try:
    import psutil
except ImportError:
    psutil = None

VW, VH = 1600, 900
BG = "#020b14"
CYAN = "#19e6ff"
BRIGHT = "#d6fbff"
MID = "#0c93b3"
DIM = "#0a4a5e"
FAINT = "#07202c"
PANEL = "#041522"
RED = "#ff4d5e"
GOLD = "#ffc94d"
GREEN = "#2ee6a6"
BLUE = "#2b8cff"
FONT = "Bahnschrift"          # Windows ka techy condensed font (na ho to default)
MONO = "Consolas"
TABS = ["HOME", "SYSTEMS", "INTELLIGENCE", "ANALYTICS", "SETTINGS"]
STATE_TEXT = {"sleep": 'STANDBY   |   SAY "JARVIS"', "listen": "ACTIVE   |   LISTENING",
              "work": "PROCESSING", "speak": "SPEAKING"}


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(a, b))


class HUD:
    def __init__(self, on_close=None, on_command=None, on_stop=None, provider=None):
        self.on_close, self.on_command, self.on_stop = on_close, on_command, on_stop
        self.provider = provider or (lambda: {})      # INTELLIGENCE / ANALYTICS / SETTINGS ke liye data
        self.actions = {}                              # SETTINGS buttons: naam -> function
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S.")
        self.root.geometry("1280x720")
        self.root.minsize(960, 540)
        self.root.configure(bg=BG)
        try:
            self.root.state("zoomed")
        except tk.TclError:
            pass
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda e: self.close())
        self.root.bind("<Control-space>", lambda e: self.on_stop and self.on_stop())
        self.root.bind("<F11>", lambda e: self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen")))
        self.cv = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<Button-1>", self._click)
        self.entry = tk.Entry(self.root, bg=PANEL, fg=BRIGHT, insertbackground=CYAN, relief="flat",
                              highlightthickness=0, font=(FONT, 13))
        self.entry.bind("<Return>", self._submit)
        self.entry.bind("<Escape>", lambda e: self._typing(False))
        self.typing = False
        self._entry_font = 0

        self.events = queue.Queue()
        self.tab = "HOME"
        self.state = "sleep"
        self.caption = "Initialising systems..."
        self.speaking = False
        self.mic_level = 0.0
        self.log = deque(maxlen=40)
        self.weather = {"temp": "--", "place": "Fetching weather...", "humidity": "--", "wind": "--",
                        "visibility": "--", "feels": "--", "desc": ""}
        self.info = {"mode": "--", "brain": "--", "voice": "--", "learnt": "0"}
        self.cpu = self.ram = self.disk = self.batt = self.net = 0.0
        self.net_down = self.net_up = 0.0
        self.hist = {k: deque([0.0] * 60, maxlen=60) for k in ("cpu", "ram", "disk", "net")}
        self._net_prev = None
        self._stats_at = 0
        self._prov_at, self._prov = 0, {}
        self.hits = []                                 # [(x1,y1,x2,y2, fn)] click areas
        self._closed = False
        self.f, self.ox, self.oy = 1.0, 0, 0
        self._tick()

    # ---------- API ----------
    def post(self, kind, value=None):
        """kind: state | say | said | log | weather | info | level | quit"""
        self.events.put((kind, value))

    def run(self):
        self.root.mainloop()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.on_close:
            self.on_close()
        self.root.destroy()

    def _submit(self, _e=None):
        text = self.entry.get().strip()
        self.entry.delete(0, "end")
        self._typing(False)
        if text and self.on_command:
            self.on_command(text)

    def _typing(self, on):
        self.typing = on
        if on:
            self.entry.focus_set()
        else:
            self.entry.place_forget()
            self.cv.focus_set()

    def _click(self, ev):
        for x1, y1, x2, y2, fn in reversed(self.hits):
            a, b = self.P(x1, y1)
            c, d = self.P(x2, y2)
            if a <= ev.x <= c and b <= ev.y <= d:
                fn()
                return

    def hit(self, x1, y1, x2, y2, fn):
        self.hits.append((x1, y1, x2, y2, fn))

    # ---------- scaling helpers ----------
    def P(self, x, y):
        return self.ox + x * self.f, self.oy + y * self.f

    def S(self, v):
        return v * self.f

    def fs(self, size):
        return max(6, int(round(size * self.f)))

    def _kw(self, kw):
        if "width" in kw:
            kw["width"] = max(1, self.S(kw["width"]))
        return kw

    def line(self, pts, **kw):
        flat = [c for x, y in pts for c in self.P(x, y)]
        return self.cv.create_line(*flat, **self._kw(kw))

    def poly(self, pts, **kw):
        flat = [c for x, y in pts for c in self.P(x, y)]
        return self.cv.create_polygon(*flat, **self._kw(kw))

    def rect(self, x1, y1, x2, y2, **kw):
        return self.cv.create_rectangle(*self.P(x1, y1), *self.P(x2, y2), **self._kw(kw))

    def oval(self, cx, cy, r, **kw):
        return self.cv.create_oval(*self.P(cx - r, cy - r), *self.P(cx + r, cy + r), **self._kw(kw))

    def arc(self, cx, cy, r, start, extent, **kw):
        return self.cv.create_arc(*self.P(cx - r, cy - r), *self.P(cx + r, cy + r), start=start, extent=extent,
                                  style="arc", **self._kw(kw))

    def text(self, x, y, s, size=11, color=CYAN, font=FONT, weight="normal", **kw):
        if "width" in kw:
            kw["width"] = self.S(kw["width"])
        return self.cv.create_text(*self.P(x, y), text=s, fill=color, font=(font, self.fs(size), weight), **kw)

    def glow_arc(self, cx, cy, r, start, extent, color, width):
        self.arc(cx, cy, r, start, extent, outline=mix(BG, color, 0.22), width=width + 8)
        self.arc(cx, cy, r, start, extent, outline=mix(BG, color, 0.5), width=width + 3)
        self.arc(cx, cy, r, start, extent, outline=color, width=width)

    def glow_oval(self, cx, cy, r, color, width):
        self.oval(cx, cy, r, outline=mix(BG, color, 0.2), width=width + 10)
        self.oval(cx, cy, r, outline=mix(BG, color, 0.45), width=width + 4)
        self.oval(cx, cy, r, outline=color, width=width)

    def frame(self, x1, y1, x2, y2, title=None, right=None, right_color=MID, cut=18):
        """Kate hue kono wala HUD panel."""
        pts = [(x1 + cut, y1), (x2 - cut, y1), (x2, y1 + cut), (x2, y2 - cut), (x2 - cut, y2), (x1 + cut, y2),
               (x1, y2 - cut), (x1, y1 + cut)]
        self.poly(pts, fill=PANEL, outline=DIM, width=1.5)
        self.line([(x1 + cut + 10, y1), (x1 + cut + 90, y1)], fill=CYAN, width=2.5)
        self.line([(x2 - cut - 60, y2), (x2 - cut - 10, y2)], fill=CYAN, width=2.5)
        if title:
            self.text(x1 + 22, y1 + 26, title, 14, CYAN, anchor="w")
            self.line([(x1 + 16, y1 + 46), (x2 - 16, y1 + 46)], fill=FAINT, width=1)
        if right:
            self.text(x2 - 22, y1 + 26, right, 10, right_color, anchor="e")

    def spark(self, x, y, w, h, data, color, lo=0, hi=100):
        pts = [(x + i * w / (len(data) - 1), y + h - (min(max(v, lo), hi) - lo) / (hi - lo or 1) * h)
               for i, v in enumerate(data)]
        self.line(pts, fill=color, width=1.4, smooth=True)

    # ---------- background ----------
    def _background(self, t):
        w, h = self.cv.winfo_width(), self.cv.winfo_height()
        cx, cy = self.P(818, 405)
        for i, r in enumerate(range(560, 0, -56)):
            rr = self.S(r)
            self.cv.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, fill=mix(BG, "#06283a", i / 10), outline="")
        step = self.S(38)
        x = (self.ox + self.S(360)) % step
        while x < w:
            self.cv.create_line(x, 0, x, h, fill="#041621")
            x += step
        y = self.oy % step
        while y < h:
            self.cv.create_line(0, y, w, y, fill="#041621")
            y += step
        # outer frame
        self.line([(12, 110), (12, 40), (60, 12), (320, 12)], fill=MID, width=2)
        self.line([(1588, 110), (1588, 40), (1540, 12), (1300, 12)], fill=MID, width=2)
        self.line([(12, 800), (12, 872), (60, 892), (330, 892)], fill=MID, width=2)
        self.line([(1588, 800), (1588, 872), (1540, 892), (1500, 892)], fill=MID, width=2)
        for gx in range(34, 200, 16):
            for gy in (860, 874, 888):
                self.oval(gx, gy, 1.2, fill=DIM, outline="")
            self.oval(1600 - gx, 876, 1.2, fill=DIM, outline="")

    # ---------- top: tabs + badge ----------
    def _topbar(self):
        self.poly([(400, 52), (1180, 52), (1160, 100), (420, 100)], fill=PANEL, outline=DIM, width=1)
        for name, x in zip(TABS, (478, 624, 776, 934, 1086)):
            w = 124 if name == "HOME" else 140
            active = name == self.tab
            if active:
                self.poly([(x - 60, 58), (x + 60, 58), (x + 66, 66), (x + 66, 92), (x + 60, 96), (x - 60, 96),
                           (x - 66, 88), (x - 66, 62)], fill="#073044", outline=CYAN, width=2)
            self.text(x, 78, name, 12, BRIGHT if active else MID, weight="bold" if active else "normal")
            self.hit(x - w / 2, 56, x + w / 2, 98, lambda n=name: setattr(self, "tab", n))
        self.poly([(1350, 58), (1600, 58), (1575, 110), (1330, 110)], fill=PANEL, outline=DIM, width=1)
        self.text(1462, 86, "STARK INDUSTRIES", 12, BRIGHT, font=FONT, weight="bold italic")
        self.poly([(1560, 70), (1600, 70), (1570, 106)], fill=BRIGHT, outline="")

    # ---------- left ----------
    def _left(self, now, t):
        self.frame(28, 90, 342, 350)
        cx, cy = 178, 200
        self.glow_oval(cx, cy, 96, CYAN, 2)
        self.arc(cx, cy, 110, -t * 25, 70, outline=MID, width=2)
        self.arc(cx, cy, 110, -t * 25 + 180, 40, outline=MID, width=2)
        self.text(cx, cy - 46, now.strftime("%B").upper(), 15, BRIGHT)
        self.text(cx, cy + 6, now.strftime("%d"), 58, BRIGHT, weight="bold")
        self.text(cx, cy + 56, now.strftime("%A").upper(), 14, BRIGHT)
        self.poly([(58, 300), (318, 300), (318, 336), (58, 336)], fill="#031019", outline=DIM, width=1)
        self.text(188, 318, now.strftime("%I:%M:%S %p"), 21, BRIGHT, weight="bold")

        self.frame(28, 368, 342, 830, "SYSTEM STATUS")
        rows = [("CPU", self.cpu, BLUE, "cpu"), ("RAM", self.ram, GREEN, "ram"),
                ("DISK", self.disk, GOLD, "disk"), ("NETWORK", self.net, RED, "net")]
        for i, (label, val, col, key) in enumerate(rows):
            y = 460 + i * 104
            self.oval(98, y, 40, outline=FAINT, width=9)
            self.arc(98, y, 40, 90, -3.6 * max(val, 1), outline=col, width=9)
            self._icon(key, 98, y, col)
            self.text(170, y - 26, label, 13, BRIGHT, anchor="w")
            self.text(170, y + 2, f"{val:.0f}%", 22, BRIGHT, anchor="w", weight="bold")
            self.spark(170, y + 16, 125, 22, self.hist[key], col)
            self.line([(305, y - 16), (313, y - 8), (305, y)], fill=MID, width=2)
            if i < 3:
                self.line([(56, y + 52), (320, y + 52)], fill=FAINT, width=1)

    def _icon(self, kind, x, y, col):
        if kind in ("cpu", "ram"):
            self.rect(x - 11, y - 11, x + 11, y + 11, outline=col, width=2)
            self.rect(x - 5, y - 5, x + 5, y + 5, fill=col, outline="")
            for d in (-6, 0, 6):
                for a, b in ((d, -15), (d, 15)):
                    self.line([(x + a, y + b - (3 if b < 0 else -3)), (x + a, y + b)], fill=col, width=1.5)
        elif kind == "disk":
            self.rect(x - 12, y - 13, x + 12, y + 13, outline=col, width=2)
            self.oval(x, y + 1, 6, outline=col, width=2)
        else:
            for r in (6, 12, 18):
                self.arc(x, y + 8, r, 45, 90, outline=col, width=2.5)
            self.oval(x, y + 8, 2.5, fill=col, outline="")

    # ---------- center ----------
    def _reactor(self, t):
        cx, cy = 818, 405
        active = self.state != "sleep"
        period = 0.8 if active else 1.3
        ph = (t % period) / period
        beat = math.exp(-((ph - 0.08) / 0.05) ** 2) + 0.7 * math.exp(-((ph - 0.28) / 0.05) ** 2)
        s = 1 + 0.06 * beat
        main = CYAN if active else mix(MID, CYAN, 0.55)
        self.oval(cx, cy, 140 + ph * 140, outline=mix(main, BG, ph), width=2)
        self.line([(cx - 330, cy), (cx - 250, cy)], fill=DIM, width=1)
        self.line([(cx + 250, cy), (cx + 330, cy)], fill=DIM, width=1)
        for a in (90, 270):                                   # top/bottom markers
            yy = cy - 262 if a == 90 else cy + 262
            d = -1 if a == 90 else 1
            self.poly([(cx - 7, yy), (cx + 7, yy), (cx, yy + 12 * -d)], fill=CYAN, outline="")
        for i in range(120):                                  # outer tick ring
            ang = math.radians(i * 3 - t * 4)
            r2 = 240 if i % 10 else 230
            self.line([(cx + 248 * math.cos(ang), cy + 248 * math.sin(ang)),
                       (cx + r2 * math.cos(ang), cy + r2 * math.sin(ang))], fill=MID if i % 10 else CYAN, width=1)
        for k, (r, sp, ext, w, col, n) in enumerate([(272, 14, 50, 3, main, 4), (216, -26, 120, 8, MID, 2),
                                                     (196, 40, 36, 3, BRIGHT, 3), (216, 18, 34, 5, RED, 1),
                                                     (176, -55, 90, 2, main, 2)]):
            for j in range(n):
                self.glow_arc(cx, cy, r, t * sp + j * 360 / n + k * 25, ext, col, w)
        self.oval(cx, cy, 160, outline=DIM, width=1, dash=(2, 4))
        self.oval(cx, cy, 142 * s, fill="#052234", outline=mix(BG, main, 0.5), width=14)
        self.glow_oval(cx, cy, 142 * s, main, 2)
        for i in range(12):                                   # segmented inner ring (rounded blocks)
            a = math.radians(i * 30 + 15 - t * 10)
            w1 = math.radians(10)
            r1, r2 = 84 * s, 118 * s
            pts = [(cx + r1 * math.cos(a - w1), cy + r1 * math.sin(a - w1)),
                   (cx + r2 * math.cos(a - w1), cy + r2 * math.sin(a - w1)),
                   (cx + r2 * math.cos(a + w1), cy + r2 * math.sin(a + w1)),
                   (cx + r1 * math.cos(a + w1), cy + r1 * math.sin(a + w1))]
            self.poly(pts, fill=mix("#062a3a", main, 0.35 + 0.4 * beat), outline=main, width=1.5)
        self.glow_oval(cx, cy, 78 * s, main, 3)
        core = 62 * (1 + 0.12 * beat)
        for i in range(7):
            self.oval(cx, cy, core * (1 - i / 7), fill=mix("#0a78a0", "#e8feff", i / 6 + 0.15 * beat), outline="")
        self.text(cx, 718, "J . A . R . V . I . S .", 28, main, weight="bold")
        dots = "." * (int(t * 3) % 4) if active and self.state != "sleep" else ""
        self.text(cx, 756, STATE_TEXT.get(self.state, "") + dots, 13, main)
        for gx in (455, 1140):
            for gy in range(720, 780, 14):
                for dx in range(0, 42, 14):
                    self.oval(gx + dx, gy, 1.3, fill=DIM, outline="")

    # ---------- right ----------
    def _right(self, t):
        w = self.weather
        self.frame(1182, 118, 1605, 336, "WEATHER", right="⟳", right_color=CYAN)
        self._weather_icon(1245, 208, t)
        self.text(1290, 208, w["temp"], 30, BRIGHT, weight="bold", anchor="w")
        self.text(1432, 208, w["place"][:60], 11, BRIGHT, anchor="w", width=160)
        self.line([(1200, 252), (1588, 252)], fill=FAINT, width=1)
        for i, (val, lab, kind) in enumerate([(w["feels"], "Feels", "temp"), (w["humidity"], "Humidity", "drop"),
                                              (w["wind"], "Wind", "wind"), (w["visibility"], "Visibility", "eye")]):
            x = 1215 + i * 98
            self._mini_icon(kind, x, 282)
            self.text(x + 14, 282, val, 11, BRIGHT, anchor="w")
            self.text(x + 34, 308, lab, 9, MID)
            if i:
                self.line([(x - 18, 262), (x - 18, 318)], fill=FAINT, width=1)

        self.frame(1182, 352, 1605, 580, "ACTIVITY LOG", right="● LIVE", right_color=GREEN)
        rows = list(self.log)[-6:] or [("--:--", "Awaiting your command, Sir.", CYAN)]
        for i, (tm, msg, col) in enumerate(reversed(rows)):
            y = 414 + i * 30
            self.text(1210, y, tm, 11, MID, anchor="w")
            self.oval(1286, y, 5, fill=col, outline="")
            self.text(1306, y, msg[:40], 11, BRIGHT, anchor="w")
        self.rect(1592, 404, 1595, 560, fill=FAINT, outline="")
        self.rect(1592, 404, 1595, 470, fill=DIM, outline="")

        self.frame(1182, 598, 1605, 812, "SYSTEM PERFORMANCE", right="◌ REAL TIME")
        gx, gy, gw, gh = 1200, 656, 392, 100
        for i in range(6):
            self.line([(gx, gy + i * gh / 5), (gx + gw, gy + i * gh / 5)], fill=FAINT, width=1)
        for i in range(13):
            self.line([(gx + i * gw / 12, gy), (gx + i * gw / 12, gy + gh)], fill=FAINT, width=1)
        for key, col in (("cpu", BLUE), ("ram", GREEN), ("disk", GOLD), ("net", RED)):
            self.spark(gx, gy, gw, gh, self.hist[key], col)
        for i, (lab, val, col) in enumerate([("CPU", self.cpu, BLUE), ("RAM", self.ram, GREEN),
                                             ("DISK", self.disk, GOLD), ("NET", self.net, RED)]):
            x = 1205 + i * 97
            self.rect(x - 6, 777, x + 6, 789, fill=col, outline="")
            self.text(x + 12, 783, f"{lab} {val:.0f}%", 10, BRIGHT, anchor="w")

    def _weather_icon(self, x, y, t):
        self.oval(x - 4, y - 16, 16, fill=GOLD, outline="")
        for k in range(8):
            a = math.radians(k * 45 + t * 15)
            self.line([(x - 4 + 21 * math.cos(a), y - 16 + 21 * math.sin(a)),
                       (x - 4 + 27 * math.cos(a), y - 16 + 27 * math.sin(a))], fill=GOLD, width=2)
        for dx, dy, r in ((-14, 8, 16), (6, 0, 20), (24, 10, 14)):
            self.oval(x + dx, y + dy, r, fill="#e9f7ff", outline="")
        self.rect(x - 30, y + 8, x + 38, y + 24, fill="#e9f7ff", outline="")

    def _mini_icon(self, kind, x, y):
        if kind == "temp":
            self.rect(x - 2, y - 11, x + 2, y + 4, outline=BRIGHT, width=1.5)
            self.oval(x, y + 7, 4, outline=BRIGHT, width=1.5)
        elif kind == "drop":
            self.poly([(x, y - 11), (x + 6, y + 2), (x, y + 8), (x - 6, y + 2)], fill="", outline=BRIGHT, width=1.5,
                      smooth=True)
        elif kind == "wind":
            for d in (-5, 0, 5):
                self.line([(x - 9, y + d), (x + 7, y + d)], fill=BRIGHT, width=1.5)
        else:
            self.oval(x, y, 9, outline=BRIGHT, width=1.5)
            self.oval(x, y, 3, fill=BRIGHT, outline="")

    # ---------- bottom ----------
    def _bottom(self, t):
        self.poly([(348, 832), (1490, 832), (1510, 852), (1510, 900), (330, 900), (330, 852)], fill="#03111b",
                  outline=DIM, width=1.5)
        self.line([(430, 832), (505, 832)], fill=CYAN, width=3)
        x, y = 430, 870
        col = CYAN if self.state != "sleep" else MID
        bob = 2 * math.sin(t * 2)
        self.line([(x, y - 50 + bob), (x, y - 40 + bob)], fill=col, width=2)
        self.oval(x, y - 52 + bob, 3, fill=col, outline="")
        helmet = [(x - 34, y - 40), (x + 34, y - 40), (x + 38, y - 18), (x + 30, y + 12), (x + 14, y + 26),
                  (x - 14, y + 26), (x - 30, y + 12), (x - 38, y - 18)]
        self.poly([(px, py + bob) for px, py in helmet], fill="#051f2b", outline=col, width=2)
        blink = (t % 4) < 0.12
        for d in (-1, 1):
            h = 1 if blink else 5
            self.poly([(x + d * 6, y - 14 + h + bob), (x + d * 24, y - 18 + h + bob), (x + d * 24, y - 18 - h + bob),
                       (x + d * 6, y - 14 - h + bob)], fill=BRIGHT if self.state != "sleep" else MID, outline="")
        m = 2 + (6 * abs(math.sin(t * 18)) if self.speaking else 0)
        self.rect(x - 11, y + 8 - m / 2 + bob, x + 11, y + 8 + m / 2 + bob, fill=col, outline="")

        bx1, by1, bx2, by2 = 515, 842, 1380, 894
        self.poly([(bx1 + 10, by1), (bx2 - 10, by1), (bx2, by1 + 10), (bx2, by2 - 10), (bx2 - 10, by2),
                   (bx1 + 10, by2), (bx1, by2 - 10), (bx1, by1 + 10)], fill=PANEL, outline=MID, width=1.5)
        self.poly([(bx1, 862), (bx1 - 14, 868), (bx1, 874)], fill=PANEL, outline=MID, width=1)
        if self.typing:
            a, b = self.P(bx1 + 20, by1 + 10)
            c, d = self.P(bx2 - 170, by2 - 10)
            self.entry.place(x=a, y=b, width=c - a, height=d - b)
            if self._entry_font != self.fs(14):
                self._entry_font = self.fs(14)
                self.entry.configure(font=(FONT, self._entry_font))
        else:
            cap = self.caption if len(self.caption) < 95 else self.caption[:92] + "..."
            self.text(bx1 + 26, 868, cap, 14, BRIGHT, anchor="w")
        amp = 1.0 if self.speaking else max(0.08, min(1.0, self.mic_level / 900))
        for i in range(34):
            h = 2 + 20 * amp * abs(math.sin(t * 7 + i * 0.55)) * math.exp(-((i - 17) / 9) ** 2)
            xx = 1225 + i * 4.3
            self.rect(xx, 868 - h, xx + 2, 868 + h, fill=mix(MID, BRIGHT, h / 22), outline="")
        mx, my = 1435, 868
        glow = 0.5 + 0.5 * math.sin(t * 3) if self.state == "listen" else 0.25
        self.oval(mx, my, 44, fill=mix(BG, CYAN, 0.12 * glow), outline=mix(BG, CYAN, 0.35), width=3)
        self.glow_oval(mx, my, 34, CYAN, 2)
        self.oval(mx, my, 30, fill="#0a4870", outline="")
        self.rect(mx - 7, my - 16, mx + 7, my + 4, fill=BRIGHT, outline="")
        self.oval(mx, my - 16, 7, fill=BRIGHT, outline="")
        self.oval(mx, my + 4, 7, fill=BRIGHT, outline="")
        self.arc(mx, my + 2, 13, 200, 140, outline=BRIGHT, width=2)
        self.line([(mx, my + 15), (mx, my + 21)], fill=BRIGHT, width=2)
        self.hit(mx - 44, my - 44, mx + 44, my + 44, lambda: self._typing(not self.typing))
        self.hit(bx1, by1, bx2, by2, lambda: self._typing(True))

    # ---------- other tabs (center area) ----------
    def _tab_panel(self, title):
        self.frame(370, 120, 1168, 810, title)

    def _kv(self, rows, x=400, y=190, gap=38, w=740):
        for i, (k, v) in enumerate(rows):
            yy = y + i * gap
            self.text(x, yy, k, 13, MID, anchor="w")
            self.text(x + w, yy, str(v)[:60], 13, BRIGHT, anchor="e")
            self.line([(x, yy + 18), (x + w, yy + 18)], fill=FAINT, width=1)

    def _systems(self):
        self._tab_panel("SYSTEMS")
        rows = [("CPU usage", f"{self.cpu:.0f} %"), ("RAM usage", f"{self.ram:.0f} %"), ("Disk C:", f"{self.disk:.0f} %"),
                ("Battery", f"{self.batt:.0f} %"), ("Download", f"{self.net_down:.0f} KB/s"), ("Upload", f"{self.net_up:.0f} KB/s")]
        if psutil:
            vm = psutil.virtual_memory()
            rows.insert(2, ("Memory", f"{vm.used / 1e9:.1f} / {vm.total / 1e9:.1f} GB"))
            rows.append(("CPU cores", psutil.cpu_count()))
            up = time.time() - psutil.boot_time()
            rows.append(("PC running for", f"{int(up // 3600)} h {int(up % 3600 // 60)} min"))
            try:
                top = sorted(psutil.process_iter(["name", "memory_percent"]),
                             key=lambda p: p.info["memory_percent"] or 0, reverse=True)[:4]
                rows.append(("Top apps (RAM)", ", ".join(p.info["name"] for p in top)))
            except Exception:
                pass
        self._kv(rows)

    def _intelligence(self, p):
        self._tab_panel("INTELLIGENCE")
        self._kv([("Brain", self.info.get("brain", "--")), ("Brain mode", p.get("brain_mode", "--")),
                  ("Knowledge", self.info.get("learnt", "0")), ("Learning now", p.get("learning", "nothing")),
                  ("Learnt subjects", p.get("subjects", "-")), ("Custom skills", p.get("skills", "0")),
                  ("Tools", p.get("tools", "-")), ("Last goal", p.get("goal", "-")),
                  ("Voice", self.info.get("voice", "--")), ("Mode", self.info.get("mode", "--"))])

    def _analytics(self, p):
        self._tab_panel("ANALYTICS")
        self._kv([("Commands handled", p.get("total", 0)), ("Success rate", p.get("rate", "-")),
                  ("Failures", p.get("failed", 0)), ("Missing skills (gaps)", p.get("gaps", 0))], y=190)
        days = p.get("by_day", {})
        items = sorted(days.items())[-10:]
        if items:
            top = max(v for _, v in items) or 1
            for i, (d, v) in enumerate(items):
                x = 420 + i * 72
                h = 220 * v / top
                self.rect(x, 740 - h, x + 40, 740, fill=MID, outline=CYAN)
                self.text(x + 20, 752, d[5:], 9, MID)
                self.text(x + 20, 728 - h, v, 10, BRIGHT)
            self.text(400, 480, "Commands per day", 12, CYAN, anchor="w")

    def _settings(self, p):
        self._tab_panel("SETTINGS")
        opts = [("Safe mode", p.get("safe_mode", False), "safe_mode"),
                ("Brain: local", p.get("brain_mode") == "local", "brain_local"),
                ("Brain: auto (cloud when online)", p.get("brain_mode") == "auto", "brain_auto"),
                ("Brain: cloud", p.get("brain_mode") == "cloud", "brain_cloud"),
                ("Pause learning", False, "learning_stop"), ("Open dashboard", False, "dashboard")]
        for i, (label, on, key) in enumerate(opts):
            y = 200 + i * 70
            self.text(410, y, label, 15, BRIGHT, anchor="w")
            self.rect(1010, y - 18, 1110, y + 18, fill="#073044" if on else FAINT, outline=CYAN if on else DIM, width=2)
            self.text(1060, y, "ON" if on else ("RUN" if key in ("learning_stop", "dashboard") else "OFF"), 12,
                      BRIGHT if on else MID)
            if key in self.actions:
                self.hit(1010, y - 18, 1110, y + 18, self.actions[key])
        self.text(410, 650, "More settings: JARVIS Data \\ my_settings.py", 12, MID, anchor="w")

    # ---------- data ----------
    def _stats(self):
        if not psutil or time.time() - self._stats_at < 1:
            return
        now = time.time()
        self.cpu = psutil.cpu_percent()
        self.ram = psutil.virtual_memory().percent
        try:
            self.disk = psutil.disk_usage("C:\\" if psutil.WINDOWS else "/").percent
        except Exception:
            pass
        try:
            b = psutil.sensors_battery()
            self.batt = b.percent if b else 100.0
        except Exception:
            self.batt = 100.0
        io = psutil.net_io_counters()
        if self._net_prev:
            dt = now - self._net_prev[0]
            self.net_down = (io.bytes_recv - self._net_prev[1]) / 1024 / dt
            self.net_up = (io.bytes_sent - self._net_prev[2]) / 1024 / dt
        self._net_prev = (now, io.bytes_recv, io.bytes_sent)
        self.net = min(100.0, (self.net_down + self.net_up) / 20)      # 2 MB/s = 100%
        for k in self.hist:
            self.hist[k].append(getattr(self, k))
        self._stats_at = now

    def _provided(self):
        if time.time() - self._prov_at > 2:
            try:
                self._prov = self.provider() or {}
            except Exception:
                self._prov = {}
            self._prov_at = time.time()
        return self._prov

    def _add_log(self, msg):
        col = GREEN if any(k in msg.lower() for k in ("ready", "online", "done", "complete")) else \
            GOLD if any(k in msg for k in ("⏰", "📚", "🛠", "🎯")) else RED if "fail" in msg.lower() else CYAN
        self.log.append((datetime.datetime.now().strftime("%H:%M"), msg, col))

    def _tick(self):
        if self._closed:
            return
        while not self.events.empty():
            kind, value = self.events.get()
            if kind == "state":
                self.state = value
            elif kind == "say":
                self.caption, self.speaking = value, True
            elif kind == "said":
                self.speaking = False
            elif kind == "log":
                self._add_log(str(value))
            elif kind == "weather":
                if isinstance(value, dict):
                    self.weather.update(value)
                else:
                    self.weather.update(temp=value[0], place=value[1])
            elif kind == "info":
                self.info.update(value)
            elif kind == "level":
                self.mic_level = 0.7 * self.mic_level + 0.3 * value
            elif kind == "quit":
                self.close()
                return
        self._stats()
        w, h = max(self.cv.winfo_width(), 100), max(self.cv.winfo_height(), 100)
        self.f = min(w / VW, h / VH)
        self.ox, self.oy = (w - VW * self.f) / 2, (h - VH * self.f) / 2
        t = time.time()
        self.cv.delete("all")
        self.hits = []
        self._background(t)
        self._topbar()
        self._left(datetime.datetime.now(), t)
        if self.tab == "HOME":
            self._reactor(t)
        elif self.tab == "SYSTEMS":
            self._systems()
        elif self.tab == "INTELLIGENCE":
            self._intelligence(self._provided())
        elif self.tab == "ANALYTICS":
            self._analytics(self._provided())
        else:
            self._settings(self._provided())
        self._right(t)
        self._bottom(t)
        self.root.after(40, self._tick)
