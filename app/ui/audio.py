"""Listen's sound: test sounds or your own music played through each version's EQ (AutoEQ Local's sound.js, natively:
Web Audio there, sounddevice and NumPy/SciPy here).

- Sources: music (a short loop made here: sub-bass, bass, drums, chords, a bell melody and hi-hats; no audio files),
  pink noise, white noise, a sweep (20 Hz-20 kHz in 10 s), a tone (any frequency, moved live) and your own file
  (mp3, flac, wav, ogg … read with soundfile, converted to the sound card's rate). Everything loops.
- Versions: EQ off, the selected EQ and this IEM's EQs to compare. Each plays through its own filters all the time
  (each filter as an IIR biquad with squiglink's formulas, eq.engines.biquad, at the sound card's rate: what you hear
  is exactly the EQ on the graph), so switching is instant; the switch fades over a few milliseconds (no click).
- Level matching: every version at the same A-weighted pink-noise loudness, then one shared cut so none can clip
  (off: each one only turned down by its own highest boost). Ears: both the same version, or one in each ear.
Engine.render(frames) makes the sound without a sound card (checks); start()/stop() play it.
"""
import threading
import time

import numpy as np
from scipy import signal

SWEEP = {"dur": 10.0, "gap": 1.0, "f0": 20.0, "f1": 20000.0}
GRID = 20 * 1000 ** (np.arange(241) / 240)


def _a_weight(f):
    f2 = f * f
    ra = 12194 ** 2 * f2 * f2 / ((f2 + 20.6 ** 2) * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2)) * (f2 + 12194 ** 2))
    return ra * ra


AW = _a_weight(GRID)


# ---------------------------------------------------------------- the sounds
def noise(sr, pink, seconds=8, seed=1):
    rng = np.random.default_rng(seed)
    w = rng.uniform(-1, 1, int(sr * seconds))
    if pink:  # (a standard pink-noise filter: -3 dB per octave)
        b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
        a = [1, -2.494956002, 2.017265875, -0.522189400]
        w = signal.lfilter(b, a, w)
    w *= 0.1 / np.sqrt(np.mean(w * w))  # (-20 dBFS RMS)
    return np.column_stack([w, w]).astype(np.float32)


def sweep(sr):
    T, L = SWEEP["dur"], np.log(SWEEP["f1"] / SWEEP["f0"])
    t = np.arange(int(sr * T)) / sr
    ph = 2 * np.pi * SWEEP["f0"] * T / L * (np.exp(t / T * L) - 1)
    fade = np.minimum(1, np.minimum(t / 0.02, (T - t) / 0.02))
    d = np.concatenate([0.2 * fade * np.sin(ph), np.zeros(int(sr * SWEEP["gap"]))])
    return np.column_stack([d, d]).astype(np.float32)


def groove(sr, seed=2):
    """A four-bar loop at 100 bpm (Am F C G), made here (sound.js grooveBuffer's parts)."""
    rng = np.random.default_rng(seed)
    beat = 60 / 100
    bar = 4 * beat
    n = int(np.ceil(sr * 4 * bar))
    out = np.zeros((n, 2))
    mf = lambda m: 440 * 2 ** ((m - 69) / 12)

    def put(x, t, pan=0.0):
        i = int(t * sr)
        x = x[:max(0, n - i)]
        out[i:i + len(x), 0] += x * np.sqrt((1 - pan) / 2) * 1.4142
        out[i:i + len(x), 1] += x * np.sqrt((1 + pan) / 2) * 1.4142

    def env(length, vol, attack):
        k = np.arange(int(length * sr)) / sr
        return vol * np.where(k < attack, k / max(attack, 1e-4), np.exp(-(k - attack) / max(length - attack, 1e-3) * 9.2))

    def tone(f, length, vol, kind="sine", attack=0.004, lp=None, f_end=None):
        k = np.arange(int(length * sr)) / sr
        freq = f if f_end is None else f * (f_end / f) ** np.minimum(k / 0.13, 1)
        ph = 2 * np.pi * np.cumsum(np.broadcast_to(freq, k.shape)) / sr
        w = {"sine": np.sin(ph), "saw": 2 * ((ph / (2 * np.pi)) % 1) - 1,
             "triangle": 2 * np.abs(2 * ((ph / (2 * np.pi)) % 1) - 1) - 1}[kind]
        if lp:
            w = signal.sosfilt(signal.butter(2, min(lp, sr * 0.45), "low", fs=sr, output="sos"), w)
        return w * env(length, vol, attack)

    def mix(a, b):  # (two sounds of slightly different lengths, added)
        n_ = max(len(a), len(b))
        return np.pad(a, (0, n_ - len(a))) + np.pad(b, (0, n_ - len(b)))

    def hiss(length, hp, vol):
        w = rng.uniform(-1, 1, int(length * sr))
        w = signal.sosfilt(signal.butter(2, min(hp, sr * 0.45), "high", fs=sr, output="sos"), w)
        return w * env(length, vol, 0.001)

    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
    bell = [[76, 72, 69, 72], [77, 72, 69, 72], [79, 76, 72, 76], [74, 71, 67, 71]]
    for k in range(4):
        t0, ch = k * bar, chords[k]
        for b in [0, 2] + ([2.5] if k % 2 else []):  # kick
            put(tone(150, 0.42, 0.9, attack=0.002, f_end=42), t0 + b * beat)
        for b in (1, 3):  # snare
            put(mix(hiss(0.22, 1400, 0.45), tone(190, 0.12, 0.3, "triangle")), t0 + b * beat)
        for e in range(8):  # hi-hats
            put(hiss(0.28 if e == 7 else 0.05, 8000, 0.12 if e % 2 else 0.18), t0 + e * beat / 2, 0.35)
            put(tone(mf(ch[0] - 24 + (12 if e == 6 else 0)), beat / 2 * 0.9, 0.32, "saw", lp=520), t0 + e * beat / 2)  # bass
        for i, m in enumerate(ch):  # pad
            for dt in (-7, 7):
                put(tone(mf(m) * 2 ** (dt / 1200), bar * 0.98, 0.035, "saw", attack=0.35, lp=1900), t0, (i - 1) * 0.5)
        for i, m in enumerate(bell[k]):  # bell
            t = t0 + i * beat
            put(mix(tone(mf(m + 12), 0.9, 0.09, attack=0.002), tone(mf(m + 12) * 3.01, 0.35, 0.02, attack=0.002)), t, -0.3)
            put(tone(mf(chords[k][i % 3] + 24), 0.5, 0.05, attack=0.002), t + beat / 2, 0.3)
    out *= 0.5 / np.max(np.abs(out))
    return out.astype(np.float32)


