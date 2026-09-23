"""Iron Man jaisa HUD: glowing arc reactor jo heartbeat ki tarah dhadakta hai, system gauges,
weather, activity log, awaaz ki waveform, hologram JARVIS character aur type karne ka box.

Poora layout 1600x900 ke hisaab se design hai aur kisi bhi window size par fit ho jata hai.
Dusre thread se sirf hud.post(...) call karo."""
import datetime
import math
import queue
import time
import tkinter as tk

try:
    import psutil
except ImportError:
    psutil = None

VW, VH = 1600, 900          # virtual design size
BG = "#010a12"
CYAN = "#19e6ff"
BRIGHT = "#bdf8ff"
MID = "#0c93b3"
DIM = "#0a4a5e"
FAINT = "#062331"
PANEL = "#03141f"
RED = "#ff4d4d"
GOLD = "#ffc94d"
GREEN = "#3dffa8"
FONT = "Consolas"
UI = "Segoe UI"

STATE_TEXT = {"sleep": "STANDBY  //  SAY \"HEY JARVIS\"", "listen": "ACTIVE  //  LISTENING",
              "work": "PROCESSING", "speak": "SPEAKING"}


def mix(c1, c2, t):
    """Do rangon ke beech ka rang (t=0 -> c1, t=1 -> c2)."""
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(a, b))


