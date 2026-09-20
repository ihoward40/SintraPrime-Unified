# G0-R3.1 / RC-001: make the package root importable as top-level so the
# test module's absolute sibling imports (from models..., from utils...) resolve
# during collection. No application or test logic is changed.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
