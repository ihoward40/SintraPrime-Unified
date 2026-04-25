export type DelegatedClassDefinition = {
  class_id: string;
  pattern: string;
  capabilities: string[];
  adapter: string;
  write: boolean;
  created_at: string;
};

export type DelegatedApprovalScope = {
  autonomy_mode: string;
  confidence_min: number;
  promotion_required: boolean;
};

export type DelegatedApprovalRecord = {
  class_id: string;
  approved_by: string;
  scope: DelegatedApprovalScope;
  approved_at: string;
};

export type DelegatedRevocationRecord = {
  class_id: string;
  revoked_by: string;
  revoked_at: string;
  reason: string;
};

export type DelegatedSuspensionRecord = {
  class_id: string;
  suspended_at: string;
  reason: string;
  details?: Record<string, unknown> | null;
};

export type DelegationDecision = {
  kind: "DelegationDecision";
  matched: boolean;
  class_id: string | null;
  active: boolean;
  inherited: boolean;
  reason:
    | "NO_MATCH"
    | "CLASS_NOT_FOUND"
    | "NOT_APPROVED"
    | "REVOKED"
    | "SUSPENDED"
    | "MODE_MISMATCH"
    | "PROMOTION_REQUIRED_MISSING"
    | "CONFIDENCE_TOO_LOW"
    | "OK";
  scope: DelegatedApprovalScope | null;
  evidence: {
    promotions_matching: number;
    promotions_meeting_confidence: number;
  };
  suspension: {
    active: boolean;
    suspended_at: string | null;
    reason: string | null;
  };
};
