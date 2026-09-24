"""Replay a WS8-CMRD-001 JSON result with the pinned algorithm version."""
import argparse
import json
from pathlib import Path
from .calculator import replay


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    result = replay(json.loads(args.receipt.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
