"""Iron Man jaisa HUD screen: beech mein dhadakta arc reactor, ghadi, CPU/RAM, weather,
log aur ek chhota JARVIS character jo bolte waqt muh hilata hai.

Dusre thread se sirf hud.post(...) call karo, baaki sab GUI thread sambhalta hai."""
import datetime
import math
import queue
import time
import tkinter as tk

try:
    import psutil
except ImportError:
    psutil = None

W, H = 1280, 720
BG = "#01080f"
CYAN = "#00e5ff"
MID = "#0b8fae"
DIM = "#07394a"
FAINT = "#04202b"
RED = "#ff3b3b"
FONT = "Consolas"

STATE_TEXT = {"sleep": "STANDBY  |  SAY 'JARVIS'", "listen": "LISTENING...",
              "work": "PROCESSING...", "speak": "SPEAKING"}


class HUD:
    def __init__(self, on_close=None):
        self.on_close = on_close
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S.")
        self.root.geometry(f"{W}x{H}")
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Escape>", lambda e: self.close())
        self.root.bind("<F11>", lambda e: self.root.attributes(
            "-fullscreen", not self.root.attributes("-fullscreen")))
        self.cv = tk.Canvas(self.root, width=W, height=H, bg=BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        self.events = queue.Queue()
        self.state = "sleep"
        self.caption = "Standing by, sir."
        self.speaking = False
        self.log = []
        self.weather = "Weather: --"
        self.cpu = self.ram = self.disk = 0.0
        self._stats_at = 0
        self._closed = False
        self._draw_static()
        self._tick()

    # ---------- thread-safe API ----------
    def post(self, kind, value=None):
        """kind: state | say | said | log | weather | quit"""
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

    # ---------- drawing ----------
    def _draw_static(self):
        cv = self.cv
        for x in range(0, W, 40):
            cv.create_line(x, 0, x, H, fill=FAINT)
        for y in range(0, H, 40):
            cv.create_line(0, y, W, y, fill=FAINT)
        # frame corners
        for x, y, dx, dy in [(10, 10, 1, 1), (W - 10, 10, -1, 1), (10, H - 10, 1, -1), (W - 10, H - 10, -1, -1)]:
            cv.create_line(x, y, x + 60 * dx, y, fill=CYAN, width=2)
            cv.create_line(x, y, x, y + 60 * dy, fill=CYAN, width=2)
        # side bars
        cv.create_line(260, 40, 260, 680, fill=DIM, width=2)
        cv.create_line(1000, 40, 1000, 680, fill=DIM, width=2)
        cv.create_text(640, 690, text="STARK  INDUSTRIES", fill=MID, font=(FONT, 16, "bold italic"))
        cv.create_text(130, 250, text="SYSTEM", fill=MID, font=(FONT, 10))
        cv.create_text(1140, 60, text="WEATHER", fill=MID, font=(FONT, 10))
        cv.create_text(1140, 200, text="ACTIVITY LOG", fill=MID, font=(FONT, 10))

    def _ring(self, cx, cy, r, pct, label, t):
        cv = self.cv
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline=DIM, width=8, tags="d")
        cv.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=-3.6 * max(pct, 0.5),
                      style="arc", outline=CYAN, width=8, tags="d")
        a = t * 60
        cv.create_arc(cx - r - 12, cy - r - 12, cx + r + 12, cy + r + 12, start=a, extent=40,
                      style="arc", outline=MID, width=2, tags="d")
        cv.create_text(cx, cy - 8, text=f"{pct:.0f}%", fill=CYAN, font=(FONT, 16, "bold"), tags="d")
        cv.create_text(cx, cy + 16, text=label, fill=MID, font=(FONT, 9), tags="d")

    def _reactor(self, t):
        cv = self.cv
        cx, cy = 630, 295
        active = self.state != "sleep"
        period = 0.75 if active else 1.3
        ph = (t % period) / period
        # lub-dub heartbeat
        beat = math.exp(-((ph - 0.08) / 0.05) ** 2) + 0.65 * math.exp(-((ph - 0.28) / 0.05) ** 2)
        s = 1 + 0.08 * beat
        main = CYAN if active else MID

        # outer tick ring
        for i in range(72):
            ang = math.radians(i * 5 + t * 6)
            r1, r2 = 205, 215 if i % 6 else 225
            cv.create_line(cx + r1 * math.cos(ang), cy + r1 * math.sin(ang),
                           cx + r2 * math.cos(ang), cy + r2 * math.sin(ang), fill=DIM if i % 6 else MID, tags="d")
        # rotating segments
        for k, (r, speed, ext, w, col) in enumerate([(190, 25, 70, 3, main), (170, -40, 110, 6, MID),
                                                      (150, 60, 40, 2, main), (190, 25, 20, 3, RED)]):
            base = t * speed + (180 if k == 3 else 0)
            for j in range(2 if k != 3 else 1):
                cv.create_arc(cx - r, cy - r, cx + r, cy + r, start=base + j * 180, extent=ext,
                              style="arc", outline=col, width=w, tags="d")
        # pulsing core
        for r, col, w in [(120, DIM, 14), (100, main, 2), (78, MID, 6)]:
            rr = r * s
            cv.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, outline=col, width=w, tags="d")
        glow = 55 * s
        cv.create_oval(cx - glow, cy - glow, cx + glow, cy + glow, fill="#0a5f78", outline=main, width=3, tags="d")
        inner = 32 * (1 + 0.15 * beat)
        cv.create_oval(cx - inner, cy - inner, cx + inner, cy + inner, fill="#9ff6ff" if active else "#3fb8cc",
                       outline="white", width=1 + 2 * beat, tags="d")
        for i in range(10):
            ang = math.radians(i * 36 - t * 20)
            cv.create_line(cx + 60 * s * math.cos(ang), cy + 60 * s * math.sin(ang),
                           cx + 95 * s * math.cos(ang), cy + 95 * s * math.sin(ang), fill=main, width=3, tags="d")
        cv.create_text(cx, cy + 240, text="J . A . R . V . I . S .", fill=main, font=(FONT, 18, "bold"), tags="d")
        blink = "" if (self.state != "sleep" and int(t * 2) % 2) else " "
        cv.create_text(cx, cy + 264, text=STATE_TEXT.get(self.state, "") + blink, fill=MID,
                       font=(FONT, 11), tags="d")

    def _character(self, t):
        """Chhota robot JARVIS: aankhein chamakti, bolte waqt muh hilta."""
        cv = self.cv
        x, y = 330, 645
        col = CYAN if self.state != "sleep" else MID
        bob = 3 * math.sin(t * 2)
        cv.create_line(x, y - 58 + bob, x, y - 42 + bob, fill=col, width=2, tags="d")
        cv.create_oval(x - 5, y - 64 + bob, x + 5, y - 54 + bob, fill=RED if self.speaking else col, outline="", tags="d")
        cv.create_polygon(x - 38, y - 42 + bob, x + 38, y - 42 + bob, x + 30, y + 20 + bob, x - 30, y + 20 + bob,
                          fill="#062a36", outline=col, width=2, tags="d")
        blink = (t % 4) < 0.12
        for ex in (-16, 16):
            eh = 1 if blink else 6
            cv.create_rectangle(x + ex - 9, y - 22 - eh + bob, x + ex + 9, y - 22 + eh + bob,
                                fill="#bff9ff" if self.state != "sleep" else MID, outline="", tags="d")
        mouth = 2 + (8 * abs(math.sin(t * 18)) if self.speaking else 0)
        cv.create_rectangle(x - 14, y + 2 - mouth / 2 + bob, x + 14, y + 2 + mouth / 2 + bob,
                            fill=col, outline="", tags="d")
        # speech bubble
        if self.caption:
            bx, by = x + 60, y - 58
            text = self.caption if len(self.caption) < 170 else self.caption[:167] + "..."
            item = cv.create_text(bx + 14, by + 12, text=text, fill=CYAN, anchor="nw",
                                  width=560, font=(FONT, 12), tags="d")
            x1, y1, x2, y2 = cv.bbox(item)
            cv.create_rectangle(bx, by, x2 + 14, y2 + 12, outline=MID, width=2, tags="d")
            cv.create_polygon(bx, by + 30, bx - 14, by + 40, bx, by + 44, fill=BG, outline=MID, tags="d")
            cv.tag_raise(item)

    def _left(self, now, t):
        cv = self.cv
        cx, cy = 130, 120
        cv.create_oval(cx - 70, cy - 70, cx + 70, cy + 70, outline=CYAN, width=3, tags="d")
        cv.create_arc(cx - 82, cy - 82, cx + 82, cy + 82, start=-t * 30, extent=100, style="arc",
                      outline=MID, width=2, tags="d")
        cv.create_text(cx, cy - 30, text=now.strftime("%B").upper(), fill=MID, font=(FONT, 11), tags="d")
        cv.create_text(cx, cy + 8, text=now.strftime("%d"), fill=CYAN, font=(FONT, 40, "bold"), tags="d")
        cv.create_text(cx, cy + 45, text=now.strftime("%A").upper(), fill=MID, font=(FONT, 9), tags="d")
        cv.create_text(130, 215, text=now.strftime("%I:%M:%S %p"), fill=CYAN, font=(FONT, 18, "bold"), tags="d")
        self._ring(130, 330, 55, self.cpu, "CPU", t)
        self._ring(130, 470, 55, self.ram, "RAM", -t)
        self._ring(130, 610, 45, self.disk, "DISK", t * 0.5)

    def _right(self, t):
        cv = self.cv
        cv.create_text(1140, 110, text=self.weather, fill=CYAN, width=230, font=(FONT, 12), tags="d")
        y = 230
        for line in self.log[-8:]:
            item = cv.create_text(1020, y, text="> " + line, fill=CYAN, anchor="nw", width=240,
                                  font=(FONT, 10), tags="d")
            y = cv.bbox(item)[3] + 8
        # equalizer bars
        for i in range(24):
            h = 4 + (26 if self.speaking else 6) * abs(math.sin(t * 7 + i * 0.7))
            cv.create_rectangle(1020 + i * 10, 670 - h, 1026 + i * 10, 670, fill=MID, outline="", tags="d")

    def _stats(self):
        if psutil and time.time() - self._stats_at > 1:
            self._stats_at = time.time()
            self.cpu = psutil.cpu_percent()
            self.ram = psutil.virtual_memory().percent
            try:
                self.disk = psutil.disk_usage("/").percent
            except Exception:
                pass

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
                self.log.append(f"{datetime.datetime.now():%H:%M} {value}")
            elif kind == "weather":
                self.weather = value
            elif kind == "quit":
                self.close()
                return
        self._stats()
        t = time.time()
        self.cv.delete("d")
        self._left(datetime.datetime.now(), t)
        self._reactor(t)
        self._character(t)
        self._right(t)
        self.root.after(40, self._tick)
