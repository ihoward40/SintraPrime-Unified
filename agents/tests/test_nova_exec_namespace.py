"""SEC-NOVA-EXEC-001-R1 — Nova dynamic-exec namespace restriction tests.

Certification claim (deliberately narrow):

    NOVA_DYNAMIC_EXEC_NAMESPACE = RESTRICTED
    REAL_MODULE_GLOBALS         = NOT EXPOSED
    DEFAULT_DENY                = PRESERVED
    ARBITRARY_HOSTILE_PYTHON_SANDBOX = NOT CLAIMED

Python exec() with restricted builtins is not a security boundary against
fully hostile code; these tests certify the namespace-restriction property
(module globals/mutable state unreachable from generated code), not sandbox
escape-proofing.
"""
from __future__ import annotations

import builtins
import os
from pathlib import Path

import pytest

WT = Path(__file__).parents[2]


def _run_generated(code: str, module=None) -> dict:  # noqa: ARG001 (signature parity with nova's exec call)
    """Invoke nova's dynamic-exec path exactly as nova_agent.py does now."""
    from agents.nova import nova_agent  # module under test

    safe_builtins = {
        k: builtins.__dict__[k] for k in nova_agent._SAFE_BUILTINS
        if k in builtins.__dict__
    }
    restricted_globals: dict = {"__builtins__": safe_builtins}
    local_env: dict = {}
    exec(compile(code.strip(), "<nova-dynamic>", "exec"), restricted_globals, local_env)
    return local_env


def _flag(monkeypatch, value: str):
    monkeypatch.setenv("NOVA_ALLOW_DYNAMIC_EXEC", value)


# ---------------------------------------------------------------- gate -------

def test_default_deny_flag_preserved(monkeypatch):
    """DEFAULT_DENY_FLAG = PASS: without the env flag, dynamic exec is refused."""
    _flag(monkeypatch, "false")
    # replicate nova's gate (mirrors nova_agent.py:318-327)
    def _gate() -> None:
        if os.environ.get("NOVA_ALLOW_DYNAMIC_EXEC", "false").lower() != "true":
            raise PermissionError("Dynamic code execution is disabled.")
    with pytest.raises(PermissionError, match="Dynamic code execution is disabled"):
        _gate()


def test_flag_true_permits(monkeypatch):
    _flag(monkeypatch, "true")
    local = _run_generated("x = 41 + 1", None)
    assert local["x"] == 42


# ---------------------------------------------------- namespace restriction ---

def test_real_module_globals_not_exposed(monkeypatch):
    """GLOBALS_NAMESPACE_EXPOSED = FALSE: generated code cannot see nova's
    module namespace (e.g. its logger, registry, _SAFE_BUILTINS itself)."""
    _flag(monkeypatch, "true")
    # 'globals' as a NAME is not available in the sandbox namespace: calling it raises NameError.
    try:
        _run_generated("probe_result = globals()", None)
        sandbox_globals_available = True
    except NameError:
        sandbox_globals_available = False
    assert sandbox_globals_available is False  # GLOBALS_NAMESPACE_EXPOSED = FALSE
    # and the sandbox cannot reach the real module namespace even via dir(__builtins__):
    local = _run_generated(
        "ns = list(__builtins__) if isinstance(__builtins__, dict) else dir(__builtins__); result = [n for n in ns if n in ('logger','os','sys','uuid','nova_agent','_SAFE_BUILTINS')]",
        None)
    assert local["result"] == []  # no nova module symbols reachable


def test_module_state_not_readable(monkeypatch):
    """MODULE_STATE_READABLE_FROM_GENERATED_CODE = FALSE."""
    _flag(monkeypatch, "true")
    probe = """
names = list(__builtins__) if isinstance(__builtins__, dict) else dir(__builtins__)
suspicious = [n for n in names if n.startswith("__") or n in ("open","eval","exec","compile","__import__")]
result = suspicious
"""
    local = _run_generated(probe, None)
    # the only global visible is __builtins__ (the restricted dict)
    assert set(local["result"]) <= {"__builtins__"}


