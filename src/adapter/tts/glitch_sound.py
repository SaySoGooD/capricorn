"""Цифровой «треск», с которым появляется Капри."""
import math
import random
import struct
import wave


def make_glitch_sound(path, volume=100):
    """Короткий цифровой «треск» при появлении. volume 0..100 — громкость Капри."""
    rnd = random.Random(42)
    frames = bytearray()
    sr = 22050
    n = int(sr * 0.22)
    freq = 900
    for i in range(n):
        if i % 600 == 0:
            freq = rnd.choice([300, 700, 1200, 1800, 2400])
        env = (1 - i / n) ** 1.5
        sq = 1 if math.sin(2 * math.pi * freq * i / sr) > 0 else -1
        noise = rnd.uniform(-1, 1) if (i // 400) % 3 == 0 else 0
        v = int(5500 * volume / 100 * env * (0.6 * sq + 0.5 * noise))
        frames += struct.pack("<h", max(-32767, min(32767, v)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(frames))


def play_sound_async(path):
    try:
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass
