"""Gera assets/icon.ico a partir de assets/finance-bot-logo.png."""
import os
from PIL import Image

SIZES  = [256, 128, 64, 48, 32, 16]
_HERE  = os.path.dirname(os.path.abspath(__file__))
SRC    = os.path.join(_HERE, "..", "assets", "finance-bot-logo.png")
OUTPUT = os.path.join(_HERE, "..", "assets", "icon.ico")

img = Image.open(SRC).convert("RGBA")
frames = [img.resize((s, s), Image.LANCZOS) for s in SIZES]
frames[0].save(OUTPUT, format="ICO", append_images=frames[1:])
print(f"Salvo: {os.path.abspath(OUTPUT)} ({os.path.getsize(OUTPUT):,} bytes, {len(SIZES)} tamanhos)")
