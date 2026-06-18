import importlib.util
from pathlib import Path

MODULE = Path(__file__).parents[1] / "scripts" / "academy_cli_v2.py"
spec = importlib.util.spec_from_file_location("academy_cli_v2", MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def valid_payload():
    h = "a" * 64
    return {
        "agent_id":"justice_scribe",
        "exam_id":"TEST",
        "exam_status":"completed",
        "scores":{k:95 for k in m.WEIGHTS},
        "predicted_confidence":94,
        "actual_correctness":95,
        "critical_failures":[],
        "review_disposition":"PASS",
        "reviewer_identity":"lex_aeternum",
        "corrections_closed":True,
        "submission_hash":h,
        "exam_hash":h,
        "review_hash":h,
        "answer_key_hash":h,
    }

def test_valid_certification():
    assert m.certify(valid_payload())["certified"] is True

def test_factual_accuracy_gate():
    p = valid_payload()
    p["scores"]["factual_accuracy"] = 89
    r = m.certify(p)
    assert r["certified"] is False
    assert "factual_accuracy_below_90" in r["gate_failures"]

def test_review_gate():
    p = valid_payload()
    p["review_disposition"] = "REJECT"
    assert m.certify(p)["certified"] is False

def test_self_review_gate():
    p = valid_payload()
    p["reviewer_identity"] = "justice_scribe"
    assert m.certify(p)["certified"] is False

def test_calibration_gate():
    p = valid_payload()
    p["predicted_confidence"] = 100
    p["actual_correctness"] = 70
    assert m.certify(p)["certified"] is False
