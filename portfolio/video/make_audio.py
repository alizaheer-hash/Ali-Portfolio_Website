"""Generate the promo soundtrack: an original synthesized ambient/electronic track plus
transition sound effects. Everything is generated from scratch with numpy, so there is no
third-party music and no licensing to worry about.

Usage: python make_audio.py <out.wav> [duration_seconds]
"""
import sys
import wave
import numpy as np

SR = 44100
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 52.0
OUT = sys.argv[1] if len(sys.argv) > 1 else 'promo_audio.wav'

BPM = 96
BEAT = 60.0 / BPM
BAR = BEAT * 4
rng = np.random.default_rng(7)

N = int(DUR * SR)
left = np.zeros(N)
right = np.zeros(N)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def add(buf, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def stereo(start, sig, gain=1.0, pan=0.0):
    gl = gain * np.cos((pan + 1) * np.pi / 4)
    gr = gain * np.sin((pan + 1) * np.pi / 4)
    add(left, start, sig, gl)
    add(right, start, sig, gr)


def env_adsr(n, a, d, s, r):
    t = np.arange(n) / SR
    e = np.ones(n)
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    e[:a_n] = np.linspace(0, 1, a_n, endpoint=False)
    e[a_n:a_n + d_n] = np.linspace(1, s, d_n, endpoint=False)
    e[a_n + d_n: n - r_n] = s
    e[n - r_n:] = np.linspace(s, 0, r_n)
    return e


def pad_note(freq, length):
    """Warm pad: a few detuned saw-ish partials, gently low-passed by weighting harmonics."""
    n = int(length * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for det in (-0.07, 0.0, 0.07):
        f = freq * 2 ** (det / 12)
        for h in range(1, 7):
            sig += np.sin(2 * np.pi * f * h * t + rng.uniform(0, 6.28)) / (h ** 1.6)
    # slow tremolo for movement
    sig *= 1 + 0.08 * np.sin(2 * np.pi * 0.25 * t + rng.uniform(0, 6.28))
    return sig * env_adsr(n, 0.9, 0.6, 0.8, 1.4) / 6


def pluck(freq, length=0.9):
    n = int(length * SR)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 9)
           + 0.25 * np.sin(2 * np.pi * freq * 3 * t) * np.exp(-t * 14))
    return sig * np.exp(-t * 5.5) * np.minimum(1, t * 400)


def bass(freq, length):
    n = int(length * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    return sig * env_adsr(n, 0.02, 0.2, 0.7, 0.25)


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 50 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 11)


def hat(open_=False):
    n = int((0.22 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=0)  # crude high-pass
    return noise * np.exp(-t * (18 if open_ else 70))


def lowpass_sweep(noise, f0, f1):
    n = len(noise)
    out = np.zeros(n)
    y = 0.0
    cut = np.geomspace(f0, f1, n)
    a = 1 - np.exp(-2 * np.pi * cut / SR)
    for i in range(n):
        y += a[i] * (noise[i] - y)
        out[i] = y
    return out


def whoosh(length=0.9):
    n = int(length * SR)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    s = lowpass_sweep(noise, 300, 7000)
    s = s - lowpass_sweep(noise, 60, 400)  # remove rumble
    env = np.sin(np.pi * t) ** 2
    return s * env * 2.2


def sparkle():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for k, f in enumerate((1318.5, 1760.0, 2637.0)):
        d = k * 0.05
        m = t > d
        sig[m] += np.sin(2 * np.pi * f * (t[m] - d)) * np.exp(-(t[m] - d) * 9) * 0.5
    return sig


# ---------------------------------------------------------------- harmony (Am - F - C - G)
chords = [
    (45, [57, 60, 64]),   # Am
    (41, [53, 57, 60]),   # F
    (48, [55, 60, 64]),   # C
    (43, [50, 55, 59]),   # G
]
n_bars = int(np.ceil(DUR / BAR))
PUNCH_IN = 15.0   # drums enter with the projects section

for b in range(n_bars):
    t0 = b * BAR
    root, tones = chords[b % 4]
    last = t0 + BAR >= DUR - 0.01
    length = BAR + 1.2
    for k, m in enumerate(tones + [tones[0] + 12]):
        stereo(t0, pad_note(midi(m), length), 0.42 if not last else 0.5, pan=(-0.5 + k * 0.33))
    # bass: root on beats 1 and 3 (a bit more movement once the beat comes in)
    hits = [0, 2] if t0 < PUNCH_IN else [0, 1.5, 2, 3]
    for h in hits:
        stereo(t0 + h * BEAT, bass(midi(root), BEAT * 1.4), 0.55)
    # arpeggio enters around 5s
    if t0 >= 5.0:
        pattern = [0, 1, 2, 3, 2, 1, 2, 1]
        arp_tones = [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[1] + 24]
        for i, p in enumerate(pattern):
            m = arp_tones[p % len(arp_tones)]
            stereo(t0 + i * BEAT / 2, pluck(midi(m)), 0.30, pan=np.sin(i * 1.3) * 0.6)
    # drums
    if t0 >= PUNCH_IN:
        for beat in range(4):
            stereo(t0 + beat * BEAT, kick(), 0.8)
            stereo(t0 + beat * BEAT + BEAT / 2, hat(), 0.18, pan=0.2)
            if beat in (1, 3):
                stereo(t0 + beat * BEAT, hat(True) * 1.4, 0.2, pan=-0.2)

# ---------------------------------------------------------------- sound effects at the visual cuts
WIPES = [15.0, 31.0, 40.0, 46.0]
for w in WIPES:
    stereo(w - 0.35, whoosh(0.9), 0.55)
    stereo(w + 0.35, sparkle(), 0.35, pan=0.3)
# project card changes (3 inner changes) get a soft pluck + sparkle
for t in (19.0, 23.0, 27.0):
    stereo(t, sparkle(), 0.28, pan=-0.3)
# title hit at the very start and a final chord swell is already in the pad
stereo(0.3, whoosh(1.2), 0.35)
stereo(1.6, sparkle(), 0.3)

# ---------------------------------------------------------------- reverb (synthetic impulse response)
ir_len = int(1.8 * SR)
ir = rng.standard_normal(ir_len) * np.exp(-np.linspace(0, 1, ir_len) * 5.5)
ir[: int(0.01 * SR)] = 0


def reverb(x):
    L = len(x) + len(ir)
    size = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return y / (np.abs(y).max() + 1e-9)


wet_l = reverb(left)
wet_r = reverb(right)
mix_l = left + 0.35 * wet_l * np.abs(left).max()
mix_r = right + 0.35 * wet_r * np.abs(right).max()

# ---------------------------------------------------------------- master: fades, gentle limiter
t = np.arange(N) / SR
master = np.minimum(1, t / 1.5) * np.minimum(1, (DUR - t) / 2.5)
out = np.stack([mix_l * master, mix_r * master], axis=1)
peak = np.abs(out).max()
out = np.tanh(out / peak * 1.3) / np.tanh(1.3) * 0.85

pcm = (out * 32767).astype('<i2')
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f'wrote {OUT}: {DUR:.1f}s')
