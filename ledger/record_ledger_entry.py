import argparse, hashlib, json, os, shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--agent', default='hermes')
    p.add_argument('--operation', required=True, help='write_file|edit_file|delete_file|config_change|agent_memory_update|registry_update')
    p.add_argument('--target', required=True, help='Repo-relative path, e.g. config/academy_registry.json')
    p.add_argument('--expected_outcome', default=None)
    p.add_argument('--actual_outcome', default=None)
    p.add_argument('--status', default='PASS', help='PASS|FAIL|INFO')
    p.add_argument('--failure_mode', default=None)
    p.add_argument('--verification', default=None, help='JSON string for verification object')
    p.add_argument('--before_hash', default=None)
    p.add_argument('--after_hash', default=None)
    p.add_argument('--snapshot', action='store_true', help='If target exists, snapshot it into ledger/snapshots')
    p.add_argument('--snapshot_name', default=None, help='Override snapshot filename (optional)')
    args = p.parse_args()

    # repo root = one directory above this script: /ledger/record_ledger_entry.py
    repo_root = Path(__file__).resolve().parents[1]
    ledger_root = repo_root / 'ledger'
    logs_dir = ledger_root / 'logs'
    snaps_dir = ledger_root / 'snapshots'
    hashes_dir = ledger_root / 'hashes'

    logs_dir.mkdir(parents=True, exist_ok=True)
    snaps_dir.mkdir(parents=True, exist_ok=True)
    hashes_dir.mkdir(parents=True, exist_ok=True)

    target_rel = Path(args.target)
    if target_rel.is_absolute():
        # Normalize to repo-relative if possible.
        target_rel = target_rel.resolve()
        try:
            target_rel = target_rel.relative_to(repo_root)
        except Exception:
            raise SystemExit(f'--target must be repo-relative (got absolute outside repo): {args.target}')

    target_path = repo_root / target_rel

    generated_at = utc_now_iso()
    ledger_id = f"LEDGER-{datetime.now().strftime('%Y-%m-%d')}-{int(datetime.now().timestamp()*1000)%1000000000:09d}"

    verification_obj = None
    if args.verification:
        verification_obj = json.loads(args.verification)

    target_exists = target_path.exists()
    actual_hash = args.after_hash
    if actual_hash is None and target_exists:
        actual_hash = sha256_file(target_path)

    entry = {
        'id': ledger_id,
        'timestamp': generated_at,
        'agent': args.agent,
        'operation': args.operation,
        'target': '/' + str(target_rel).replace('\\', '/'),
        'input_hash': args.before_hash,
        'after_hash': actual_hash,
        'expected_outcome': args.expected_outcome,
        'actual_outcome': args.actual_outcome,
        'verification': verification_obj,
        'status': args.status,
        'failure_mode': args.failure_mode,
    }

    if args.snapshot and target_exists:
        ts = datetime.now().strftime('%Y-%m-%dT%H%M%S%f')
        snap_name = args.snapshot_name or f"{ts}_{target_rel.name}"
        snap_path = snaps_dir / snap_name
        shutil.copy2(target_path, snap_path)
        entry['snapshot'] = {
            'path': str(snap_path.relative_to(repo_root)).replace('\\', '/'),
            'filename': snap_name,
        }

    if actual_hash:
        save_json(hashes_dir / f"{ledger_id}.sha256", {
            'sha256': actual_hash,
            'target': '/' + str(target_rel).replace('\\', '/'),
        })

    log_path = logs_dir / f"{ledger_id}.json"
    save_json(log_path, entry)

    index_path = ledger_root / 'ledger_index.json'
    index = load_json(index_path, {
        'total_entries': 0,
        'last_entry': None,
        'operations': {},
    })

    index['total_entries'] = int(index.get('total_entries', 0)) + 1
    index['last_entry'] = ledger_id
    ops = index.setdefault('operations', {})
    ops[args.operation] = int(ops.get(args.operation, 0)) + 1

    save_json(index_path, index)

    print(json.dumps({'ok': True, 'ledger_id': ledger_id, 'log_path': str(log_path)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