def read_file(path, sr):
    """Your own audio at the sound card's rate, stereo (mono plays in both ears). Raises RuntimeError/OSError when it
    can't be read."""
    import soundfile
    from fractions import Fraction
    data, rate = soundfile.read(path, dtype="float32", always_2d=True)
    data = data[:, :2] if data.shape[1] >= 2 else np.repeat(data, 2, axis=1)
    if rate != sr:
        fr = Fraction(sr, rate).limit_denominator(1000)
        data = signal.resample_poly(data, fr.numerator, fr.denominator, axis=0).astype(np.float32)
    return data


# ---------------------------------------------------------------- an EQ: filters as biquads, its loudness
def sos_of(filters, sr):
    """The filters as second-order sections at this sample rate (a filter above what the card can play is skipped)."""
    from eq import engines
    rows = []
    for f in filters:
        if f.get("enabled", True) is False or not f.get("freq") or not f.get("q") or f["freq"] >= sr * 0.49:
            continue
        a1, a2, b0, b1, b2 = engines.biquad(f.get("type", "PK"), float(f["freq"]), float(f["gain"]), float(f["q"]), sr)
        rows.append([b0, b1, b2, 1.0, a1, a2])
    return np.asarray(rows, dtype=float).reshape(-1, 6)


def levels(filters, sr):
    """(peak boost dB, A-weighted pink-noise loudness dB) of an EQ: for level matching and clipping headroom."""
    from eq import engines
    on = [f for f in filters if f.get("enabled", True) is not False]
    g = engines.eq_gain(GRID, on, sr) if on else np.zeros_like(GRID)
    return max(0.0, float(np.max(g))), float(10 * np.log10(np.sum(AW * 10 ** (g / 10)) / np.sum(AW)))


