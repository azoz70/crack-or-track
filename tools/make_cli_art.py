"""Generate cli_art.txt (character ASCII art) from the silhouette PNG."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
W, ROWS = 64, 30

img = Image.open(ROOT / "static" / "cli_silhouette.png").convert("RGB")
img = img.resize((W, ROWS), Image.LANCZOS)
px = img.load()
ramp = " .:=+*#%@"

lines = []
for y in range(ROWS):
    row = []
    for x in range(W):
        r, g, b = px[x, y]
        d = 255 - (r + g + b) // 3
        if d < 30:
            row.append(" ")
        else:
            row.append(ramp[min(len(ramp) - 1, int(d / 255 * 8))])
    lines.append("".join(row).rstrip())

(ROOT / "cli_art.txt").write_text("\n".join(lines) + "\n")
print("wrote cli_art.txt")
