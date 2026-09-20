"""Generate fixed-width badges (assets/badges/*.svg) in the shields.io "for-the-badge" style.

shields.io sizes every badge to its text, so a column of them has ragged widths and there is
no width parameter. These badges share one width so they stack into clean columns. Text is
forced to an exact length with SVG textLength (the same trick shields uses), so rendering is
identical regardless of which fallback font the viewer has.

Run:  python scripts/build-badges.py
"""
from __future__ import annotations
import re
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "badges"
ICONS = OUT / "icons"

HEIGHT = 28
# WIDTH is derived: label section fits the longest label, colour bar fits the longest message,
# so every badge shares one split point and the colour bars line up as equal blocks.
VPAD = 3                         # transparent margin above/below, so stacked badges breathe
RADIUS = 5                       # rounded outer corners (applied via clip so the colour split stays sharp)
LABEL_BG = "#0a0f0d"
FONT = "Verdana,Geneva,DejaVu Sans,sans-serif"
CHAR_W = 8.0                     # forced width per uppercase char at 10px bold + letter spacing
PAD = 12                         # horizontal padding inside each half
ICON = 14                        # logo box size
ICON_GAP = 7

# Each set gets its own geometry (label section / colour bar sized to ITS longest strings) and
# its own output folder. Entries: slug, label, message, message colour, icon
# (None | simple-icons file stem in assets/badges/icons | "linkedin-glyph").
SETS = {
    "": [  # README header: about | connect columns -> assets/badges/*.svg
        ("education",    "BS Software Engineering", "UMT Lahore",          "#065F46", None),
        ("class",        "Class of",                "2021",                "#059669", None),
        ("location",     "Based in",                "Lahore, Pakistan",    "#10B981", "googlemaps"),
        ("availability", "Open to",                 "Remote / Relocation", "#34D399", None),
        ("portfolio",    "Portfolio",               "Live",                "#065F46", "vercel"),
        ("linkedin",     "LinkedIn",                "Connect",             "#059669", "linkedin-glyph"),
        ("email",        "Email",                   "Reach Out",           "#10B981", "gmail"),
        ("github",       "GitHub",                  "Follow",              "#34D399", "github"),
    ],
    "focus": [  # About section: 2x2 grid of focus areas -> assets/badges/focus/*.svg
        ("software-engineering", "Software Engineering", "Full Stack",   "#065F46", None),
        ("ai-ml",                "AI / ML",              "RAG & Agents", "#059669", None),
        ("web3",                 "Web3",                 "Multi-Chain",  "#10B981", None),
        ("product-engineering",  "Product Engineering",  "Ship & Own",   "#34D399", None),
    ],
    "coding": [  # Coding Profiles: 2x2 grid -> assets/badges/coding/*.svg
        ("leetcode",      "LeetCode",      "Solve & Grow", "#065F46", "leetcode"),
        ("geeksforgeeks", "GeeksforGeeks", "Practice",     "#059669", "geeksforgeeks"),
        ("hackerrank",    "HackerRank",    "Certified",    "#10B981", "hackerrank"),
        ("codechef",      "CodeChef",      "Contests",     "#34D399", "codechef"),
    ],
    "connect": [  # Connect section: 2x2 grid -> assets/badges/connect/*.svg
        ("gmail",     "Gmail",     "kamranhafeez300@gmail.com", "#065F46", "gmail"),
        ("linkedin",  "LinkedIn",  "in/kamranhafeez",           "#059669", "linkedin-glyph"),
        ("github",    "GitHub",    "kamranhafeez-3499",         "#10B981", "github"),
        ("portfolio", "Portfolio", "View Work",                 "#34D399", "vercel"),
    ],
    "certs": [  # Certifications table -> assets/badges/certs/*.svg
        ("aws-cloud-practitioner",  "AWS Cloud Practitioner",             "In Progress", "#065F46", None),
        ("aws-solutions-architect", "AWS Solutions Architect",            "Planned",     "#059669", None),
        ("oracle-cloud-foundations","Oracle Cloud Foundations",           "Planned",     "#10B981", None),
        ("nptel-blockchain",        "NPTEL Blockchain & Its Applications","Planned",     "#34D399", None),
        ("cisco-networking",        "Cisco Networking Essentials",        "Planned",     "#059669", None),
    ],
}


