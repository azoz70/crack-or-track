"""Build cli_silhouette.svg from the mascot: black body, grey eyes with pupils."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

src = (ROOT / "static" / "logo_cli.svg").read_text()

# Drop background, glow, and ring so only the camel remains.
src = re.sub(r'<rect width="512".*?/>', "", src)
src = re.sub(r'<circle cx="256" cy="230".*?/>', "", src)
src = re.sub(r'<circle cx="256" cy="248".*?/>', "", src)

# Recolor every remaining shape to solid black.
src = re.sub(r'fill="url\(#[^)]*\)"', 'fill="#000"', src)
src = re.sub(r'fill="#[0-9A-Fa-f]{6}"', 'fill="#000"', src)
src = re.sub(r'stroke="#[0-9A-Fa-f]{6}"', 'stroke="#000"', src)
src = re.sub(r'(stroke-opacity|opacity)="[0-9.]+"', r'\1="1"', src)

# Draw eyes on top: grey sclera maps to a light ASCII glyph, black pupil.
eyes = """
  <ellipse cx="221" cy="204" rx="30" ry="34" fill="#9A9A9A"/>
  <ellipse cx="291" cy="204" rx="30" ry="34" fill="#9A9A9A"/>
  <circle cx="226" cy="208" r="11" fill="#000000"/>
  <circle cx="286" cy="208" r="11" fill="#000000"/>
"""
src = src.replace("</svg>", eyes + "</svg>")

(ROOT / "static" / "cli_silhouette.svg").write_text(src)
print("wrote cli_silhouette.svg")
