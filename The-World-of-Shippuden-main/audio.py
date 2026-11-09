"""
audio.py — music + sound effects for THE WORLD OF SHIPPUDEN.

No setup needed: it plays the WAV files in assets/ with whatever the OS offers.
Backend order:
  1. pygame        (pip install pygame — best: real mixing, no gaps in loops)
  2. Windows       (built-in winsound for music + MCI for effects)
  3. macOS / Linux (afplay / paplay / aplay / ffplay / play / mpv as a child process)
If nothing works, the game simply runs silent. Audio can never crash the game.

Switches
  SHIPPUDEN_MUTE=1   start muted
  SHIPPUDEN_FAST=1   (or piped output) — audio is off automatically
  Sound menu in-game (main menu [3], game menu [S]) toggles music / effects.
"""
import atexit
import json
import os
import shutil
import subprocess
import sys
import threading
import time

BASE = os.path.dirname(os.path.abspath(__file__))
SFX_DIR = os.path.join(BASE, "assets", "sfx")
MUS_DIR = os.path.join(BASE, "assets", "music")
SETTINGS = os.path.join(BASE, "shippuden_audio.json")

_ACTIVE = sys.stdout.isatty() and not os.environ.get("SHIPPUDEN_FAST")
_DEBUG = os.environ.get("SHIPPUDEN_AUDIO_DEBUG")        # log events instead of playing (tests)

_lock = threading.RLock()
_backend = None
_inited = False
_track = None                 # the track the game WANTS right now
_playing = None               # the track actually playing
_last = {}                    # per-sfx throttle
_cfg = {"music": True, "sfx": True}
log = []                      # filled when SHIPPUDEN_AUDIO_DEBUG is set


# ═════════════════════════════════════════════════════
#  backends
# ═════════════════════════════════════════════════════
class _Null:
    name = "none"

    def sfx(self, path): pass
    def music(self, path): pass
    def stop_music(self): pass
    def close(self): pass


class _Debug(_Null):
    name = "debug"

    def sfx(self, path): log.append(("sfx", os.path.basename(path)[:-4]))
    def music(self, path): log.append(("music", os.path.basename(path)[:-4]))
    def stop_music(self): log.append(("music", None))


class _Pygame(_Null):
    name = "pygame"

    def __init__(self):
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        import pygame
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)
        self.pg = pygame
        self.cache = {}

    def sfx(self, path):
        s = self.cache.get(path)
        if s is None:
            s = self.cache[path] = self.pg.mixer.Sound(path)
            s.set_volume(0.9)
        s.play()

    def music(self, path):
        m = self.pg.mixer.music
        m.fadeout(250) if m.get_busy() else None
        m.load(path)
        m.set_volume(0.8)
        m.play(-1)

    def stop_music(self):
        self.pg.mixer.music.fadeout(300)

    def close(self):
        try:
            self.pg.mixer.quit()
        except Exception:
            pass


class _Windows(_Null):
    """music: winsound loop · effects: MCI (so both can play at once)"""
    name = "windows"

    def __init__(self):
        import ctypes
        import winsound
        self.ws = winsound
        self.mci = ctypes.windll.winmm.mciSendStringW
        self.opened = {}

    def _mci(self, cmd):
        return self.mci(cmd, None, 0, None)

    def sfx(self, path):
        alias = self.opened.get(path)
        if alias is None:
            alias = "sh_" + os.path.basename(path)[:-4]
            if self._mci(f'open "{path}" type waveaudio alias {alias}') != 0:
                self.opened[path] = False
                return
            self.opened[path] = alias
        if alias:
            self._mci(f"play {alias} from 0")

    def music(self, path):
        self.ws.PlaySound(path, self.ws.SND_FILENAME | self.ws.SND_ASYNC | self.ws.SND_LOOP)

    def stop_music(self):
        self.ws.PlaySound(None, self.ws.SND_PURGE)

    def close(self):
        self.stop_music()
        for alias in self.opened.values():
            if alias:
                self._mci(f"close {alias}")


