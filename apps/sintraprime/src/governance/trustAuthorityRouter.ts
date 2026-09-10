/**
 * Governed Trust Authority Router
 *
 * Enforces the Howard Trust Authority Stack at the SintraPrime control plane.
 * The router is intentionally fail-closed for legal-effect conclusions and
 * external execution. It does not pretend that secondary educational material
 * is controlling law and it does not fabricate a current-law verification.
 */

import type { PlanStep, TaskRequest } from '../types/index.js';

export type TrustAuthorityStage =
  | 'trust-instrument-authority'
  | 'weisss-trustee-handbook'
  | 'current-law-verifier';

export interface TrustAuthorityVerification {
  status: 'VERIFIED_CURRENT' | 'NOT_YET_VERIFIED' | 'CONFLICT_FOUND';
  jurisdiction?: string;
  authorities?: string[];
  verifiedAt?: string;
  verifier?: string;
}

export interface TrustAuthorityRoute {
  isTrustRelated: boolean;
  routeId: 'HOWARD-TRUST-AUTHORITY';
  authorityOrder: TrustAuthorityStage[];
  legalEffectRequested: boolean;
  externalExecutionRequested: boolean;
  currentLawVerification: TrustAuthorityVerification;
  principalApproval: boolean;
  executionAllowed: boolean;
  blockingReasons: string[];
}

const TRUST_PATTERNS = [
  /\bisiah\s+tarik\s+howard\s+trust\b/i,
  /\btrust instrument\b/i,
  /\bcertification of trust\b/i,
  /\bdeclaration of trust\b/i,
  /\btrustee\b/i,
  /\bco-?trustee\b/i,
  /\bbeneficiar(?:y|ies)\b/i,
  /\bsettlor\b/i,
  /\btrust corpus\b/i,
  /\bfiduciary dut(?:y|ies)\b/i,
  /\btrust administration\b/i,
  /\btrust banking\b/i,
  /\btrust resolution\b/i,
  /\btrust amendment\b/i,
];

const LEGAL_EFFECT_PATTERNS = [
  /\blegal effect\b/i,
  /\blegally binding\b/i,
  /\benforce(?:able|ment)?\b/i,
  /\bperfect(?:ion|ed)?\b/i,
  /\blien\b/i,
  /\bjurisdiction\b/i,
  /\btax(?:able|ation| filing| status)?\b/i,
  /\bcourt\b/i,
  /\bcreditor\b/i,
  /\bbank obligation\b/i,
  /\bborrow(?:ing)?\b/i,
  /\bencumber\b/i,
  /\bdistribut(?:e|ion)\b/i,
  /\btransfer\b/i,
  /\bamend(?:ment)?\b/i,
  /\bterminate|termination\b/i,
];

const EXTERNAL_EXECUTION_PATTERNS = [
  /\bfile\b/i,
  /\bsubmit\b/i,
  /\bsend\b/i,
  /\bmail\b/i,
  /\bemail\b/i,
  /\btransmit\b/i,
  /\bexecute\b/i,
  /\bsign\b/i,
  /\brecord\b/i,
  /\bpublish\b/i,
  /\bserve\b/i,
  /\bopen (?:an )?account\b/i,
  /\bborrow\b/i,
  /\btransfer\b/i,
  /\bencumber\b/i,
  /\bdistribute\b/i,
];

const AUTHORITY_TOOL_NAMES = new Set<TrustAuthorityStage>([
  'trust-instrument-authority',
  'weisss-trustee-handbook',
  'current-law-verifier',
]);

function searchableRequestText(request: TaskRequest): string {
  let context = '';
  try {
    context = request.context ? JSON.stringify(request.context) : '';
  } catch {
    context = '';
  }
  return `${request.prompt}\n${context}`;
}

function initialVerification(request: TaskRequest): TrustAuthorityVerification {
  // A caller may supply jurisdiction as routing context, but may NOT pre-seed
  // VERIFIED_CURRENT. Only applyTrustAuthorityStepResult can promote a route
  // after the explicit current-law-verifier stage executes successfully.
  const jurisdiction = request.context?.trustAuthority?.jurisdiction;
  return jurisdiction
    ? { status: 'NOT_YET_VERIFIED', jurisdiction: String(jurisdiction) }
    : { status: 'NOT_YET_VERIFIED' };
}

function recalculateRoute(route: TrustAuthorityRoute): TrustAuthorityRoute {
  const blockingReasons: string[] = [];
  if (
    (route.legalEffectRequested || route.externalExecutionRequested) &&
    route.currentLawVerification.status !== 'VERIFIED_CURRENT'
  ) {
    blockingReasons.push(
      'Current-law verification is required before a legal-effect conclusion or external execution.',
    );
  }
  if (route.externalExecutionRequested && !route.principalApproval) {
    blockingReasons.push(
      'Principal/trustee approval is required before external trust execution.',
    );
  }
  return {
    ...route,
    executionAllowed: blockingReasons.length === 0,
    blockingReasons,
  };
}

