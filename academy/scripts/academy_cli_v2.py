from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

WEIGHTS = {
    "factual_accuracy":20,
    "source_quality":15,
    "reasoning_quality":15,
    "issue_spotting":10,
    "counterargument_strength":10,
    "risk_recognition":10,
    "actionability":10,
    "clarity":5,
    "memory_contribution":5,
}

MINIMUMS = {"factual_accuracy":90, "source_quality":90}
ALLOWED_REVIEW = {"PASS", "PASS WITH CORRECTIONS"}
MAX_CALIBRATION_ERROR = 10

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()

def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def validate_submission(payload: dict) -> list[str]:
    errors = []
    required = ["submission_id","exam_id","exam_version","agent_id","exam_status","answers",
                "predicted_confidence","submitted_at","exam_hash"]
    for field in required:
        if field not in payload:
            errors.append(f"missing:{field}")
    if payload.get("exam_status") != "completed":
        errors.append("exam_not_completed")
    if not isinstance(payload.get("answers"), list) or not payload.get("answers"):
        errors.append("answers_missing")
    conf = payload.get("predicted_confidence")
    if conf is not None and not 0 <= float(conf) <= 100:
        errors.append("invalid_confidence")
    if len(str(payload.get("exam_hash",""))) != 64:
        errors.append("invalid_exam_hash")
    return errors

def certify(payload: dict) -> dict:
    errors = []
    scores = payload.get("scores", {})
    for key in WEIGHTS:
        if key not in scores:
            errors.append(f"missing_score:{key}")
        elif not 0 <= float(scores[key]) <= 100:
            errors.append(f"invalid_score:{key}")

    if errors:
        return {"certified":False, "decision":"INVALID", "gate_failures":errors}

    weighted = round(sum(float(scores[k]) * WEIGHTS[k] / 100 for k in WEIGHTS), 2)
    predicted = float(payload.get("predicted_confidence", 0))
    actual = float(payload.get("actual_correctness", 0))
    calibration_error = round(abs(predicted - actual), 2)

    gate_failures = []
    if weighted < 90:
        gate_failures.append("overall_below_90")
    for k, minimum in MINIMUMS.items():
        if float(scores[k]) < minimum:
            gate_failures.append(f"{k}_below_{minimum}")
    if payload.get("critical_failures"):
        gate_failures.append("critical_failure_present")
    if payload.get("exam_status") != "completed":
        gate_failures.append("exam_not_completed")
    if payload.get("review_disposition") not in ALLOWED_REVIEW:
        gate_failures.append("review_not_approved")
    if not payload.get("reviewer_identity"):
        gate_failures.append("reviewer_identity_missing")
    if payload.get("reviewer_identity") == payload.get("agent_id"):
        gate_failures.append("self_review_prohibited")
    if calibration_error > MAX_CALIBRATION_ERROR:
        gate_failures.append("confidence_calibration_exceeds_10")
    if payload.get("review_disposition") == "PASS WITH CORRECTIONS" and not payload.get("corrections_closed"):
        gate_failures.append("corrections_not_closed")
    for field in ["submission_hash","exam_hash","review_hash","answer_key_hash"]:
        value = str(payload.get(field,""))
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower()):
            gate_failures.append(f"{field}_invalid")

    certified = not gate_failures
    return {
        **payload,
        "overall_score":weighted,
        "confidence_calibration_error":calibration_error,
        "certified":certified,
        "decision":"CERTIFIED" if certified else "NOT_CERTIFIED",
        "gate_failures":gate_failures,
        "evaluated_at":datetime.now(timezone.utc).isoformat(),
    }

def write_audit(result: dict, output_dir: str) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out / f"{result.get('agent_id','unknown')}-{stamp}.audit.json"
    record = {
        "audit_version":"2.0.0",
        "recorded_at":datetime.now(timezone.utc).isoformat(),
        "decision":result.get("decision"),
        "agent_id":result.get("agent_id"),
        "exam_id":result.get("exam_id"),
        "reviewer_identity":result.get("reviewer_identity"),
        "hashes":{k:result.get(k) for k in ["submission_hash","exam_hash","review_hash","answer_key_hash"]},
        "gate_failures":result.get("gate_failures",[]),
        "overall_score":result.get("overall_score"),
        "previous_status":result.get("previous_status","trainee"),
        "new_status":"certified" if result.get("certified") else result.get("previous_status","trainee"),
    }
    encoded = json.dumps(record, indent=2, sort_keys=True)
    record["audit_record_hash"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return path

def self_test():
    valid_hash = "a"*64
    payload = {
        "agent_id":"justice_scribe","exam_id":"TEST","exam_status":"completed",
        "scores":{k:95 for k in WEIGHTS},"predicted_confidence":94,"actual_correctness":95,
        "critical_failures":[],"review_disposition":"PASS","reviewer_identity":"lex_aeternum",
        "corrections_closed":True,"submission_hash":valid_hash,"exam_hash":valid_hash,
        "review_hash":valid_hash,"answer_key_hash":valid_hash,
    }
    result = certify(payload)
    assert result["certified"] is True
    payload["scores"]["factual_accuracy"] = 89
    result = certify(payload)
    assert result["certified"] is False
    assert "factual_accuracy_below_90" in result["gate_failures"]
    print("SELF-TEST PASS")

def main():
    parser = argparse.ArgumentParser(description="SintraPrime Intelligence Academy v2")
    sub = parser.add_subparsers(dest="command", required=True)

    p_hash = sub.add_parser("hash")
    p_hash.add_argument("--file", required=True)

    p_validate = sub.add_parser("validate-submission")
    p_validate.add_argument("--input", required=True)

    p_cert = sub.add_parser("certify")
    p_cert.add_argument("--input", required=True)
    p_cert.add_argument("--output")
    p_cert.add_argument("--audit-dir")

    sub.add_parser("self-test")
    args = parser.parse_args()

    if args.command == "hash":
        print(sha256_file(Path(args.file)))
    elif args.command == "validate-submission":
        errors = validate_submission(load(args.input))
        print(json.dumps({"valid":not errors,"errors":errors}, indent=2))
        sys.exit(1 if errors else 0)
    elif args.command == "certify":
        result = certify(load(args.input))
        text = json.dumps(result, indent=2)
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        if args.audit_dir:
            audit = write_audit(result, args.audit_dir)
            result["audit_file"] = str(audit)
            text = json.dumps(result, indent=2)
        print(text)
        sys.exit(0 if result["certified"] else 2)
    elif args.command == "self-test":
        self_test()

if __name__ == "__main__":
    main()
