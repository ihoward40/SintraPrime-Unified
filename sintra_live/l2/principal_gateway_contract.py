"""Immutable L2-I7 principal gateway, trust-root, and authority-resolution contracts.

Genesis trust anchor is pinned independently of any request caller.
No private key material is stored in this module.
"""
from __future__ import annotations
import hashlib,re
from dataclasses import asdict,dataclass,field
from enum import Enum
from typing import Any,Tuple
from sintra_live.l2.mission.model import canonical_bytes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

MAX=2**63-1
RESOLVER_VERSION="sp-live-001-l2-i7-resolver-v1"
SCHEMA={x:f"sp-live-001-l2-i7-{x}-v1" for x in ("trust-root","trusted-root-set","trust-anchor-binding","session-attestation","revocation-evidence","step-up-evidence","authority-attestation","principal-auth","authority-snapshot-validation","authority-resolution","authority-denial","authority-incomplete")}
DOMAIN={x:f"SP-LIVE-001:L2:I7:{x.upper()}:v1\0".encode() for x in ("trust-root","trusted-root-set","trust-anchor-binding","session-attestation","revocation-evidence","step-up-evidence","authority-attestation","principal-auth","authority-snapshot-validation","authority-resolution","authority-denial","authority-incomplete")}

# ====== PINNED GENESIS VALUES (from offline ceremony) ======
GENESIS_TRUST_ROOT_SHA256="bd1847872752d4f0c9091608747c690b3e0f36e2c2047ce98c49b15eb858e458"
PINNED_TRUSTED_ROOT_SET_SHA256="666496ce1d1975644e66b01e2182c85acccaa22bc48239636a0e75640f6bc5c3"
AUTHORITY_TRUST_ANCHOR_BINDING_SHA256="d65a7205571e1c088c03103369716ad8a273ce6ab388df6662af47974e9872f0"
GENESIS_PUBLIC_KEY_HEX="52b71c963cbd57ad20a8dc1ffea865ab7ef3b8e766aaaaec484422475c7a2ba2"
GENESIS_TRUST_ROOT_ID="sp-live-001-genesis-root"
GENESIS_TRUST_ROOT_VERSION="v1"
INITIAL_BINDING_SIGNATURE_HEX="9f9fd2d6fdfe5938dd5e597e98e82fad90db91bbef779c04885606af9786e113fd06f0fb603e9f58f01c97d1638b0617c2a1ee9724410a13480be861ae676e0f"

class Assurance(str,Enum):BASIC="BASIC";ELEVATED="ELEVATED"
class TrustRootUsage(str,Enum):SESSION_ATTESTATION="SESSION_ATTESTATION";SESSION_REVOCATION="SESSION_REVOCATION";STEP_UP_ATTESTATION="STEP_UP_ATTESTATION";AUTHORITY_ISSUANCE="AUTHORITY_ISSUANCE";AUTHORITY_REVOCATION="AUTHORITY_REVOCATION"
class AuthResult(str,Enum):ALLOW="ALLOW";DENY="DENY";INCOMPLETE="INCOMPLETE"
class PrincipalAuthResult(str,Enum):AUTHENTICATED="AUTHENTICATED";NOT_AUTHENTICATED="NOT_AUTHENTICATED";SESSION_EXPIRED="SESSION_EXPIRED";SESSION_REVOKED="SESSION_REVOKED";SESSION_NOT_YET_VALID="SESSION_NOT_YET_VALID";SESSION_BINDING_MISMATCH="SESSION_BINDING_MISMATCH";SIGNATURE_INVALID="SIGNATURE_INVALID";STEP_UP_REQUIRED="STEP_UP_REQUIRED";STEP_UP_EVIDENCE_INVALID="STEP_UP_EVIDENCE_INVALID";STEP_UP_ASSURANCE_INSUFFICIENT="STEP_UP_ASSURANCE_INSUFFICIENT";REVOCATION_EVIDENCE_MISSING="REVOCATION_EVIDENCE_MISSING";REVOCATION_STATUS_UNKNOWN="REVOCATION_STATUS_UNKNOWN";REVOCATION_EVIDENCE_EXPIRED="REVOCATION_EVIDENCE_EXPIRED"
class SnapshotResult(str,Enum):VALID="VALID";MISSING="MISSING";EXPIRED="EXPIRED";REVOKED="REVOKED";REVOCATION_UNKNOWN="REVOCATION_UNKNOWN";REVOCATION_EXPIRED="REVOCATION_EXPIRED";SIGNATURE_INVALID="SIGNATURE_INVALID";SCOPE_INSUFFICIENT="SCOPE_INSUFFICIENT";CAPABILITY_NOT_COVERED="CAPABILITY_NOT_COVERED";BUDGET_EXCEEDED="BUDGET_EXCEEDED";CONSEQUENCE_CEILING_EXCEEDED="CONSEQUENCE_CEILING_EXCEEDED";BINDING_MISMATCH="BINDING_MISMATCH";NOT_YET_VALID="NOT_YET_VALID";ISSUER_NOT_TRUSTED="ISSUER_NOT_TRUSTED"
class RevocationStatus(str,Enum):NOT_REVOKED="NOT_REVOKED";REVOKED="REVOKED";UNKNOWN="UNKNOWN"
class BindingBasis(str,Enum):DEPLOYMENT_BASELINE="DEPLOYMENT_BASELINE";CERTIFICATION_FREEZE="CERTIFICATION_FREEZE"
CONSEQUENCE_ORDER=("READ_ONLY","REVERSIBLE_INTERNAL","SCOPED_WRITE","EXTERNAL_COMMUNICATION","FINANCIAL","PRODUCTION","LEGAL","SECURITY_SENSITIVE","GOVERNANCE_PROTECTED")

