"""Normalize CRLF to LF in all Python files."""
import pathlib
import sys

for p in pathlib.Path(".").rglob("*.py"):
    data = p.read_bytes()
    if b"\r" in data:
        normalized = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        p.write_bytes(normalized)
        print(f"Normalized: {p}")
    else:
        print(f"OK (already LF): {p}")

print("Done normalizing line endings.")