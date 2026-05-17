"""Gera assets/icon.ico a partir de assets/finance-bot-logo.png."""
import os
from PIL import Image

SIZES  = [16, 32, 48, 64, 128, 256]
_HERE  = os.path.dirname(os.path.abspath(__file__))
SRC    = os.path.join(_HERE, "..", "assets", "finance-bot-logo.png")
OUTPUT = os.path.join(_HERE, "..", "assets", "icon.ico")

img = Image.open(SRC).convert("RGBA")

images = [img.copy().resize((s, s), Image.LANCZOS) for s in SIZES]
images[0].save(OUTPUT, format="ICO",
               sizes=[(s, s) for s in SIZES],
               append_images=images[1:])
print(f"Salvo: {os.path.abspath(OUTPUT)}")
