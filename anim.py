# ═══════════════════════════════════════════════════════
#  anim.py — animated text / visual effects
#  Pure standard library (ANSI colour codes).
# ═══════════════════════════════════════════════════════

import shutil
import sys
import time

from data import RESET, BOLD, DIM, YELLOW

# 5-row pixel font used for the big titles
_FONT = {
    "S": [" ████", "█    ", " ███ ", "    █", "████ "],
    "H": ["█   █", "█   █", "█████", "█   █", "█   █"],
    "I": ["███", " █ ", " █ ", " █ ", "███"],
    "N": ["█   █", "██  █", "█ █ █", "█  ██", "█   █"],
    "O": [" ███ ", "█   █", "█   █", "█   █", " ███ "],
    "B": ["████ ", "█   █", "████ ", "█   █", "████ "],
    "C": [" ████", "█    ", "█    ", "█    ", " ████"],
    "R": ["████ ", "█   █", "████ ", "█  █ ", "█   █"],
    "L": ["█    ", "█    ", "█    ", "█    ", "█████"],
    "E": ["█████", "█    ", "████ ", "█    ", "█████"],
    "A": [" ███ ", "█   █", "█████", "█   █", "█   █"],
    "T": ["█████", "  █  ", "  █  ", "  █  ", "  █  "],
    "W": ["█   █", "█   █", "█ █ █", "██ ██", "█   █"],
    "D": ["████ ", "█   █", "█   █", "█   █", "████ "],
    "F": ["█████", "█    ", "████ ", "█    ", "█    "],
    "P": ["████ ", "█   █", "████ ", "█    ", "█    "],
    "U": ["█   █", "█   █", "█   █", "█   █", " ███ "],
    " ": ["   ", "   ", "   ", "   ", "   "],
}

# jutsu-style colour palettes (RGB)
STYLE_RGB = {
    "Fire": (255, 120, 40), "Water": (60, 150, 255), "Wind": (150, 255, 200),
    "Lightning": (255, 240, 90), "Earth": (200, 150, 90), "Shadow": (170, 110, 255),
    "Taijutsu": (120, 255, 120), "Genjutsu": (255, 70, 110),
}

GRADIENT = [(255, 140, 30), (255, 200, 60), (255, 255, 255), (120, 200, 255), (255, 140, 30)]


def _rgb(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def _term_w() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def _lerp_color(keys: list, t: float) -> tuple:
    t = t % 1.0
    n = len(keys) - 1
    lo = int(t * n)
    hi = min(lo + 1, n)
    f = t * n - lo
    return tuple(int(keys[lo][i] + (keys[hi][i] - keys[lo][i]) * f) for i in range(3))


def big_text(text: str) -> list:
    rows = ["", "", "", "", ""]
    for ch in text.upper():
        glyph = _FONT.get(ch, _FONT[" "])
        for i in range(5):
            rows[i] += glyph[i] + " "
    return rows


def _print_centered(rows: list, color: str) -> None:
    width = _term_w()
    for row in rows:
        pad = max(0, (width - len(row)) // 2)
        print(f"{color}{BOLD}{' ' * pad}{row}{RESET}")


def _animate_rows(rows: list, keys: list, frames: int = 16) -> None:
    pad = max(0, (_term_w() - max(len(r) for r in rows)) // 2)
    n = len(rows)
    first = True
    for i in range(frames):
        r, g, b = _lerp_color(keys, (i / frames) * 0.8)
        if not first:
            sys.stdout.write(f"\033[{n}A")
        first = False
        for row in rows:
            sys.stdout.write(f"\033[2K{_rgb(r, g, b)}{BOLD}{' ' * pad}{row}{RESET}\n")
        sys.stdout.flush()
        time.sleep(0.03)


# ── headers ──────────────────────────────────────────────
def ascii_header(title: str, color_rgb: tuple = None) -> None:
    """Section header: a clean banner with an underline."""
    width = _term_w()
    r, g, b = color_rgb or (255, 180, 60)
    line = "═" * min(width - 4, max(len(title) + 8, 40))
    pad = max(0, (width - len(line)) // 2)
    print()
    print(f"{_rgb(r, g, b)}{' ' * pad}{line}{RESET}")
    tpad = max(0, (width - len(title)) // 2)
    print(f"{_rgb(r, g, b)}{BOLD}{' ' * tpad}{title}{RESET}")
    print(f"{_rgb(r, g, b)}{' ' * pad}{line}{RESET}")
    print()


def battle_header() -> None:
    rows = big_text("BATTLE")
    _print_centered(rows, _rgb(255, 90, 90))
    print()


def title_splash() -> None:
    print("[2J[H", end="")
    print("\n")
    print(f"{DIM}{' ' * max(0, (_term_w() - 7) // 2)}T H E{RESET}\n")
    _animate_rows(big_text("WORLD OF"), GRADIENT, 22)
    print()
    _animate_rows(big_text("SHIPPUDEN"), GRADIENT[::-1], 22)
    print()
    sub = "NARUTO SHIPPUDEN  ·  A TEXT-BASED PYTHON RPG"
    print(f"{DIM}{' ' * max(0, (_term_w() - len(sub)) // 2)}{sub}{RESET}\n")
    time.sleep(0.5)


def animated_main_menu() -> None:
    print("[2J[H", end="")
    print("\n")
    print(f"{DIM}{' ' * max(0, (_term_w() - 7) // 2)}T H E{RESET}\n")
    _print_centered(big_text("WORLD OF"), _rgb(255, 170, 50))
    print()
    _print_centered(big_text("SHIPPUDEN"), _rgb(120, 200, 255))
    print()
    print("  [1] New Game")
    print("  [2] Load Game")
    print("  [0] Quit\n")


# ── jutsu effects ────────────────────────────────────────
def style_colored(style: str, text: str) -> str:
    r, g, b = STYLE_RGB.get(style, (255, 255, 255))
    return f"{_rgb(r, g, b)}{BOLD}{text}{RESET}"


def jutsu_banner(style: str, jutsu_name: str, duration: float = 0.25) -> None:
    r, g, b = STYLE_RGB.get(style, (255, 255, 255))
    text = f"»»  {jutsu_name}  ««"
    print()
    for i in range(4):
        k = 0.5 + 0.5 * (i / 3)
        print(f"\r  {_rgb(int(r * k), int(g * k), int(b * k))}{BOLD}{text}{RESET}", end="", flush=True)
        time.sleep(duration / 4)
    print()


def ultimate_flash(style: str, name: str) -> None:
    r, g, b = STYLE_RGB.get(style, (255, 255, 255))
    width = min(_term_w() - 4, 60)
    bar = "▓" * width
    print()
    for k in (0.4, 0.7, 1.0, 0.7, 1.0):
        print(f"  {_rgb(int(r * k), int(g * k), int(b * k))}{bar}{RESET}")
        time.sleep(0.05)
    print(f"\n  {YELLOW}{BOLD}✦ ULTIMATE ✦{RESET}  {style_colored(style, name)}\n")
    for k in (1.0, 0.7, 0.4):
        print(f"  {_rgb(int(r * k), int(g * k), int(b * k))}{bar}{RESET}")
        time.sleep(0.05)
    print()