class HUD:
    def __init__(self, on_close=None, on_command=None, on_stop=None):
        self.on_close = on_close
        self.on_command = on_command
        self.on_stop = on_stop
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S.")
        self.root.geometry("1280x720")
        self.root.minsize(960, 540)
        self.root.configure(bg=BG)
        try:
            self.root.state("zoomed")          # Windows par maximize
        except tk.TclError:
            pass
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda e: self.close())
        self.root.bind("<Control-space>", lambda e: self.on_stop and self.on_stop())
        self.root.bind("<F11>", lambda e: self.root.attributes(
            "-fullscreen", not self.root.attributes("-fullscreen")))
        self.cv = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        self.entry = tk.Entry(self.root, bg=PANEL, fg=BRIGHT, insertbackground=CYAN, relief="flat",
                              highlightthickness=1, highlightbackground=DIM, highlightcolor=CYAN,
                              font=(FONT, 13))
        self.entry.bind("<Return>", self._submit)
        self._entry_font = 0

        self.events = queue.Queue()
        self.state = "sleep"
        self.caption = "Initialising systems..."
        self.speaking = False
        self.mic_level = 0.0
        self.log = []
        self.weather = ("--", "Fetching weather")
        self.info = {"mode": "--", "brain": "--", "voice": "--", "learnt": "0"}
        self.cpu = self.ram = self.disk = self.batt = 0.0
        self.net_up = self.net_down = 0.0
        self._net_prev = None
        self._stats_at = 0
        self._closed = False
        self.f, self.ox, self.oy = 1.0, 0, 0
        self._tick()

    # ---------- thread-safe API ----------
    def post(self, kind, value=None):
        """kind: state | say | said | log | weather | info | quit"""
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

    def _submit(self, _event=None):
        text = self.entry.get().strip()
        self.entry.delete(0, "end")
        if text and self.on_command:
            self.on_command(text)

    # ---------- scaling helpers ----------
    def P(self, x, y):
        return self.ox + x * self.f, self.oy + y * self.f

    def S(self, v):
        return v * self.f

    def fs(self, size):
        return max(6, int(round(size * self.f)))

    def line(self, pts, **kw):
        flat = []
        for x, y in pts:
            flat += self.P(x, y)
        if "width" in kw:
            kw["width"] = max(1, self.S(kw["width"]))
        return self.cv.create_line(*flat, **kw)

    def poly(self, pts, **kw):
        flat = []
        for x, y in pts:
            flat += self.P(x, y)
        if "width" in kw:
            kw["width"] = max(1, self.S(kw["width"]))
        return self.cv.create_polygon(*flat, **kw)

    def rect(self, x1, y1, x2, y2, **kw):
        if "width" in kw:
            kw["width"] = max(1, self.S(kw["width"]))
        return self.cv.create_rectangle(*self.P(x1, y1), *self.P(x2, y2), **kw)

    def oval(self, cx, cy, r, **kw):
        if "width" in kw:
            kw["width"] = max(1, self.S(kw["width"]))
        return self.cv.create_oval(*self.P(cx - r, cy - r), *self.P(cx + r, cy + r), **kw)

    def arc(self, cx, cy, r, start, extent, **kw):
        if "width" in kw:
            kw["width"] = max(1, self.S(kw["width"]))
        return self.cv.create_arc(*self.P(cx - r, cy - r), *self.P(cx + r, cy + r),
                                  start=start, extent=extent, style="arc", **kw)

    def text(self, x, y, s, size=11, color=CYAN, font=FONT, weight="normal", **kw):
        if "width" in kw:
            kw["width"] = self.S(kw["width"])
        return self.cv.create_text(*self.P(x, y), text=s, fill=color, font=(font, self.fs(size), weight), **kw)

    def glow_arc(self, cx, cy, r, start, extent, color, width):
        self.arc(cx, cy, r, start, extent, outline=mix(BG, color, 0.25), width=width + 8)
        self.arc(cx, cy, r, start, extent, outline=mix(BG, color, 0.5), width=width + 3)
        self.arc(cx, cy, r, start, extent, outline=color, width=width)

    def glow_oval(self, cx, cy, r, color, width):
        self.oval(cx, cy, r, outline=mix(BG, color, 0.2), width=width + 10)
        self.oval(cx, cy, r, outline=mix(BG, color, 0.45), width=width + 4)
        self.oval(cx, cy, r, outline=color, width=width)

    def panel(self, x1, y1, x2, y2, title):
        self.rect(x1, y1, x2, y2, fill=PANEL, outline=DIM, width=1)
        c = 14
        for (x, y, dx, dy) in [(x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)]:
            self.line([(x + c * dx, y), (x, y), (x, y + c * dy)], fill=CYAN, width=2)
        self.rect(x1 + 12, y1 + 12, x1 + 16, y1 + 26, fill=CYAN, outline="")
        self.text(x1 + 24, y1 + 19, title, 10, MID, anchor="w", weight="bold")
        self.line([(x1 + 24 + len(title) * 8 + 10, y1 + 19), (x2 - 14, y1 + 19)], fill=FAINT, width=1)

    # ---------- sections ----------
    def _background(self, t):
        w, h = self.cv.winfo_width(), self.cv.winfo_height()
        # halka radial glow beech mein
        cx, cy = self.P(800, 410)
        for i, r in enumerate(range(620, 0, -60)):
            rr = self.S(r)
            self.cv.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, fill=mix(BG, "#062a3a", i / 11), outline="")
        step = self.S(40)
        x = self.ox % step
        while x < w:
            self.cv.create_line(x, 0, x, h, fill="#03121b")
            x += step
        y = self.oy % step
        while y < h:
            self.cv.create_line(0, y, w, y, fill="#03121b")
            y += step
        # scan line
        sy = (t * 60) % VH
        self.line([(0, sy), (VW, sy)], fill="#062a3a", width=2)

    def _topbar(self, now, t):
        self.line([(20, 58), (560, 58), (580, 40), (1020, 40), (1040, 58), (1580, 58)], fill=DIM, width=2)
        self.text(30, 30, "J.A.R.V.I.S.", 20, CYAN, weight="bold", anchor="w")
        self.text(262, 32, "JUST A RATHER VERY INTELLIGENT SYSTEM", 9, MID, anchor="w")
        self.text(800, 22, now.strftime("%A, %d %B %Y").upper(), 11, MID)
        online = self.info.get("mode") == "ONLINE"
        col = GREEN if online else GOLD
        self.oval(1400, 30, 6, fill=col if int(t * 2) % 2 else mix(BG, col, 0.4), outline="")
        self.text(1415, 30, "ONLINE" if online else "OFFLINE", 11, col, anchor="w", weight="bold")
        self.text(1575, 30, now.strftime("%H:%M:%S"), 13, CYAN, anchor="e", weight="bold")

    def _left(self, now, t):
        # ---- clock panel ----
        self.panel(20, 75, 400, 330, "CHRONO")
        cx, cy = 115, 205
        self.glow_oval(cx, cy, 68, CYAN, 2)
        self.arc(cx, cy, 80, -t * 40, 100, outline=MID, width=2)
        self.arc(cx, cy, 80, -t * 40 + 180, 60, outline=MID, width=2)
        sec = now.second + now.microsecond / 1e6
        self.arc(cx, cy, 58, 90, -sec * 6, outline=CYAN, width=4)
        self.text(cx, cy - 30, now.strftime("%b").upper(), 12, MID)
        self.text(cx, cy + 5, now.strftime("%d"), 36, BRIGHT, weight="bold")
        self.text(cx, cy + 40, now.strftime("%a").upper(), 10, MID)
        self.text(300, 180, now.strftime("%I:%M"), 38, BRIGHT, weight="bold")
        self.text(300, 225, now.strftime("%S  %p"), 14, CYAN)
        self.text(300, 262, f"WEEK {now.isocalendar()[1]:02d}  |  DAY {now.timetuple().tm_yday:03d}", 9, MID)

        # ---- system panel ----
        self.panel(20, 345, 400, 640, "SYSTEM DIAGNOSTICS")
        for i, (label, val) in enumerate([("CPU", self.cpu), ("RAM", self.ram),
                                          ("DISK", self.disk), ("POWER", self.batt)]):
            gx = 115 + (i % 2) * 190
            gy = 435 + (i // 2) * 130
            self.oval(gx, gy, 48, outline=FAINT, width=9)
            col = RED if val > 85 else CYAN
            self.glow_arc(gx, gy, 48, 90, -3.6 * max(val, 0.5), col, 6)
            for k in range(12):
                a = math.radians(k * 30)
                self.line([(gx + 58 * math.cos(a), gy + 58 * math.sin(a)),
                           (gx + 62 * math.cos(a), gy + 62 * math.sin(a))], fill=DIM, width=1)
            self.text(gx, gy - 6, f"{val:.0f}%", 16, BRIGHT, weight="bold")
            self.text(gx, gy + 18, label, 9, MID)

        # ---- status panel ----
        self.panel(20, 655, 400, 880, "CORE STATUS")
        rows = [("MODE", self.info.get("mode", "--")), ("BRAIN", self.info.get("brain", "--")),
                ("VOICE", self.info.get("voice", "--")), ("KNOWLEDGE", f"{self.info.get('learnt', '0')} topics"),
                ("NET", f"↓{self.net_down:.0f} KB/s  ↑{self.net_up:.0f} KB/s")]
        for i, (k, v) in enumerate(rows):
            y = 705 + i * 34
            self.text(40, y, k, 10, MID, anchor="w")
            self.text(385, y, str(v)[:26], 11, CYAN, anchor="e", weight="bold")
            self.line([(40, y + 15), (385, y + 15)], fill=FAINT, width=1)

    def _reactor(self, t):
        cx, cy = 800, 400
        active = self.state != "sleep"
        period = 0.8 if active else 1.3
        ph = (t % period) / period
        beat = math.exp(-((ph - 0.08) / 0.05) ** 2) + 0.7 * math.exp(-((ph - 0.28) / 0.05) ** 2)
        s = 1 + 0.07 * beat
        main = CYAN if active else mix(MID, CYAN, 0.4)

        # heartbeat shockwave
        wave = (t % period) / period
        self.oval(cx, cy, 130 + wave * 190, outline=mix(main, BG, wave), width=2)

        # outer segmented ring
        for i in range(36):
            a0 = i * 10 + t * 8
            col = main if i % 9 else RED
            self.arc(cx, cy, 300, a0, 6, outline=mix(BG, col, 0.8), width=6)
        for i in range(90):
            a = math.radians(i * 4 - t * 5)
            r2 = 280 if i % 5 else 270
            self.line([(cx + 285 * math.cos(a), cy + 285 * math.sin(a)),
                       (cx + r2 * math.cos(a), cy + r2 * math.sin(a))], fill=MID if i % 5 else CYAN, width=1)
        # rotating arcs
        for r, speed, ext, w, col, n in [(255, 22, 80, 3, main, 3), (232, -35, 130, 7, MID, 2),
                                         (210, 55, 30, 2, BRIGHT, 4), (255, 22, 18, 3, GOLD, 1)]:
            for j in range(n):
                self.glow_arc(cx, cy, r, t * speed + j * 360 / n + (40 if col == GOLD else 0), ext, col, w)
        # dashed guide ring
        self.oval(cx, cy, 190, outline=DIM, width=1, dash=(3, 5))

        # main body
        self.oval(cx, cy, 170 * s, fill="#041c28", outline=mix(BG, main, 0.5), width=16)
        self.glow_oval(cx, cy, 170 * s, main, 2)
        # coils (10 trapezoids like Mark I reactor)
        for i in range(10):
            a = math.radians(i * 36 - t * 12)
            w1, w2 = math.radians(11), math.radians(8)
            r1, r2 = 88 * s, 150 * s
            pts = [(cx + r1 * math.cos(a - w1), cy + r1 * math.sin(a - w1)),
                   (cx + r2 * math.cos(a - w2), cy + r2 * math.sin(a - w2)),
                   (cx + r2 * math.cos(a + w2), cy + r2 * math.sin(a + w2)),
                   (cx + r1 * math.cos(a + w1), cy + r1 * math.sin(a + w1))]
            self.poly(pts, fill=mix("#062a3a", main, 0.25 + 0.35 * beat), outline=main, width=1)
        self.glow_oval(cx, cy, 82 * s, main, 3)
        # core
        core = 70 * (1 + 0.12 * beat)
        for i in range(6):
            r = core * (1 - i / 6)
            self.oval(cx, cy, r, fill=mix("#0b6e85", "#e8feff", i / 5 + 0.15 * beat), outline="")
        # triangle (Mark II style)
        tri = 62 * s
        pts = [(cx + tri * math.cos(math.radians(a - 90)), cy + tri * math.sin(math.radians(a - 90)))
               for a in (0, 120, 240)]
        self.poly(pts, fill="", outline=mix(MID, "#ffffff", 0.3 + 0.7 * beat), width=4)

        # title + state
        self.text(cx, 745, "J.A.R.V.I.S.", 22, main, weight="bold")
        dots = "." * (int(t * 3) % 4) if active else ""
        self.text(cx, 778, STATE_TEXT.get(self.state, "") + dots, 11, MID)

    def _character(self, t):
        """Hologram JARVIS helmet: aankhein chamakti hain, bolte waqt muh hilta hai."""
        x, y = 505, 818
        active = self.state != "sleep"
        col = CYAN if active else MID
        bob = 3 * math.sin(t * 2)
        # projector beam + base
        self.poly([(x - 8, y + 44), (x + 8, y + 44), (x + 50, y - 10 + bob), (x - 50, y - 10 + bob)],
                  fill="", outline=mix(BG, col, 0.35), width=1)
        self.oval(x, y + 50, 14, fill=mix(BG, col, 0.3), outline=col, width=1)
        # helmet
        y += bob
        helmet = [(x - 32, y - 40), (x - 18, y - 52), (x + 18, y - 52), (x + 32, y - 40), (x + 34, y - 8),
                  (x + 24, y + 18), (x + 10, y + 28), (x - 10, y + 28), (x - 24, y + 18), (x - 34, y - 8)]
        self.poly(helmet, fill="#051f2b", outline=col, width=2)
        self.poly([(x - 20, y - 44), (x + 20, y - 44), (x + 24, y - 30), (x - 24, y - 30)],
                  fill=mix("#051f2b", col, 0.25), outline="")
        blink = (t % 4) < 0.12
        eye = BRIGHT if active else MID
        for d in (-1, 1):
            h = 1 if blink else 4
            self.poly([(x + d * 6, y - 20 + h), (x + d * 24, y - 22 + h), (x + d * 24, y - 22 - h), (x + d * 6, y - 20 - h)],
                      fill=eye, outline="")
        m = 2 + (7 * abs(math.sin(t * 18)) if self.speaking else 0)
        self.rect(x - 12, y + 8 - m / 2, x + 12, y + 8 + m / 2, fill=col, outline="")
        # speech bubble
        if self.caption:
            cap = self.caption if len(self.caption) < 190 else self.caption[:187] + "..."
            self.rect(560, 790, 1040, 845, fill=PANEL, outline=DIM, width=1)
            self.line([(560, 790), (575, 790)], fill=CYAN, width=2)
            self.poly([(560, 810), (545, 818), (560, 826)], fill=PANEL, outline=DIM, width=1)
            self.text(572, 817, cap, 11, BRIGHT, anchor="w", width=460)

    def _right(self, t):
        # ---- weather ----
        self.panel(1200, 75, 1580, 260, "ENVIRONMENT")
        temp, desc = self.weather
        self.text(1225, 150, temp, 34, BRIGHT, anchor="w", weight="bold")
        self.text(1225, 205, desc[:34], 11, CYAN, anchor="w")
        cx, cy = 1510, 160
        self.glow_oval(cx, cy, 34, GOLD, 2)
        for k in range(8):
            a = math.radians(k * 45 + t * 20)
            self.line([(cx + 42 * math.cos(a), cy + 42 * math.sin(a)),
                       (cx + 52 * math.cos(a), cy + 52 * math.sin(a))], fill=GOLD, width=2)

        # ---- activity log ----
        self.panel(1200, 275, 1580, 640, "ACTIVITY LOG")
        y = 315
        for line in self.log[-9:]:
            self.text(1220, y, "›", 12, CYAN, anchor="nw", weight="bold")
            item = self.text(1238, y + 2, line, 10, BRIGHT, anchor="nw", width=325)
            y = (self.cv.bbox(item)[3] - self.oy) / self.f + 10
        if not self.log:
            self.text(1390, 450, "No commands yet", 10, DIM)

        # ---- voice waveform ----
        self.panel(1200, 655, 1580, 880, "AUDIO INTERFACE")
        mic = min(1.0, self.mic_level / 900)
        amp = 1.0 if self.speaking else max(0.06, mic)
        for i in range(34):
            h = 4 + 70 * amp * abs(math.sin(t * 6 + i * 0.55) * math.sin(t * 2.3 + i * 0.2))
            x = 1222 + i * 10.5
            self.rect(x, 775 - h, x + 6, 775 + h, fill=mix(MID, CYAN, h / 70), outline="")
        self.text(1390, 860, "SPEAKING" if self.speaking else f"MIC LEVEL {self.mic_level:4.0f}", 9, MID)

    def _entry(self):
        x1, y1 = self.P(560, 853)
        x2, y2 = self.P(1040, 885)
        self.entry.place(x=x1, y=y1, width=x2 - x1, height=y2 - y1)
        if self._entry_font != self.fs(12):
            self._entry_font = self.fs(12)
            self.entry.configure(font=(FONT, self._entry_font))
        self.text(800, 896, "Type a command + Enter  ·  Say/type STOP or Ctrl+Space to interrupt  ·  F11 full screen  ·  Esc exit", 8, DIM)

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
        self._stats_at = now

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
                self.log.append(f"{datetime.datetime.now():%H:%M}  {value}")
            elif kind == "weather":
                self.weather = value
            elif kind == "level":
                self.mic_level = 0.7 * self.mic_level + 0.3 * value
            elif kind == "info":
                self.info.update(value)
            elif kind == "quit":
                self.close()
                return
        self._stats()
        w, h = max(self.cv.winfo_width(), 100), max(self.cv.winfo_height(), 100)
        self.f = min(w / VW, h / VH)
        self.ox, self.oy = (w - VW * self.f) / 2, (h - VH * self.f) / 2
        t = time.time()
        now = datetime.datetime.now()
        self.cv.delete("all")
        self._background(t)
        self._topbar(now, t)
        self._left(now, t)
        self._reactor(t)
        self._character(t)
        self._right(t)
        self._entry()
        self.root.after(40, self._tick)
