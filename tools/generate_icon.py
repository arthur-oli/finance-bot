"""Gera assets/icon.ico — círculo branco com $ no centro, fundo #0f172a."""
import os
from PIL import Image, ImageDraw, ImageFont

SIZES    = [16, 32, 48, 64, 128, 256]
BG       = (15,  23,  42,  255)   # #0f172a
CIRCLE   = (255, 255, 255, 255)   # branco
TEXT_COL = (15,  23,  42,  255)   # #0f172a

_HERE   = os.path.dirname(os.path.abspath(__file__))
OUTPUT  = os.path.join(_HERE, "..", "assets", "icon.ico")
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

# Fontes candidatas (Windows)
_FONT_CANDIDATES = [
    "calibrib.ttf", "calibri.ttf",
    "arialbd.ttf",  "arial.ttf",
    "segoeui.ttf",
]

def _font(size):
    for name in _FONT_CANDIDATES:
        for base in [r"C:\Windows\Fonts", os.path.expanduser("~\\AppData\\Local\\Microsoft\\Windows\\Fonts")]:
            path = os.path.join(base, name)
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
    return ImageFont.load_default()

images = []
for sz in SIZES:
    img  = Image.new("RGBA", (sz, sz), BG)
    draw = ImageDraw.Draw(img)

    pad = max(2, int(sz * 0.055))
    draw.ellipse([pad, pad, sz - pad, sz - pad], fill=CIRCLE)

    font_sz = int(sz * 0.52)
    font    = _font(font_sz)
    bbox    = draw.textbbox((0, 0), "$", font=font)
    tw, th  = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (sz - tw) // 2 - bbox[0]
    y = (sz - th) // 2 - bbox[1]
    draw.text((x, y), "$", fill=TEXT_COL, font=font)

    images.append(img)

images[0].save(OUTPUT, format="ICO",
               sizes=[(s, s) for s in SIZES],
               append_images=images[1:])
print(f"Salvo: {os.path.abspath(OUTPUT)}")
