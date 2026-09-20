"""Slice assets/hero.svg into clickable column tiles for the GitHub profile README.

GitHub (and VS Code's markdown preview) render SVGs as static <img> elements, so the
banner cannot receive hover or click events. The one thing an <img> *can* do is sit
inside an <a>. This script crops the master banner into vertical slices - each a full
copy of the artwork with a narrower viewBox - so every node cluster becomes its own
link while the wave, gradient and grid stay continuous across the seams.

Run:  python scripts/build-tiles.py
Then commit assets/tiles/*.svg together with assets/hero.svg.
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "assets" / "hero.svg"
OUT = ROOT / "assets" / "tiles"
HEIGHT = 320
TOTAL = 1200

# (slug, x_start, x_end)  -- x ranges in the master's 1200-unit viewBox.
TILES = [
    ("portfolio", 0, 150),
    ("linkedin", 150, 220),
    ("github", 220, 340),
    ("email", 340, 470),
    ("name", 470, 730),
    ("stack", 730, 1200),
]


def main() -> None:
    src = MASTER.read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    assert sum(b - a for _, a, b in TILES) == TOTAL, "tiles must cover the full width"

    for slug, x0, x1 in TILES:
        w = x1 - x0
        tile = re.sub(
            r'viewBox="0 0 1200 320" width="100%"',
            f'viewBox="{x0} 0 {w} {HEIGHT}" width="{w}" height="{HEIGHT}"',
            src,
            count=1,
        )
        assert tile != src, "master root attributes changed; update the regex"
        # Each tile is a static image on GitHub: mark it decorative-of-a-part, keep a11y sane.
        tile = tile.replace(
            'aria-label="Kamran Hafeez — Full-Stack Software Engineer"',
            f'aria-label="Kamran Hafeez — banner segment: {slug}"',
            1,
        )
        (OUT / f"hero-{slug}.svg").write_text(tile, encoding="utf-8", newline="\n")
        print(f"wrote assets/tiles/hero-{slug}.svg  ({x0}-{x1}, {w / TOTAL:.4%})")


if __name__ == "__main__":
    main()
