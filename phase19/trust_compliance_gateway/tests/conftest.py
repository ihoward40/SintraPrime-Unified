# G0-R3.1 / RC-003: make the package root importable as top-level so the
# test module's absolute sibling imports (from tool_registry..., from
# trust_compliance_adapter..., from policy_mapping...) resolve during collection.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
