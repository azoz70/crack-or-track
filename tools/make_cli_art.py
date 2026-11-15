"""Render the smoking camel as a green ANSI truecolor half-block banner."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
W, H = 60, 52

img = Image.open(ROOT / "static" / "logo_cli.png").convert("RGBA")
bg = Image.new("RGBA", img.size, (6, 18, 13, 255))
img = Image.alpha_composite(bg, img).convert("RGB").resize((W, H), Image.LANCZOS)
px = img.load()

def green(r, g, b):
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    return (int(6 + lum * 10), int(20 + lum * 165), int(14 + lum * 114))

lines = []
for y in range(0, H, 2):
    row = []
    for x in range(W):
        r1, g1, b1 = green(*px[x, y])
        r2, g2, b2 = green(*px[x, min(y + 1, H - 1)])
        row.append(f"\x1b[38;2;{r1};{g1};{b1}m\x1b[48;2;{r2};{g2};{b2}m\u2580")
    lines.append("".join(row) + "\x1b[0m")

(ROOT / "cli_art.txt").write_text("\n".join(lines) + "\n")
print("wrote cli_art.txt", len("\n".join(lines)))