def _iv(x):
 if isinstance(x,bool) or not isinstance(x,int) or not 0<=x<=MAX:raise ValueError("INVALID_INTEGER")
 return x
def _ts(x):
 if not isinstance(x,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z",x):raise ValueError("INVALID_TIME")
 return x
def ts(x):return _ts(x)
def _ss(x):
 x=tuple(x)
 if len(x)!=len(set(x)):raise ValueError("NONCANONICAL_INPUT")
 return x
def _body(x,own):
 d=asdict(x);d.pop(own,None)
 for k,v in tuple(d.items()):
  if isinstance(v,Enum):d[k]=v.value
  elif isinstance(v,tuple):d[k]=[i.value if isinstance(i,Enum) else i for i in v]
 return d
def _hr(domain,d):return hashlib.sha256(domain+canonical_bytes(d)).hexdigest()
def _seal(x,own,key):
 h=_hr(DOMAIN[key],_body(x,own));old=getattr(x,own)
 if old and old!=h:raise ValueError("HASH_MISMATCH")
 object.__setattr__(x,own,h)

@dataclass(frozen=True)
class TrustRoot:
 schema_version:str;trust_root_id:str;trust_root_version:str;issuer_id:str;issuer_type:str;verification_algorithm:str;verification_material:str;verification_material_sha256:str;permitted_usages:Tuple[str,...];valid_from:str;valid_until:str;trust_root_sha256:str=""
 def __post_init__(self):
  object.__setattr__(self,"permitted_usages",_ss(self.permitted_usages))
  _ts(self.valid_from);_ts(self.valid_until)
  _seal(self,"trust_root_sha256","trust-root")
 def permits(self,usage):return usage in self.permitted_usages

@dataclass(frozen=True)
class TrustedRootSet:
 schema_version:str;trusted_root_set_version:str;ordered_trust_root_sha256s:Tuple[str,...];trusted_root_set_sha256:str=""
 def __post_init__(self):
  object.__setattr__(self,"ordered_trust_root_sha256s",_ss(self.ordered_trust_root_sha256s))
  _seal(self,"trusted_root_set_sha256","trusted-root-set")

@dataclass(frozen=True)
class TrustAnchorBinding:
 schema_version:str;binding_version:str;program_id:str;gate_id:str;mission_id:str;authority_snapshot_reference:str;trusted_root_set_sha256:str;binding_basis_code:str;authority_delta:int=0;authority_trust_anchor_binding_sha256:str=""
 def __post_init__(self):
  if self.authority_delta:raise ValueError("AUTHORITY_DELTA_NONZERO")
  _seal(self,"authority_trust_anchor_binding_sha256","trust-anchor-binding")

@dataclass(frozen=True)
class SessionAttestation:
 schema_version:str;attestation_version:str;session_id:str;trust_root_id:str;trust_root_version:str;issuer_id:str;issuer_type:str;principal_identity_reference:str;authentication_method:str;authentication_assurance_level:str;authentication_timestamp:str;session_valid_from:str;session_valid_until:str;session_nonce:str;bound_program_id:str;bound_gate_id:str;bound_mission_id:str;bound_request_sha256:str;step_up_required:bool;step_up_assurance_level:str;step_up_completed:bool;step_up_method:str;step_up_completed_at:str;step_up_evidence_sha256:str;revocation_status_reference:str;attestation_sha256:str="";session_attestation_signature:str=""
 def __post_init__(self):
  _ts(self.authentication_timestamp);_ts(self.session_valid_from);_ts(self.session_valid_until)
  if self.authentication_assurance_level not in ("BASIC","ELEVATED"):raise ValueError("INVALID_ASSURANCE")
  _seal(self,"attestation_sha256","session-attestation")

@dataclass(frozen=True)
class RevocationEvidence:
 schema_version:str;revocation_version:str;subject_type:str;subject_id:str;issuer_id:str;status:str;status_as_of:str;valid_until:str;source_reference:str;revocation_evidence_sha256:str=""
 def __post_init__(self):
  if self.status not in ("NOT_REVOKED","REVOKED","UNKNOWN"):raise ValueError("INVALID_REVOCATION_STATUS")
  _ts(self.status_as_of);_ts(self.valid_until)
  _seal(self,"revocation_evidence_sha256","revocation-evidence")

@dataclass(frozen=True)
class StepUpEvidence:
 schema_version:str;step_up_version:str;session_id:str;step_up_method:str;step_up_assurance_level:str;step_up_completed_at:str;step_up_evidence_sha256:str=""
 def __post_init__(self):
  if self.step_up_assurance_level not in ("BASIC","ELEVATED"):raise ValueError("INVALID_ASSURANCE")
  _ts(self.step_up_completed_at);_seal(self,"step_up_evidence_sha256","step-up-evidence")

@dataclass(frozen=True)
class AuthoritySnapshotAttestation:
 schema_version:str;attestation_version:str;snapshot_id:str;trust_root_id:str;trust_root_version:str;issuer_id:str;issuer_type:str;principal_identity_reference:str;bound_mission_id:str;bound_request_sha256:str;bound_mission_scope_sha256:str;bound_operation_sha256:str;bound_consequence_classification_sha256:str;bound_capability_id:str;bound_capability_version:str;bound_destination_class:str;bound_provider_account_reference:str;declared_scope_ids:Tuple[str,...];declared_capability_ids:Tuple[str,...];declared_side_effect_ceiling:int;declared_cost_ceiling:int;declared_token_ceiling:int;declared_latency_ceiling_ms:int;declared_consequence_ceiling:str;issued_at:str;valid_from:str;valid_until:str;parent_authority_evidence_sha256:str;authority_attestation_sha256:str="";authority_attestation_signature:str=""
 def __post_init__(self):
  for n in ("declared_scope_ids","declared_capability_ids"):object.__setattr__(self,n,_ss(getattr(self,n)))
  for n in ("declared_side_effect_ceiling","declared_cost_ceiling","declared_token_ceiling","declared_latency_ceiling_ms"):_iv(getattr(self,n))
  if self.declared_consequence_ceiling not in CONSEQUENCE_ORDER:raise ValueError("INVALID_CONSEQUENCE")
  _ts(self.issued_at);_ts(self.valid_from);_ts(self.valid_until)
  _seal(self,"authority_attestation_sha256","authority-attestation")

@dataclass(frozen=True)
class PrincipalAuthRecord:
 schema_version:str;resolver_version:str;result:str;session_id:str;program_id:str;gate_id:str;principal_identity_reference:str;bound_mission_id:str;bound_request_sha256:str;authentication_method:str;authentication_timestamp:str;session_valid_from:str;session_valid_until:str;step_up_required:bool;step_up_completed:bool;evaluation_time:str;reason_code:str;authority_delta:int=0;principal_auth_sha256:str=""
 def __post_init__(self):
  if self.authority_delta:raise ValueError("AUTHORITY_DELTA_NONZERO")
  _seal(self,"principal_auth_sha256","principal-auth")

@dataclass(frozen=True)
class SnapshotValidationRecord:
 schema_version:str;resolver_version:str;result:str;snapshot_id:str;program_id:str;gate_id:str;principal_identity_reference:str;bound_mission_id:str;bound_operation_sha256:str;bound_consequence_classification_sha256:str;bound_capability_id:str;bound_capability_version:str;bound_destination_class:str;bound_provider_account_reference:str;scope_check:str;capability_check:str;budget_check:str;consequence_check:str;binding_check:str;validity_check:str;revocation_check:str;hash_check:str;evaluation_time:str;reason_codes:Tuple[str,...];authority_delta:int=0;authority_snapshot_validation_sha256:str=""
 def __post_init__(self):
  if self.authority_delta:raise ValueError("AUTHORITY_DELTA_NONZERO")
  object.__setattr__(self,"reason_codes",_ss(self.reason_codes))
  _seal(self,"authority_snapshot_validation_sha256","authority-snapshot-validation")

@dataclass(frozen=True)
class AuthorityResolution:
 schema_version:str;resolver_version:str;result:str;reason_code:str;principal_auth_sha256:str;authority_snapshot_validation_sha256:str;policy_decision_sha256:str;trust_root_id:str;trust_root_version:str;program_id:str;gate_id:str;principal_identity_reference:str;mission_id:str;request_sha256:str;mission_scope_sha256:str;aggregate_version:int;aggregate_sha256:str;proposed_operation_sha256:str;consequence_classification_sha256:str;evaluation_time:str;authority_snapshot_valid:bool;approval_granted:bool=False;capability_available:bool=False;capability_certified:bool=False;execution_ready:bool=False;authority_delta:int=0;authority_resolution_sha256:str=""
 def __post_init__(self):
  if any((self.approval_granted,self.capability_available,self.capability_certified,self.execution_ready)) or self.authority_delta:raise ValueError("AUTHORITY_EXPANSION")
  _iv(self.aggregate_version)
  _seal(self,"authority_resolution_sha256","authority-resolution")

@dataclass(frozen=True)
class Resolution:
 result:AuthResult;record:AuthorityResolution;principal_auth:PrincipalAuthRecord|None=None;snapshot_validation:SnapshotValidationRecord|None=None

def verify_ed25519(public_key_hex:str,payload:bytes,signature_hex:str)->bool:
 try:
  pub=Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
  pub.verify(bytes.fromhex(signature_hex),payload)
  return True
 except (InvalidSignature,ValueError):
  return False