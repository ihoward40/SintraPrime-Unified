# G0-R3.1 / RC-002: make phase19/revenue_smoke_test importable as top-level so the
# package's mixed relative/absolute imports (from test_config import ... in
# scenarios.py / run_smoke_test.py) resolve during collection. No source changed.
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'revenue_smoke_test'))
