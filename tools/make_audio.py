#!/usr/bin/env python3
"""
Synthesizes every sound effect and music loop for THE WORLD OF SHIPPUDEN.
All audio is generated from scratch (no samples, no copyrighted music) —
original taiko / koto / shakuhachi-style sounds in Japanese scales.

    pip install numpy
    python tools/make_audio.py          # (re)writes assets/sfx/*.wav, assets/music/*.wav

The game does NOT need numpy — it only plays the WAV files that this script made.
"""
import os
import sys
import wave

import numpy as np

SR = 22050
rng = np.random.default_rng(2026)
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


# ═════════════════════════════════════════════════════
#  DSP building blocks
# ═════════════════════════════════════════════════════
def T(d):
    return np.arange(int(d * SR)) / SR


def hz(m):
    return 440.0 * 2 ** ((np.asarray(m, dtype=float) - 69) / 12)


def sine(freq):
    return np.sin(np.cumsum(2 * np.pi * freq / SR))


def ad(n, a=0.005, r=0.05):
    """attack/release envelope"""
    e = np.ones(n)
    na, nr = min(int(a * SR), n // 2), min(int(r * SR), n // 2)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def bandnoise(d, lo, hi):
    n = int(d * SR)
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    m = np.ones_like(f)
    if lo > 0:
        m *= np.clip((f - lo * 0.8) / max(lo * 0.4, 40), 0, 1)
    if hi < SR / 2:
        m *= np.clip((hi * 1.2 - f) / max(hi * 0.4, 40), 0, 1)
    y = np.fft.irfft(X * m, n)
    return y / (np.std(y) + 1e-9) * 0.35


def sweep(d, f0, f1, bw=0.5, K=8):
    """whoosh: a band of noise that glides from f0 to f1"""
    n = int(d * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for i in range(K):
        c = f0 * (f1 / f0) ** (i / (K - 1))
        tc = d * (0.15 + 0.7 * i / (K - 1))
        sg = d * 0.9 / K + 0.01
        out += bandnoise(d, c * (1 - bw * 0.6), c * (1 + bw)) * np.exp(-(((t - tc) / sg) ** 2))
    return out / (np.max(np.abs(out)) + 1e-9) * 0.9


def buf(sec):
    return np.zeros(int(sec * SR))


def add(b, sig, at=0.0, g=1.0, wrap=False):
    s, n, N = int(at * SR), len(sig), len(b)
    if wrap:
        s %= N
        done = 0
        while done < n:
            k = min(n - done, N - s)
            b[s:s + k] += sig[done:done + k] * g
            done += k
            s = 0
    elif s < N:
        e = min(N, s + n)
        b[s:e] += sig[:e - s] * g
    return b


def reverb(x, taps, wrap=False):
    y = x.copy()
    for delay, g in taps:
        k = int(delay * SR)
        if wrap:
            y += np.roll(x, k) * g
        else:
            y[k:] += x[:-k] * g
    return y


def finish(x, peak=0.85, fade=0.01):
    x = np.asarray(x, dtype=float)
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    nf = min(int(fade * SR), len(x) // 4)
    if nf:
        x[-nf:] *= np.linspace(1, 0, nf)
    return x


def save_wav(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ═════════════════════════════════════════════════════
#  instruments
# ═════════════════════════════════════════════════════
def koto(m, d=1.2, vel=1.0):
    t, f = T(d), float(hz(m))
    s = np.zeros_like(t)
    for h, a in enumerate([1, .55, .35, .2, .12, .07], 1):
        s += a * np.sin(2 * np.pi * f * h * (1 + 0.0004 * h * h) * t) * np.exp(-(3.2 + 2.2 * h) * t)
    s[:int(.004 * SR)] += bandnoise(.004, 1500, 6000)[:int(.004 * SR)] * 1.5
    return s * vel * ad(len(t), 0.001, 0.03)


def shamisen(m, d=0.5, vel=1.0):
    t, f = T(d), float(hz(m))
    s = np.zeros_like(t)
    for h, a in enumerate([1, .9, .75, .6, .5, .35, .25, .15], 1):
        s += a * np.sin(2 * np.pi * f * h * t) * np.exp(-(5 + 1.6 * h) * t)
    n = int(.012 * SR)
    s[:n] += bandnoise(.012, 2000, 7000)[:n] * 2.0
    return s * vel * ad(len(t), 0.001, 0.02)


def flute(m, d=1.0, vel=1.0):
    t, f = T(d), float(hz(m))
    fr = f * (1 + 0.007 * np.minimum(1, t / 0.45) * np.sin(2 * np.pi * 5.3 * t))
    ph = np.cumsum(2 * np.pi * fr / SR)
    s = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    s += bandnoise(d, 1500, 5500) * 0.22 * np.minimum(1, t / 0.1) * np.exp(-t * 1.2)
    return s * vel * ad(len(t), 0.07, min(0.2, d / 2)) * (0.85 + 0.15 * np.sin(np.pi * t / d))


def pad(m, d=4.0, vel=1.0):
    t, f = T(d), float(hz(m))
    s = sum(np.sin(2 * np.pi * f * (1 + dt) * t + ph) for dt, ph in ((-.003, 0), (0, 1.3), (.003, 2.1)))
    s = s + 0.35 * np.sin(2 * np.pi * 2 * f * t)
    return s / 3 * vel * ad(len(t), min(1.0, d / 3), min(1.2, d / 3))


def strings(m, d=1.0, vel=1.0):
    t, f = T(d), float(hz(m))
    s = np.zeros_like(t)
    for dt in (-.004, .004):
        for h in range(1, 9):
            s += np.sin(2 * np.pi * f * (1 + dt) * h * t) / h ** 1.15
    return s / 3 * vel * ad(len(t), 0.05, min(0.15, d / 3))


def bass(m, d=0.4, vel=1.0):
    t, f = T(d), float(hz(m))
    s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t)
    return s * vel * np.exp(-3.5 * t) * ad(len(t), 0.004, 0.03)


def taiko(vel=1.0, size=1.0):
    t = T(0.9 * size + 0.2)
    fr = 50 + 85 * np.exp(-t * 16)
    body = sine(fr) * np.exp(-t * (5.5 / size))
    skin = bandnoise(len(t) / SR, 0, 900) * np.exp(-t * 45) * 1.4
    return (body + skin) * vel


def kodo(vel=1.0):
    t = T(0.3)
    return (sine(110 + 130 * np.exp(-t * 28)) * np.exp(-t * 14) + bandnoise(.3, 300, 3000) * np.exp(-t * 60)) * vel


def wood(vel=1.0):
    t = T(0.12)
    return (np.sin(2 * np.pi * 1700 * t) * np.exp(-t * 70) + bandnoise(.12, 1500, 7000) * np.exp(-t * 90)) * vel


def bell(m, d=1.4, vel=1.0):
    t, f = T(d), float(hz(m))
    s = np.zeros_like(t)
    for r, a, k in ((1, 1, 2.5), (2.76, .5, 3.5), (5.4, .25, 5), (8.9, .12, 7)):
        s += a * np.sin(2 * np.pi * f * r * t) * np.exp(-k * t)
    return s * vel * ad(len(t), 0.001, 0.05)


def thump(f0=160, f1=45, d=0.25, k=14):
    t = T(d)
    return sine(f1 + (f0 - f1) * np.exp(-t * 40)) * np.exp(-k * t)


def crack(d=0.06, lo=1500, hi=9000, k=60):
    return bandnoise(d, lo, hi) * np.exp(-k * T(d)) * 1.4


def both(*sigs):
    """sum signals of different lengths (shorter ones are zero-padded)"""
    n = max(len(x) for x in sigs)
    out = np.zeros(n)
    for x in sigs:
        out[:len(x)] += x
    return out


def rnd(a, b):
    return float(rng.uniform(a, b))


# ═════════════════════════════════════════════════════
#  MUSIC
# ═════════════════════════════════════════════════════
class Track:
    def __init__(self, bpm, bars, beats=4):
        self.spb = 60.0 / bpm
        self.beats = bars * beats
        self.sec = self.beats * self.spb
        self.b = buf(self.sec)

    def put(self, sig, beat, g=1.0):
        add(self.b, sig, beat * self.spb, g, wrap=True)

    def notes(self, inst, seq, g=1.0, off=0.0):
        """seq: (beat, midi, dur_in_beats[, vel])"""
        for ev in seq:
            beat, m, dur = ev[:3]
            vel = ev[3] if len(ev) > 3 else 1.0
            self.put(inst(m, dur * self.spb + 0.05, vel), beat + off, g)

    def arp(self, inst, chord, start, bars, pat, step=0.5, g=1.0, accent=1.25):
        for bar in range(bars):
            for i, ci in enumerate(pat):
                beat = start + bar * 4 + i * step
                self.put(inst(chord[ci], 1.4, accent if i % 4 == 0 else 1.0), beat, g)

    def render(self, peak=0.30, rev=True):
        x = self.b
        if rev:
            x = reverb(x, [(0.083, .30), (0.151, .22), (0.233, .15), (0.347, .10)], wrap=True)
        x = np.tanh(x * 1.15)
        return x / np.max(np.abs(x)) * peak


def music_title():
    t = Track(72, 8)
    for i, ch in enumerate([(38, 45), (34, 41), (41, 45), (38, 45)]):
        for m in ch:
            t.put(pad(m, 2 * 4 * t.spb + 1.4), i * 8, 0.16)
    for beat, v, s in ((0, 1.0, 1.2), (8, .6, 1.0), (16, 1.0, 1.2), (24, .6, 1.0)):
        t.put(taiko(v, s), beat, 0.9)
    for k, b in enumerate((30, 30.5, 31, 31.5)):
        t.put(kodo(.35 + .1 * k), b, 0.6)
    t.notes(koto, [(4, 74, 2), (6, 69, 2)], 0.5)
    for start, chord in ((8, [58, 65, 70, 74]), (16, [65, 69, 77, 81]), (24, [62, 69, 74, 77])):
        t.arp(koto, chord, start, 2, [0, 1, 2, 3, 2, 1, 2, 1], 0.5, 0.33)
    # shakuhachi-style lead
    t.notes(flute, [
        (8, 69, 2), (10, 74, 1), (11, 76, 1), (12, 77, 3), (15, 76, 1),
        (16, 74, 2), (18, 69, 1), (19, 70, 1), (20, 69, 4),
        (24, 74, 1), (25, 77, 1), (26, 81, 2), (28, 82, 1), (29, 81, 1), (30, 77, 2)], 0.55)
    return t.render()


def music_village():
    t = Track(92, 8)
    for i, ch in enumerate([[55, 62, 67, 69], [60, 67, 69, 72], [57, 64, 67, 69], [55, 62, 64, 67]]):
        t.arp(koto, ch, i * 8, 2, [0, 2, 1, 3, 2, 1, 3, 2], 0.5, 0.30)
    for i, r in enumerate([43, 48, 45, 43]):
        for b in (0, 2, 4, 6):
            t.put(bass(r, .5, 1.0 if b % 4 == 0 else .7), i * 8 + b, 0.5)
    for bar in range(8):
        for b in (1, 3):
            t.put(wood(.45), bar * 4 + b, 0.35)
        t.put(kodo(.4), bar * 4, 0.45)
    t.notes(flute, [
        (0, 79, 1.5), (1.5, 81, .5), (2, 79, 1), (3, 76, 1), (4, 74, 2), (6, 76, 1), (7, 72, 1),
        (8, 74, 1.5), (9.5, 76, .5), (10, 79, 1), (11, 81, 1), (12, 79, 3), (15, 76, 1),
        (16, 72, 1.5), (17.5, 74, .5), (18, 76, 1), (19, 79, 1), (20, 81, 2), (22, 79, 1), (23, 76, 1),
        (24, 74, 1), (25, 76, 1), (26, 79, 1), (27, 76, 1), (28, 74, 3), (31, 72, 1)], 0.6)
    return t.render()


def music_story():
    t = Track(62, 8)
    for i, ch in enumerate([(45, 52), (41, 48), (48, 52), (40, 47)]):
        for m in ch:
            t.put(pad(m, 2 * 4 * t.spb + 1.6), i * 8, 0.20)
    t.put(taiko(.4, 1.3), 0, 0.8)
    t.put(taiko(.4, 1.3), 16, 0.8)
    for i, ch in enumerate([[57, 64, 69, 72], [53, 60, 65, 72], [60, 64, 72, 76], [52, 59, 64, 71]]):
        t.arp(koto, ch, i * 8, 2, [0, 1, 2, 3], 1.0, 0.36, accent=1.0)
    t.notes(flute, [
        (0, 76, 3), (3, 72, 1), (4, 71, 2), (6, 69, 2),
        (8, 72, 2), (10, 76, 1), (11, 77, 1), (12, 76, 4),
        (16, 76, 2), (18, 77, 1), (19, 76, 1), (20, 72, 4),
        (24, 71, 2), (26, 69, 1), (27, 71, 1), (28, 69, 4)], 0.62)
    return t.render()


def music_battle():
    t = Track(152, 8)
    for bar in range(8):
        o = bar * 4
        t.put(taiko(1.0, .8), o, 0.8)
        t.put(taiko(.8, .8), o + 2.5, 0.7)
        for b in (1, 1.5, 3, 3.5):
            t.put(kodo(.55), o + b, 0.5)
        for b in (0.5, 2, 3.75):
            t.put(kodo(.3), o + b, 0.35)
    for b in (30, 30.5, 31, 31.25, 31.5, 31.75):
        t.put(kodo(.8), b, 0.7)
    for i, r in enumerate([40, 40, 43, 45, 40, 40, 45, 47]):
        for k in range(8):
            t.put(bass(r, .22, 1.0 if k % 2 == 0 else .55), i * 4 + k * .5, 0.5)
    riff1 = [(0, 64, .5), (.5, 64, .5), (1, 67, .5), (1.5, 64, .5), (2, 62, .5), (2.5, 64, .5), (3, 69, .5), (3.5, 67, .5)]
    riff2 = [(0, 64, .5), (.5, 64, .5), (1, 71, .5), (1.5, 69, .5), (2, 67, .5), (2.5, 64, .5), (3, 62, 1)]
    for rep in range(4):
        t.notes(shamisen, riff1, 0.55, off=rep * 8)
        t.notes(shamisen, riff2, 0.55, off=rep * 8 + 4)
    for bar in range(4, 8):
        for b in (0, 2.5):
            for m in (64, 67, 71):
                t.put(strings(m, .4, 1.0), bar * 4 + b, 0.22)
    t.notes(flute, [(16, 76, 3), (19, 79, 1), (20, 81, 2), (22, 79, 1), (23, 76, 1),
                    (24, 74, 2), (26, 76, 1), (27, 79, 1), (28, 81, 3), (31, 83, 1)], 0.55)
    return t.render(0.34)


def music_boss():
    t = Track(138, 8)
    t.put(pad(38, t.sec + 1.5), 0, 0.2)
    t.put(pad(45, t.sec + 1.5), 0, 0.14)
    for bar in range(8):
        o = bar * 4
        for b, v, s in ((0, 1.0, 1.2), (1.5, .8, 1.0), (3, .9, 1.0)):
            t.put(taiko(v, s), o + b, 0.85)
        for b in (0.5, 2, 2.5, 3.5):
            t.put(kodo(.45), o + b, 0.5)
    for b in (28, 29, 30, 30.5, 31, 31.25, 31.5, 31.75):
        t.put(kodo(.9), b, 0.7)
    for k in range(64):
        t.put(bass(38 if (k // 8) % 2 == 0 else (39 if k % 16 < 12 else 41), .2, 1.0 if k % 4 == 0 else .5), k * .5, 0.5)
    riff = [(0, 62, .5), (.5, 63, .5), (1, 62, .5), (1.5, 67, .5), (2, 69, .5), (2.5, 67, .5), (3, 63, .5), (3.5, 62, .5)]
    for rep in range(8):
        t.notes(shamisen, riff, 0.5, off=rep * 4)
    for bar in range(8):
        for m in (50, 57, 62):
            t.put(strings(m, 2.0, 1.0), bar * 4, 0.20 if bar % 2 == 0 else 0.15)
    t.notes(flute, [(8, 75, 2), (10, 74, 1), (11, 72, 1), (12, 74, 4),
                    (16, 79, 2), (18, 81, 1), (19, 79, 1), (20, 75, 3), (23, 74, 1),
                    (24, 81, 2), (26, 84, 1), (27, 81, 1), (28, 79, 2), (30, 75, 2)], 0.55)
    return t.render(0.36)


# ═════════════════════════════════════════════════════
#  SOUND EFFECTS
# ═════════════════════════════════════════════════════
def mix_at(length, parts):
    b = buf(length)
    for sig, at, g in parts:
        add(b, sig, at, g)
    return b


def sfx_all():
    S = {}
    S["ui_move"] = finish(sine(np.full(int(.05 * SR), 1300)) * np.exp(-60 * T(.05)), .35)
    t = T(.14)
    S["ui_select"] = finish(np.where(t < .06, np.sin(2 * np.pi * 880 * t), np.sin(2 * np.pi * 1320 * t)) * ad(len(t), .002, .06) * np.exp(-12 * t), .5)
    t = T(.14)
    S["ui_back"] = finish(np.where(t < .06, np.sin(2 * np.pi * 660 * t), np.sin(2 * np.pi * 440 * t)) * ad(len(t), .002, .06) * np.exp(-12 * t), .45)
    t = T(.24)
    S["ui_error"] = finish(np.sign(np.sin(2 * np.pi * 150 * t)) * ((t % .12) < .09) * ad(len(t), .003, .03), .4)
    S["tick"] = finish(crack(.02, 2500, 8000, 200), .35)
    S["page"] = finish(bandnoise(.18, 1800, 6000) * ad(int(.18 * SR), .04, .1), .3)
    S["gong"] = finish(sum(a * np.sin(2 * np.pi * f * T(2.6)) * np.exp(-k * T(2.6))
                           for f, a, k in ((110, 1, 1.1), (166, .6, 1.4), (237, .5, 1.8), (312, .35, 2.4), (451, .2, 3.2))) * ad(int(2.6 * SR), .004, .3), .75)

    S["slash"] = finish(mix_at(.34, [(sweep(.22, 2500, 7500, .6, 7), 0, .8), (thump(130, 60, .14), .14, .5), (crack(.05, 2500, 9000), .14, .35)]), .85)
    S["hit"] = finish(mix_at(.3, [(thump(170, 55, .25, 12), 0, 1.0), (crack(.06, 1200, 8000), 0, .6)]), .9)
    S["hit_heavy"] = finish(mix_at(.55, [(thump(140, 38, .5, 8), 0, 1.0), (crack(.1, 600, 7000, 35), 0, .8), (bandnoise(.4, 60, 600) * np.exp(-9 * T(.4)), 0, .5)]), .95)
    ring = np.sin(2 * np.pi * 2600 * T(.5)) * np.exp(-9 * T(.5)) + .5 * np.sin(2 * np.pi * 3900 * T(.5)) * np.exp(-12 * T(.5))
    S["crit"] = finish(mix_at(.7, [(thump(150, 36, .5, 8), 0, 1.0), (crack(.12, 500, 9000, 30), 0, .9), (ring, .02, .35), (sweep(.25, 1000, 6000, .6, 6), 0, .5)]), .95)
    S["hurt"] = finish(mix_at(.4, [(thump(120, 45, .3, 10), 0, 1.0), (crack(.07, 300, 3500, 40), 0, .7), (bandnoise(.3, 100, 900) * np.exp(-14 * T(.3)), 0, .5)]), .9)
    S["enemy_swing"] = finish(sweep(.26, 3500, 900, .6, 6) * ad(int(.26 * SR), .01, .08), .6)
    S["dodge"] = finish(sweep(.3, 700, 5000, .8, 7) * ad(int(.3 * SR), .03, .1), .55)
    clang = sum(a * np.sin(2 * np.pi * f * T(.6)) * np.exp(-k * T(.6)) for f, a, k in ((820, 1, 9), (1250, .7, 11), (1930, .5, 14), (2900, .3, 18)))
    S["guard"] = finish(mix_at(.6, [(clang, 0, .8), (thump(110, 60, .2, 18), 0, .7), (crack(.03, 2000, 9000), 0, .5)]), .85)

    # jutsu by nature
    d = 1.0
    t = T(d)
    roar = bandnoise(d, 150, 2600) * (1 - np.exp(-t * 14)) * np.exp(-t * 2.0) * 1.4
    pops = buf(d)
    for _ in range(26):
        add(pops, crack(.03, 400, 4000, 120), rnd(.05, .9), rnd(.3, .9))
    S["jutsu_fire"] = finish(mix_at(d, [(roar, 0, .9), (sweep(.35, 400, 3200, .7, 6), 0, .7), (thump(110, 45, .3, 9), 0, .7), (pops, 0, .6)]), .9)
    d = .95
    sp = buf(d)
    for _ in range(16):
        n_ = int(.08 * SR)
        tt = np.arange(n_) / SR
        f0 = rnd(350, 900)
        add(sp, np.sin(np.cumsum(2 * np.pi * (f0 * (1 + 2.5 * tt / .08)) / SR)) * np.exp(-tt * 38), rnd(0, .8), rnd(.2, .5))
    S["jutsu_water"] = finish(mix_at(d, [(sweep(d, 500, 2600, .7, 8) * ad(int(d * SR), .05, .3), 0, .5), (sp, 0, 1.0), (bandnoise(.3, 1500, 6500) * np.exp(-8 * T(.3)), .05, .4)]), .85)
    d = .9
    t = T(d)
    S["jutsu_wind"] = finish(sweep(d, 500, 3800, .8, 10) * (0.75 + .25 * np.sin(2 * np.pi * 14 * t)) * ad(len(t), .04, .25), .8)
    d = .85
    t = T(d)
    zap = np.sign(np.sin(np.cumsum(2 * np.pi * (200 + 2400 * np.exp(-t * 5)) / SR))) * np.exp(-t * 4.5) * ((t % .035) < .02)
    cr = buf(d)
    for tt in (0, .08, .16, .3):
        add(cr, crack(.07, 3000, 11000, 40), tt, .9)
    for _ in range(40):
        add(cr, crack(.012, 2500, 10000, 300), rnd(0, .7), rnd(.2, .7))
    S["jutsu_lightning"] = finish(mix_at(d, [(zap, 0, .6), (cr, 0, 1.0), (thump(100, 50, .3, 10), 0, .5)]), .9)
    d = 1.1
    t = T(d)
    rumble = bandnoise(d, 25, 150) * np.exp(-t * 2.2) * 3
    rocks = buf(d)
    for tt in (0, .13, .26, .42, .6):
        add(rocks, thump(100, 38, .3, 10), tt, rnd(.6, 1))
        add(rocks, crack(.1, 250, 2200, 30), tt, .6)
    S["jutsu_earth"] = finish(mix_at(d, [(rumble, 0, 1.0), (rocks, 0, .9)]), .95)
    d = 1.15
    t = T(d)
    fr = 320 * np.exp(-t * 1.25) + 70
    eerie = (sine(fr) + sine(fr * 1.012) + .4 * sine(fr * 2.01)) * (1 + .4 * np.sin(2 * np.pi * 7 * t)) * ad(len(t), .15, .4)
    S["jutsu_shadow"] = finish(mix_at(d, [(eerie, 0, .7), (bandnoise(d, 2200, 6500) * np.sin(np.pi * t / d) ** 2, 0, .35), (thump(70, 35, .5, 5), .55, .6)]), .85)
    d = .8
    p_ = buf(d)
    for k, tt in enumerate((0, .08, .16, .27, .4)):
        add(p_, both(thump(230, 70, .14, 20), crack(.05, 800, 5500, 70)), tt, .7 + .06 * k)
    add(p_, both(thump(140, 38, .35, 9), crack(.08, 500, 6000, 35) * 1.2), .52, 1.3)
    S["jutsu_taijutsu"] = finish(p_, .9)
    d = 1.2
    t = T(d)
    f1 = 700 + 300 * np.sin(2 * np.pi * 3 * t) + 250 * t
    gen = (sine(f1 + 80 * np.sin(2 * np.pi * 8 * t)) + sine(f1 * 1.5 + 60 * np.sin(2 * np.pi * 6 * t)) * .5) * np.sin(np.pi * t / d) ** 1.5
    sp2 = buf(d)
    for _ in range(9):
        add(sp2, bell(rnd(84, 100), .5, 1), rnd(.1, 1.0), rnd(.2, .45))
    S["jutsu_genjutsu"] = finish(mix_at(d, [(gen, 0, .7), (sp2, 0, .6)]), .8)

    d = 1.7
    t = T(d)
    rise = sine(120 * (14 ** np.minimum(t / 1.1, 1))) * np.minimum(1, t / 1.1) ** 2 * (t < 1.1)
    S["ult_charge"] = finish(mix_at(d, [(rise, 0, .6), (sweep(1.1, 300, 7000, .8, 9) * np.linspace(0, 1, int(1.1 * SR)) ** 2, 0, .6),
                                        (thump(120, 30, .6, 6), 1.1, 1.3), (crack(.25, 200, 5000, 14), 1.1, .9), (bell(88, .6), 1.12, .4)]), .95)
    d = 1.9
    t = T(d)
    r = np.minimum(1, t / 1.0)
    ch = sum(sine(f * (1 + .5 * r)) for f in (110, 165, 220, 330)) * (1 + .3 * np.sin(2 * np.pi * 9 * t)) * ad(len(t), .2, .5) * .25
    sp3 = buf(d)
    for k in range(7):
        add(sp3, bell(84 + k * 2, .7), 1.0 + k * .08, .5)
    S["awaken"] = finish(mix_at(d, [(ch, 0, 1.0), (bandnoise(1.0, 3000, 9000) * np.linspace(0, 1, int(SR)), 0, .35),
                                    (thump(110, 32, .7, 5), 1.0, 1.3), (crack(.2, 300, 6000, 12), 1.0, .8), (sp3, 0, .8)]), .95)
    S["battle_start"] = finish(mix_at(1.3, [(taiko(1, 1.1), 0, 1.0), (taiko(.8, .9), .32, .9), (sweep(.45, 3200, 9000, .7, 6), .08, .45), (gong_hit(), .0, .25)]), .95)
    S["title_whoosh"] = finish(sweep(1.5, 300, 5500, .8, 10) * np.linspace(.1, 1, int(1.5 * SR)) ** 1.5, .6)
    S["title_boom"] = finish(mix_at(2.4, [(taiko(1, 1.6), 0, 1.0), (gong_hit(), 0, .5), (bell(69, 2.0, .6), .05, .35)]), .95)

    # pickups & ui jingles
    S["heal"] = finish(mix_at(.9, [(bell(m, .7), i * .1, .8) for i, m in enumerate((81, 85, 88))] + [(sine(np.full(int(.8 * SR), 440)) * np.sin(np.pi * T(.8) / .8) * .2, 0, 1)]), .7)
    t = T(.6)
    S["chakra"] = finish(both(sine(300 + 600 * t / .6) * (1 + .4 * np.sin(2 * np.pi * 12 * t)) * np.sin(np.pi * t / .6) * .5, bell(93, .5, .5) * .4), .6)
    S["coin"] = finish(mix_at(.5, [(bell(88, .35), 0, 1), (bell(95, .45), .07, .9)]), .6)
    S["save"] = finish(mix_at(.9, [(bell(m, .6), i * .11, .8) for i, m in enumerate((79, 83, 86))]), .65)
    S["success"] = finish(mix_at(.8, [(bell(m, .5), i * .07, .9) for i, m in enumerate((84, 88, 91))]), .65)
    t = T(.5)
    S["fail"] = finish((np.sign(np.sin(2 * np.pi * np.where(t < .22, 220, 165) * t)) * .5 + .5 * np.sin(2 * np.pi * np.where(t < .22, 110, 82) * t)) * ad(len(t), .004, .1), .5)
    for name, base in (("reveal_low", 76), ("reveal_mid", 81), ("reveal_high", 86)):
        parts = [(bell(base + o, 1.2), i * .09, .8) for i, o in enumerate((0, 4, 7, 12))]
        if name != "reveal_low":
            parts.append((taiko(.7, .9), 0, .8))
        if name == "reveal_high":
            parts += [(bell(base + 12 + o, .9), .4 + i * .06, .5) for i, o in enumerate((0, 4, 7, 12))]
            parts.append((sweep(.6, 2000, 9000, .8, 7), .1, .4))
        S[name] = finish(mix_at(2.0, parts), .85)

    # fanfares
    def fan(seq, d, drums):
        parts = []
        for at, m, dur in seq:
            parts += [(strings(m, dur + .1, 1), at, .5), (koto(m + 12, dur + .3, .9), at, .5)]
        parts += [(taiko(1, 1.2), at, .9) for at in drums]
        return mix_at(d, parts)
    S["victory"] = finish(reverb(fan([(0, 69, .2), (.22, 74, .2), (.44, 76, .2), (.66, 81, 1.5)], 3.0, (0, .66)), [(.09, .3), (.17, .2)]), .9)
    S["rank_up"] = finish(reverb(fan([(0, 62, .2), (.2, 69, .2), (.4, 74, .2), (.7, 76, .2), (.9, 78, .2), (1.1, 81, .2), (1.4, 86, 1.8)], 3.6, (0, .7, 1.4)), [(.09, .3), (.17, .2)]), .92)
    lv = [(bell(72 + o, 1.0), i * .075, .7) for i, o in enumerate((0, 4, 7, 9, 12, 16, 19, 21, 24))]
    lv += [(pad(60, 1.6), 0, .25), (pad(67, 1.6), 0, .2), (sweep(.5, 2000, 9000, .8, 6), .1, .3)]
    S["level_up"] = finish(mix_at(2.0, lv), .85)
    df = []
    for i, m in enumerate((69, 67, 64, 62)):
        df.append((flute(m, .9 if i < 3 else 1.6, .9), i * .55, .8))
    df += [(pad(38, 3.0), 0, .35), (taiko(.5, 1.4), 0, .8), (thump(70, 35, .8, 4), 1.9, .6)]
    S["defeat"] = finish(reverb(mix_at(3.4, df), [(.12, .3), (.25, .2)]), .8)
    return S


def gong_hit():
    return sum(a * np.sin(2 * np.pi * f * T(.9)) * np.exp(-k * T(.9)) for f, a, k in ((310, 1, 4), (470, .5, 5), (710, .3, 7)))


# ═════════════════════════════════════════════════════
def main():
    songs = {"title": music_title, "village": music_village, "story": music_story,
             "battle": music_battle, "boss": music_boss}
    for name, fn in songs.items():
        x = fn()
        save_wav(os.path.join(ROOT, "music", name + ".wav"), x)
        print(f"music/{name}.wav  {len(x) / SR:5.1f}s")
    for name, x in sfx_all().items():
        save_wav(os.path.join(ROOT, "sfx", name + ".wav"), x)
        print(f"sfx/{name}.wav  {len(x) / SR:4.2f}s")


if __name__ == "__main__":
    sys.exit(main())
