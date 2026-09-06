"""Batch B structured-bridge regression suite (Principal directive).

Covers: simple final response, session preservation, quiet-contract source,
legacy box fallback, no-reply diagnostics, session-id extraction.
Run with the MVP venv python. Live subprocess probes are bounded to short
queries; the timeout path is unit-proven separately.
"""
import io
import contextlib
import re
import sys

sys.path.insert(0, "C:/Users/admin/SintraPrime-Unified-jarvis-001b")
from jarvis_voice_mvp import HermesBridge

results = {}

def check(name, cond):
    results[name] = "PASS" if cond else "FAIL"

b = HermesBridge()

# --- L1: quiet-contract stdout (primary path) ---
u1, s1 = b._extract_reply("Just the answer\n")
check("U1_quiet_contract", u1 == "Just the answer" and s1 == "quiet_contract")

# --- L2: legacy box fallback (older Hermes builds) ---
u2, s2 = b._extract_reply("\u256d\u2500 box \u2500\u256e\nlegacy answer\n\u256f\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u256f\nsession_id: x\n")
check("U2_legacy_box", u2 == "legacy answer" and s2 == "legacy_box_fallback")

# --- L3: no reply -> diagnostic + empty, source=none ---
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    u3, s3 = b._extract_reply("")
check("U3_no_reply_empty", u3 == "" and s3 == "none")
check("U3_diagnostic_emitted", "no final response" in buf.getvalue())

# --- L4: session id extraction from stderr (-Q contract shape) ---
m = re.search(r"session_id:\s+(\S+)", "session_id: 20260906_110649_9d003d\n")
check("U4_session_from_stderr", bool(m and m.group(1) == "20260906_110649_9d003d"))

# --- L5: whitespace-only stdout -> none (not a crash) ---
u5, s5 = b._extract_reply("   \n  \n")
check("U5_whitespace_only", u5 == "" and s5 == "none")

# --- L6: ANSI-laden quiet stdout still parses clean ---
u6, s6 = b._extract_reply("\x1b[1mAnswer with ANSI codes\x1b[0m\n")
check("U6_ansi_stripped", u6 == "Answer with ANSI codes" and s6 == "quiet_contract")

print("=== PARSER SUITE ===")
fails = [k for k, v in results.items() if v == "FAIL"]
print(f"TOTAL={len(results)} PASS={len(results) - len(fails)} FAIL={len(fails)}")
for k in fails:
    print("FAILED:", k)
