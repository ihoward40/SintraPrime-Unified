"""WAKE-DIAG harness (Principal-driven, local only).

Proves the audio-to-model contract and produces real scores from YOUR mic.
No STT, no Hermes, no TTS. PRE_WAKE_CLOUD_AUDIO_UPLOADS = 0.

Run:  C:\\Users\\admin\\AppData\\Local\\hermes\\hermes-agent\\venv\\Scripts\\python.exe test_wake_diag.py
Follow the on-screen prompts (you will say "Hey Jarvis" three times).
"""
import sys
import time

import numpy as np
import sounddevice as sd

sys.path.insert(0, "C:/Users/admin/SintraPrime-Unified-jarvis-001b")
import jarvis_voice_mvp as jvm  # noqa: E402

RATE = jvm.SAMPLE_RATE
THRESHOLD = 0.5

print("=" * 64)
print("WAKE-DIAG - wake-only scoring diagnostic (local, no cloud)")
print("=" * 64)

# ---- Load wake model (same path as the MVP) ----
from openwakeword.model import Model  # noqa: E402
model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
model.predict(np.zeros(12800, dtype=np.int16))  # warm-up
print("[diag] wake model loaded + warmed up\n")

def record(seconds: float) -> np.ndarray:
    audio = sd.rec(int(seconds * RATE), samplerate=RATE, channels=1, dtype="float32")
    sd.wait()
    return audio

def max_score(audio: np.ndarray, frame_samples: int) -> float:
    pcm = (audio * 32767).clip(-32768, 32767).astype(np.int16)[:, 0]
    best = 0.0
    for off in range(0, len(pcm) - frame_samples + 1, frame_samples):
        s = model.predict(pcm[off:off + frame_samples])
        v = float(s.get("hey_jarvis", 0.0)) if isinstance(s, dict) else float(s)
        best = max(best, v)
    model.reset()
    return best

# ---- PHASE 0: PCM contract + cast proof ----
print("[PHASE 0] audio contract (1s capture, stay quiet)")
a0 = record(1.0)
raw = a0[:, 0]
trunc = raw.astype(np.int16)                      # the OLD (buggy) cast
proper = (raw * 32767).clip(-32768, 32767).astype(np.int16)
print(f"  WAKE_PCM_DTYPE          = float32 (sounddevice stream)")
print(f"  WAKE_PCM_SAMPLE_RATE    = {RATE}")
print(f"  WAKE_PCM_CHANNELS       = {a0.shape[1]}")
print(f"  raw float  min/max      = {raw.min():.4f} / {raw.max():.4f}")
print(f"  truncating cast uniq    = {np.unique(trunc)[:5]}  (flattened!)")
print(f"  proper scale   min/max  = {proper.min()} / {proper.max()}")
print(f"  rms(float)              = {float(np.sqrt(np.mean(raw**2))):.5f}")
print()

# ---- PHASE 1: silence baseline ----
print("[PHASE 1] SILENCE baseline (3s, stay quiet)")
s0 = record(3.0)
SILENCE_MAX = max_score(s0, 1280)
print(f"  SILENCE_MAX_SCORE = {SILENCE_MAX:.4f}\n")

# ---- PHASE 2: three spoken attempts ----
attempts = []
for i in (1, 2, 3):
    print(f"[PHASE 2.{i}] >>> SAY \"HEY JARVIS\" NOW ({i}/3) <<<")
    for t in (3, 2, 1):
        print(f"    {t}...", flush=True)
        time.sleep(1.0)
    a = record(4.0)
    m1280 = max_score(a, 1280)
    m3840 = max_score(a, 3840)
    m12800 = max_score(a, 12800)
    rms = float(np.sqrt(np.mean(a[:, 0] ** 2)))
    attempts.append((m1280, m3840, m12800, rms))
    fired = m1280 >= THRESHOLD
    print(f"  rms={rms:.5f}  FRAME_1280_MAX={m1280:.4f}  "
          f"FRAME_3840_MAX={m3840:.4f}  FRAME_12800_MAX={m12800:.4f}  "
          f"=> WAKE_ONLY_{i} = {'PASS' if fired else 'FAIL'}")
    print()

# ---- Summary ----
print("=" * 64)
print("RESULT PACKET")
print("=" * 64)
print(f"WAKE_PCM_DTYPE              = float32 -> int16 (proper scale)")
print(f"WAKE_PCM_SAMPLE_RATE        = {RATE}")
print(f"WAKE_PCM_CHANNELS           = 1")
print(f"SILENCE_MAX_SCORE           = {SILENCE_MAX:.4f}")
for i, (m1, m3, m12, rms) in enumerate(attempts, 1):
    print(f"ATTEMPT_{i}_MAX_SCORE (1280) = {m1:.4f}   (rms={rms:.5f})")
if attempts:
    print(f"FRAME_1280_MAX_SCORE        = {max(a[0] for a in attempts):.4f}")
    print(f"FRAME_3840_MAX_SCORE        = {max(a[1] for a in attempts):.4f}")
    print(f"FRAME_12800_MAX_SCORE       = {max(a[2] for a in attempts):.4f}")
print(f"DETECTION_THRESHOLD         = {THRESHOLD} (single-score policy)")
wake_only = [a[0] >= THRESHOLD for a in attempts]
for i, ok in enumerate(wake_only, 1):
    print(f"WAKE_ONLY_{i}                = {'PASS' if ok else 'FAIL'}")