class _Process(_Null):
    """afplay / paplay / aplay / ffplay … one child process per sound"""
    name = "process"

    PLAYERS = (
        ("afplay", ["afplay"]),
        ("paplay", ["paplay"]),
        ("aplay", ["aplay", "-q"]),
        ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]),
        ("play", ["play", "-q"]),
        ("mpv", ["mpv", "--no-video", "--really-quiet"]),
    )

    def __init__(self):
        for exe, cmd in self.PLAYERS:
            if shutil.which(exe):
                self.cmd = cmd
                self.exe = exe
                break
        else:
            raise RuntimeError("no audio player found")
        self.gen = 0
        self.proc = None

    def _spawn(self, path):
        kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.name == "posix":
            kw["start_new_session"] = True      # Ctrl+C in the game must not kill the music
        return subprocess.Popen(self.cmd + [path], **kw)

    def sfx(self, path):
        try:
            self._spawn(path)
        except OSError:
            pass

    def music(self, path):
        self.stop_music()
        self.gen += 1
        gen = self.gen

        def loop():
            while gen == self.gen:
                try:
                    self.proc = self._spawn(path)
                    self.proc.wait()
                except OSError:
                    return
                if gen == self.gen and self.proc.returncode not in (0, None):
                    return                       # player failed — don't spin

        threading.Thread(target=loop, daemon=True).start()

    def stop_music(self):
        self.gen += 1
        p = self.proc
        if p and p.poll() is None:
            try:
                p.terminate()
            except OSError:
                pass

    def close(self):
        self.stop_music()


# ═════════════════════════════════════════════════════
#  public API  (every call is safe — never raises)
# ═════════════════════════════════════════════════════
def init() -> str:
    """Pick a backend and load saved settings. Safe to call many times."""
    global _backend, _inited
    with _lock:
        if _inited:
            return _backend.name
        _inited = True
        _load_cfg()
        if os.environ.get("SHIPPUDEN_MUTE"):
            _cfg["music"] = _cfg["sfx"] = False
        if _DEBUG:
            _backend = _Debug()
        elif not _ACTIVE or not os.path.isdir(SFX_DIR):
            _backend = _Null()
        else:
            _backend = _Null()
            candidates = [_Pygame]
            if os.name == "nt":
                candidates.append(_Windows)
            candidates.append(_Process)
            for cls in candidates:
                try:
                    _backend = cls()
                    break
                except Exception:
                    continue
        atexit.register(shutdown)
        return _backend.name


def backend_name() -> str:
    init()
    return _backend.name


def available() -> bool:
    init()
    return _backend.name != "none"


def sfx(name: str, gap: float = 0.0) -> None:
    """Play a sound effect (fire-and-forget). `gap` = ignore repeats within that many seconds."""
    try:
        init()
        if not _cfg["sfx"]:
            return
        now = time.time()
        if now - _last.get(name, 0) < max(gap, 0.03):
            return
        _last[name] = now
        path = os.path.join(SFX_DIR, name + ".wav")
        if _DEBUG or os.path.exists(path):
            _backend.sfx(path)
    except Exception:
        pass


def music(track) -> None:
    """Switch background music (None = silence). Does nothing if that track is already playing."""
    global _track, _playing
    try:
        init()
        with _lock:
            _track = track
            if not _cfg["music"]:
                return
            if track == _playing:
                return
            _playing = track
            if track is None:
                _backend.stop_music()
                return
            path = os.path.join(MUS_DIR, track + ".wav")
            if _DEBUG or os.path.exists(path):
                _backend.music(path)
    except Exception:
        pass


def current():
    return _track


def settings() -> dict:
    init()
    return dict(_cfg)


def set_music(on: bool) -> None:
    global _playing
    init()
    with _lock:
        _cfg["music"] = bool(on)
        _save_cfg()
        if not on:
            _playing = None
            try:
                _backend.stop_music()
            except Exception:
                pass
        else:
            want, _playing = _track, None
            music(want)


def set_sfx(on: bool) -> None:
    init()
    _cfg["sfx"] = bool(on)
    _save_cfg()
    if on:
        sfx("ui_select")


def shutdown() -> None:
    global _playing
    try:
        if _backend:
            _backend.close()
    except Exception:
        pass
    _playing = None


def _load_cfg() -> None:
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            d = json.load(f)
        for k in _cfg:
            if k in d:
                _cfg[k] = bool(d[k])
    except (OSError, ValueError):
        pass


def _save_cfg() -> None:
    try:
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(_cfg, f)
    except OSError:
        pass