class Engine:
    """The versions and the source; render() makes the next block of sound (the sound card's callback calls it)."""

    def __init__(self, sr=48000):
        self.sr, self.lock = sr, threading.Lock()
        self.slots = []            # [{"key", "label", "filters", "sig", "sos", "zi", "gain" (linear), "now": [L, R]}]
        self.active, self.ears, self.left, self.right = "off", "both", "off", "sel"
        self.level_match, self.volume_db = True, -24.0
        self._vol_now, self._mute, self._muted = None, False, False  # (the volume as applied; Stop's fade-out)
        self.source, self.pos, self.kind = None, 0, ""
        self.tone_hz, self.tone_phase, self.tone_level = 1000.0, 0.0, 0.0
        self.stream = None
        self.played = 0            # (samples since Play: where the sweep is)

    # ---------------------------------------------------------------- versions
    def set_versions(self, versions):
        """versions: [(key, label, filters)]; a version whose filters didn't change keeps its state (no click). One
        whose filters changed, or that's gone, fades out over the next block while the new one fades in (no dip)."""
        with self.lock:
            old = {s["key"]: s for s in self.slots if not s.get("fading")}
            slots, kept = [], set()
            for key, label, filters in versions:
                sig = repr([(f.get("type"), f.get("freq"), f.get("gain"), f.get("q"), f.get("enabled", True)) for f in filters])
                s = old.get(key)
                if s and s["sig"] == sig:
                    kept.add(key)
                if not s or s["sig"] != sig:
                    sos = sos_of(filters, self.sr)
                    # (an edited version goes on from its filters' state when it has as many: no restart transient)
                    zi = s["zi"].copy() if s and len(s["sos"]) == len(sos) else np.zeros((len(sos), 2, 2))
                    s = {"key": key, "filters": filters, "sig": sig, "sos": sos, "now": [0.0, 0.0],
                         "zi": zi, "lv": levels(filters, self.sr)}
                s["label"] = label
                slots.append(s)
            fading = [dict(s, fading=True) for k, s in old.items() if k not in kept and any(s["now"])]
            # (ones still fading from a change before the sound card's next block go on fading: two changes in one
            # block, e.g. a slider dragged, would otherwise cut the version heard dead)
            still = [s for s in self.slots if s.get("fading") and any(s["now"])]
            self.slots = slots
            self._gains()
            self.slots += still + fading

    def _gains(self):
        live = [s for s in self.slots if not s.get("fading")]
        if not live:
            return
        lv = [s["lv"] for s in live]
        c = min(loud - peak for peak, loud in lv)  # (the shared cut: none clips)
        for s, (peak, loud) in zip(live, lv):
            s["gain_db"] = (-loud + c) if self.level_match else -peak
            s["gain"] = 10 ** (s["gain_db"] / 20)

    def set_level_match(self, on):
        with self.lock:
            self.level_match = bool(on)
            self._gains()

    def target(self, s):
        """[L, R] gain the version should have now (0: not heard)."""
        if s.get("fading"):
            return [0.0, 0.0]
        if self.ears == "split":
            return [s["gain"] if s["key"] == self.left else 0.0, s["gain"] if s["key"] == self.right else 0.0]
        return [s["gain"], s["gain"]] if s["key"] == self.active else [0.0, 0.0]

    # ---------------------------------------------------------------- the source
    def set_source(self, kind, data=None):
        with self.lock:
            self.kind, self.source, self.pos, self.played = kind, data, 0, 0

    def _source_block(self, n):
        if self.kind == "tone":
            k = np.arange(n)
            step = 2 * np.pi * self.tone_hz / self.sr
            ph = self.tone_phase + step * (k + 1)
            self.tone_phase = float(ph[-1] % (2 * np.pi))
            lvl = self.tone_level + (0.2 - self.tone_level) * np.minimum(1, (k + 1) / (0.01 * self.sr))  # (fades in)
            self.tone_level = float(lvl[-1])
            x = (lvl * np.sin(ph)).astype(np.float32)
            return np.column_stack([x, x])
        if self.source is None or not len(self.source):
            return np.zeros((n, 2), np.float32)
        idx = (self.pos + np.arange(n)) % len(self.source)
        self.pos = int((self.pos + n) % len(self.source))
        return self.source[idx]

    def render(self, n):
        """The next n frames, stereo float32: the source through every version, each version's ears faded to where
        they should be over the block."""
        with self.lock:
            x = self._source_block(n).astype(float)
            out = np.zeros((n, 2))
            ramp = np.linspace(0, 1, n)
            for s in self.slots:
                want = self.target(s)
                if len(s["sos"]):
                    y = np.empty_like(x)
                    for ch in range(2):
                        y[:, ch], s["zi"][:, ch, :] = signal.sosfilt(s["sos"], x[:, ch], zi=s["zi"][:, ch, :])
                else:
                    y = x
                for ch in range(2):
                    a, b = s["now"][ch], want[ch]
                    if a or b:
                        out[:, ch] += y[:, ch] * (a + (b - a) * ramp)
                s["now"] = want
            self.slots = [s for s in self.slots if not (s.get("fading") and not any(s["now"]))]  # (faded out: gone)
            self.played += n
            # (the volume glides over the block from where it was, and to 0 when Stop asked: no clicks)
            want = 0.0 if self._mute else 10 ** (self.volume_db / 20)
            was = want if self._vol_now is None else self._vol_now
            self._vol_now = want
            if self._mute:
                self._muted = True
            return (out * (was + (want - was) * ramp)[:, None]).astype(np.float32)

    def sweep_hz(self):
        """Where the sweep is now (None in its gap, or for other sounds)."""
        if self.kind != "sweep":
            return None
        t = (self.played / self.sr) % (SWEEP["dur"] + SWEEP["gap"])
        return SWEEP["f0"] * (SWEEP["f1"] / SWEEP["f0"]) ** (t / SWEEP["dur"]) if t < SWEEP["dur"] else None

    # ---------------------------------------------------------------- the sound card
    def start(self):
        import sounddevice
        if self.stream is None:
            def callback(outdata, frames, _time, _status):
                outdata[:] = self.render(frames)
            self.stream = sounddevice.OutputStream(samplerate=self.sr, channels=2, dtype="float32", callback=callback,
                                                   latency="low")
        self.stream.start()

    def stop(self):
        if self.stream is not None:
            self._mute, self._muted = True, False
            t0 = time.time()
            while not self._muted and time.time() - t0 < 0.25:  # (one faded block played first)
                time.sleep(0.005)
            time.sleep(0.03)
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.tone_level = 0.0
        self._vol_now, self._mute, self._muted = None, False, False


def card_rate():
    """The default sound card's sample rate (48000 when it can't be asked)."""
    try:
        import sounddevice
        return int(sounddevice.query_devices(kind="output")["default_samplerate"])
    except Exception:  # noqa: BLE001 - no sound card, no driver: the default
        return 48000
