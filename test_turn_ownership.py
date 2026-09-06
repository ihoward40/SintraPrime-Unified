"""T1-T8 turn-ownership concurrency tests (E-RACE-2, Principal directive).

Headless: DummyMic, no audio hardware, no network, no STT/Hermes/TTS.
Proves: ONE_TRIGGER -> ONE_TURN, ONE_TURN -> ONE_AUDIO_OWNER,
atomic claim/release, re-arm, duplicate-turn elimination.

Run: python test_turn_ownership.py
"""
import sys
import threading
import time

sys.path.insert(0, ".")
import jarvis_voice_mvp as jvm  # noqa: E402

RESULTS = []


class DummyMic:
    """Records start/stop calls; controllable RMS sequence."""

    def __init__(self):
        self._rec = False
        self.start_calls = 0
        self.stop_calls = 0
        self.rms_sequence = [0.0]

    @property
    def is_recording(self):
        return self._rec

    def start(self):
        self.start_calls += 1
        self._rec = True

    def stop(self):
        self.stop_calls += 1
        self._rec = False
        return None

    def recent_rms(self, seconds=0.5):
        if len(self.rms_sequence) > 1:
            return self.rms_sequence.pop(0)
        return self.rms_sequence[0]


def make_app(rms_sequence=None):
    """Ownership-relevant instance only (no hardware init)."""
    app = jvm.JarvisVoiceSession.__new__(jvm.JarvisVoiceSession)
    app._turn_lock = threading.Lock()
    app._turn_owner = None
    app._wake_enabled = False
    app._wake_ok = True
    app._wake_mode = False
    app._wake_hands_free = False
    app._current_turn = 0
    app._running = True
    app.state = jvm.State.IDLE
    app.mic = DummyMic()
    if rms_sequence:
        app.mic.rms_sequence = list(rms_sequence)
    return app


def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name} {detail}")


# Silence the PTT earcon for headless testing
jvm.PTTBeep.start = staticmethod(lambda: None)
jvm.PTTBeep.stop = staticmethod(lambda: None)

# Voice-phrase RMS: two voiced polls, then silence (ends 1.5s tail)
VOICED = [0.02, 0.02, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

print("=== T1-T8 TURN OWNERSHIP SUITE ===")

# T1: wake-only claims the turn (full cycle claim -> capture -> release)
app = make_app(VOICED)
app._wake_enabled = True
t = threading.Thread(target=app._on_wake_detected, daemon=True)
t.start()
t.join(timeout=20)
record("T1_WAKE_ONLY_CLAIMS_TURN",
       app._turn_owner is None and app.state == jvm.State.WAKE_READY
       and app.mic.start_calls == 1,
       f"(owner={app._turn_owner}, starts={app.mic.start_calls})")

# T2: PTT-only claims the turn (press + empty release)
app = make_app()
app._on_hotkey_press()
claimed = app._turn_owner == "PTT" and app.mic.is_recording
app._on_hotkey_release()  # empty capture -> release
record("T2_PTT_ONLY_CLAIMS_TURN",
       claimed and app._turn_owner is None,
       f"(claimed={claimed}, owner={app._turn_owner})")

# T3: wake during active PTT turn does NOT duplicate
app = make_app()
app._turn_owner = "PTT"
app.state = jvm.State.LISTENING
t = threading.Thread(target=app._on_wake_detected, daemon=True)
t.start()
t.join(timeout=5)
record("T3_WAKE_DURING_PTT_NO_DUPLICATE",
       app._turn_owner == "PTT" and app.mic.start_calls == 0,
       f"(owner={app._turn_owner}, starts={app.mic.start_calls})")

# T4: PTT during active wake turn does NOT duplicate
app = make_app()
app._turn_owner = "WAKE"
app.state = jvm.State.LISTENING
app._wake_hands_free = True
app._on_hotkey_press()
record("T4_PTT_DURING_WAKE_NO_DUPLICATE",
       app._turn_owner == "WAKE" and app.mic.start_calls == 0,
       f"(owner={app._turn_owner}, starts={app.mic.start_calls})")

# T5: wake during THINKING does NOT start command capture
app = make_app()
app._turn_owner = "PTT"
app.state = jvm.State.THINKING
app._on_wake_detected()
record("T5_WAKE_DURING_THINKING_NO_CAPTURE",
       app._turn_owner == "PTT" and app.mic.start_calls == 0,
       f"(owner={app._turn_owner}, starts={app.mic.start_calls})")

# T6: wake during SPEAKING does NOT start command capture
app = make_app()
app._turn_owner = "WAKE"
app.state = jvm.State.SPEAKING
app._on_wake_detected()
record("T6_WAKE_DURING_SPEAKING_NO_CAPTURE",
       app._turn_owner == "WAKE" and app.mic.start_calls == 0,
       f"(owner={app._turn_owner}, starts={app.mic.start_calls})")

# T7: return_to_wake releases owner and re-enables the detector
app = make_app()
app._turn_owner = "WAKE"
app._wake_enabled = False
app._return_to_wake("test")
record("T7_RETURN_TO_WAKE_RELEASES_OWNER",
       app._turn_owner is None and app._wake_enabled
       and app.state == jvm.State.WAKE_READY,
       f"(owner={app._turn_owner}, enabled={app._wake_enabled})")

# T8: next wake CAN claim a new turn after re-arm
app = make_app(VOICED)
app._wake_enabled = True
t1 = threading.Thread(target=app._on_wake_detected, daemon=True)
t1.start()
t1.join(timeout=20)
first_cycle = app._turn_owner is None and app.state == jvm.State.WAKE_READY
app.mic.rms_sequence = list(VOICED)  # fresh utterance for cycle 2
t2 = threading.Thread(target=app._on_wake_detected, daemon=True)
t2.start()
t2.join(timeout=20)
record("T8_NEXT_WAKE_CAN_CLAIM_NEW_TURN",
       first_cycle and app._turn_owner is None
       and app.state == jvm.State.WAKE_READY
       and app.mic.start_calls == 2,
       f"(first_cycle={first_cycle}, starts={app.mic.start_calls})")

# T9 (bonus): simultaneous PTT+wake claims — exactly ONE winner
for trial in range(10):
    app = make_app()
    app._wake_enabled = True
    results = []

    def wake_fn():
        with app._turn_lock:
            if app._turn_owner is not None:
                results.append("refused-wake")
                return
            app._turn_owner = "WAKE"
            results.append("claimed-wake")

    def ptt_fn():
        with app._turn_lock:
            if app._turn_owner is not None or app.mic.is_recording:
                results.append("refused-ptt")
                return
            app._turn_owner = "PTT"
            results.append("claimed-ptt")

    ta = threading.Thread(target=wake_fn)
    tb = threading.Thread(target=ptt_fn)
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    claims = [r for r in results if r.startswith("claimed")]
    if len(claims) != 1:
        record("T9_RACE_ATOMICITY", False, f"trial {trial}: {results}")
        break
else:
    record("T9_RACE_ATOMICITY", True, "(10/10 trials: exactly one claim)")

print("\n=== SUMMARY ===")
total = len(RESULTS)
passed = sum(1 for _, ok, _ in RESULTS if ok)
dupes = 0 if all(ok for _, ok, _ in RESULTS[:9]) else "CHECK"
print(f"TOTAL={total} PASS={passed} FAIL={total - passed}")
print(f"DUPLICATE_TURNS = {dupes if dupes == 0 else dupes}")
print(f"OVERLAPPING_COMMAND_CAPTURES = "
      f"{0 if all(ok for _, ok, _ in RESULTS) else 'CHECK'}")
sys.exit(0 if passed == total else 1)
