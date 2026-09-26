"""SP-OMNIBRAIN-RUNTIME-001 — governed agent runtime integration layer.

Composes existing governed subsystems (agent_runtime, memory, governance,
decision fabric). Adds no second memory system, no new persistence engine,
and no authority source: probability may select a workflow; probability may
not create authority. Every component here FAILS CLOSED.
"""
