"""Offline-only I5 binding and sealed-decision attestation."""
from .model_routing_contract import *
from .model_routing_policy import route

def attest(requirement,policy,catalog_entries,*,mission_state="SPECIALISTS_RECONCILED",terminal=False,cancelled=False,reconciliation_complete=True,reconciliation_authority_delta=0):
 if terminal:return RoutingOutcome(Result.DENIED,"TERMINAL_MISSION",None,())
 if cancelled:return RoutingOutcome(Result.DENIED,"CANCELLED_MISSION",None,())
 if mission_state!="SPECIALISTS_RECONCILED":return RoutingOutcome(Result.DENIED,"WRONG_MISSION_STATE",None,())
 if not reconciliation_complete:return RoutingOutcome(Result.DENIED,"I4_RECONCILIATION_NOT_COMPLETE",None,())
 if reconciliation_authority_delta!=0:return RoutingOutcome(Result.DENIED,"I4_AUTHORITY_DELTA_NONZERO",None,())
 return route(requirement,policy,catalog_entries)
def verify_sealed(requirement,policy,catalog_entries,decision):
 result=attest(requirement,policy,catalog_entries)
 return result.result is Result.COMPLETE and result.decision==decision and result.decision.model_decision_sha256==decision.model_decision_sha256
