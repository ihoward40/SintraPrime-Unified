# Execution Ledger (v1)

This folder records **verifiable** file/config mutations as JSON receipts.

## Layout
- `ledger/logs/` — one JSON file per ledger entry
- `ledger/snapshots/` — optional snapshots of edited files
- `ledger/hashes/` — sha256 receipts
- `ledger/ledger_index.json` — rolling index

## Record an entry
Example:

```bash
python ledger/record_ledger_entry.py \
  --operation write_file \
  --target config/academy_registry.json \
  --expected_outcome "path updated to ./academy" \
  --actual_outcome "path verified as ./academy" \
  --status PASS \
  --verification '{"read_back":true,"head_match":true}' \
  --snapshot
```
