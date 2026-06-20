from __future__ import annotations
import argparse, json
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

def calculate(payload: dict) -> dict:
    scores = payload.get("scores", {})
    missing = [k for k in WEIGHTS if k not in scores]
    if missing:
        raise ValueError(f"Missing score fields: {', '.join(missing)}")
    for k, v in scores.items():
        if k in WEIGHTS and not (0 <= float(v) <= 100):
            raise ValueError(f"{k} must be between 0 and 100")
    weighted = sum(float(scores[k]) * WEIGHTS[k] / 100 for k in WEIGHTS)
    critical = payload.get("critical_failures", [])
    if critical:
        band = "suspended_pending_review"
        certified = False
    elif weighted >= 95:
        band = "elite"
        certified = True
    elif weighted >= 90:
        band = "certified"
        certified = True
    elif weighted >= 80:
        band = "restricted_duty"
        certified = False
    elif weighted >= 70:
        band = "retraining_required"
        certified = False
    else:
        band = "suspended"
        certified = False
    predicted = float(payload.get("predicted_confidence", 0))
    actual = float(payload.get("actual_correctness", 0))
    calibration_error = abs(predicted - actual)
    return {
        **payload,
        "overall_score": round(weighted, 2),
        "certification_band": band,
        "certified": certified,
        "confidence_calibration_error": round(calibration_error, 2),
    }

def main():
    parser = argparse.ArgumentParser(description="SintraPrime Intelligence Academy CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    score = sub.add_parser("score")
    score.add_argument("--input", required=True)
    score.add_argument("--output")
    args = parser.parse_args()
    if args.command == "score":
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = calculate(payload)
        text = json.dumps(result, indent=2)
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        print(text)

if __name__ == "__main__":
    main()
