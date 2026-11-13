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


DEFAULT_CUTOFF = 2800.0  # every sound is softened above this (Hz) so nothing sounds sharp or bright


MASTER = 0.6  # overall level of every file; the game's volume setting comes on top


def save(name: str, x: np.ndarray, gain: float = 0.7, cutoff: float = DEFAULT_CUTOFF) -> None:
    gain *= MASTER
    x = lowpass(lowpass(x, cutoff), cutoff * 1.3)  # two passes: gentle, darker top end
    fade = min(len(x), int(RATE * 0.01))
    if fade:
        x[-fade:] *= np.linspace(1.0, 0.0, fade)  # no click at the end
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
    crack_part = highpass(n, crack) * env(dur, 0.0008, 90) * 0.3  # only a hint of crack
    body_part = lowpass(n, body) * env(dur, 0.001, tail * 1.6) * 1.4  # short, light tail
    out = crack_part + body_part
    if thump:
        out = out + sine(np.linspace(thump, thump * 0.5, int(RATE * dur)), dur) * env(dur, 0.001, 30) * 0.35
    return out


def step(cut: float, thump: float, dur: float = 0.07) -> np.ndarray:
    """Light, short footstep: a soft muffled tap that is gone after a few hundredths of a second (no boom, no tail)."""
    n = noise(dur)
    body = lowpass(lowpass(n, cut), cut * 1.2) * env(dur, 0.003, 70)
    low = sine(np.linspace(thump, thump * 0.85, int(RATE * dur)), dur) * env(dur, 0.004, 90) * 0.3
    return body + low


