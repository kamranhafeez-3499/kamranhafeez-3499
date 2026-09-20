"""Generate self-hosted, theme-matched GitHub stats cards from the GraphQL API.

Why: the hosted streak/summary cards cannot see private contributions and are cached by
GitHub's image proxy, so they showed stale and wildly low numbers. This script pulls the
contribution calendar (private contributions included, since "Private contributions" is
enabled on the profile) and renders two SVGs in the README's emerald palette:

  streak.svg    total contributions · current streak · longest streak
  activity.svg  total + last-12-months contributions and an area chart of that year

Runs in .github/workflows/snake.yml every 12h and on push; outputs go to the `output` branch.

Local run:  GH_TOKEN=$(gh auth token) python scripts/build-stats.py [out_dir]
"""
from __future__ import annotations
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

LOGIN = os.environ.get("GH_LOGIN", "kamranhafeez-3499")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "assets" / "stats"

# ---- palette (mirrors assets/badges + hero) ----
BG = "#0a0f0d"
BORDER = "#065f46"
TEXT = "#ecfdf5"
LABEL = "#a7f3d0"
MUTED = "#6ee7b7"
ACCENT = "#10b981"
ACCENT_2 = "#34d399"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"

GQL = "https://api.github.com/graphql"


def gql(query: str, variables: dict) -> dict:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GH_TOKEN / GITHUB_TOKEN is required")
    req = urllib.request.Request(
        GQL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-stats-builder"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if payload.get("errors"):
        sys.exit(f"GraphQL error: {payload['errors']}")
    return payload["data"]


PROFILE_Q = """
query($login: String!) {
  user(login: $login) {
    createdAt
  }
}"""

CALENDAR_Q = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""


def fetch() -> tuple[dict[dt.date, int], dt.date]:
    prof = gql(PROFILE_Q, {"login": LOGIN})["user"]
    created = dt.datetime.fromisoformat(prof["createdAt"].replace("Z", "+00:00")).date()

    today = dt.datetime.now(dt.timezone.utc).date()
    days: dict[dt.date, int] = {}
    start = dt.date(created.year, 1, 1)
    while start <= today:
        end = min(dt.date(start.year, 12, 31), today)
        data = gql(CALENDAR_Q, {
            "login": LOGIN,
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{end.isoformat()}T23:59:59Z",
        })
        for week in data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for d in week["contributionDays"]:
                day = dt.date.fromisoformat(d["date"])
                if day <= today:
                    days[day] = d["contributionCount"]
        start = dt.date(start.year + 1, 1, 1)
    return days, created


# ---------------------------------------------------------------- stats

def streaks(days: dict[dt.date, int], today: dt.date):
    active = sorted(d for d, n in days.items() if n > 0)
    first = active[0] if active else today

    best = cur = 0
    best_range = (today, today)
    run_start = None
    prev = None
    for d in active:
        if prev is not None and (d - prev).days == 1:
            cur += 1
        else:
            cur, run_start = 1, d
        if cur > best:
            best, best_range = cur, (run_start, d)
        prev = d

    # current streak: today counts if active, otherwise count back from yesterday
    cursor = today if days.get(today, 0) > 0 else today - dt.timedelta(days=1)
    current = 0
    cur_end = cursor
    while days.get(cursor, 0) > 0:
        current += 1
        cursor -= dt.timedelta(days=1)
    cur_start = cursor + dt.timedelta(days=1)
    return first, current, (cur_start, cur_end), best, best_range


def fmt_num(n: int) -> str:
    return f"{n:,}"


def fmt_short(n: int) -> str:
    return f"{n/1000:.2f}k" if n >= 1000 else str(n)


def fmt_date(d: dt.date, year: bool = True) -> str:
    s = f"{d.strftime('%b')} {d.day}"
    return f"{s}, {d.year}" if year else s


def fmt_range(a: dt.date, b: dt.date) -> str:
    if a == b:
        return fmt_date(a)
    if a.year == b.year:
        return f"{fmt_date(a, False)} - {fmt_date(b)}"
    return f"{fmt_date(a)} - {fmt_date(b)}"


# ---------------------------------------------------------------- streak card

def streak_card(total: int, first: dt.date, current: int, cur_range, best: int, best_range, today: dt.date) -> str:
    W, H = 495, 195
    cur_label = "Today" if cur_range[1] == today and current > 0 else fmt_date(cur_range[1], False)
    if current > 1:
        cur_label = f"{fmt_date(cur_range[0], False)} - {cur_label}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub streak: {fmt_num(total)} total contributions, current streak {current} days, longest streak {best} days">
  <title>GitHub streak</title>
  <style>
    text {{ font-family: {FONT}; }}
    .num {{ font-size: 28px; font-weight: 700; fill: {TEXT}; }}
    .lbl {{ font-size: 14px; font-weight: 600; fill: {LABEL}; }}
    .sub {{ font-size: 12px; fill: {MUTED}; }}
    .ring {{ animation: grow 0.9s ease-out forwards; stroke-dasharray: 0 999; }}
    @keyframes grow {{ to {{ stroke-dasharray: 999 0; }} }}
    @media (prefers-reduced-motion: reduce) {{ .ring {{ animation: none; stroke-dasharray: none; }} }}
  </style>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="{BG}" stroke="{BORDER}"/>
  <line x1="165" y1="30" x2="165" y2="165" stroke="{BORDER}" stroke-width="1"/>
  <line x1="330" y1="30" x2="330" y2="165" stroke="{BORDER}" stroke-width="1"/>

  <g text-anchor="middle">
    <text x="82.5" y="82" class="num">{fmt_num(total)}</text>
    <text x="82.5" y="112" class="lbl">Total Contributions</text>
    <text x="82.5" y="136" class="sub">{escape(fmt_date(first))} - Present</text>
  </g>

  <g text-anchor="middle">
    <circle cx="247.5" cy="78" r="40" fill="none" stroke="{BORDER}" stroke-width="5"/>
    <circle class="ring" cx="247.5" cy="78" r="40" fill="none" stroke="{ACCENT}" stroke-width="5" stroke-linecap="round" transform="rotate(-90 247.5 78)"/>
    <circle cx="247.5" cy="38" r="5" fill="{ACCENT_2}"/>
    <text x="247.5" y="87" class="num">{current}</text>
    <text x="247.5" y="142" class="lbl">Current Streak</text>
    <text x="247.5" y="162" class="sub">{escape(cur_label)}</text>
  </g>

  <g text-anchor="middle">
    <text x="412.5" y="82" class="num">{best}</text>
    <text x="412.5" y="112" class="lbl">Longest Streak</text>
    <text x="412.5" y="136" class="sub">{escape(fmt_range(*best_range))}</text>
  </g>
</svg>
'''


# ---------------------------------------------------------------- activity card

def smooth_path(pts: list[tuple[float, float]]) -> str:
    """Catmull-Rom -> cubic Bezier for a soft area curve."""
    if len(pts) < 3:
        return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    d = [f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"]
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    return " ".join(d)


def activity_card(days: dict[dt.date, int], total: int, created: dt.date, today: dt.date) -> str:
    W, H = 870, 260
    # weekly buckets for the last 52 weeks
    weeks: list[tuple[dt.date, int]] = []
    end = today
    for _ in range(52):
        start = end - dt.timedelta(days=6)
        weeks.append((start, sum(days.get(start + dt.timedelta(d), 0) for d in range(7))))
        end = start - dt.timedelta(days=1)
    weeks.reverse()
    last_year = sum(n for _, n in weeks)
    peak = max((n for _, n in weeks), default=0) or 1

    # chart box
    cx0, cx1, cy0, cy1 = 330, 800, 60, 200
    step = (cx1 - cx0) / (len(weeks) - 1)
    pts = [(cx0 + i * step, cy1 - (n / peak) * (cy1 - cy0)) for i, (_, n) in enumerate(weeks)]
    line = smooth_path(pts)
    area = f"{line} L{cx1:.1f} {cy1} L{cx0:.1f} {cy1} Z"

    # month ticks (every ~2 months)
    ticks = []
    for i in range(0, len(weeks), 9):
        x = cx0 + i * step
        ticks.append(f'<text x="{x:.1f}" y="{cy1 + 20}" class="tick" text-anchor="middle">{weeks[i][0].strftime("%b %y")}</text>')
    grid = "".join(
        f'<line x1="{cx0}" y1="{cy1 - f*(cy1-cy0):.1f}" x2="{cx1}" y2="{cy1 - f*(cy1-cy0):.1f}" stroke="{BORDER}" stroke-opacity="0.6" stroke-dasharray="3 5"/>'
        f'<text x="{cx1 + 10}" y="{cy1 - f*(cy1-cy0) + 4:.1f}" class="tick">{round(peak*f)}</text>'
        for f in (0.5, 1.0)
    )
    years = max(1, (today - created).days // 365)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Contribution activity: {fmt_num(total)} contributions on GitHub, {fmt_num(last_year)} in the last year">
  <title>Contribution activity</title>
  <defs>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0.02"/>
    </linearGradient>
    <clipPath id="chart"><rect x="{cx0}" y="{cy0 - 10}" width="{cx1 - cx0}" height="{cy1 - cy0 + 10}"/></clipPath>
  </defs>
  <style>
    text {{ font-family: {FONT}; }}
    .name {{ font-size: 22px; font-weight: 700; fill: {TEXT}; }}
    .big {{ font-size: 30px; font-weight: 700; fill: {TEXT}; }}
    .lbl {{ font-size: 14px; fill: {LABEL}; }}
    .tick {{ font-size: 11px; fill: {MUTED}; }}
    .hdr {{ font-size: 12px; fill: {MUTED}; }}
    .reveal {{ animation: reveal 1.2s ease-out forwards; transform-origin: {cx0}px {cy1}px; transform: scaleY(0); }}
    @keyframes reveal {{ to {{ transform: scaleY(1); }} }}
    @media (prefers-reduced-motion: reduce) {{ .reveal {{ animation: none; transform: none; }} }}
  </style>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="{BG}" stroke="{BORDER}"/>

  <text x="32" y="52" class="name">{escape(LOGIN)}</text>
  <text x="32" y="118" class="big">{fmt_short(total)}</text>
  <text x="32" y="140" class="lbl">contributions on GitHub</text>
  <text x="32" y="176" class="big">{fmt_short(last_year)}</text>
  <text x="32" y="198" class="lbl">in the last 12 months</text>
  <text x="32" y="228" class="lbl">Joined GitHub {years} year{'s' if years != 1 else ''} ago · {escape(created.strftime('%b %Y'))}</text>

  <text x="{cx1}" y="40" class="hdr" text-anchor="end">weekly contributions · last 12 months</text>
  {grid}
  <g clip-path="url(#chart)">
    <path class="reveal" d="{area}" fill="url(#fill)"/>
    <path class="reveal" d="{line}" fill="none" stroke="{ACCENT_2}" stroke-width="2" stroke-linejoin="round"/>
  </g>
  <line x1="{cx0}" y1="{cy1}" x2="{cx1}" y2="{cy1}" stroke="{BORDER}"/>
  {"".join(ticks)}
</svg>
'''


def main() -> None:
    today = dt.datetime.now(dt.timezone.utc).date()
    days, created = fetch()
    total = sum(days.values())
    first, current, cur_range, best, best_range = streaks(days, today)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "streak.svg").write_text(streak_card(total, first, current, cur_range, best, best_range, today), encoding="utf-8", newline="\n")
    (OUT / "activity.svg").write_text(activity_card(days, total, created, today), encoding="utf-8", newline="\n")
    print(f"total={total} first={first} current={current} {cur_range} longest={best} {best_range} -> {OUT}")


if __name__ == "__main__":
    main()
