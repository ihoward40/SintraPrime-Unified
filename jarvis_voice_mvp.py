#!/usr/bin/env python3
"""JARVIS SPEAKS DESKTOP — MVP-1+ (JARVIS_VOICE_CONVERGENCE_002)
Push-to-talk → mic capture → faster_whisper STT → Hermes bridge → SAPI TTS → speakers.
Thin I/O shell. No competing intelligence. No B2 mutation. Read-only conversation.
Voice answer style: concise by default.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SAMPLE_RATE = 16000          # Whisper expects 16kHz
CHANNELS = 1                   # Mono
HOTKEY = "<ctrl>+<alt>+j"     # Push-to-talk (hold-to-speak)
DEVICE_INDEX = None            # None = system default input
MAX_RECORD_SECONDS = 30        # Safety bound — stop capture after this
SILENCE_RMS_FLOOR = 0.005      # Not used for VAD yet — release-to-stop

# V13 — Voice response style
VOICE_RESPONSE_STYLE = "CONCISE_BY_DEFAULT"

# V14 — Status queries require fresh context
STATUS_QUERY_FRESH_CONTEXT = True

# SAPI voice index (0 = David, 1 = Zira). Pick the one that sounds best.
SAPI_VOICE_IDX = 0
SAPI_RATE = 1                  # -10..10 speaking rate

RECEIPTS_DIR = Path.home() / ".jarvis" / "receipts"
SESSION_DIR = Path.home() / ".jarvis" / "session"
TEMP_DIR = Path(tempfile.mkdtemp(prefix="jarvis_mvp_"))

# V15 — ElevenLabs TTS (optional — set ELEVEN_API_KEY env var to enable)
ELEVEN_API_KEY = os.environ.get("ELEVEN_API_KEY", "")

# BATCH D — Wake word (LOCAL ONLY; PRE_WAKE_CLOUD_AUDIO_UPLOADS = 0)
# Trigger-only change: "Hey Jarvis" starts the SAME certified voice loop.
WAKE_WORD_ENABLED = True
WAKE_WORD = "hey jarvis"
WAKE_SENSITIVITY = 0.5           # openWakeWord default positive threshold
WAKE_CONFIRMATION_FRAMES = 1     # single qualifying score (diagnosis-first
                                 # policy; debounce/confirmation returns after
                                 # false-trigger testing)
WAKE_FRAME_MS = 80               # upstream openWakeWord test cadence:
                                 # predict() in 1280-sample (80ms) steps at
                                 # 16kHz - the model's native stride
WAKE_SPEECH_RMS = 0.01           # hands-free speech threshold
WAKE_REARM_DELAY_S = 1.0         # cooldown before re-arming after a turn

# ---------------------------------------------------------------------------
# Voice session states (mirrors SP-VOICE-001 semantics)
# ---------------------------------------------------------------------------
class State:
    WAKE_READY = "WAKE_READY"
    WAKE_DETECTED = "WAKE_DETECTED"
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    RETURNING_TO_WAKE = "RETURNING_TO_WAKE"
    ERROR = "ERROR"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")

def hermes_exe() -> str:
    """Locate the hermes CLI executable."""
    candidates = [
        shutil.which("hermes"),
        str(Path.home() / "AppData" / "Local" / "hermes" / "hermes-agent" / "venv" / "Scripts" / "hermes.exe"),
        str(Path.home() / "AppData" / "Local" / "hermes" / "hermes-agent" / "hermes.exe"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return "hermes"

HERMES_CMD = hermes_exe()
# Voice bridge model provider. The machine default (thinkingmachines) can
# hard-fail with credential 404s and hang one-shot runs; voice uses the
# explicitly-configured OpenRouter path (key present, verified).
VOICE_PROVIDER = os.environ.get("JARVIS_VOICE_PROVIDER", "openrouter")

# ---------------------------------------------------------------------------
# Audio capture (V3)
# ---------------------------------------------------------------------------
class MicCapture:
    """Bounded push-to-talk microphone capture via sounddevice."""

    def __init__(self, device: Optional[int] = None, rate: int = SAMPLE_RATE,
                 channels: int = CHANNELS):
        self.device = device
        self.rate = rate
        self.channels = channels
        self._buffer: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._is_recording = False
        self._lock = threading.Lock()
        # BATCH D — persistent wake front-end (single shared stream)
        self._fe_running = False
        self._fe_stream = None

    def _callback(self, indata: np.ndarray, frames: int, time_info, status):
        if status:
            print(f"[mic] status: {status}")
        # BATCH D: front-end mode buffers continuously (wake scoring drains
        # it); PTT recording buffers as before. One stream serves both.
        if self._is_recording or self._fe_running:
            with self._lock:
                self._buffer.append(indata.copy())

    def start_fe(self):
        """Persistent capture front-end for wake scoring (BATCH D).

        Opens ONE stream at startup; wake detector drains it. PTT start/stop
        reuse this stream (no second device stream)."""
        if self._fe_stream is not None:
            return
        self._fe_running = True
        self._fe_stream = sd.InputStream(
            samplerate=self.rate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
            callback=self._callback,
            blocksize=1024,
        )
        self._fe_stream.start()

    def stop_fe(self):
        """Close the persistent front-end stream (shutdown)."""
        self._fe_running = False
        if self._fe_stream is not None:
            try:
                self._fe_stream.stop()
                self._fe_stream.close()
            except Exception:
                pass
            self._fe_stream = None

    def start(self):
        with self._lock:
            self._buffer = []
            self._is_recording = True
        if self._fe_stream is not None:
            return  # persistent front-end is already capturing
        self._stream = sd.InputStream(
            samplerate=self.rate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
            callback=self._callback,
            blocksize=1024,
        )
        self._stream.start()

    def stop(self) -> Optional[np.ndarray]:
        with self._lock:
            self._is_recording = False
        if self._fe_stream is not None:
            # Front-end stream stays open; return just the PTT/hands-free window
            with self._lock:
                if not self._buffer:
                    return None
                return np.concatenate(self._buffer, axis=0)
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._buffer:
                return None
            return np.concatenate(self._buffer, axis=0)

    def drain(self):
        """Return and clear buffered audio (wake-scoring front-end)."""
        with self._lock:
            if not self._buffer:
                return None
            audio = np.concatenate(self._buffer, axis=0)
            self._buffer = []
            return audio

    def recent_rms(self, seconds: float = 0.8) -> float:
        """RMS of the most recent `seconds` of buffered audio (read-only).

        BATCH D: used ONLY for hands-free end-of-utterance detection after
        wake-word capture. Does not alter push-to-talk behavior.
        """
        with self._lock:
            if not self._buffer:
                return 0.0
            need = int(self.rate * seconds)
            tail = []
            for blk in reversed(self._buffer):
                tail.insert(0, blk)
                if sum(len(b) for b in tail) >= need:
                    break
        audio = np.concatenate(tail, axis=0)[-need:]
        return float(np.sqrt(np.mean(audio ** 2)))

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def duration_seconds(self) -> float:
        with self._lock:
            if not self._buffer:
                return 0.0
            total_samples = sum(len(b) for b in self._buffer)
            return total_samples / self.rate

# ---------------------------------------------------------------------------
# STT (V4)
# ---------------------------------------------------------------------------
class LocalSTT:
    """faster_whisper wrapper. Model preloaded at startup in JARVIS_VOICE_CONVERGENCE_002."""

    def __init__(self, model_size: str = "base", language: str = "en"):
        self.model_size = model_size
        self.language = language
        self._model = None
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        print(f"[stt] Loading faster_whisper model '{self.model_size}'...")
        from faster_whisper import WhisperModel
        self._model = WhisperModel(
            self.model_size,
            device="cpu",
            compute_type="int8",
        )
        self._loaded = True
        print("[stt] Model ready.")

    def preload(self):
        """Preload the model at startup to eliminate cold-start latency."""
        self._load()

    def transcribe(self, audio: np.ndarray) -> Optional[dict]:
        self._load()
        t0 = time.time()

        # Save audio to temp WAV for WhisperModel
        wav_path = TEMP_DIR / f"capture_{int(time.time()*1000)}.wav"
        try:
            audio_i16 = (audio * 32767).clip(-32768, 32767).astype(np.int16)
            if audio_i16.ndim == 1:
                pass
            elif audio_i16.shape[1] == 1:
                audio_i16 = audio_i16[:, 0]
            else:
                audio_i16 = audio_i16.mean(axis=1).astype(np.int16)

            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_i16.tobytes())

            segments, info = self._model.transcribe(
                str(wav_path),
                language=self.language,
                beam_size=5,
                vad_filter=True,
            )
            text_parts = []
            for seg in segments:
                text_parts.append(seg.text.strip())
            full_text = " ".join(text_parts).strip()
            elapsed = time.time() - t0
            return {
                "text": full_text,
                "language": info.language if info else self.language,
                "duration_seconds": info.duration if info else 0.0,
                "stt_ms": round(elapsed * 1000),
            }
        finally:
            try:
                wav_path.unlink(missing_ok=True)
            except Exception:
                pass

# ---------------------------------------------------------------------------
# Hermes bridge (V5)
# ---------------------------------------------------------------------------
class HermesBridge:
    """Persistent Hermes session via the machine-readable -Q/--quiet contract.

    Primary contract (CLI_PRESENTATION_FORMAT != MACHINE_INTERFACE):
      stdout = ONLY the final assistant response
      stderr = diagnostics + "session_id: <id>"
    Turn 1: hermes chat -q "<text>" -Q --yolo
    Turn N: ... --resume <session_id>
    Legacy TUI-box parsing is kept ONLY as a diagnostic fallback if -Q
    ever returns box graphics (e.g. older Hermes build).
    """

    def __init__(self):
        self._session_id: Optional[str] = None
        self._turn_count = 0
        self._lock = threading.Lock()

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    def send(self, text: str) -> Optional[dict]:
        """Send text to Hermes and return response dict."""
        with self._lock:
            t0 = time.time()
            # -Q/--quiet: machine-readable single-query contract — stdout
            # carries ONLY the final response; stderr carries session_id.
            cmd = [HERMES_CMD, "chat", "-q", text, "-Q", "--yolo",
                   "--provider", VOICE_PROVIDER]
            if self._session_id:
                cmd.extend(["--resume", self._session_id])

            env = {**os.environ}
            env.setdefault("PYTHONUTF8", "1")
            env.setdefault("PYTHONIOENCODING", "utf-8")

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=600,
                    env=env,
                )
            except UnicodeDecodeError as e:
                self._bridge_error = f"UTF8_DECODE_FAIL: {e}"
                print(f"\n✗ Bridge decode error: {e}", flush=True)
                return None
            except subprocess.TimeoutExpired as e:
                self._bridge_error = f"HERMES_TIMEOUT: {e}"
                print(f"\n✗ Bridge timeout after 600s", flush=True)
                return None

            stdout = result.stdout or ""
            stderr = result.stderr or ""

            # Session id: prefer stderr "session_id: <id>" (-Q contract);
            # fall back to the legacy stdout "Session: <id>" line.
            if not self._session_id:
                m = re.search(r"session_id:\s+(\S+)", stderr) or \
                    re.search(r"Session:\s+(\S+)", stdout + stderr)
                if m:
                    self._session_id = m.group(1).strip()

            reply, reply_source = self._extract_reply(stdout)

            elapsed = time.time() - t0
            self._turn_count += 1

            return {
                "reply": reply,
                "reply_source": reply_source,
                "session_id": self._session_id,
                "turn": self._turn_count,
                "hermes_ms": round(elapsed * 1000),
                "raw_stdout": stdout,
                "raw_stderr": stderr,
                "returncode": result.returncode,
            }

    def _extract_reply(self, stdout: str) -> tuple:
        """Return (reply_text, source).

        Primary: -Q quiet contract — stdout IS the final response.
        Fallback: legacy TUI box parsing (last non-empty box), used only
        when -Q output unexpectedly contains box markers.
        """
        ansi = re.compile(r"\x1b\[[0-9;]*m")
        text = ansi.sub("", stdout).strip()

        # Machine contract: clean stdout, no presentation graphics.
        if text and "╭" not in text and "╰" not in text:
            return text, "quiet_contract"

        # Legacy fallback — older Hermes builds printed TUI boxes.
        reply = self._extract_reply_from_boxes(stdout)
        if reply:
            return reply, "legacy_box_fallback"

        # No reply at all — emit diagnostics so failures are distinguishable.
        lines = [l.strip() for l in stdout.split("\n")[-12:] if l.strip()]
        print("  ⚠ bridge: no final response found. stdout tail:")
        for l in lines:
            print(f"    | {l}")
        return "", "none"

    def _extract_reply_from_boxes(self, stdout: str) -> str:
        """DEPRECATED legacy TUI-box parser. Kept only as diagnostic fallback."""
        ansi = re.compile(r"\x1b\[[0-9;]*m")
        lines = stdout.split("\n")
        boxes = []          # each box: list of stripped text lines
        in_box = False
        for line in lines:
            stripped = ansi.sub("", line)
            if "╭" in stripped[:4]:
                in_box = True
                boxes.append([])
                continue
            if "╰" in stripped[:4] or "╯" in stripped[:4]:
                in_box = False
                continue
            if in_box:
                s = stripped.strip()
                if s:
                    boxes[-1].append(s)

        # Return the LAST non-empty box (the final assistant reply).
        for box in reversed(boxes):
            text = " ".join(box).strip()
            if text:
                return text
        return ""


# ---------------------------------------------------------------------------
# TTS (V6) — SAPI via win32com (zero new dependencies)
# ---------------------------------------------------------------------------
class SAPITTS:
    """Windows SAPI text-to-speech via COM."""

    def __init__(self, voice_idx: int = SAPI_VOICE_IDX, rate: int = SAPI_RATE,
                 eleven_api_key: str = ""):
        self.voice_idx = voice_idx
        self.rate = rate
        self._voice = None
        self._stream = None
        self._eleven_api_key = eleven_api_key
        self._init_sapi()

    def _init_sapi(self):
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            self._pythoncom = pythoncom

            # Enumerate and pick voice
            cat = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
            cat.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices", False)
            tokens = cat.EnumerateTokens()
            if tokens.Count == 0:
                raise RuntimeError("No SAPI voices installed")
            self._voice_token = tokens.Item(min(self.voice_idx, tokens.Count - 1))
            self._voice = win32com.client.Dispatch("SAPI.SpVoice")
            self._voice.Voice = self._voice_token
            self._voice.Rate = self.rate
            print(f"[tts] SAPI voice: {self._voice_token.GetDescription()}")
        except Exception as e:
            print(f"[tts] SAPI init failed: {e}")
            raise

    def synthesize_to_file(self, text: str) -> Optional[Path]:
        """Synthesize text to a temp WAV file. Returns path or None."""
        if not self._voice:
            return None
        import win32com.client
        wav_path = TEMP_DIR / f"sapi_{int(time.time()*1000)}.wav"
        try:
            stream = win32com.client.Dispatch("SAPI.SpFileStream")
            stream.Format.Type = "SAFT16kHz16BitMono"
            stream.Open(str(wav_path))
            self._voice.AudioOutputStream = stream
            self._voice.Speak(text)
            stream.Close()
            return wav_path
        except Exception as e:
            print(f"[tts] file synthesis failed: {e}")
            return None

    def speak_blocking(self, text: str):
        """Speak text directly through default audio output (simplest path)."""
        if not self._voice:
            return
        try:
            self._voice.Speak(text)
        except Exception as e:
            print(f"[tts] speak failed: {e}")

    def cleanup(self):
        try:
            self._pythoncom.CoUninitialize()
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Speaker playback (V7)
# ---------------------------------------------------------------------------
class SpeakerPlayback:
    """Play audio through Windows speakers via sounddevice."""

    def __init__(self, device: Optional[int] = None, rate: int = SAMPLE_RATE):
        self.device = device
        self.rate = rate

    def play_wav(self, wav_path: Path) -> bool:
        """Play a WAV file. Returns True if playback succeeded."""
        try:
            with wave.open(str(wav_path), "rb") as wf:
                audio_data = wf.readframes(wf.getnframes())
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
                audio_array /= 32768.0
                actual_rate = wf.getframerate()
                if wf.getnchannels() > 1:
                    audio_array = audio_array.reshape(-1, wf.getnchannels())
                sd.play(audio_array, samplerate=actual_rate, device=self.device)
                sd.wait()
                return True
        except Exception as e:
            print(f"[playback] failed: {e}")
            return False

    def play_numpy(self, audio: np.ndarray, rate: int = SAMPLE_RATE) -> bool:
        try:
            sd.play(audio, samplerate=rate, device=self.device)
            sd.wait()
            return True
        except Exception as e:
            print(f"[playback] failed: {e}")
            return False

# ---------------------------------------------------------------------------
# PTT beep (V7+)
# ---------------------------------------------------------------------------
class PTTBeep:
    """Short tone on PTT start/stop for audible feedback."""

    FREQ = 800          # Hz — noticeable but not harsh
    DURATION = 0.10     # seconds

    @staticmethod
    def _tone(freq: float = FREQ, duration: float = DURATION):
        """Play a short tone through the default output device."""
        try:
            t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
            audio = (np.sin(2 * np.pi * freq * t) * 0.3).astype(np.float32)
            sd.play(audio, samplerate=SAMPLE_RATE)
            sd.wait()
        except Exception:
            pass  # Beep is best-effort, never blocks the voice loop

    @staticmethod
    def start():
        PTTBeep._tone()

    @staticmethod
    def stop():
        PTTBeep._tone()

# ---------------------------------------------------------------------------
# Voice receipts (V9)
# ---------------------------------------------------------------------------
class VoiceReceipts:
    """Minimal JSON-line receipts. Hash-only by default."""

    def __init__(self, receipts_dir: Path = RECEIPTS_DIR):
        self.receipts_dir = receipts_dir
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self._file = self.receipts_dir / f"voice_turns_{datetime.now(UTC).strftime('%Y%m%d')}.jsonl"

    def record(self, turn_id: str, transcript: str, response: str,
               latency_ms: int, result: str, stt_ms: int = 0,
               hermes_ms: int = 0, session_id: str = "",
               stage_ms: dict = None):
        entry = {
            "timestamp": now_iso(),
            "turn_id": turn_id,
            "session_id": session_id,
            "transcript_hash": sha256_text(transcript),
            "response_hash": sha256_text(response),
            "latency_ms": latency_ms,
            "stt_ms": stt_ms,
            "hermes_ms": hermes_ms,
            "stage_ms": stage_ms or {},
            "result": result,
        }
        with open(self._file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

# ---------------------------------------------------------------------------
# Main voice loop (V8 — state machine, JARVIS_VOICE_CONVERGENCE_002)
# ---------------------------------------------------------------------------
class JarvisVoiceSession:
    """Orchestrates the MVP-1 voice session."""

    def __init__(self):
        self.state = State.IDLE
        self.mic = MicCapture(device=DEVICE_INDEX)
        self.stt = LocalSTT(model_size="base", language="en")
        self.bridge = HermesBridge()
        self.tts = None
        self.playback = SpeakerPlayback()
        self.receipts = VoiceReceipts()
        self._running = False
        self._current_turn = 0
        # V11 — per-stage timing
        self._stage_times: dict = {}
        # BATCH D — wake word state
        self._wake_mode = False          # current turn originated from wake
        self._wake_hands_free = False    # hands-free capture in progress
        self._wake_ok = False
        self._wake_model = None
        self._wake_thread: Optional[threading.Thread] = None

    def _set_state(self, new_state: str, reason: str = ""):
        old = self.state
        self.state = new_state
        indicator = {
            State.IDLE: "●",
            State.LISTENING: "🎙",
            State.TRANSCRIBING: "⋯",
            State.THINKING: "…",
            State.SPEAKING: "🔊",
            State.WAKE_READY: "👂",
            State.WAKE_DETECTED: "✨",
            State.RETURNING_TO_WAKE: "↺",
            State.ERROR: "⚠",
        }.get(new_state, "?")
        print(f"\r{indicator} {new_state:<12} {reason}")

    def _start_stage(self, name: str):
        """Record stage start time for per-stage latency measurement."""
        self._stage_times[name] = time.time()

    def _end_stage(self, name: str) -> int:
        """Record stage end time, return elapsed ms."""
        if name not in self._stage_times:
            return 0
        ms = round((time.time() - self._stage_times[name]) * 1000)
        del self._stage_times[name]
        return ms

    def _run_turn(self, audio: np.ndarray):
        """Process one captured audio turn through the full pipeline."""
        turn_start = time.time()
        self._current_turn += 1
        turn_id = f"vturn-{self._current_turn:04d}"

        try:
            # V4 — STT (with per-stage timing)
            self._set_state(State.TRANSCRIBING, "transcribing...")
            self._start_stage("stt")
            stt_result = self.stt.transcribe(audio)
            stt_ms = self._end_stage("stt")
            if not stt_result or not stt_result["text"].strip():
                if self._wake_ok:
                    self._return_to_wake("(no speech detected)")
                else:
                    self._set_state(State.IDLE, "(no speech detected)")
                return

            transcript = stt_result["text"].strip()
            print(f"  📝 You said: \"{transcript}\"")

            # V5 — Hermes bridge (with per-stage timing)
            self._set_state(State.THINKING, "asking Hermes...")
            self._start_stage("hermes")
            bridge_result = self.bridge.send(transcript)
            hermes_ms = self._end_stage("hermes")
            if not bridge_result or not bridge_result.get("reply"):
                self._set_state(State.ERROR, "Hermes returned no reply")
                self.receipts.record(turn_id, transcript, "", 0, "hermes_no_reply",
                                     stt_ms=stt_result.get("stt_ms", 0),
                                     hermes_ms=hermes_ms)
                return

            reply = bridge_result["reply"]
            print(f"  🤖 Jarvis: \"{reply}\"")

            # V6+V7 — TTS + playback
            self._set_state(State.SPEAKING, "speaking...")
            tts = self._get_tts()
            if tts:
                tts.speak_blocking(reply)
            else:
                print("  (TTS unavailable — text only)")

            turn_ms = round((time.time() - turn_start) * 1000)
            stt_ms_val = stt_result.get("stt_ms", stt_ms)
            hermes_ms_val = bridge_result.get("hermes_ms", hermes_ms)

            # Per-stage summary
            stage_summary = {k: f"{v}ms" for k, v in self._stage_times.items()}
            print(f"  ⏱ stages: stt={stt_ms_val}ms hermes={hermes_ms_val}ms total={turn_ms}ms"
                  + (f" extra={stage_summary}" if stage_summary else ""))

            if self._wake_ok:
                self._return_to_wake(f"done in {turn_ms}ms")
            else:
                self._set_state(State.IDLE, f"done in {turn_ms}ms")

            # V9 — Receipt with per-stage timing
            self.receipts.record(
                turn_id, transcript, reply, turn_ms, "completed",
                stt_ms=stt_ms_val,
                hermes_ms=hermes_ms_val,
                session_id=bridge_result.get("session_id", ""),
                stage_ms={k: v for k, v in self._stage_times.items()},
            )

        except Exception as e:
            self._set_state(State.ERROR, str(e))
            self.receipts.record(turn_id, "", "", 0, f"error: {e}")
        finally:
            # BATCH D: in wake mode every turn ends by re-arming the
            # detector (canonical cycle ... SPEAKING -> RETURNING_TO_WAKE
            # -> WAKE_READY). Errors and empty captures re-arm too.
            if self._wake_ok and self.state != State.WAKE_READY:
                self._return_to_wake("re-arm after turn")

    # ------------------------------------------------------------------
    # BATCH D — wake word: "Hey Jarvis" -> SAME certified voice loop.
    # LOCAL ONLY: openWakeWord ONNX scores mic frames on-device.
    # PRE_WAKE_CLOUD_AUDIO_UPLOADS = 0 (no audio leaves the machine).
    # ------------------------------------------------------------------

    def _return_to_wake(self, reason: str = ""):
        """Re-arm wake detection after a hands-free turn."""
        self._set_state(State.RETURNING_TO_WAKE, reason)
        self._wake_hands_free = False
        self._wake_mode = False          # detector thread resumes scoring
        time.sleep(WAKE_REARM_DELAY_S)
        if self._running:
            self._set_state(State.WAKE_READY, "(say \"Hey Jarvis\")")

    def _start_wake_listener(self):
        """Load the local wake model, then start the detector thread."""
        try:
            from openwakeword.model import Model as WakeModel
        except Exception as e:
            print(f"  ✗ Wake detection unavailable (openwakeword import): {e}")
            self._wake_ok = False
            return False
        try:
            self._wake_model = WakeModel(
                wakeword_models=["hey_jarvis"],
                inference_framework="onnx",
            )
        except Exception as e:
            print(f"  ✗ Wake model load failed: {e}")
            self._wake_ok = False
            return False
        self._wake_ok = True
        print(f"  ✓ Wake model ready: \"{WAKE_WORD}\" (local ONNX)")
        try:
            # Warm-up inference: eliminates first-frame latency spike
            self._wake_model.predict(
                np.zeros(int(SAMPLE_RATE * WAKE_FRAME_MS / 1000), dtype=np.int16))
        except Exception:
            pass  # warm-up is best-effort
        self.mic.start_fe()   # persistent capture front-end (single stream)
        self._wake_thread = threading.Thread(
            target=self._wake_detector_loop, name="wake-detector", daemon=True)
        self._wake_thread.start()
        print("  Say \"Hey Jarvis\" for hands-free. Ctrl+Alt+J still works.\n")
        return True

    def _wake_detector_loop(self):
        """Background thread: local wake scoring on the shared mic front-end.

        While idle, drains short audio chunks from MicCapture (callback keeps
        running) and scores them frame-by-frame with openWakeWord. On
        confirmation, switches to hands-free capture on the SAME stream and
        hands the audio to the SAME _run_turn pipeline as push-to-talk.
        """
        frame_samples = int(SAMPLE_RATE * WAKE_FRAME_MS / 1000)   # 1280 @16k
        pending = 0
        roll_max = 0.0            # WAKE-DIAG-1: rolling max score
        roll_rms = 0.0
        roll_samples = 0
        roll_t0 = time.time()
        while self._running:
            if self._wake_mode or self.mic.is_recording:
                time.sleep(0.05)
                continue
            try:
                audio = self.mic.drain()
            except Exception:
                time.sleep(0.05)
                continue
            if audio is None or len(audio) == 0:
                time.sleep(0.02)
                continue
            try:
                # WAKE-DIAG-2 FIX: sounddevice delivers float32 in [-1, 1];
                # a raw truncating cast flattens it to {0} (model scored
                # digital silence). Scale properly, matching the certified
                # STT path conversion.
                chunk = (audio[:, 0] * 32767.0).clip(-32768, 32767).astype(np.int16)
            except Exception:
                continue
            for off in range(0, len(chunk) - frame_samples + 1, frame_samples):
                frame = chunk[off:off + frame_samples]
                try:
                    scores = self._wake_model.predict(frame)
                except Exception:
                    continue
                key = WAKE_WORD.replace(" ", "_")
                if isinstance(scores, dict):
                    score = float(scores.get(key) or max(scores.values() or [0.0]))
                else:
                    score = float(scores)
                # WAKE-DIAG-1 telemetry: bounded rolling window (1 line / 5s)
                roll_samples += len(frame)
                roll_rms = max(roll_rms, float(np.sqrt(np.mean(frame.astype(np.float32) ** 2))))
                roll_max = max(roll_max, score)
                if time.time() - roll_t0 >= 5.0:
                    print(f"  [wake] rms={roll_rms:.4f} samples={roll_samples} "
                          f"score_hey_jarvis_max={roll_max:.3f} threshold={WAKE_SENSITIVITY}")
                    roll_max = 0.0
                    roll_rms = 0.0
                    roll_samples = 0
                    roll_t0 = time.time()
                if score >= WAKE_SENSITIVITY:
                    pending += 1
                else:
                    pending = 0
                if pending >= WAKE_CONFIRMATION_FRAMES:
                    pending = 0
                    try:
                        # WAKE-DIAG-5: clear residual feature-window state
                        self._wake_model.reset()
                    except Exception:
                        pass
                    print(f"  [wake] TRIGGER score={score:.3f}")
                    self._on_wake_detected()
                    break

    def _on_wake_detected(self):
        """Wake phrase confirmed — capture hands-free until end of speech.

        Uses the SAME MicCapture stream and the SAME _run_turn pipeline as
        the certified push-to-talk path (trigger-only change).
        """
        self._set_state(State.WAKE_DETECTED, f"\"{WAKE_WORD}\"")
        self._wake_hands_free = True
        self._wake_mode = True
        self.mic.start()
        self._set_state(State.LISTENING, "(speak now — pause when done)")
        speech_seen = False
        silent_for = 0.0
        max_wait = time.time() + MAX_RECORD_SECONDS   # absolute cap
        last_poll = 0.0
        while self._running and self.mic.is_recording:
            time.sleep(0.1)
            if time.time() > max_wait:
                break
            if time.time() - last_poll >= 0.2:
                last_poll = time.time()
                # require at least one voiced interval before accepting silence
                if self.mic.recent_rms(0.5) >= WAKE_SPEECH_RMS:
                    speech_seen = True
                    silent_for = 0.0
                elif speech_seen:
                    silent_for += 0.2
                    if silent_for >= 1.5:
                        break
        audio = self.mic.stop()
        if not self._running:
            return
        if audio is None or len(audio) == 0:
            self._return_to_wake("(empty capture)")
            return
        duration = audio.shape[0] / SAMPLE_RATE
        print(f"  🎙 captured {duration:.1f}s of audio (hands-free)")
        threading.Thread(target=self._run_turn, args=(audio,), daemon=True).start()

    def _get_tts(self) -> Optional[SAPITTS]:
        if self.tts is None:
            try:
                self.tts = SAPITTS()
            except Exception as e:
                print(f"[tts] unavailable: {e}")
        return self.tts

    def _on_hotkey_press(self):
        """Callback when push-to-talk hotkey is pressed."""
        if self.mic.is_recording or self._wake_hands_free:
            return
        PTTBeep.start()
        self._set_state(State.LISTENING, f"(hold {HOTKEY} to speak)")
        self.mic.start()

    def _on_hotkey_release(self):
        """Callback when push-to-talk hotkey is released."""
        if not self.mic.is_recording:
            return
        audio = self.mic.stop()
        PTTBeep.stop()
        if audio is None or len(audio) == 0:
            self._set_state(State.IDLE, "(empty capture)")
            return
        duration = self.mic.duration_seconds
        print(f"  🎙 captured {duration:.1f}s of audio")
        # Run turn in background thread to keep hotkey responsive
        threading.Thread(target=self._run_turn, args=(audio,), daemon=True).start()

    def _fallback_cli_mode(self):
        """CLI fallback: type text if hotkey registration fails."""
        print("\n🎙 CLI fallback mode — type your message (or 'quit' to exit):")
        self._set_state(State.IDLE, "cli fallback")
        while self._running:
            try:
                text = input("> ").strip()
                if not text:
                    continue
                if text.lower() in ("quit", "exit", "/q", "q"):
                    break
                self._current_turn += 1
                turn_id = f"vturn-{self._current_turn:04d}"
                self._set_state(State.THINKING, "asking Hermes...")
                result = self.bridge.send(text)
                if result and result.get("reply"):
                    print(f"🤖 {result['reply']}")
                    self._set_state(State.SPEAKING, "speaking...")
                    tts = self._get_tts()
                    if tts:
                        tts.speak_blocking(result["reply"])
                    turn_ms = round((time.time() - self._stage_times.get("turn_start", time.time())) * 1000)
                    self._set_state(State.IDLE, f"done in {turn_ms}ms")
                    self.receipts.record(turn_id, text, result["reply"], turn_ms, "completed")
                else:
                    self._set_state(State.ERROR, "Hermes returned no reply")
            except (EOFError, KeyboardInterrupt):
                break

    def _play_welcome(self):
        """Short welcome beep to confirm startup."""
        try:
            t = np.linspace(0, 0.2, int(SAMPLE_RATE * 0.2), endpoint=False)
            audio = (np.sin(2 * np.pi * 600 * t) * 0.2).astype(np.float32)
            sd.play(audio, samplerate=SAMPLE_RATE)
            sd.wait()
        except Exception:
            pass

    def run(self):
        """Main loop: push-to-talk → STT → Hermes → TTS → speakers."""
        print(f"  STT:  faster_whisper (local, preloaded)")
        print(f"  TTS:  Windows SAPI (local)")
        print(f"  Hermes: {HERMES_CMD}")
        print(f"  Hotkey: {HOTKEY}")
        print(f"  Wake:  \"{WAKE_WORD}\" (local, hands-free)" if WAKE_WORD_ENABLED else "  Wake:  disabled")
        print(f"  Mode:  READ_ONLY conversation")
        print(f"  Style: CONCISE_BY_DEFAULT")
        print("-" * 60)

        self._running = True
        self._set_state(State.IDLE, "ready")

        # Preload Whisper at startup — eliminates cold-start latency (V10)
        print("[stt] Preloading Whisper model...")
        self.stt.preload()
        print("[stt] Whisper preloaded. Hotkey active.")

        # Welcome beep
        self._play_welcome()

        # BATCH D — local wake-word listener ("Hey Jarvis")
        if WAKE_WORD_ENABLED:
            try:
                self._start_wake_listener()
            except Exception as e:
                print(f"  ✗ Wake listener failed to start: {e}")

        # Virtual key codes for J on Windows
        VK_J = 74

        def _key_is_j(key):
            """Detect 'j' regardless of whether pynput gives us char or vk."""
            if hasattr(key, 'char') and key.char and key.char.lower() == 'j':
                return True
            if getattr(key, 'vk', None) == VK_J:
                return True
            return False

        def _key_name(key):
            """Return a readable name for tracing."""
            if hasattr(key, 'char') and key.char:
                return key.char
            return str(key)

        # Try to register global hotkey via Listener state machine
        hotkey_ok = False
        try:
            from pynput import keyboard as pynkbd
            self._ptt = {
                'ctrl': False,
                'alt': False,
                'j': False,
                'listener': None,
            }

            def on_press(key):
                try:
                    if getattr(key, 'name', None) in ('ctrl_l', 'ctrl_r'):
                        self._ptt['ctrl'] = True
                    elif getattr(key, 'name', None) in ('alt_l', 'alt_r'):
                        self._ptt['alt'] = True
                    elif _key_is_j(key):
                        self._ptt['j'] = True
                    if (self._ptt['ctrl'] and self._ptt['alt'] and
                            self._ptt['j'] and not self.mic.is_recording):
                        self._on_hotkey_press()
                except Exception:
                    pass

            def on_release(key):
                try:
                    if getattr(key, 'name', None) in ('ctrl_l', 'ctrl_r'):
                        self._ptt['ctrl'] = False
                    elif getattr(key, 'name', None) in ('alt_l', 'alt_r'):
                        self._ptt['alt'] = False
                    elif _key_is_j(key):
                        self._ptt['j'] = False
                    if (not self._ptt['j'] and self.mic.is_recording):
                        self._on_hotkey_release()
                except Exception:
                    pass

            self._ptt['listener'] = pynkbd.Listener(
                on_press=on_press,
                on_release=on_release,
            )
            self._ptt['listener'].start()
            hotkey_ok = True
            print(f"\n  ✓ Global hotkey registered: {HOTKEY}")
            print("  Hold to speak, release to send.\n")
        except Exception as e:
            print(f"\n  ✗ Hotkey registration failed: {e}")
            print("  Falling back to CLI input mode.\n")

        if hotkey_ok:
            try:
                if self._wake_ok:
                    self._set_state(State.WAKE_READY, f"(say \"{WAKE_WORD}\" or hold {HOTKEY})")
                while self._running:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass
            if self._ptt.get('listener'):
                self._ptt['listener'].stop()
        else:
            self._fallback_cli_mode()

        self.shutdown()

    def shutdown(self):
        print("\nShutting down...")
        self._running = False
        self.mic.stop_fe()   # BATCH D: close persistent wake front-end
        if self.tts:
            self.tts.cleanup()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    session = JarvisVoiceSession()
    session.run()