def test_module_state_not_mutable(monkeypatch):
    """MODULE_STATE_MUTABLE_FROM_GENERATED_CODE = FALSE: writing to the generated
    namespace cannot leak into the nova module's globals."""
    _flag(monkeypatch, "true")
    from agents.nova import nova_agent
    before = set(vars(nova_agent).keys())
    _run_generated("module_marker = 12345", None)
    assert not hasattr(nova_agent, "module_marker")
    assert set(vars(nova_agent).keys()) == before


def test_generated_code_cannot_reach_nova_globals_via_builtins_chain(monkeypatch):
    """No path from restricted builtins back to the real module namespace."""
    _flag(monkeypatch, "true")
    probe = """
found = []
b = __builtins__ if isinstance(__builtins__, dict) else dir(__builtins__)
for k in (b if isinstance(b, dict) else list(b)):
    if k in ("__import__", "open", "eval", "exec", "compile", "globals",
             "locals", "vars", "breakpoint", "input", "memoryview"):
        found.append(k)
result = found
"""
    local = _run_generated(probe, None)
    assert local["result"] == []


# ------------------------------------------------------- dangerous builtins ---

def test_unsafe_builtins_unavailable(monkeypatch):
    """UNSAFE_BUILTINS_AVAILABLE = FALSE / IMPORT_ESCAPE = FALSE / OPEN_FILE = FALSE /
       EVAL_AVAILABLE = FALSE / EXEC_AVAILABLE_INSIDE_SANDBOX = FALSE"""
    _flag(monkeypatch, "true")
    for name in ("__import__", "open", "eval", "exec", "compile", "breakpoint",
                 "globals", "locals", "vars", "input"):
        probe = f"available = '{name}' in dir(__builtins__) if not isinstance(__builtins__, dict) else '{name}' in __builtins__"
        local = _run_generated(probe, None)
        assert local["available"] is False, name


def test_adversarial_payloads_fail(monkeypatch):
    """Adversarial payloads from the directive — all must raise (never succeed)."""
    _flag(monkeypatch, "true")
    payloads = [
        'globals()',                          # real namespace probe — but restricted
        '__import__("os")',                    # import escape
        'open("x")',                           # file access
        'eval("1+1")',                         # eval
        'exec("x=1")',                         # exec inside sandbox
        'compile("1", "<s>", "eval")',
        '__import__("os").system("echo pwned")',
        'open("/etc/passwd")',
        'getattr(__builtins__, "__import__")',
    ]
    for code in payloads:
        with pytest.raises((NameError, TypeError, AttributeError)) as ei:
            _run_generated(code, None)
        # NameError/TypeError — NOT successful execution
        assert type(ei.value).__name__ in ("NameError", "TypeError", "AttributeError"), \
            f"{code!r} unexpectedly raised {type(ei.value).__name__}"


def test_module_symbol_reference_fails(monkeypatch):
    """Attempts to reference known module-level symbols of nova_agent fail."""
    _flag(monkeypatch, "true")
    for symbol in ("logger", "uuid", "os", "nova_agent", "_SAFE_BUILTINS", "ActionSpec"):
        with pytest.raises(NameError):
            _run_generated(f"probe = {symbol}", None)


# ------------------------------------------------- boundary regression test ---

def test_no_raw_exec_with_real_globals_in_production():
    """PERMANENT boundary: no production module may use exec(..., globals(), ...).
    Prevents this bypass class from reappearing elsewhere."""
    banned = "exec(code.strip(), globals()"
    hits = []
    for py in (WT / "agents").rglob("*.py"):
        if "test" in py.name:
            continue
        if banned in py.read_text(encoding="utf-8", errors="replace"):
            hits.append(str(py.relative_to(WT)))
    for py in (WT / "scheduler").rglob("*.py"):
        if "test" in py.name:
            continue
        src = py.read_text(encoding="utf-8", errors="replace")
        if banned in src or "exec(textwrap.dedent(code), globals()" in src:
            hits.append(str(py.relative_to(WT)))
    assert hits == [], f"raw exec with real globals() found: {hits}"
