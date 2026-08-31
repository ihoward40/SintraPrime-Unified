"""Production workflow handler for the internal legal workflow capability.

This is the first and only production capability admitted through the
governed Mission Control activation path.  It wraps the existing
``orchestration.langgraph_engine.legal_workflow`` state graph as a
``DurableWorkflowEngine`` workflow function.

Constitutional guarantees:
  - ZERO external side effects (no court filings, no messages, no payments)
  - The ``file`` node's ``filing_reference`` is explicitly synthetic — it is
    an internal draft reference, NOT a real court filing receipt.
  - No connector writes, no shell/browser mutations, no provider calls.
  - All state transformation is in-memory and deterministic for a given input.

Eligibility:
  EXTERNAL_SIDE_EFFECTS = 0
  REAL_OUTBOUND_MESSAGES = 0
  REAL_FILINGS = 0
  FINANCIAL_MUTATIONS = 0
  CONNECTOR_WRITES = 0
  PROVIDER_SIDE_EFFECTS = 0
  SHELL_MUTATIONS = 0
  BROWSER_MUTATIONS = 0
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from orchestration.durable_execution import WorkflowContext
from orchestration.langgraph_engine import create_legal_graph

logger = logging.getLogger(__name__)

# The workflow type identifier used by the capability registry.
LEGAL_WORKFLOW_TYPE = "legal_workflow"

# Explicit flag: the ``file`` node output is synthetic, not a real filing.
REAL_EXTERNAL_ACTION = False


async def legal_workflow_handler(ctx: WorkflowContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the internal legal workflow graph.

    Returns a result dict containing:
      - ``stage``: final workflow stage (e.g. "filed")
      - ``filing_reference``: SYNTHETIC internal reference (NOT a real court filing)
      - ``real_external_action``: always False
      - ``visited_nodes``: ordered list of graph nodes executed
      - ``checkpoints_saved``: number of state checkpoints
      - ``final_state``: full final graph state
    """
    graph = create_legal_graph()

    # Execute the legal workflow graph with the provided input data.
    # The graph runs fully in-memory — no external I/O, no connectors.
    result = await graph._graph.run(
        initial_state=dict(input_data),
        run_id=ctx.workflow_id,
    )

    # The ``file`` terminal node sets ``stage = "filed"`` and generates a
    # synthetic ``filing_reference``.  This is an internal draft reference
    # (a UUID hex string), NOT a confirmation of a real court filing.
    return {
        "stage": result.final_state.get("stage"),
        "filing_reference": result.final_state.get("filing_reference"),
        "real_external_action": REAL_EXTERNAL_ACTION,
        "visited_nodes": result.visited_nodes,
        "checkpoints_saved": result.checkpoints_saved,
        "final_state": result.final_state,
    }