export function routeTrustAuthority(request: TaskRequest): TrustAuthorityRoute {
  const text = searchableRequestText(request);
  const isTrustRelated = TRUST_PATTERNS.some((pattern) => pattern.test(text));
  const legalEffectRequested =
    isTrustRelated && LEGAL_EFFECT_PATTERNS.some((pattern) => pattern.test(text));
  const externalExecutionRequested =
    isTrustRelated && EXTERNAL_EXECUTION_PATTERNS.some((pattern) => pattern.test(text));
  const currentLawVerification = initialVerification(request);
  const principalApproval = request.context?.trustAuthority?.principalApproval === true;

  return recalculateRoute({
    isTrustRelated,
    routeId: 'HOWARD-TRUST-AUTHORITY',
    authorityOrder: [
      'trust-instrument-authority',
      'weisss-trustee-handbook',
      'current-law-verifier',
    ],
    legalEffectRequested,
    externalExecutionRequested,
    currentLawVerification,
    principalApproval,
    executionAllowed: true,
    blockingReasons: [],
  });
}

export function attachTrustAuthorityRoute(request: TaskRequest): TaskRequest {
  const route = routeTrustAuthority(request);
  if (!route.isTrustRelated) return request;

  return {
    ...request,
    context: {
      ...(request.context ?? {}),
      trustAuthorityRoute: route,
      mandatoryAuthorityInstructions: [
        'Consult trust-instrument-authority first for trust-specific governing language.',
        'Consult weisss-trustee-handbook second as secondary educational authority only.',
        'Obtain current-law verification before stating any legal-effect conclusion or executing any external trust action.',
        'Do not execute an external trust action unless the required principal/trustee approval is documented.',
        'Record conflicts rather than silently reconciling lower-ranked sources with controlling authority.',
      ],
    },
  };
}

function isAuthorityResearchStep(step: PlanStep): boolean {
  const stage = step.args?.authorityStage;
  if (!AUTHORITY_TOOL_NAMES.has(step.tool as TrustAuthorityStage)) {
    return false;
  }
  return stage === step.tool;
}

function isExternalStep(step: PlanStep): boolean {
  const marker = `${step.description ?? ''} ${step.tool ?? ''} ${JSON.stringify(step.args ?? {})}`;
  return EXTERNAL_EXECUTION_PATTERNS.some((pattern) => pattern.test(marker));
}

export function evaluateTrustAuthorityStep(
  step: PlanStep,
  route: TrustAuthorityRoute,
): { allowed: boolean; reason?: string } {
  if (!route.isTrustRelated || isAuthorityResearchStep(step)) {
    return { allowed: true };
  }

  if (
    (route.legalEffectRequested || route.externalExecutionRequested || isExternalStep(step)) &&
    route.currentLawVerification.status !== 'VERIFIED_CURRENT'
  ) {
    return {
      allowed: false,
      reason: 'Trust authority gate: current law has not been verified.',
    };
  }

  if ((route.externalExecutionRequested || isExternalStep(step)) && !route.principalApproval) {
    return {
      allowed: false,
      reason: 'Trust authority gate: principal/trustee approval is not documented.',
    };
  }

  return { allowed: true };
}

/**
 * Accepts a verifier result only from the explicit current-law stage and only
 * when it contains jurisdiction plus at least one authority. Anything weaker
 * remains fail-closed.
 */
export function applyTrustAuthorityStepResult(
  route: TrustAuthorityRoute,
  step: PlanStep,
  result: any,
): TrustAuthorityRoute {
  if (
    !route.isTrustRelated ||
    step.tool !== 'current-law-verifier' ||
    step.args?.authorityStage !== 'current-law-verifier'
  ) {
    return route;
  }

  const candidate = result?.verification ?? result;
  const status = candidate?.status;
  const authorities = Array.isArray(candidate?.authorities) ? candidate.authorities : [];
  const jurisdiction = candidate?.jurisdiction;

  if (
    status === 'VERIFIED_CURRENT' &&
    jurisdiction &&
    authorities.length > 0 &&
    candidate?.verifier === 'current-law-verifier'
  ) {
    return recalculateRoute({
      ...route,
      currentLawVerification: {
        status: 'VERIFIED_CURRENT',
        jurisdiction,
        authorities,
        verifiedAt: candidate?.verifiedAt ?? new Date().toISOString(),
        verifier: 'current-law-verifier',
      },
    });
  }

  if (status === 'CONFLICT_FOUND') {
    return recalculateRoute({
      ...route,
      currentLawVerification: {
        status: 'CONFLICT_FOUND',
        jurisdiction,
        authorities,
        verifiedAt: candidate?.verifiedAt ?? new Date().toISOString(),
        verifier: 'current-law-verifier',
      },
    });
  }

  return recalculateRoute({
    ...route,
    currentLawVerification: {
      status: 'NOT_YET_VERIFIED',
      jurisdiction: route.currentLawVerification.jurisdiction,
    },
  });
}
