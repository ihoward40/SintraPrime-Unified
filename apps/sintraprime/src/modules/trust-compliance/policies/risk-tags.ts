/**
 * Risk Tag Definitions
 *
 * Canonical descriptions for each risk tag used by the Risk Classifier Agent.
 * These descriptions drive human-readable explanations in the risk register
 * and the run receipt.
 */

import type { RiskTag } from '../types.js';

export const RISK_TAG_DEFINITIONS: Record<RiskTag, string> = {
  TRUST_ADMIN:
    'Trust administration language — generally safe with attorney review.',
  BANKING_AUTHORITY:
    'Banking authority assertion — verify with the relevant financial institution.',
  UCC_RECORD:
    'UCC filing reference — confirm accuracy and jurisdictional validity.',
  TAX_POSITION:
    'Tax-sensitive language — requires CPA or tax-attorney review before use.',
  A4V_LANGUAGE:
    'Accepted-for-Value language — legally unsupported in most contexts; do not send without expert review.',
  NONRESIDENT_CLAIM:
    'Non-resident or foreign-status claim — requires expert legal and tax review.',
  BIRTH_CERTIFICATE_ACCOUNT_CLAIM:
    'Birth-certificate account claim — legally unsupported; block from all external use.',
  SELF_EXECUTING_CONTRACT:
    'Self-executing contract language — legally questionable; rewrite required.',
  MARITIME_LIEN_CLAIM:
    'Maritime/admiralty lien claim — typically inapplicable; review carefully.',
  THREATENING_FEE_SCHEDULE:
    'Threatening administrative fee schedule — do not send; creates legal and reputational risk.',
  REWRITE_REQUIRED:
    'Language requires compliance rewrite before any external use.',
  DO_NOT_SEND:
    'Clause must remain internal — do not file, submit, or transmit externally.',
};
