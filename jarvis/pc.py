"""PC Agent ke haath-pair: mouse, keyboard, screen padhna (Windows OCR), browser shortcuts.
Koi extra library nahi: Windows ke built-in ctypes aur PowerShell OCR use hote hain."""
import os
import platform
import subprocess
import tempfile
import time

WIN = platform.system() == "Windows"
NO_WINDOW = 0x08000000

if WIN:
    import ctypes
    try:                                    # asli pixels, taaki click sahi jagah ho
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

VK = {"ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B, "windows": 0x5B,
      "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B, "backspace": 0x08,
      "delete": 0x2E, "del": 0x2E, "space": 0x20, "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
      "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22, "insert": 0x2D, "printscreen": 0x2C,
      "capslock": 0x14}
VK.update({f"f{i}": 0x6F + i for i in range(1, 13)})


def _need_windows():
    if not WIN:
        raise RuntimeError("ye kaam sirf Windows par chalta hai")


# ---------------- keyboard ----------------
def hotkey(combo):
    """'ctrl+t', 'alt+f4', 'win+d', 'enter' jaisi keys dabao."""
    _need_windows()
    kb = ctypes.windll.user32.keybd_event
    codes = []
    for k in combo.lower().replace(" ", "").split("+"):
        if k in VK:
            codes.append(VK[k])
        elif len(k) == 1:
            codes.append(ord(k.upper()))
        else:
            raise ValueError(f"unknown key {k}")
    for c in codes:
        kb(c, 0, 0, 0)
    for c in reversed(codes):
        kb(c, 0, 2, 0)
    time.sleep(0.05)
    return f"pressed {combo}"


def type_text(text):
    """Jis window par focus hai usme text type karo (Unicode bhi chalega)."""
    _need_windows()

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort), ("dwFlags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_size_t)]

    class INPUT(ctypes.Structure):
        class _U(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]
        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_ulong), ("u", _U)]

    send = ctypes.windll.user32.SendInput
    for ch in text:
        if ch == "\n":
            hotkey("enter")
            continue
        for flags in (0x0004, 0x0004 | 0x0002):          # KEYEVENTF_UNICODE, + KEYUP
            inp = INPUT(type=1)
            inp.ki = KEYBDINPUT(0, ord(ch), flags, 0, 0)
            send(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        time.sleep(0.005)
    return f"typed {len(text)} characters"


# ---------------- mouse ----------------
def screen_size():
    _need_windows()
    u = ctypes.windll.user32
    return u.GetSystemMetrics(0), u.GetSystemMetrics(1)


def click(x, y, button="left", double=False):
    _need_windows()
    u = ctypes.windll.user32
    u.SetCursorPos(int(x), int(y))
    down, up = (0x0002, 0x0004) if button == "left" else (0x0008, 0x0010)
    for _ in range(2 if double else 1):
        u.mouse_event(down, 0, 0, 0, 0)
        u.mouse_event(up, 0, 0, 0, 0)
        time.sleep(0.08)
    return f"{'double ' if double else ''}{button} click at {int(x)},{int(y)}"


def scroll(direction="down", amount=5):
    _need_windows()
    delta = -120 if direction == "down" else 120
    for _ in range(int(amount)):
        ctypes.windll.user32.mouse_event(0x0800, 0, 0, delta, 0)
        time.sleep(0.02)
    return f"scrolled {direction}"


# ---------------- screen padhna (Windows OCR) ----------------
OCR_PS = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
Function Await($op, $type) { $t = $asTask.MakeGenericMethod($type).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result }
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync('__PATH__')) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bmp = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$res = Await ($engine.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
foreach ($l in $res.Lines) {
  foreach ($w in $l.Words) { $r = $w.BoundingRect; "W`t{0}`t{1}`t{2}`t{3}`t{4}" -f $w.Text, [int]$r.X, [int]$r.Y, [int]$r.Width, [int]$r.Height }
  "L"
}
"""


def ocr_screen():
    """Poori screen ka text padho. [[(word, x, y, w, h), ...], ...] (har line ki list)."""
    _need_windows()
    from PIL import ImageGrab
    path = os.path.join(tempfile.gettempdir(), "jarvis_screen.png")
    ImageGrab.grab().save(path)
    out = subprocess.run(["powershell", "-NoProfile", "-Command", OCR_PS.replace("__PATH__", path)],
                         capture_output=True, text=True, timeout=40, creationflags=NO_WINDOW).stdout
    lines, cur = [], []
    for row in out.splitlines():
        if row.startswith("W\t"):
            _, word, x, y, w, h = row.split("\t")
            cur.append((word, int(x), int(y), int(w), int(h)))
        elif row.strip() == "L" and cur:
            lines.append(cur)
            cur = []
    return lines


def read_screen():
    lines = ocr_screen()
    text = "\n".join(" ".join(w[0] for w in line) for line in lines)
    return text or "(screen par koi text nahi mila)"


def click_text(query, double=False):
    """Screen par likhe text ko dhoondh kar us par click karo, jaise 'Submit' ya 'Sign in'."""
    q = query.lower().split()
    best = None
    for line in ocr_screen():
        words = [w[0].lower().strip(".,:;!?") for w in line]
        for i in range(len(words) - len(q) + 1):
            if all(q[j] in words[i + j] for j in range(len(q))):
                first, last = line[i], line[i + len(q) - 1]
                x = (first[1] + last[1] + last[3]) / 2
                y = first[2] + first[4] / 2
                exact = all(q[j] == words[i + j] for j in range(len(q)))
                if best is None or (exact and not best[2]):
                    best = (x, y, exact)
    if not best:
        return f"'{query}' screen par nahi mila"
    click(best[0], best[1], double=double)
    return f"clicked on '{query}'"


# ---------------- browser (Chrome/Edge) shortcuts ----------------
BROWSER_KEYS = {"new_tab": "ctrl+t", "close_tab": "ctrl+w", "next_tab": "ctrl+tab", "previous_tab": "ctrl+shift+tab",
                "back": "alt+left", "forward": "alt+right", "refresh": "f5", "address_bar": "ctrl+l",
                "reopen_tab": "ctrl+shift+t", "bookmark": "ctrl+d", "history": "ctrl+h", "downloads": "ctrl+j",
                "zoom_in": "ctrl+=", "zoom_out": "ctrl+-", "fullscreen": "f11", "find": "ctrl+f"}


def browser(action):
    if action not in BROWSER_KEYS:
        return f"unknown browser action {action}"
    combo = BROWSER_KEYS[action].replace("=", "+").replace("ctrl++", "ctrl+=")
    if action == "zoom_in":
        _need_windows()
        kb = ctypes.windll.user32.keybd_event
        kb(0x11, 0, 0, 0); kb(0xBB, 0, 0, 0); kb(0xBB, 0, 2, 0); kb(0x11, 0, 2, 0)
        return "zoomed in"
    if action == "zoom_out":
        _need_windows()
        kb = ctypes.windll.user32.keybd_event
        kb(0x11, 0, 0, 0); kb(0xBD, 0, 0, 0); kb(0xBD, 0, 2, 0); kb(0x11, 0, 2, 0)
        return "zoomed out"
    return hotkey(combo)
