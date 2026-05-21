"""Take screenshots of every wizard page for validation."""
import subprocess, time, ctypes, os, sys
from PIL import Image

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32)]

PY     = sys.executable
WIZARD = os.path.join(os.path.dirname(__file__), "setup_wizard.py")
OUT    = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(OUT, exist_ok=True)

u32   = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

FindWindow   = u32.FindWindowW
GetWindowRect = u32.GetWindowRect
ShowWindow   = u32.ShowWindow

def _capture(hwnd):
    """Captura o conteúdo da janela via PrintWindow (funciona mesmo se coberta por outra janela)."""
    rect = RECT()
    GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None
    hdc_win = u32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
    hbmp    = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
    gdi32.SelectObject(hdc_mem, hbmp)
    u32.PrintWindow(hwnd, hdc_mem, 2)  # PW_RENDERFULLCONTENT

    bmi = BITMAPINFOHEADER()
    bmi.biSize      = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth     = w
    bmi.biHeight    = -h   # negativo = top-down
    bmi.biPlanes    = 1
    bmi.biBitCount  = 32
    buf = (ctypes.c_char * (w * h * 4))()
    gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)

    img = Image.frombytes("RGBA", (w, h), bytes(buf), "raw", "BGRA")
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    u32.ReleaseDC(hwnd, hdc_win)
    return img

PAGES = [
    ("01_welcome",         "welcome"),
    ("02_prereqs",         "prereqs"),
    ("03_clone",           "clone"),
    ("04_supabase",        "supabase"),
    ("05_supabase_keys",   "supabase_keys"),
    ("06_telegram_bot",    "telegram"),
    ("07_telegram_id",     "telegram_id"),
    ("08_groq",            "groq"),
    ("09_fly",             "fly"),
    ("10_vercel_login",    "vercel"),
    ("11_vercel_password", "vercel_password"),
    ("12_review",          "review"),
    ("13_deploy",          "deploy"),
    ("14_done",            "done"),
]

for name, page in PAGES:
    print(f"  {name}...", end=" ", flush=True)
    proc = subprocess.Popen([PY, WIZARD, "--demo", page])
    wait = 5 if page == "deploy" else 4
    time.sleep(wait)
    hwnd = FindWindow(None, "Finance Bot — Setup")
    if hwnd:
        ShowWindow(hwnd, 9)   # SW_RESTORE
        time.sleep(0.3)
        img = _capture(hwnd)
        if img:
            img.save(os.path.join(OUT, f"{name}.png"))
            print(f"OK ({img.width}x{img.height})")
        else:
            print("CAPTURE FAILED")
    else:
        print("NOT FOUND")
    if proc.poll() is None:
        proc.kill()
    proc.wait()
    time.sleep(0.8)

print("Done.")