def build() -> None:
    # weapons by class
    save("shot_pistol", gunshot(1800, 3000, 26, 0.28, thump=160))
    save("shot_smg", gunshot(2200, 3500, 34, 0.20, thump=180))
    save("shot_rifle", gunshot(1400, 2600, 18, 0.40, thump=120))
    save("shot_sniper", gunshot(900, 2000, 7, 0.95, thump=80))
    save("shot_shotgun", gunshot(1000, 1800, 11, 0.6, thump=90) + gunshot(1200, 2200, 16, 0.6) * 0.6)
    save("shot_heavy", gunshot(1200, 2400, 22, 0.32, thump=100))
    # suppressed: a soft, short "thup" and the click of the action, no crack and no tail
    save("shot_silenced", mix(lowpass(noise(0.09), 700) * env(0.09, 0.001, 55),
                              sine(np.linspace(150, 90, int(RATE * 0.09)), 0.09) * env(0.09, 0.001, 60) * 0.5,
                              at(highpass(noise(0.02), 1800) * env(0.02, 0.0005, 160) * 0.35, 0.035)), gain=0.5, cutoff=1600)
    save("knife", highpass(noise(0.16), 2500) * env(0.16, 0.02, 25) * sine(np.linspace(900, 300, int(RATE * 0.16)), 0.16))
    save("empty", pad(highpass(noise(0.03), 3000) * env(0.03, 0.0005, 150), 0.08))
    save("reload", mix(pad(highpass(noise(0.05), 2500) * env(0.05, 0.001, 80), 0.6),
                       at(lowpass(noise(0.08), 1200) * env(0.08, 0.001, 50), 0.3),
                       at(highpass(noise(0.04), 3500) * env(0.04, 0.0005, 120), 0.5)))
    save("equip", mix(highpass(noise(0.12), 1500) * env(0.12, 0.01, 30) * 0.6, at(highpass(noise(0.03), 4000) * env(0.03, 0.0005, 150), 0.1)))
    # footsteps by surface
    save("step_hard", step(700, 140), gain=0.22, cutoff=1300)
    save("step_metal", step(850, 170) + sine(np.full(int(RATE * 0.07), 320.0), 0.07) * env(0.07, 0.003, 80) * 0.15, gain=0.22, cutoff=1500)
    save("step_soft", step(520, 120), gain=0.18, cutoff=1000)
    save("step_wood", step(640, 180) + sine(np.full(int(RATE * 0.07), 220.0), 0.07) * env(0.07, 0.003, 85) * 0.18, gain=0.2, cutoff=1300)
    save("land", lowpass(noise(0.12), 500) * env(0.12, 0.004, 40) + sine(np.linspace(110, 80, int(RATE * 0.12)), 0.12) * env(0.12, 0.004, 45) * 0.4, gain=0.3, cutoff=1000)
    # hits and kills
    save("hit_body", lowpass(noise(0.08), 900) * env(0.08, 0.001, 40) + sine(np.full(int(RATE * 0.08), 180.0), 0.08) * env(0.08, 0.001, 30))
    save("hit_head", mix(lowpass(noise(0.05), 1500) * env(0.05, 0.002, 70), sine(np.full(int(RATE * 0.22), 880.0), 0.22) * env(0.22, 0.003, 16) * 0.5), gain=0.5, cutoff=1600)
    save("kill", mix(sine(np.full(int(RATE * 0.14), 523.0), 0.14) * env(0.14, 0.004, 18),
                     at(sine(np.full(int(RATE * 0.2), 659.0), 0.2) * env(0.2, 0.004, 13), 0.08)), gain=0.5)
    save("death", lowpass(noise(0.4), 400) * env(0.4, 0.005, 9))
    # abilities (one per building block family)
    save("ab_smoke", lowpass(noise(1.2), 1800) * env(1.2, 0.05, 2.5))
    save("ab_wall", lowpass(noise(0.9), 2500) * env(0.9, 0.02, 3.5) + sine(np.linspace(120, 80, int(RATE * 0.9)), 0.9) * env(0.9, 0.02, 4) * 0.4)
    save("ab_throw", highpass(noise(0.18), 1200) * env(0.18, 0.04, 14))
    save("ab_flash", mix(sine(np.linspace(700, 1100, int(RATE * 0.35)), 0.35) * env(0.35, 0.003, 9), lowpass(noise(0.35), 2000) * env(0.35, 0.002, 25)), gain=0.55)
    save("ab_blast", mix(lowpass(noise(0.6), 900) * env(0.6, 0.001, 8) * 1.3, sine(np.linspace(100, 50, int(RATE * 0.6)), 0.6) * env(0.6, 0.001, 9) * 0.5), gain=0.6)
    save("ab_wave", sine(np.linspace(140, 420, int(RATE * 0.6)), 0.6) * env(0.6, 0.02, 5) + lowpass(noise(0.6), 900) * env(0.6, 0.02, 6) * 0.5)
    save("ab_sensor", mix(sine(np.full(int(RATE * 0.15), 1200.0), 0.15) * env(0.15, 0.001, 18),
                          at(sine(np.full(int(RATE * 0.15), 1600.0), 0.15) * env(0.15, 0.001, 18), 0.12)))
    save("ab_alarm", sine(np.full(int(RATE * 0.5), 520.0), 0.5) * env(0.5, 0.01, 3) * (0.6 + 0.4 * sine(np.full(int(RATE * 0.5), 8.0), 0.5)), gain=0.5)
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
    save("bomb_beep", sine(np.full(int(RATE * 0.09), 1100.0), 0.09) * env(0.09, 0.004, 26), gain=0.45)
    save("bomb_plant", mix(*(at(sine(np.full(int(RATE * 0.07), 880.0), 0.07) * env(0.07, 0.004, 26), d) for d in (0, 0.15, 0.3))), gain=0.45)
    save("bomb_planted", mix(sine(np.full(int(RATE * 0.6), 660.0), 0.6) * env(0.6, 0.005, 5), at(sine(np.full(int(RATE * 0.6), 990.0), 0.6) * env(0.6, 0.005, 5), 0.2)))
    save("bomb_defuse", mix(*(at(highpass(noise(0.04), 3500) * env(0.04, 0.0005, 100), d) for d in np.arange(0, 0.8, 0.16))))
    save("bomb_defused", sine(np.linspace(900, 300, int(RATE * 0.7)), 0.7) * env(0.7, 0.005, 5))
    save("bomb_explode", mix(lowpass(noise(1.4), 700) * env(1.4, 0.002, 3.5) * 1.5, sine(np.linspace(80, 40, int(RATE * 1.4)), 1.4) * env(1.4, 0.002, 4.0) * 0.6), gain=0.6)
    # movement, weapons handling, feedback
    save("jump", lowpass(noise(0.1), 900) * env(0.1, 0.004, 45), gain=0.25, cutoff=1000)
    save("reload_out", mix(highpass(noise(0.05), 1500) * env(0.05, 0.001, 70), at(lowpass(noise(0.06), 900) * env(0.06, 0.001, 50), 0.05)),
         gain=0.45, cutoff=2200)
    save("reload_in", mix(lowpass(noise(0.05), 1200) * env(0.05, 0.001, 60), at(highpass(noise(0.03), 2000) * env(0.03, 0.0005, 120), 0.04)),
         gain=0.5, cutoff=2400)
    save("knife_heavy", highpass(noise(0.24), 1600) * env(0.24, 0.03, 16) * sine(np.linspace(700, 200, int(RATE * 0.24)), 0.24), gain=0.6)
    save("hurt", lowpass(noise(0.12), 500) * env(0.12, 0.001, 30) + sine(np.linspace(120, 70, int(RATE * 0.12)), 0.12) * env(0.12, 0.001, 30) * 0.6,
         gain=0.5, cutoff=800)
    save("pickup", mix(highpass(noise(0.04), 1800) * env(0.04, 0.001, 90), at(lowpass(noise(0.05), 1000) * env(0.05, 0.001, 60), 0.05)), gain=0.45)
    save("ult_ready", mix(*(at(sine(np.full(int(RATE * 0.3), f), 0.3) * env(0.3, 0.01, 9) * 0.5, d) for f, d in ((587, 0), (880, 0.1)))), gain=0.4)
    # ability casts: a broad palette for every kind of ability (abilities pick one with sound="...")
    n = lambda d: int(RATE * d)  # noqa: E731
    save("ability_equip", mix(highpass(noise(0.06), 1800) * env(0.06, 0.002, 60), at(sine(np.full(n(0.08), 660.0), 0.08) * env(0.08, 0.002, 40) * 0.4, 0.03)), gain=0.4)
    save("cast_throw_light", highpass(noise(0.16), 1500) * env(0.16, 0.03, 18) * sine(np.linspace(3, 1, n(0.16)), 0.16) ** 2, gain=0.5)
    save("cast_throw_heavy", mix(lowpass(noise(0.25), 900) * env(0.25, 0.04, 12), sine(np.linspace(160, 90, n(0.25)), 0.25) * env(0.25, 0.02, 14) * 0.4), gain=0.55)
    save("cast_deploy", mix(lowpass(noise(0.12), 1200) * env(0.12, 0.002, 40), at(highpass(noise(0.4), 1200) * env(0.4, 0.05, 7) * 0.6, 0.08)), gain=0.5)
    save("cast_place_trap", mix(highpass(noise(0.04), 2500) * env(0.04, 0.001, 110), at(sine(np.full(n(0.12), 980.0), 0.12) * env(0.12, 0.002, 30) * 0.4, 0.06),
                                at(highpass(noise(0.03), 3000) * env(0.03, 0.001, 140), 0.16)), gain=0.45)
    save("cast_charge_up", sine(np.linspace(180, 620, n(0.6)), 0.6) * env(0.6, 0.4, 4) + lowpass(noise(0.6), 1500) * env(0.6, 0.4, 5) * 0.3, gain=0.5)
    save("cast_whoosh", highpass(noise(0.35), 900) * env(0.35, 0.12, 9), gain=0.5)
    save("cast_magic", mix(*(at(sine(np.full(n(0.35), f), 0.35) * env(0.35, 0.01, 8) * 0.4, d) for f, d in ((660, 0), (880, 0.05), (1320, 0.1)))), gain=0.4)
    save("cast_arcane", sine(np.linspace(900, 300, n(0.5)), 0.5) * env(0.5, 0.02, 6) * (1 + 0.4 * sine(np.full(n(0.5), 18.0), 0.5)), gain=0.45)
    save("cast_tech", mix(*(at(sine(np.full(n(0.06), f), 0.06) * env(0.06, 0.001, 50), d) for f, d in ((1500, 0), (1100, 0.08), (1800, 0.16)))), gain=0.35)
    save("cast_heal", mix(*(at(sine(np.full(n(0.5), f), 0.5) * env(0.5, 0.05, 5) * 0.35, d) for f, d in ((523, 0), (784, 0.1), (1047, 0.2)))), gain=0.45)
    save("cast_buff", sine(np.linspace(300, 900, n(0.35)), 0.35) * env(0.35, 0.02, 8) + highpass(noise(0.35), 2500) * env(0.35, 0.02, 18) * 0.2, gain=0.45)
    save("cast_shield_up", sine(np.full(n(0.5), 260.0), 0.5) * env(0.5, 0.05, 5) * (1 + 0.5 * sine(np.full(n(0.5), 9.0), 0.5)), gain=0.45)
    save("cast_beam", mix(sine(np.full(n(0.5), 440.0), 0.5) * env(0.5, 0.01, 5) * 0.5, highpass(noise(0.5), 3000) * env(0.5, 0.01, 6) * 0.3), gain=0.45)
    save("cast_burst", mix(lowpass(noise(0.3), 1200) * env(0.3, 0.001, 14), sine(np.linspace(220, 80, n(0.3)), 0.3) * env(0.3, 0.001, 12) * 0.5), gain=0.55)
    save("cast_dark", sine(np.linspace(140, 60, n(0.8)), 0.8) * env(0.8, 0.1, 3) + lowpass(noise(0.8), 500) * env(0.8, 0.1, 3) * 0.5, gain=0.55)
    save("cast_fire", lowpass(noise(0.7), 1600) * env(0.7, 0.02, 4) * (0.7 + 0.3 * sine(np.full(n(0.7), 23.0), 0.7)), gain=0.5)
    save("cast_ice", mix(highpass(noise(0.4), 3500) * env(0.4, 0.002, 10) * 0.5, *(at(sine(np.full(n(0.2), f), 0.2) * env(0.2, 0.001, 20) * 0.3, d)
                                                                                  for f, d in ((1760, 0.02), (2093, 0.09)))), gain=0.4)
    save("cast_electric", highpass(noise(0.35), 2000) * env(0.35, 0.001, 10) * (0.5 + 0.5 * np.sign(sine(np.full(n(0.35), 37.0), 0.35))), gain=0.4)
    save("cast_wind", lowpass(highpass(noise(0.5), 400), 2500) * env(0.5, 0.15, 6), gain=0.5)
    save("cast_poison", mix(*(at(lowpass(noise(0.12), 700) * env(0.12, 0.01, 30) * 0.6, d) for d in (0, 0.15, 0.27, 0.42))), gain=0.5)
    save("cast_sonic", sine(np.linspace(240, 120, n(0.5)), 0.5) * env(0.5, 0.01, 6) * (1 + 0.6 * sine(np.full(n(0.5), 30.0), 0.5)), gain=0.5)
    save("cast_earth", mix(lowpass(noise(0.6), 400) * env(0.6, 0.03, 6) * 1.2, sine(np.linspace(70, 45, n(0.6)), 0.6) * env(0.6, 0.03, 6) * 0.6), gain=0.6)
    save("ult_cast", mix(sine(np.linspace(150, 900, n(0.9)), 0.9) * env(0.9, 0.3, 3) * 0.6, lowpass(noise(0.9), 1800) * env(0.9, 0.3, 4) * 0.4,
                         at(sine(np.full(n(0.4), 1320.0), 0.4) * env(0.4, 0.01, 8) * 0.3, 0.55)), gain=0.55)
    # spike: plant (4 s: device out, seven rising key beeps, arming tone), defuse (7 s of mechanical work), halfway chime
    plant = [lowpass(noise(0.3), 700) * env(0.3, 0.01, 12)]
    plant += [at(sine(np.full(n(0.08), 600.0 + 60 * i), 0.08) * env(0.08, 0.002, 30) * 0.5, 0.45 + i * 0.45) for i in range(7)]
    plant.append(at(sine(np.linspace(500, 900, n(0.35)), 0.35) * env(0.35, 0.02, 8) * 0.4, 3.65))
    save("spike_plant", pad(mix(*plant), 4.05), gain=0.5)
    work = [at(highpass(noise(0.03), 2500) * env(0.03, 0.001, 140) * 0.7, t) for t in np.arange(0.1, 6.9, 0.23)]
    work += [at(lowpass(noise(0.2), 600) * env(0.2, 0.01, 18), t) for t in (0.0, 1.8, 3.6, 5.4)]
    work += [at(sine(np.full(n(0.06), 1400.0), 0.06) * env(0.06, 0.001, 50) * 0.3, t) for t in (1.2, 2.9, 4.7, 6.3)]
    save("spike_defuse", pad(mix(*work), 7.05), gain=0.45)
    save("spike_defuse_half", mix(*(at(sine(np.full(n(0.25), f), 0.25) * env(0.25, 0.005, 10) * 0.5, d) for f, d in ((880, 0), (1320, 0.12)))), gain=0.45)
    # kill streak (1-5 kills in a round, rising), round titles, ultimate orb
    for k in range(1, 6):
        base_f = 440.0 * (2 ** ((k - 1) * 2 / 12))
        save(f"kill_{k}", mix(sine(np.full(n(0.12), base_f), 0.12) * env(0.12, 0.003, 20),
                              at(sine(np.full(n(0.18), base_f * 1.5), 0.18) * env(0.18, 0.003, 14), 0.07)), gain=0.45 + 0.03 * k)
    save("round_title", mix(*(at(sine(np.full(n(0.4), f), 0.4) * env(0.4, 0.005, 6) * 0.45, d) for f, d in ((523, 0), (784, 0.12), (1047, 0.24), (1568, 0.36)))), gain=0.5)
    save("orb_pickup", mix(sine(np.linspace(600, 1200, n(0.3)), 0.3) * env(0.3, 0.01, 9), at(sine(np.full(n(0.2), 1500.0), 0.2) * env(0.2, 0.005, 14) * 0.4, 0.15)), gain=0.45)
    # match flow and interface
    save("round_start", mix(*(at(sine(np.full(int(RATE * 0.25), f), 0.25) * env(0.25, 0.005, 10), d) for f, d in ((440, 0), (660, 0.15)))))
    save("round_win", mix(*(at(sine(np.full(int(RATE * 0.5), f), 0.5) * env(0.5, 0.005, 5) * 0.5, d) for f, d in ((523, 0), (659, 0.15), (784, 0.3), (1047, 0.45)))))
    save("round_loss", mix(*(at(sine(np.full(int(RATE * 0.6), f), 0.6) * env(0.6, 0.005, 4) * 0.5, d) for f, d in ((392, 0), (330, 0.2), (262, 0.4)))))
    save("ui_click", lowpass(noise(0.04), 1500) * env(0.04, 0.002, 90) + sine(np.full(int(RATE * 0.04), 600.0), 0.04) * env(0.04, 0.002, 70), gain=0.4)
    save("ui_buy", mix(sine(np.full(int(RATE * 0.12), 523.0), 0.12) * env(0.12, 0.004, 20), at(sine(np.full(int(RATE * 0.12), 784.0), 0.12) * env(0.12, 0.004, 20), 0.06)), gain=0.45)
    save("assist", mix(sine(587.0, 0.13) * env(0.13, 0.008, 21),
                       at(sine(698.0, 0.17) * env(0.17, 0.008, 17), 0.065)), gain=0.34)
    save("door", lowpass(noise(0.5), 700) * env(0.5, 0.05, 6) + sine(np.linspace(140, 100, int(RATE * 0.5)), 0.5) * env(0.5, 0.05, 7) * 0.5)
    fire = lowpass(noise(2.0), 1300) + 0.3 * highpass(noise(2.0), 1900)
    flicker = 0.65 + 0.18 * sine(7.0, 2.0) + 0.12 * sine(11.5, 2.0)
    save("incendiary_fire", fire * flicker, gain=0.38)
    flight = lowpass(highpass(noise(0.4), 450), 2300)
    save("recon_flight", flight * 0.8 + sine(510.0, 0.4) * 0.18, gain=0.48)
    rotor = sine(92.0, 1.0) * 0.42 + sine(184.0, 1.0) * 0.18 + lowpass(noise(1.0), 900) * 0.35
    save("owl_rotor", rotor * (0.7 + 0.3 * sine(46.0, 1.0)), gain=0.42)
    warning = sine(520.0, 0.22) * env(0.22, 0.012, 13)
    save("lockdown_warning", pad(mix(warning, at(warning * 0.65, 0.26)), 1.0), gain=0.42)


if __name__ == "__main__":
    build()
    print(f"{len(list(OUT.glob('*.wav')))} sounds in {OUT}")