def icon_markup(name: str | None, x: float, y: float) -> str:
    if not name:
        return ""
    if name == "linkedin-glyph":
        # simple-icons dropped the LinkedIn mark; draw a compact "in" tile instead.
        return (f'<g transform="translate({x},{y})">'
                f'<rect width="{ICON}" height="{ICON}" rx="2.5" fill="#fff"/>'
                f'<text x="{ICON/2}" y="10.8" font-family="{FONT}" font-size="9.5" font-weight="bold" '
                f'fill="{LABEL_BG}" text-anchor="middle" letter-spacing="-0.3">in</text></g>')
    svg = (ICONS / f"{name}.svg").read_text(encoding="utf-8")
    d = re.search(r'<path[^>]*\sd="([^"]+)"', svg).group(1)
    s = ICON / 24  # simple-icons are on a 24-unit grid
    return f'<path transform="translate({x},{y}) scale({s:.4f})" fill="#fff" d="{d}"/>'


def text_len(s: str) -> float:
    return round(len(s) * CHAR_W, 1)


def section_widths(badges) -> tuple[int, int]:
    label_w = max(PAD + ((ICON + ICON_GAP) if icon else 0) + text_len(l.upper()) + PAD for _, l, _, _, icon in badges)
    msg_w = max(PAD + text_len(m.upper()) + PAD for _, _, m, _, _ in badges)
    return round(label_w), round(msg_w)


def build(slug: str, label: str, message: str, color: str, icon: str | None, label_w: int, msg_w: int) -> str:
    label_u, msg_u = label.upper(), message.upper()
    tl, ml = text_len(label_u), text_len(msg_u)          # widths from raw text, before escaping
    label, message = escape(label), escape(message)      # XML-safe for <title>/aria-label
    label_u, msg_u = escape(label_u), escape(msg_u)
    icon_w = (ICON + ICON_GAP) if icon else 0
    WIDTH = label_w + msg_w

    # label content (icon + text) is centred inside the fixed label section
    content_w = icon_w + tl
    icon_x = (label_w - content_w) / 2
    label_x = icon_x + icon_w + tl / 2
    msg_x = label_w + msg_w / 2
    baseline = HEIGHT / 2 + 3.6

    total_h = HEIGHT + 2 * VPAD
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{total_h}" viewBox="0 0 {WIDTH} {total_h}" role="img" aria-label="{label}: {message}">
  <title>{label}: {message}</title>
  <clipPath id="rounded"><rect width="{WIDTH}" height="{HEIGHT}" rx="{RADIUS}"/></clipPath>
  <g transform="translate(0,{VPAD})" clip-path="url(#rounded)">
    <rect width="{label_w}" height="{HEIGHT}" fill="{LABEL_BG}"/>
    <rect x="{label_w}" width="{msg_w}" height="{HEIGHT}" fill="{color}"/>
    {icon_markup(icon, icon_x, (HEIGHT - ICON) / 2)}
    <g font-family="{FONT}" font-size="10" font-weight="bold" text-anchor="middle" text-rendering="geometricPrecision">
      <text x="{label_x:.1f}" y="{baseline:.1f}" fill="#fff" textLength="{tl}" lengthAdjust="spacing">{label_u}</text>
      <text x="{msg_x:.1f}" y="{baseline:.1f}" fill="#fff" textLength="{ml}" lengthAdjust="spacing">{msg_u}</text>
    </g>
  </g>
</svg>
'''


def main() -> None:
    for folder, badges in SETS.items():
        out = OUT / folder if folder else OUT
        out.mkdir(parents=True, exist_ok=True)
        label_w, msg_w = section_widths(badges)
        print(f"[{folder or 'header'}] label {label_w}px + bar {msg_w}px = {label_w + msg_w}px per badge")
        for slug, label, message, color, icon in badges:
            svg = build(slug, label, message, color, icon, label_w, msg_w)
            (out / f"{slug}.svg").write_text(svg, encoding="utf-8", newline="\n")
            print(f"  wrote {(out / slug).relative_to(ROOT).as_posix()}.svg")


if __name__ == "__main__":
    main()
