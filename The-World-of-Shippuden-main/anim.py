import atexit
import os
import random
import re
import shutil
import sys
import textwrap
import time

from data import RESET, BOLD, DIM, YELLOW, GREEN, RED, CYAN, MAGENTA, BLUE, WHITE
import audio

TTY  = sys.stdout.isatty()
FAST = (not TTY) or bool(os.environ.get("SHIPPUDEN_FAST"))

if os.name == "nt":
    os.system("")                       # enable ANSI on Windows consoles
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── palette ──────────────────────────────────────────────
GOLD    = (255, 200, 70)
ORANGE  = (255, 130, 40)
SKY     = (110, 190, 255)
LEAF    = (120, 210, 120)
CRIMSON = (235, 80, 85)
VIOLET  = (170, 120, 255)
PAPER   = (245, 238, 225)
TRACK   = (44, 48, 62)

STYLE_RGB = {
    "Fire": (255, 120, 40), "Water": (60, 150, 255), "Wind": (150, 255, 200),
    "Lightning": (255, 240, 90), "Earth": (200, 150, 90), "Shadow": (170, 110, 255),
    "Taijutsu": (120, 255, 120), "Genjutsu": (255, 70, 110),
}
COLOR_RGB = {
    "RED": (240, 90, 80), "GREEN": (110, 220, 120), "YELLOW": (250, 205, 80),
    "BLUE": (90, 150, 255), "MAGENTA": (210, 120, 255), "CYAN": (90, 220, 230),
    "WHITE": (235, 235, 235),
}
RARITY_RGB = {
    "Common": (200, 200, 205), "Uncommon": (110, 220, 120), "Rare": (90, 200, 255),
    "Legendary": (255, 205, 70), "Mythic": (230, 120, 255), "Secret": (255, 80, 90),
}


# ═════════════════════════════════════════════════════
#  low-level helpers
# ═════════════════════════════════════════════════════
_ANSI = re.compile(r"\033\[[0-9;?]*[A-Za-z]")


def rgb(r, g, b) -> str:
    return f"\033[38;2;{int(r)};{int(g)};{int(b)}m"


def bgc(r, g, b) -> str:
    return f"\033[48;2;{int(r)};{int(g)};{int(b)}m"


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def dimc(c, k):
    return tuple(int(v * k) for v in c)


def grad(keys, t):
    t = max(0.0, min(1.0, t))
    n = len(keys) - 1
    if n <= 0:
        return keys[0]
    x = t * n
    lo = min(int(x), n - 1)
    return mix(keys[lo], keys[lo + 1], x - lo)


def strip(s: str) -> str:
    return _ANSI.sub("", s)


def vlen(s: str) -> int:
    return len(_ANSI.sub("", s))


def fit(s: str, w: int) -> str:
    """Pad or truncate to exactly w visible columns (ANSI-aware)."""
    n = vlen(s)
    if n <= w:
        return s + " " * (w - n)
    out, vis, i = [], 0, 0
    while i < len(s) and vis < w - 1:
        m = _ANSI.match(s, i)
        if m:
            out.append(m.group())
            i = m.end()
            continue
        out.append(s[i])
        vis += 1
        i += 1
    return "".join(out) + "…" + RESET


