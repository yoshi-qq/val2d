"""Generates Val2d's own sound effects as WAV files in assets/sounds/ (procedural synthesis, no samples).

Run:  python tools/make_sounds.py        (overwrites the files; deterministic thanks to a fixed seed)
Every sound is built from noise, sine/square oscillators, envelopes and simple filters. Tune the recipes below.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

RATE = 22050
OUT = Path(__file__).resolve().parent.parent / "assets" / "sounds"
rng = np.random.default_rng(2026)


# ------------------------------------------------------------------ building blocks
def t(dur: float) -> np.ndarray:
    return np.arange(int(RATE * dur)) / RATE


def noise(dur: float) -> np.ndarray:
    return rng.uniform(-1.0, 1.0, int(RATE * dur))


def sine(freq: float | np.ndarray, dur: float) -> np.ndarray:
    tt = t(dur)
    phase = 2 * np.pi * np.cumsum(np.broadcast_to(freq, tt.shape)) / RATE
    return np.sin(phase)


def env(dur: float, attack: float = 0.002, decay: float = 10.0) -> np.ndarray:
    tt = t(dur)
    a = np.clip(tt / max(attack, 1e-4), 0, 1)
    return a * np.exp(-tt * decay)


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    alpha = 1 - np.exp(-2 * np.pi * cutoff / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        y[i] = acc
    return y


def highpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    return x - lowpass(x, cutoff)


def pad(x: np.ndarray, dur: float) -> np.ndarray:
    n = int(RATE * dur)
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def mix(*parts: np.ndarray) -> np.ndarray:
    n = max(len(p) for p in parts)
    return sum(np.pad(p, (0, n - len(p))) for p in parts)


def at(x: np.ndarray, delay: float) -> np.ndarray:
    return np.concatenate([np.zeros(int(RATE * delay)), x])


def save(name: str, x: np.ndarray, gain: float = 0.9) -> None:
    peak = float(np.max(np.abs(x))) or 1.0
    data = (x / peak * gain * 32767).astype(np.int16)
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data.tobytes())


# ------------------------------------------------------------------ recipes
def gunshot(body: float, crack: float, tail: float, dur: float, thump: float = 0.0) -> np.ndarray:
    n = noise(dur)
    crack_part = highpass(n, crack) * env(dur, 0.0005, 60)
    body_part = lowpass(n, body) * env(dur, 0.001, tail) * 1.6
    out = crack_part + body_part
    if thump:
        out = out + sine(np.linspace(thump, thump * 0.4, int(RATE * dur)), dur) * env(dur, 0.001, 18) * 0.8
    return out


def step(cut: float, click: float, dur: float = 0.09) -> np.ndarray:
    n = noise(dur)
    return lowpass(n, cut) * env(dur, 0.001, 45) + highpass(noise(dur), click) * env(dur, 0.0005, 120) * 0.4


def build() -> None:
    # weapons by class
    save("shot_pistol", gunshot(1800, 3000, 26, 0.28, thump=160))
    save("shot_smg", gunshot(2200, 3500, 34, 0.20, thump=180))
    save("shot_rifle", gunshot(1400, 2600, 18, 0.40, thump=120))
    save("shot_sniper", gunshot(900, 2000, 7, 0.95, thump=80))
    save("shot_shotgun", gunshot(1000, 1800, 11, 0.6, thump=90) + gunshot(1200, 2200, 16, 0.6) * 0.6)
    save("shot_heavy", gunshot(1200, 2400, 22, 0.32, thump=100))
    save("shot_silenced", lowpass(noise(0.18), 1600) * env(0.18, 0.001, 40) + highpass(noise(0.18), 5000) * env(0.18, 0.0005, 90) * 0.5)
    save("knife", highpass(noise(0.16), 2500) * env(0.16, 0.02, 25) * sine(np.linspace(900, 300, int(RATE * 0.16)), 0.16))
    save("empty", pad(highpass(noise(0.03), 3000) * env(0.03, 0.0005, 150), 0.08))
    save("reload", mix(pad(highpass(noise(0.05), 2500) * env(0.05, 0.001, 80), 0.6),
                       at(lowpass(noise(0.08), 1200) * env(0.08, 0.001, 50), 0.3),
                       at(highpass(noise(0.04), 3500) * env(0.04, 0.0005, 120), 0.5)))
    save("equip", mix(highpass(noise(0.12), 1500) * env(0.12, 0.01, 30) * 0.6, at(highpass(noise(0.03), 4000) * env(0.03, 0.0005, 150), 0.1)))
    # footsteps by surface
    save("step_hard", step(1400, 3500))
    save("step_metal", step(2400, 4000) + sine(np.full(int(RATE * 0.09), 620.0), 0.09) * env(0.09, 0.001, 35) * 0.5)
    save("step_soft", step(600, 2500) * 0.8)
    save("step_wood", step(900, 2500) + sine(np.full(int(RATE * 0.09), 190.0), 0.09) * env(0.09, 0.001, 40) * 0.6)
    save("land", lowpass(noise(0.2), 500) * env(0.2, 0.001, 22))
    # hits and kills
    save("hit_body", lowpass(noise(0.08), 900) * env(0.08, 0.001, 40) + sine(np.full(int(RATE * 0.08), 180.0), 0.08) * env(0.08, 0.001, 30))
    save("hit_head", mix(highpass(noise(0.05), 3000) * env(0.05, 0.0005, 90), sine(np.full(int(RATE * 0.25), 1760.0), 0.25) * env(0.25, 0.001, 14) * 0.6))
    save("kill", mix(sine(np.full(int(RATE * 0.12), 880.0), 0.12) * env(0.12, 0.001, 20),
                     at(sine(np.full(int(RATE * 0.18), 1320.0), 0.18) * env(0.18, 0.001, 14), 0.07)))
    save("death", lowpass(noise(0.4), 400) * env(0.4, 0.005, 9))
    # abilities (one per building block family)
    save("ab_smoke", lowpass(noise(1.2), 1800) * env(1.2, 0.05, 2.5))
    save("ab_wall", lowpass(noise(0.9), 2500) * env(0.9, 0.02, 3.5) + sine(np.linspace(120, 80, int(RATE * 0.9)), 0.9) * env(0.9, 0.02, 4) * 0.4)
    save("ab_throw", highpass(noise(0.18), 1200) * env(0.18, 0.04, 14))
    save("ab_flash", mix(sine(np.linspace(2400, 3200, int(RATE * 0.35)), 0.35) * env(0.35, 0.001, 9), highpass(noise(0.35), 4000) * env(0.35, 0.0005, 30)))
    save("ab_blast", mix(lowpass(noise(0.9), 600) * env(0.9, 0.001, 5) * 1.5, sine(np.linspace(90, 35, int(RATE * 0.9)), 0.9) * env(0.9, 0.001, 6)))
    save("ab_wave", sine(np.linspace(140, 420, int(RATE * 0.6)), 0.6) * env(0.6, 0.02, 5) + lowpass(noise(0.6), 900) * env(0.6, 0.02, 6) * 0.5)
    save("ab_sensor", mix(sine(np.full(int(RATE * 0.15), 1200.0), 0.15) * env(0.15, 0.001, 18),
                          at(sine(np.full(int(RATE * 0.15), 1600.0), 0.15) * env(0.15, 0.001, 18), 0.12)))
    save("ab_alarm", np.sign(sine(np.full(int(RATE * 0.5), 900.0), 0.5)) * env(0.5, 0.005, 3) * 0.4)
    save("ab_trap", mix(highpass(noise(0.06), 3000) * env(0.06, 0.0005, 70), at(sine(np.full(int(RATE * 0.2), 300.0), 0.2) * env(0.2, 0.001, 15), 0.03)))
    save("ab_dash", highpass(noise(0.35), 800) * env(0.35, 0.03, 9) * sine(np.linspace(6, 2, int(RATE * 0.35)), 0.35) ** 2)
    save("ab_hop", mix(lowpass(noise(0.25), 700) * env(0.25, 0.001, 18), sine(np.linspace(200, 500, int(RATE * 0.25)), 0.25) * env(0.25, 0.005, 12) * 0.5))
    save("ab_teleport", sine(np.linspace(300, 1800, int(RATE * 0.45)), 0.45) * env(0.45, 0.01, 6) + highpass(noise(0.45), 3000) * env(0.45, 0.2, 8) * 0.3)
    save("ab_heal", mix(*(at(sine(np.full(int(RATE * 0.4), f), 0.4) * env(0.4, 0.02, 6) * 0.5, d) for f, d in ((523, 0), (659, 0.08), (784, 0.16)))))
    save("ab_shield", sine(np.full(int(RATE * 0.5), 220.0), 0.5) * env(0.5, 0.02, 5) * (1 + 0.3 * sine(np.full(int(RATE * 0.5), 12.0), 0.5)))
    save("ab_revive", mix(*(at(sine(np.full(int(RATE * 0.5), f), 0.5) * env(0.5, 0.02, 5) * 0.5, d) for f, d in ((392, 0), (523, 0.12), (784, 0.24)))))
    save("ab_stim", sine(np.linspace(200, 700, int(RATE * 0.3)), 0.3) * env(0.3, 0.005, 9) + highpass(noise(0.3), 2500) * env(0.3, 0.005, 20) * 0.3)
    save("ab_reveal", mix(*(at(sine(np.full(int(RATE * 0.25), 1000.0), 0.25) * env(0.25, 0.001, 14), d) for d in (0, 0.25, 0.5))))
    save("ab_decoy", mix(*(at(step(1200, 3200), d) for d in (0, 0.3, 0.6))))
    save("ab_zone", lowpass(noise(1.0), 1200) * env(1.0, 0.1, 3) + sine(np.full(int(RATE * 1.0), 70.0), 1.0) * env(1.0, 0.1, 3) * 0.6)
    save("ab_power", mix(sine(np.linspace(100, 600, int(RATE * 0.8)), 0.8) * env(0.8, 0.05, 3), lowpass(noise(0.8), 2000) * env(0.8, 0.05, 4) * 0.4))
    # bomb
    save("bomb_beep", sine(np.full(int(RATE * 0.08), 2000.0), 0.08) * env(0.08, 0.001, 30))
    save("bomb_plant", mix(*(at(np.sign(sine(np.full(int(RATE * 0.06), 1500.0), 0.06)) * env(0.06, 0.001, 30) * 0.4, d) for d in (0, 0.15, 0.3))))
    save("bomb_planted", mix(sine(np.full(int(RATE * 0.6), 660.0), 0.6) * env(0.6, 0.005, 5), at(sine(np.full(int(RATE * 0.6), 990.0), 0.6) * env(0.6, 0.005, 5), 0.2)))
    save("bomb_defuse", mix(*(at(highpass(noise(0.04), 3500) * env(0.04, 0.0005, 100), d) for d in np.arange(0, 0.8, 0.16))))
    save("bomb_defused", sine(np.linspace(900, 300, int(RATE * 0.7)), 0.7) * env(0.7, 0.005, 5))
    save("bomb_explode", mix(lowpass(noise(2.5), 400) * env(2.5, 0.002, 2.2) * 2.0, sine(np.linspace(70, 25, int(RATE * 2.5)), 2.5) * env(2.5, 0.002, 2.0)))
    # match flow and interface
    save("round_start", mix(*(at(sine(np.full(int(RATE * 0.25), f), 0.25) * env(0.25, 0.005, 10), d) for f, d in ((440, 0), (660, 0.15)))))
    save("round_win", mix(*(at(sine(np.full(int(RATE * 0.5), f), 0.5) * env(0.5, 0.005, 5) * 0.5, d) for f, d in ((523, 0), (659, 0.15), (784, 0.3), (1047, 0.45)))))
    save("round_loss", mix(*(at(sine(np.full(int(RATE * 0.6), f), 0.6) * env(0.6, 0.005, 4) * 0.5, d) for f, d in ((392, 0), (330, 0.2), (262, 0.4)))))
    save("ui_click", highpass(noise(0.03), 2000) * env(0.03, 0.0005, 120) + sine(np.full(int(RATE * 0.03), 1200.0), 0.03) * env(0.03, 0.0005, 80))
    save("ui_buy", mix(sine(np.full(int(RATE * 0.12), 1046.0), 0.12) * env(0.12, 0.001, 20), at(sine(np.full(int(RATE * 0.12), 1568.0), 0.12) * env(0.12, 0.001, 20), 0.06)))
    save("door", lowpass(noise(0.5), 700) * env(0.5, 0.05, 6) + sine(np.linspace(140, 100, int(RATE * 0.5)), 0.5) * env(0.5, 0.05, 7) * 0.5)


if __name__ == "__main__":
    build()
    print(f"{len(list(OUT.glob('*.wav')))} sounds in {OUT}")
