"""I6 sealed-decision attestation and drift verification."""
from .policy_resolution_contract import *
from .policy_resolver import resolve

def attest(*, mission_id, mission_allowed, mission_prohibited, mission_side_effect_budget,
           mission_cost_ceiling, mission_token_ceiling, mission_latency_ceiling,
           mission_consequence_ceiling, operation, classification, policies,
           evaluation_time, authority_evidence=None, upstream_complete=True):
    return resolve(
        mission_id=mission_id,
        mission_allowed=mission_allowed,
        mission_prohibited=mission_prohibited,
        mission_side_effect_budget=mission_side_effect_budget,
        mission_cost_ceiling=mission_cost_ceiling,
        mission_token_ceiling=mission_token_ceiling,
        mission_latency_ceiling=mission_latency_ceiling,
        mission_consequence_ceiling=mission_consequence_ceiling,
        operation=operation,
        classification=classification,
        policies=policies,
        evaluation_time=evaluation_time,
        authority_evidence=authority_evidence,
        upstream_complete=upstream_complete,
    )

def verify_sealed(resolution, **kwargs):
    re_run = attest(**kwargs)
    return (re_run.result is resolution.result
            and re_run.record.__class__ is resolution.record.__class__)