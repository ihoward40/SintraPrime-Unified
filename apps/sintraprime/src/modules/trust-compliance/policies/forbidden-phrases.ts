/**
 * Forbidden Phrases
 *
 * Phrases that automatically trigger RED classification (DO_NOT_SEND or
 * REWRITE_REQUIRED) when found in a document section.
 *
 * Matching is case-insensitive and checks for substring presence.
 */

export interface ForbiddenPhrase {
  phrase: string;
  reason: string;
}

export const FORBIDDEN_PHRASES: ForbiddenPhrase[] = [
  // Accepted-for-Value / A4V
  { phrase: 'accepted for value', reason: 'A4V_LANGUAGE — legally unsupported debt-discharge claim.' },
  { phrase: 'accept for value', reason: 'A4V_LANGUAGE — legally unsupported debt-discharge claim.' },
  { phrase: 'a4v', reason: 'A4V_LANGUAGE — shorthand for accepted-for-value scheme.' },
  { phrase: 'return for value', reason: 'A4V_LANGUAGE — variation of accepted-for-value scheme.' },

  // Sovereign / nonresident claims
  { phrase: 'non-domestic', reason: 'NONRESIDENT_CLAIM — sovereign-citizen framing.' },
  { phrase: 'non domestic', reason: 'NONRESIDENT_CLAIM — sovereign-citizen framing.' },
  { phrase: 'strawman', reason: 'NONRESIDENT_CLAIM — sovereign-citizen legal fiction.' },
  { phrase: 'straw man', reason: 'NONRESIDENT_CLAIM — sovereign-citizen legal fiction.' },
  { phrase: 'flesh and blood', reason: 'NONRESIDENT_CLAIM — sovereign-citizen framing.' },
  { phrase: 'all capital letters', reason: 'NONRESIDENT_CLAIM — all-caps name legal fiction.' },
  { phrase: 'capitis diminutio', reason: 'NONRESIDENT_CLAIM — legally unsupported status claim.' },

  // Birth certificate / bond redemption
  { phrase: 'birth certificate bond', reason: 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM — legally unsupported.' },
  { phrase: 'birth certificate account', reason: 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM — legally unsupported.' },
  { phrase: 'cestui que vie', reason: 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM — legally inapplicable in this context.' },
  { phrase: 'redemption process', reason: 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM — sovereign redemption scheme.' },
  { phrase: 'bond discharge', reason: 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM — legally unsupported discharge claim.' },
  { phrase: 'private bond', reason: 'BIRTH_CERTIFICATE_ACCOUNT_CLAIM — legally unsupported.' },

  // Maritime / admiralty
  { phrase: 'maritime lien', reason: 'MARITIME_LIEN_CLAIM — typically inapplicable outside commercial shipping.' },
  { phrase: 'admiralty jurisdiction', reason: 'MARITIME_LIEN_CLAIM — typically inapplicable in this context.' },
  { phrase: 'law of the flag', reason: 'MARITIME_LIEN_CLAIM — sovereign-citizen maritime framing.' },

  // Self-executing / private contracts
  { phrase: 'self-executing', reason: 'SELF_EXECUTING_CONTRACT — legally questionable; rewrite required.' },
  { phrase: 'self executing', reason: 'SELF_EXECUTING_CONTRACT — legally questionable; rewrite required.' },
  { phrase: 'by operation of law this notice', reason: 'SELF_EXECUTING_CONTRACT — unilateral legal effect claim.' },
  { phrase: 'your silence is acquiescence', reason: 'SELF_EXECUTING_CONTRACT — legally invalid consent claim.' },
  { phrase: 'silence is consent', reason: 'SELF_EXECUTING_CONTRACT — legally invalid consent claim.' },

  // Threatening fee schedules
  { phrase: 'administrative fee schedule', reason: 'THREATENING_FEE_SCHEDULE — creates legal and reputational risk.' },
  { phrase: 'private fee schedule', reason: 'THREATENING_FEE_SCHEDULE — creates legal and reputational risk.' },
  { phrase: 'fee schedule notice', reason: 'THREATENING_FEE_SCHEDULE — creates legal and reputational risk.' },
  { phrase: 'penalty fee', reason: 'THREATENING_FEE_SCHEDULE — threatening demand without legal basis.' },
];

/**
 * Check if content contains any forbidden phrase.
 * Returns the first matching forbidden phrase, or null if clean.
 */
export function findForbiddenPhrase(content: string): ForbiddenPhrase | null {
  const lower = content.toLowerCase();
  for (const fp of FORBIDDEN_PHRASES) {
    if (lower.includes(fp.phrase.toLowerCase())) {
      return fp;
    }
  }
  return null;
}

/**
 * Return all forbidden phrases found in content.
 */
export function findAllForbiddenPhrases(content: string): ForbiddenPhrase[] {
  const lower = content.toLowerCase();
  return FORBIDDEN_PHRASES.filter((fp) => lower.includes(fp.phrase.toLowerCase()));
}
