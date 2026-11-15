"""Render static/logo.png as ANSI truecolor half-block art for the CLI."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
img = Image.open(ROOT / "static" / "logo.png").convert("RGBA")
W, H = 44, 36
img = img.resize((W, H), Image.LANCZOS)
px = img.load()
lines = []
for y in range(0, H, 2):
    line = []
    for x in range(W):
        r1, g1, b1, _ = px[x, y]
        r2, g2, b2, _ = px[x, min(y + 1, H - 1)]
        line.append(f"\x1b[38;2;{r1};{g1};{b1}m\x1b[48;2;{r2};{g2};{b2}m\u2580")
    lines.append("".join(line) + "\x1b[0m")
(ROOT / "cli_art.txt").write_text("\n".join(lines) + "\n")
print("wrote cli_art.txt")
