"""Batch D wake-wiring smoke harness (headless, no TUI loop).

Verifies: wake model load + warm-up, persistent mic front-end + drain,
0.8s openWakeWord scoring cadence, re-arm flag lifecycle, PTT guard,
front-end cleanup. Run with the MVP venv python.
Local only - PRE_WAKE_CLOUD_AUDIO_UPLOADS = 0.
"""
import sys
import threading
import time

import numpy as np

sys.path.insert(0, "C:/Users/admin/SintraPrime-Unified-jarvis-001b")
import jarvis_voice_mvp as jvm  # noqa: E402

results = {}

def check(name, cond):
    results[name] = bool(cond)
    print(f"{name}: {'PASS' if cond else 'FAIL'}")

s = jvm.JarvisVoiceSession()

# A) wake model load + warm-up (same code path as _start_wake_listener)
from openwakeword.model import Model  # noqa: E402
s._wake_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
s._wake_model.predict(
    np.zeros(int(jvm.SAMPLE_RATE * jvm.WAKE_FRAME_MS / 1000), dtype=np.int16))
check("A_WAKE_MODEL_WARMUP", s._wake_model is not None)

# B) persistent front-end + drain
s.mic.start_fe()
time.sleep(1.0)
buf = s.mic.drain()
check("B_FRONTEND_DRAIN", buf is not None and len(buf) > 0)
print("   samples in 1.0s:", 0 if buf is None else len(buf))

# C) score the drained chunk through the 0.8s cadence (same slicing logic)
chunk = buf[:, 0].astype(np.int16)
fs = int(jvm.SAMPLE_RATE * jvm.WAKE_FRAME_MS / 1000)
n = 0
for off in range(0, len(chunk) - fs + 1, fs):
    scores = s._wake_model.predict(chunk[off:off + fs])
    n += 1
check("C_SCORE_PATH", n >= 1)
print("   chunks scored:", n)

# D) re-arm flag lifecycle (canonical cycle ... -> RETURNING_TO_WAKE -> WAKE_READY)
s._wake_mode = True
s._wake_hands_free = True
s._running = True
s._return_to_wake("smoke")
check("D_REARM_FLAGS", s._wake_mode is False and s._wake_hands_free is False
      and s.state == jvm.State.WAKE_READY)

# E) PTT guard while hands-free capture is active
s._wake_hands_free = True
s._on_hotkey_press()
check("E_PTT_GUARD", s.mic.is_recording is False)
s._wake_hands_free = False

# E2) Step 5: synthetic wake-score injection — deterministic proof that
# owner=NONE + state=WAKE_READY + qualifying score -> claim -> capture,
# with zero microphone uncertainty.
s._wake_enabled = True
s.state = jvm.State.WAKE_READY
s._current_turn = 0
synth = threading.Thread(target=s._on_wake_detected, daemon=True)
synth.start()
synth.join(timeout=3)
check("E2_SYNTHETIC_WAKE_INJECTION",
      s._turn_owner == "WAKE" and s.mic.is_recording)
s._wake_hands_free = False          # stop capture loop from spinning
s.mic._rec = False                  # dummy-mic style release
with s._turn_lock:
    s._turn_owner = None            # release claim
s._wake_enabled = False             # keep detector quiet for F)

# F) cleanup
s.mic.stop_fe()
check("F_CLEANUP", s.mic._fe_stream is None)

fails = [k for k, v in results.items() if not v]
print(f"\n=== WAKE SMOKE: TOTAL={len(results)} PASS={len(results) - len(fails)} FAIL={len(fails)} ===")
for k in fails:
    print("FAILED:", k)
sys.exit(1 if fails else 0)
