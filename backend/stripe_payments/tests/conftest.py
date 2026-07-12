"""pytest configuration for backend/stripe_payments tests.

Ensures the repository root is on sys.path and preloads the parent packages
so that pytest's importlib import mode can resolve sibling package imports
inside backend.stripe_payments correctly during test collection.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Pre-load parent packages so pytest importlib mode can resolve relative imports
# across sibling subpackages (api -> services -> models) during test collection.
import backend.stripe_payments.api  # noqa: E402
import backend.stripe_payments.models  # noqa: E402
import backend.stripe_payments.services  # noqa: E402

# Reference the preloaded modules to satisfy linters while preserving side effects.
_preloaded = [
    backend.stripe_payments.api,
    backend.stripe_payments.models,
    backend.stripe_payments.services,
]
assert all(m.__name__.startswith("backend.stripe_payments") for m in _preloaded)
