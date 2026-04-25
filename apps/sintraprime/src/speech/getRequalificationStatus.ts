export type RequalificationState = "ACTIVE" | "SUSPENDED" | "PROBATION" | "ELIGIBLE";

export type RequalificationStatus = {
  fingerprint?: string;
  state?: RequalificationState;
  cause?: string;
};

function isState(x: unknown): x is RequalificationState {
  return x === "ACTIVE" || x === "SUSPENDED" || x === "PROBATION" || x === "ELIGIBLE";
}

/**
 * Extract requalification posture from a receipt-like object.
 * Read-only, deterministic, no inference.
 */
export function getRequalificationStatus(receipt: any): RequalificationStatus {
  const rq =
    receipt?.requalification ??
    receipt?.requalifier ??
    (receipt?.requalification_state ? { state: receipt.requalification_state } : undefined) ??
    (receipt?.transition && typeof receipt.transition === "object" ? { fingerprint: receipt.transition.fingerprint, state: receipt.transition.to, cause: receipt.transition.reason } : undefined);

  if (!rq || typeof rq !== "object") return {};

  const fingerprint = typeof rq.fingerprint === "string" ? rq.fingerprint : undefined;
  const stateRaw = (rq as any).state;
  const state = isState(stateRaw) ? stateRaw : undefined;
  const cause = typeof (rq as any).cause === "string" ? (rq as any).cause : undefined;

  return { fingerprint, state, cause };
}