def center(s: str, w: int) -> str:
    return " " * max(0, (w - vlen(s)) // 2) + s


def spread(left: str, right: str, w: int) -> str:
    gap = max(1, w - vlen(left) - vlen(right))
    return left + " " * gap + right


def term_w() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def term_h() -> int:
    return shutil.get_terminal_size((80, 24)).lines


def pw() -> int:
    """Standard panel width."""
    return max(50, min(76, term_w() - 2))


def margin(w: int) -> int:
    return max(0, (term_w() - w) // 2)


_LAST_M = None     # left margin of the most recent panel (prompts line up with it)


def mpad() -> str:
    return " " * (_LAST_M if _LAST_M is not None else margin(pw()))


def out(s: str = "") -> None:
    sys.stdout.write(s)
    sys.stdout.flush()


def sleep(t: float) -> None:
    if not FAST and t > 0:
        time.sleep(t)


def cursor(visible: bool) -> None:
    if TTY:
        out("\033[?25h" if visible else "\033[?25l")


atexit.register(lambda: cursor(True))


def clear() -> None:
    global _LAST_M
    _LAST_M = None
    if TTY:
        out("\033[2J\033[H")
    else:
        out("\n" + "─" * 40 + "\n")


def flush_stdin() -> None:
    try:
        import termios
        termios.tcflush(0, termios.TCIFLUSH)
    except Exception:
        pass


# ═════════════════════════════════════════════════════
#  panels
# ═════════════════════════════════════════════════════
SEP = "\x00SEP"
#          tl   tr   bl   br   h    v    ml   mr
_BOX = {
    "round":  ("╭", "╮", "╰", "╯", "─", "│", "├", "┤"),
    "double": ("╔", "╗", "╚", "╝", "═", "║", "╠", "╣"),
    "heavy":  ("┏", "┓", "┗", "┛", "━", "┃", "┣", "┫"),
}


def _edge(l, r, label, w, c1, c2, fill):
    label = strip(label)
    if label:
        label = " " + label + " "
        room = w - 4
        if len(label) > room:
            label = label[:max(0, room - 2)] + "… "
    cells = [l] + ([fill] + list(label) if label else [])
    cells += [fill] * max(0, w - 1 - len(cells)) + [r]
    s = []
    for i, ch in enumerate(cells):
        if label and 2 <= i < 2 + len(label):
            s.append(f"{RESET}{BOLD}{rgb(*PAPER)}{ch}")
        else:
            s.append(f"{RESET}{rgb(*mix(c1, c2, i / max(1, w - 1)))}{ch}")
    return "".join(s) + RESET


def panel(lines, title="", c1=GOLD, c2=None, width=None, kind="round", footer=""):
    w = width or pw()
    c2 = c2 or mix(c1, (255, 255, 255), 0.35)
    tl, tr, bl, br, h, v, ml, mr = _BOX[kind]
    inner = w - 4
    rows = [_edge(tl, tr, title, w, c1, c2, h)]
    for ln in lines:
        if ln == SEP:
            rows.append(_edge(ml, mr, "", w, c1, c2, h))
        else:
            rows.append(f"{rgb(*c1)}{v}{RESET} {fit(ln, inner)} {rgb(*c2)}{v}{RESET}")
    rows.append(_edge(bl, br, footer, w, c1, c2, h))
    return rows


def show(lines, dx=0) -> None:
    if not lines:
        return
    global _LAST_M
    m = max(0, margin(max(vlen(l) for l in lines)) + dx)
    _LAST_M = m
    out("".join(" " * m + l + "\n" for l in lines))


def columns(a, b, gap=3):
    wa = max((vlen(x) for x in a), default=0)
    res = []
    for i in range(max(len(a), len(b))):
        left = a[i] if i < len(a) else ""
        right = b[i] if i < len(b) else ""
        res.append(fit(left, wa) + " " * gap + right)
    return res


def say(text: str, c=None) -> None:
    """One margin-aligned line of text."""
    out(mpad() + (f"{rgb(*c)}{text}{RESET}" if c else text) + "\n")


# ── bars ─────────────────────────────────────────────────
_EIGHTHS = " ▏▎▍▌▋▊▉█"


def hp_color(ratio):
    return (88, 214, 126) if ratio > 0.5 else (245, 196, 60) if ratio > 0.25 else (240, 72, 72)


def bar(cur, mx, width=20, kind="hp", ghost=None, flash=False) -> str:
    ratio = max(0.0, min(1.0, cur / mx if mx else 0))
    base = {"hp": hp_color(ratio), "chakra": (64, 160, 255), "exp": (190, 120, 255)}.get(kind, GOLD)
    if flash:
        base = (255, 255, 255)
    full = ratio * width
    whole = int(full)
    frac = int((full - whole) * 8)
    gfull = (max(0.0, min(1.0, ghost / mx)) * width) if (ghost is not None and mx) else 0
    cells = []
    for i in range(width):
        t = i / max(1, width - 1)
        col = mix(dimc(base, 0.72), mix(base, (255, 255, 255), 0.18), t)
        if i < whole:
            cells.append(f"{rgb(*col)}{bgc(*TRACK)}█")
        elif i == whole and frac > 0:
            cells.append(f"{rgb(*col)}{bgc(*TRACK)}{_EIGHTHS[frac]}")
        elif i < gfull:
            cells.append(f"{rgb(255, 235, 200)}{bgc(*TRACK)}█")
        else:
            cells.append(f"{rgb(*TRACK)}█")
    return "".join(cells) + RESET


def bar_line(label, cur, mx, width=20, kind="hp", ghost=None) -> str:
    return f"{DIM}{label}{RESET} {bar(cur, mx, width, kind, ghost)} {BOLD}{int(cur):>3}{RESET}{DIM}/{mx}{RESET}"


# ── menus ────────────────────────────────────────────────
def opt(n, label, desc="", tag="", locked=False):
    num = f"{rgb(*GOLD)}{BOLD}[{n}]{RESET}"
    lab = f"{DIM}{label}{RESET}" if locked else f"{BOLD}{label}{RESET}"
    lines = [f"{num} {lab}" + (f"  {tag}" if tag else "")]
    if desc:
        lines.append(f"    {DIM}{desc}{RESET}")
    return lines


def menu_panel(title, entries, c1=GOLD, c2=None, back="Back", head=None, width=None) -> None:
    """entries: tuples (n, label[, desc[, tag[, locked]]]). Prints a panel with a [0] row."""
    lines = list(head or [])
    if lines:
        lines.append("")
    for e in entries:
        lines += opt(*e)
    if back:
        lines.append("")
        lines += opt(0, back)
    show(panel(lines, title, c1, c2, width))


def ascii_header(title: str, color=None) -> None:
    """Gradient banner that wipes in from the centre."""
    w = pw()
    c = color or GOLD
    title = strip(title)
    if len(title) > w - 10:
        title = title[:w - 11] + "…"
    text = f" ✦ {title} ✦ "
    left = (w - len(text)) // 2
    cells = ["━"] * left + list(text) + ["━"] * (w - left - len(text))
    keys = [dimc(c, 0.45), c, mix(c, (255, 255, 255), 0.45), c, dimc(c, 0.45)]
    colored = []
    for i, ch in enumerate(cells):
        if left <= i < left + len(text) and ch != " ":
            colored.append(f"{BOLD}{rgb(*PAPER)}{ch}{RESET}")
        else:
            colored.append(f"{rgb(*grad(keys, i / max(1, w - 1)))}{ch}{RESET}")
    m = " " * margin(w)
    out("\n")
    if FAST:
        out(m + "".join(colored) + "\n\n")
        return
    mid, steps = w // 2, 9
    for k in range(1, steps + 1):
        lo = mid - int(mid * k / steps)
        hi = mid + int((w - mid) * k / steps)
        out("\r" + m + " " * lo + "".join(colored[lo:hi]))
        sleep(0.012)
    out("\n\n")


# ═════════════════════════════════════════════════════
#  text effects
# ═════════════════════════════════════════════════════
def story_panel(title, lines, c1=GOLD, c2=None, footer="", delay=0.011) -> None:
    """Typewriter text inside a gradient panel. Ctrl+C skips to the end."""
    w = pw()
    inner = w - 4
    c2 = c2 or mix(c1, (255, 255, 255), 0.35)
    wrapped = []
    for ln in lines:
        wrapped += textwrap.wrap(strip(ln), inner) or [""]
    global _LAST_M
    top, bottom = panel([], title, c1, c2, w, footer=footer)
    pad = " " * margin(w)
    _LAST_M = margin(w)
    out(pad + top + "\n")
    audio.sfx("page", gap=0.3)
    skip = FAST
    for ln in wrapped:
        left = f"{pad}{rgb(*c1)}│{RESET} "
        right = f" {rgb(*c2)}│{RESET}\n"
        if skip:
            out(left + ln + " " * (inner - len(ln)) + right)
            continue
        out(left)
        try:
            for i, ch in enumerate(ln):
                out(ch)
                time.sleep(delay * (7 if ch in ",.;:!?—" else 1))
        except KeyboardInterrupt:
            skip = True
            out(ln[i + 1:])
        out(" " * (inner - len(ln)) + right)
        if not skip:
            time.sleep(0.07)
    out(pad + bottom + "\n")


def notice(lines, title="", c=GOLD) -> None:
    show(panel(lines, title, c))


# ── big pixel font ───────────────────────────────────────
_FONT = {
    "A": (" ███ ", "█   █", "█████", "█   █", "█   █"),
    "B": ("████ ", "█   █", "████ ", "█   █", "████ "),
    "C": (" ████", "█    ", "█    ", "█    ", " ████"),
    "D": ("████ ", "█   █", "█   █", "█   █", "████ "),
    "E": ("█████", "█    ", "████ ", "█    ", "█████"),
    "F": ("█████", "█    ", "████ ", "█    ", "█    "),
    "G": (" ████", "█    ", "█  ██", "█   █", " ███ "),
    "H": ("█   █", "█   █", "█████", "█   █", "█   █"),
    "I": ("███", " █ ", " █ ", " █ ", "███"),
    "J": ("  ███", "    █", "    █", "█   █", " ███ "),
    "K": ("█   █", "█  █ ", "███  ", "█  █ ", "█   █"),
    "L": ("█    ", "█    ", "█    ", "█    ", "█████"),
    "M": ("█   █", "██ ██", "█ █ █", "█   █", "█   █"),
    "N": ("█   █", "██  █", "█ █ █", "█  ██", "█   █"),
    "O": (" ███ ", "█   █", "█   █", "█   █", " ███ "),
    "P": ("████ ", "█   █", "████ ", "█    ", "█    "),
    "Q": (" ███ ", "█   █", "█ █ █", "█  █ ", " ██ █"),
    "R": ("████ ", "█   █", "████ ", "█  █ ", "█   █"),
    "S": (" ████", "█    ", " ███ ", "    █", "████ "),
    "T": ("█████", "  █  ", "  █  ", "  █  ", "  █  "),
    "U": ("█   █", "█   █", "█   █", "█   █", " ███ "),
    "V": ("█   █", "█   █", "█   █", " █ █ ", "  █  "),
    "W": ("█   █", "█   █", "█ █ █", "██ ██", "█   █"),
    "X": ("█   █", " █ █ ", "  █  ", " █ █ ", "█   █"),
    "Y": ("█   █", " █ █ ", "  █  ", "  █  ", "  █  "),
    "Z": ("█████", "   █ ", "  █  ", " █   ", "█████"),
    "0": (" ███ ", "█  ██", "█ █ █", "██  █", " ███ "),
    "1": (" █ ", "██ ", " █ ", " █ ", "███"),
    "2": (" ███ ", "█   █", "  ██ ", " █   ", "█████"),
    "3": ("████ ", "    █", " ███ ", "    █", "████ "),
    "4": ("█  █ ", "█  █ ", "█████", "   █ ", "   █ "),
    "5": ("█████", "█    ", "████ ", "    █", "████ "),
    "!": ("█", "█", "█", " ", "█"),
    "-": ("     ", "     ", "█████", "     ", "     "),
    " ": ("   ", "   ", "   ", "   ", "   "),
}


def big_text(text: str) -> list:
    rows = ["", "", "", "", ""]
    for ch in text.upper():
        g = _FONT.get(ch, _FONT[" "])
        for i in range(5):
            rows[i] += g[i] + " "
    return [r.rstrip() for r in rows]


def _shine(col, x, edge, radius=5):
    d = abs(x - edge)
    return mix(col, (255, 255, 255), 1 - d / radius) if d < radius else col


def reveal_rows(rows, keys, frames=18, delay=0.03) -> None:
    """Print big text with a left→right reveal and a white shine."""
    W = max(len(r) for r in rows)
    m = " " * margin(W)
    n = len(rows)

    def frame(f):
        edge = (f / max(1, frames - 1)) * (W + 10) - 2
        lines = []
        for r in rows:
            s = []
            for x, ch in enumerate(r):
                if ch == " " or x > edge:
                    s.append(" ")
                else:
                    c = _shine(grad(keys, x / max(1, W - 1)), x, edge)
                    s.append(f"{rgb(*c)}{BOLD}{ch}")
            lines.append(m + "".join(s) + RESET)
        return lines

    if FAST:
        out("".join(l + "\n" for l in frame(frames - 1)))
        return
    for f in range(frames):
        if f:
            out(f"\033[{n}A")
        out("".join(l + "\033[K\n" for l in frame(f)))
        sleep(delay)


def banner(text, keys, frames=16) -> None:
    W = term_w()
    rows = big_text(text)
    if max(len(r) for r in rows) > W - 2:
        say(f"{BOLD}{text}{RESET}", keys[0])
        return
    out("\n")
    reveal_rows(rows, keys, frames)
    out("\n")


def victory_banner() -> None:
    audio.sfx("victory")
    banner("VICTORY", [(255, 150, 30), (255, 220, 90), (255, 255, 230)])


def defeat_banner() -> None:
    audio.sfx("defeat")
    banner("DEFEATED", [(120, 20, 30), (235, 70, 80), (255, 140, 130)], 14)


def level_up_banner(level, hp_bonus, atk_bonus) -> None:
    audio.sfx("level_up")
    w = min(pw(), 50)
    inner = w - 4
    title = grad_text("✦  L E V E L   U P  ✦", [GOLD, (255, 255, 255), GOLD])
    lines = [center(title, inner),
             center(f"{DIM}Level {level - 1}  ➜  {RESET}{BOLD}{rgb(*GOLD)}Level {level}{RESET}", inner),
             center(f"{rgb(*LEAF)}Max HP +{hp_bonus}   ATK +{atk_bonus}{RESET}", inner),
             center(f"{DIM}HP & chakra fully restored{RESET}", inner)]
    if not FAST:
        spark = "✦ · ˚ ✦ · ˚ ✦ · ˚ ✦ · ˚ ✦"
        for k in range(4):
            say(center(f"{rgb(*mix(GOLD, (255, 255, 255), k / 3))}{spark}{RESET}", w).rstrip(), None)
            sleep(0.06)
    show(panel(lines, "", GOLD, ORANGE, w, kind="double"))


def grad_text(text, keys, bold=True, offset=0.0) -> str:
    n = max(1, len(text) - 1)
    return "".join(f"{BOLD if bold else ''}{rgb(*grad(keys, (i / n + offset) % 1.0))}{ch}"
                   for i, ch in enumerate(text)) + RESET


def style_colored(style, text) -> str:
    return f"{rgb(*STYLE_RGB.get(style, (255, 255, 255)))}{BOLD}{text}{RESET}"


def typewrite(text, delay=0.03, c=None) -> None:
    pre = mpad()
    out(pre + (rgb(*c) if c else ""))
    for ch in text:
        out(ch)
        sleep(delay)
    out(RESET + "\n")


def countdown_bar(seconds, label="", c=GOLD, width=40) -> None:
    """A bar that drains over `seconds` (visual timer)."""
    if FAST:
        return
    steps = int(seconds / 0.05)
    for i in range(steps + 1):
        left = 1 - i / steps
        out("\r" + mpad() + f"{DIM}{label}{RESET} {bar(left * 100, 100, width, 'x')}  ")
        time.sleep(0.05)
    out("\r" + " " * (term_w() - 1) + "\r")


# ═════════════════════════════════════════════════════
#  title splash + main menu
# ═════════════════════════════════════════════════════
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.cells = [[None] * w for _ in range(h)]

    def put(self, x, y, ch, col, bold=False):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.cells[y][x] = (ch, col, bold)

    def lines(self):
        res = []
        for row in self.cells:
            s = []
            for cell in row:
                if cell is None:
                    s.append(" ")
                else:
                    ch, col, b = cell
                    s.append(f"{BOLD if b else ''}{rgb(*col)}{ch}{RESET}")
            res.append("".join(s))
        return res


TIPS = [
    "Jutsu cost chakra — basic attacks and Guard win it back.",
    "Your home village's country gives +15% EXP on every chapter.",
    "Reach Jonin to awaken your nature and unlock a signature jutsu.",
    "Press Ctrl+C while story text types to skip to the end.",
    "Train between chapters — three mini-games raise STR, SPD and END.",
    "Kage-Level shinobi can forge a jutsu of their very own.",
]

_KEY_WO = [(255, 120, 30), (255, 200, 70), (255, 245, 200)]
_KEY_SH = [(255, 150, 40), (255, 225, 110), (255, 255, 255), (130, 200, 255)]


def _compact_title() -> None:
    t = grad_text("T H E   W O R L D   O F   S H I P P U D E N", _KEY_SH)
    show(["", center(f"{DIM}━━━━━━━━━━━━  ✦  ━━━━━━━━━━━━{RESET}", 60), center(t, 60),
          center(f"{DIM}━━━━━━━━━━━━  ✦  ━━━━━━━━━━━━{RESET}", 60), ""])


def title_splash() -> None:
    tw = term_w()
    tagline = "A   N A R U T O   S H I P P U D E N   T E X T   R P G"
    if FAST or tw < 58 or term_h() < 22:
        clear()
        _compact_title()
        say(f"{DIM}{tagline}{RESET}")
        out("\n")
        flush_stdin()
        input(mpad() + f"{DIM}▸ PRESS ENTER{RESET} ")
        return

    W, H = min(tw, 80), 15
    wo, sh = big_text("WORLD OF"), big_text("SHIPPUDEN")
    x_wo, x_sh = (W - len(wo[0])) // 2, (W - len(sh[0])) // 2
    parts = [dict(x=random.uniform(0, W), y=random.uniform(0, H),
                  vx=random.uniform(0.4, 1.3), vy=random.uniform(0.05, 0.35),
                  ch=random.choice("·*˚◦✦"),
                  col=random.choice([(120, 215, 120), (160, 235, 130), (255, 170, 70), (200, 255, 200)]))
             for _ in range(30)]
    total, hold = 46, 12

    def render(f):
        cv = Canvas(W, H)
        for pt in parts:
            cv.put(int(pt["x"]) % W, int(pt["y"]) % H, pt["ch"], pt["col"])
            pt["x"] += pt["vx"]
            pt["y"] += pt["vy"]
        p = min(1.0, f / (total - hold))
        for ch_i, ch in enumerate("T H E"):
            if p > 0.05 and ch != " ":
                cv.put((W - 5) // 2 + ch_i, 2, ch, (170, 170, 185))
        for rows, x0, y0, keys, pr in ((wo, x_wo, 3, _KEY_WO, p),
                                       (sh, x_sh, 9, _KEY_SH, max(0.0, (p - 0.25) / 0.75))):
            if pr <= 0:
                continue
            L = len(rows[0])
            reveal = pr * (L + 8) - 2
            shine = reveal if pr < 1 else ((f - (total - hold)) / hold) * (L + 14) - 4
            for r, row in enumerate(rows):
                for c, ch in enumerate(row):
                    if ch == " " or c > reveal:
                        continue
                    cv.put(x0 + c, y0 + r, ch, _shine(grad(keys, c / max(1, L - 1)), c, shine), True)
        if f > total * 0.8:
            orn = "────────────  ✦  ────────────"
            for i, ch in enumerate(orn):
                cv.put((W - len(orn)) // 2 + i, 14, ch, dimc(GOLD, 0.7 if ch != "✦" else 1))
        return cv.lines()

    m = " " * margin(W)
    clear()
    cursor(False)
    for f in range(total):
        if f == 0:
            audio.sfx("title_whoosh")
        if f == total - hold:
            audio.sfx("title_boom")
        if f:
            out(f"\033[{H}A")
        out("".join(m + l + "\033[K\n" for l in render(f)))
        time.sleep(0.04)
    out("\n")
    typewrite_center(tagline, W)
    out("\n")
    flush_stdin()
    for k in range(4):
        col = PAPER if k % 2 == 0 else (110, 110, 125)
        out("\r" + m + center(f"{rgb(*col)}{BOLD}▶  PRESS  ENTER  ◀{RESET}", W) + "\033[K")
        time.sleep(0.16)
    cursor(True)
    out("\r")
    input(m + center(f"{rgb(*PAPER)}{BOLD}▶  PRESS  ENTER  ◀{RESET} ", W))


def typewrite_center(text, W, delay=0.012):
    m = " " * margin(W)
    out(m + " " * ((W - len(text)) // 2) + DIM)
    for ch in text:
        out(ch)
        time.sleep(delay)
    out(RESET + "\n")


def audio_status() -> str:
    if not audio.available():
        return f"{DIM}(no audio device found){RESET}"
    c = audio.settings()
    on = lambda v: f"{GREEN}ON{RESET}{DIM}" if v else f"{RED}OFF{RESET}{DIM}"
    return f"{DIM}♪ {on(c['music'])} · ♫ {on(c['sfx'])}{RESET}"


def animated_main_menu() -> None:
    clear()
    t = grad_text("T H E   W O R L D   O F   S H I P P U D E N", _KEY_SH)
    w = pw()
    show(["", center(f"{DIM}━━━━━━━━━━━━━━━  ✦  ━━━━━━━━━━━━━━━{RESET}", w), center(t, w),
          center(f"{DIM}━━━━━━━━━━━━━━━  ✦  ━━━━━━━━━━━━━━━{RESET}", w), ""])
    rows = []
    rows += opt(1, "New Game", "Begin a new shinobi's journey")
    rows += opt(2, "Load Game", "Continue from shippuden_save.json")
    rows += opt(3, "Sound", "Music & effects  " + audio_status())
    rows += opt(0, "Quit")
    show(panel(rows, "MAIN MENU", ORANGE, SKY, width=min(w, 50)))
    say(f"{DIM}Tip: {random.choice(TIPS)}{RESET}")
    out("\n")


# ═════════════════════════════════════════════════════
#  clan reveal (slot-machine reel)
# ═════════════════════════════════════════════════════
def clan_reveal(names, chosen, rarity) -> None:
    col = RARITY_RGB.get(rarity, PAPER)
    w = pw()
    m = " " * margin(w)
    cursor(False)
    steps = 1 if FAST else 28
    for i in range(steps):
        nm = chosen if i == steps - 1 else random.choice(names)
        c = mix((150, 150, 165), col, i / steps)
        audio.sfx("tick", gap=0.05)
        out("\r" + m + center(f"{rgb(*c)}◂  {BOLD}{nm:^14}{RESET}{rgb(*c)}  ▸{RESET}", w) + "\033[K")
        sleep(0.03 + (i / steps) ** 2 * 0.2)
    audio.sfx({"Common": "reveal_low", "Uncommon": "reveal_low", "Rare": "reveal_mid"}.get(rarity, "reveal_high"))
    if not FAST:
        for k in range(8):
            c = (255, 255, 255) if k % 2 == 0 else col
            out("\r" + m + center(f"{rgb(*c)}{BOLD}✦  {chosen:^14}  ✦{RESET}", w) + "\033[K")
            time.sleep(0.07)
    out("\n")
    cursor(True)


# ═════════════════════════════════════════════════════
#  battle screen
# ═════════════════════════════════════════════════════
_FX = {
    "Basic":     dict(g="─/✦", c=[(255, 255, 255), (210, 215, 230), (140, 145, 165)], trail=10, dens=.7),
    "Enemy":     dict(g="✦╲─", c=[(255, 255, 255), (255, 140, 120), (200, 50, 60)], trail=12, dens=.75),
    "Fire":      dict(g="▲✦*^", c=[(255, 240, 120), (255, 150, 40), (220, 60, 30)], trail=18, dens=.9, jit=True),
    "Water":     dict(g="~≈~-", c=[(210, 240, 255), (80, 170, 255), (40, 100, 220)], trail=20, dens=.85),
    "Wind":      dict(g="─═≡»", c=[(235, 255, 245), (150, 255, 200), (70, 200, 150)], trail=24, dens=.55),
    "Lightning": dict(g="╱╲/\\", c=[(255, 255, 255), (255, 240, 90), (200, 170, 40)], trail=14, dens=.6, zig=True),
    "Earth":     dict(g="▓▒■▪", c=[(235, 200, 150), (200, 150, 90), (120, 90, 55)], trail=14, dens=.8),
    "Shadow":    dict(g="◆◇▒░", c=[(220, 190, 255), (170, 110, 255), (90, 55, 150)], trail=20, dens=.8),
    "Taijutsu":  dict(g="»›●✦", c=[(255, 255, 200), (120, 255, 120), (60, 170, 70)], trail=9, dens=.9),
    "Genjutsu":  dict(g="◎○◉@", c=[(255, 200, 220), (255, 70, 110), (150, 30, 80)], trail=18, dens=.8, jit=True),
}


def _fx_frame(style, f, n, W, rows=3, rtl=False):
    sp = _FX.get(style, _FX["Basic"])
    grid = [[None] * W for _ in range(rows)]
    prog = f / max(1, n - 1)
    head = int(prog * (W - 10)) + 2
    if sp.get("zig"):
        head += random.randint(-2, 2)
    trail, cols = sp["trail"], sp["c"]
    for r in range(rows):
        for k in range(trail):
            x = head - k
            if 0 <= x < W and random.random() < sp["dens"] * (1 - k / trail):
                col = dimc(cols[min(len(cols) - 1, k * len(cols) // trail)], 1 - 0.45 * k / trail)
                rr = max(0, min(rows - 1, r + (random.randint(-1, 1) if sp.get("jit") else 0)))
                grid[rr][x] = (random.choice(sp["g"]), col)
    if prog > 0.78:
        cx, spr = W - 9, int((prog - 0.78) / 0.22 * 8) + 2
        for r in range(rows):
            for x in range(max(0, cx - spr), min(W, cx + spr)):
                if random.random() < 0.65:
                    grid[r][x] = (random.choice(sp["g"]), random.choice(cols))
    if rtl:
        grid = [row[::-1] for row in grid]
    return ["".join(f"{rgb(*c[1])}{c[0]}" if c else " " for c in row) + RESET for row in grid]


class BattleScreen:
    """Redraws in place (cursor-home) so bars drain smoothly with no flicker."""

    def __init__(self, player, enemy):
        self.p, self.e = player, enemy
        self.sp = self.se = self.sc = 0
        self.pg = self.eg = None
        self.flash = None
        self.dx = 0
        self.turn = 1
        self.arena = None
        self.log = []
        self.menu_title = "YOUR TURN"
        self.menu = []
        self.hint = ""
        self._first = True
        if FAST:
            self._settle()

    # ── layout ───────────────────────────────────────
    def _settle(self):
        self.sp, self.se, self.sc = self.p.hp, self.e.hp, self.p.chakra

    def _hp_line(self, label, cur, mx, ghost, kind, inner):
        bw = max(12, min(46, inner - 17))
        return bar_line(label, cur, mx, bw, kind, ghost)

    def _log_lines(self):
        last = self.log[-3:]
        rows = [""] * (3 - len(last))
        for i, l in enumerate(last):
            newest = i == len(last) - 1
            rows.append(" " + (l if newest else f"{DIM}{strip(l)}{RESET}"))
        return rows

    def render(self):
        w = pw()
        inner = w - 4
        p, e = self.p, self.e
        rev_e = "\033[7m" if self.flash == "e" else ""
        rev_p = "\033[7m" if self.flash == "p" else ""
        sty = style_colored(p.style, p.get_style_name()) if p.style else f"{DIM}no style{RESET}"
        rows = [
            spread(f"{rev_e}{BOLD}{rgb(*CRIMSON)}☠ {e.name.upper()}{RESET}", f"{DIM}{e.enemy_type}{RESET}", inner),
            self._hp_line("HP ", self.se, e.max_hp, self.eg, "hp", inner),
            SEP,
            *(self.arena if self.arena is not None else self._log_lines()),
            SEP,
            spread(f"{rev_p}{BOLD}{rgb(*PAPER)}✦ {p.name}{RESET}",
                   f"{DIM}Lv {p.level} · {p.rank} ·{RESET} {sty}", inner),
            self._hp_line("HP ", self.sp, p.max_hp, self.pg, "hp", inner),
            self._hp_line("CHK", self.sc, p.max_chakra, None, "chakra", inner),
        ]
        battle = panel(rows, f"BATTLE · TURN {self.turn}", (235, 80, 80), (255, 190, 70), w)
        menu_rows = list(self.menu) + ([f"{YELLOW}{self.hint}{RESET}"] if self.hint else [])
        return battle + panel(menu_rows, self.menu_title, (80, 170, 255), (150, 120, 255), w)

    def draw(self):
        lines = self.render()
        m = margin(vlen(lines[0]))
        if not TTY:
            out("".join(" " * m + l + "\n" for l in lines))
            return
        buf = "\033[?25l"
        if self._first:
            buf += "\033[2J"
            self._first = False
        buf += "\033[H" + "".join(" " * max(0, m + self.dx) + l + "\033[K\n" for l in lines) + "\033[J"
        out(buf)

    def _frame(self, t=0.03):
        if not FAST:
            self.draw()
            sleep(t)

    # ── public: input ────────────────────────────────
    def ask(self, prompt="»") -> str:
        self.arena = None
        self.draw()
        cursor(True)
        flush_stdin()
        return input(" " * margin(pw()) + f"{rgb(*GOLD)}{BOLD}{prompt}{RESET} ").strip().lower()

    def set_menu(self, title, lines, hint=""):
        self.menu_title, self.menu, self.hint = title, lines, hint

    def say(self, text):
        self.log.append(text)
        self.arena = None

    def busy(self, text="…"):
        self.menu_title, self.menu, self.hint = text, [f"{DIM}Resolving the turn…{RESET}"], ""

    # ── animation primitives ─────────────────────────
    def intro(self, name):
        audio.sfx("battle_start")
        self.say(f"{BOLD}{name}{RESET} blocks your path!")
        if FAST:
            return
        inner = pw() - 4
        for k in range(5):
            c = (255, 255, 255) if k % 2 == 0 else CRIMSON
            self.arena = ["", center(f"{rgb(*c)}{BOLD}»»   B A T T L E   S T A R T   ««{RESET}", inner), ""]
            self._frame(0.1)
        p_t, e_t = (self.p.hp, self.e.hp), self.p.chakra
        for i in range(1, 13):
            t = i / 12
            self.sp, self.se, self.sc = int(p_t[0] * t), int(p_t[1] * t), int(e_t * t)
            self._frame(0.022)
        self._settle()
        self.arena = None

    def _anim_hp(self, who, frames=14):
        attr, gattr = ("se", "eg") if who == "e" else ("sp", "pg")
        new = (self.e if who == "e" else self.p).hp
        old = getattr(self, attr)
        if FAST or old == new:
            setattr(self, attr, new)
            return
        if new > old:
            for i in range(1, 9):
                setattr(self, attr, old + (new - old) * i / 8)
                self._frame(0.025)
            setattr(self, attr, new)
            return
        setattr(self, attr, new)
        for i in range(frames):
            setattr(self, gattr, old + (new - old) * (i + 1) / frames)
            self._frame(0.028)
        setattr(self, gattr, None)

    def _anim_chk(self):
        new, old = self.p.chakra, self.sc
        if FAST or new == old:
            self.sc = new
            return
        for i in range(1, 7):
            self.sc = old + (new - old) * i / 6
            self._frame(0.02)
        self.sc = new

    def sync(self):
        self._anim_hp("e")
        self._anim_hp("p")
        self._anim_chk()
        self.arena = None
        self.flash = None

    def _fx(self, style, rtl=False, n=11):
        if FAST:
            return
        inner = pw() - 4
        for f in range(n):
            self.arena = _fx_frame(style, f, n, inner, rtl=rtl)
            self._frame(0.03)

    def _banner(self, name, style, ult):
        if FAST:
            return
        col = STYLE_RGB.get(style, PAPER)
        inner = pw() - 4
        if ult:
            for k in (0.4, 0.8, 1.0, 0.6):
                row = f"{rgb(*dimc(col, k))}{'▓' * inner}{RESET}"
                self.arena = [row, row, row]
                self._frame(0.05)
        text = f"✦ {name} ✦" if ult else f"»  {name}  «"
        self.arena = ["", center(f"{BOLD}{rgb(*col)}{text}{RESET}", inner), ""]
        self._frame(0.55 if ult else 0.35)

    def _popup_rows(self, text, x, row, col):
        inner = pw() - 4
        rows = [""] * 3
        rows[row] = " " * max(0, x - len(strip(text)) // 2) + f"{BOLD}{rgb(*col)}{text}{RESET}"
        return rows

    def _impact(self, who, text, col):
        if FAST:
            return
        inner = pw() - 4
        x = int(inner * (0.78 if who == "e" else 0.2))
        self.flash = who
        for row in (2, 1):
            self.arena = self._popup_rows(text, x, row, col)
            self._frame(0.04)
            if who == "p":
                self.dx = 2 if row == 2 else -2
        if who == "p":
            for dx in (2, -2, 1, -1, 0):
                self.dx = dx
                self.arena = self._popup_rows(text, x, 1, col)
                self._frame(0.03)
        self.flash = None
        self.arena = self._popup_rows(text, x, 0, col)
        self.dx = 0

    def _hold(self, t=0.3):
        if not FAST:
            self._frame(t)
        self.arena = None

    # ── public: combat events ────────────────────────
    def player_attack(self, dmg, style=None, name=None, ult=False, awakened=False):
        self.busy()
        if name:
            audio.sfx("ult_charge" if ult else "jutsu_" + (style or "").lower())
            self._banner(name, style, ult)
        else:
            audio.sfx("slash")
        self._fx(style or "Basic")
        col = STYLE_RGB.get(style, (255, 255, 255))
        audio.sfx("hit_heavy" if name else "hit")
        self._impact("e", f"-{dmg}", col)
        self._anim_hp("e")
        self._anim_chk()
        self._hold()
        tag = f" {YELLOW}[AWAKENED]{RESET}" if awakened else ""
        if name:
            self.say(f"{style_colored(style, name)} hits for {GREEN}{BOLD}{dmg}{RESET}!{tag}")
        else:
            self.say(f"You strike for {GREEN}{dmg}{RESET} damage!{tag}")
        self.sync()

    def enemy_attack(self, dmg, crit=False, blocked=0):
        self.busy("ENEMY TURN")
        audio.sfx("enemy_swing")
        self._fx("Enemy", rtl=True)
        text = f"CRITICAL!  -{dmg}" if crit else f"-{dmg}"
        audio.sfx("crit" if crit else "hurt")
        self._impact("p", text, (255, 215, 90) if crit else (255, 110, 110))
        self._anim_hp("p")
        self._hold()
        name = self.e.name
        if blocked:
            self.say(f"{name} strikes — you take {RED}{dmg}{RESET} {DIM}(blocked {blocked}){RESET}.")
        elif crit:
            self.say(f"{RED}{BOLD}{name} lands a CRITICAL HIT for {dmg}!{RESET}")
        else:
            self.say(f"{name} attacks for {RED}{dmg}{RESET} damage.")
        self.sync()

    def dodge(self):
        self.busy("ENEMY TURN")
        audio.sfx("enemy_swing")
        if not FAST:
            inner = pw() - 4
            self._fx("Enemy", rtl=True, n=8)
            audio.sfx("dodge")
            for row in (2, 1, 0):
                self.arena = self._popup_rows("DODGE!", int(inner * 0.2), row, (110, 230, 255))
                self._frame(0.05)
            self._hold(0.2)
        self.say(f"{CYAN}{self.e.name} attacks — you slip past it!{RESET}")
        self.sync()

    def guard(self, gained):
        self.busy()
        audio.sfx("guard")
        audio.sfx("chakra", gap=0.2)
        if not FAST:
            inner = pw() - 4
            for k in range(4):
                shield = "▓▒░ G U A R D ░▒▓" if k % 2 == 0 else "░▒▓ G U A R D ▓▒░"
                self.arena = ["", " " * int(inner * 0.08) + f"{BOLD}{rgb(*SKY)}{shield}{RESET}", ""]
                self._frame(0.07)
        self.say(f"{BLUE}You guard and gather your chakra.{RESET} {DIM}(+{gained} CHK){RESET}")
        self.sync()

    def awaken(self, name, desc):
        self.busy()
        audio.sfx("awaken")
        self._banner(name, self.p.style, True)
        self.say(f"{YELLOW}{BOLD}✦ {name.upper()} ✦{RESET}  {DIM}{desc}{RESET}")
        self.say(f"{RED}-10 HP{RESET} · {GREEN}Damage ×2 and free chakra this turn!{RESET}")
        self.sync()

    def finish(self):
        self.arena = None
        self.flash = None
        self.dx = 0
        cursor(True)
