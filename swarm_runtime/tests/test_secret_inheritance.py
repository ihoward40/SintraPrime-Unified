"""Secret inheritance denial test — workers must not inherit controller secrets.

Sets fake secret env vars, builds a worker environment, and verifies secrets
are NOT propagated unless explicitly leased.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO))

from swarm_runtime.capability_lease import (
    DENIED_SECRETS,
    WorkerCapabilityLease,
    build_worker_environment,
    check_secret_inheritance,
)


def run_secret_inheritance_test() -> dict:
    print(f"\n{'='*60}")
    print("SWARM SECRET INHERITANCE DENIAL TEST")
    print(f"{'='*60}")

    # Create a fake parent environment with secrets
    parent_env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": "/some/path",
        "TEMP": "/tmp",
        "HOME": "/home/user",
        "GITHUB_TOKEN": "ghp_fake_token_12345",
        "OPENAI_API_KEY": "sk-fake-key-67890",
        "ANTHROPIC_API_KEY": "sk-ant-fake-key",
        "AWS_ACCESS_KEY_ID": "AKIAFAKE123",
        "AWS_SECRET_ACCESS_KEY": "fake_secret",
        "STRIPE_SECRET_KEY": "sk_stripe_fake",
        "DATABASE_URL": "postgresql://user:pass@host/db",
        "POSTGRES_PASSWORD": "secretpass",
        "JWT_SECRET_KEY": "jwt_secret_fake",
    }

    # Test 1: Default worker environment — no lease → secrets denied
    lease_default = WorkerCapabilityLease.create(
        worker_id="test_worker",
        allowed_tools=["code_search"],
    )
    env_default = build_worker_environment(lease_default, parent_env)
    check_default = check_secret_inheritance(env_default, lease_default)

    print("\n  Default lease (no secrets):")
    print(f"    SWARM_SECRET_INHERITANCE_DEFAULT = {check_default['SWARM_SECRET_INHERITANCE_DEFAULT']}")
    if check_default['leaked']:
        print(f"    LEAKED: {check_default['leaked']}")

    # Test 2: Worker with explicit lease for GITHUB_TOKEN
    lease_with_token = WorkerCapabilityLease.create(
        worker_id="test_worker_token",
        allowed_tools=["git_operations"],
        leased_env_vars=["GITHUB_TOKEN"],
    )
    env_with_token = build_worker_environment(lease_with_token, parent_env)
    check_with_token = check_secret_inheritance(env_with_token, lease_with_token)

    print("\n  Leased GITHUB_TOKEN:")
    print(f"    SWARM_SECRET_INHERITANCE_DEFAULT = {check_with_token['SWARM_SECRET_INHERITANCE_DEFAULT']}")
    print(f"    GITHUB_TOKEN present: {'GITHUB_TOKEN' in env_with_token}")
    print(f"    OPENAI_API_KEY present: {'OPENAI_API_KEY' in env_with_token}")

    # Test 3: Verify all denied secrets are absent from default env
    all_denied_absent = True
    for secret in DENIED_SECRETS:
        if secret in parent_env and secret in env_default:
            all_denied_absent = False
            print(f"    LEAKED: {secret}")

    criteria = [
        ("SWARM_SECRET_INHERITANCE_DEFAULT = DENIED (no lease)",
         check_default['SWARM_SECRET_INHERITANCE_DEFAULT'] == "DENIED"),
        ("NO_LEAKED_SECRETS_IN_DEFAULT", len(check_default['leaked']) == 0),
        ("ALL_DENIED_SECRETS_ABSENT", all_denied_absent),
        ("LEASED_TOKEN_PROPAGATED", "GITHUB_TOKEN" in env_with_token),
        ("UNLEASED_TOKEN_DENIED", "OPENAI_API_KEY" not in env_with_token),
        ("UNLEASED_STRIPE_DENIED", "STRIPE_SECRET_KEY" not in env_with_token),
        ("UNLEASED_AWS_DENIED", "AWS_ACCESS_KEY_ID" not in env_with_token),
        ("UNLEASED_DB_DENIED", "DATABASE_URL" not in env_with_token),
    ]
    all_pass = all(p for _, p in criteria)
    print(f"\n{'='*60}")
    print("ACCEPTANCE CRITERIA")
    print(f"{'='*60}")
    for name, passed in criteria:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    print(f"\n  OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return {"all_pass": all_pass}


if __name__ == "__main__":
    result = run_secret_inheritance_test()
    sys.exit(0 if result['all_pass'] else 1)
