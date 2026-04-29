/**
 * Evidence Binder Agent
 *
 * Builds a public/reserve exhibit index from the parsed document and its
 * classified clauses.
 *
 * Public exhibits may be transmitted to banks, courts, credit bureaus,
 * creditors, and government agencies — but only after safety gates pass.
 *
 * Reserve exhibits are for internal trust records only and must not be
 * attached to any external submission without attorney or CPA sign-off.
 *
 * Standard structure:
 *   Public Ex. A  — UCC Filing Acknowledgment
 *   Public Ex. B  — Certification of Trust
 *   Public Ex. C  — Banking Resolution
 *   Public Ex. D  — Trustee Minutes
 *   Reserve Ex. R-1 — Security Agreement (internal review only)
 *   Reserve Ex. R-2 — Tax affidavits / W-8 materials (internal review only)
 *   Reserve Ex. R-3 — Legacy notices (internal review only)
 */

import type {
  ParsedDocument,
  ClassifiedClause,
  Exhibit,
  ExhibitIndex,
} from '../types.js';

// ── Exhibit template catalog ──────────────────────────────────────────────────

const PUBLIC_EXHIBIT_TEMPLATES: Array<{
  id: string;
  title: string;
  keywords: string[];
  description: string;
}> = [
  {
    id: 'Ex-A',
    title: 'UCC Filing Acknowledgment',
    keywords: ['ucc', 'financing statement', 'ucc-1'],
    description: 'Acknowledgment of UCC financing statement filing.',
  },
  {
    id: 'Ex-B',
    title: 'Certification of Trust',
    keywords: ['certification of trust', 'certificate of trust'],
    description:
      'Certification establishing trust existence, trustee authority, and trust powers.',
  },
  {
    id: 'Ex-C',
    title: 'Banking Resolution',
    keywords: ['banking resolution', 'bank resolution', 'banking authority'],
    description: 'Trustee resolution authorizing banking activity on behalf of the trust.',
  },
  {
    id: 'Ex-D',
    title: 'Trustee Minutes',
    keywords: ['trustee minutes', 'minutes of the trustee', 'trustee meeting'],
    description: 'Formal minutes of trustee actions and decisions.',
  },
];

const RESERVE_EXHIBIT_TEMPLATES: Array<{
  id: string;
  title: string;
  keywords: string[];
  description: string;
}> = [
  {
    id: 'R-1',
    title: 'Security Agreement — Internal Review Only',
    keywords: ['security agreement'],
    description:
      'Security agreement documenting collateral interests. Internal review only; do not attach to external filings without counsel.',
  },
  {
    id: 'R-2',
    title: 'Tax Affidavits / W-8 Materials — Internal Review Only',
    keywords: ['w-8', 'w8', 'tax affidavit', '1099', 'w-9', 'withholding'],
    description:
      'Tax position affidavits and withholding certificates. Requires CPA or tax-attorney review.',
  },
  {
    id: 'R-3',
    title: 'Legacy Notices — Internal Review Only',
    keywords: ['notice of default', 'notice of dishonor', 'administrative notice'],
    description:
      'Legacy administrative notices retained for historical record. Do not resubmit without compliance rewrite.',
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function sectionMatchesKeywords(section: ClassifiedClause, keywords: string[]): boolean {
  const combined = `${section.sectionTitle} ${section.content}`.toLowerCase();
  return keywords.some((kw) => combined.includes(kw));
}

function documentMatchesKeywords(doc: ParsedDocument, keywords: string[]): boolean {
  const combined = `${doc.title} ${doc.documentType}`.toLowerCase();
  return keywords.some((kw) => combined.includes(kw));
}

// ── Main builder ─────────────────────────────────────────────────────────────

/**
 * Run the Evidence Binder Agent.
 *
 * Matches document type and section content against exhibit templates to
 * build the public/reserve exhibit index.
 */
export function runEvidenceBinderAgent(
  document: ParsedDocument,
  clauses: ClassifiedClause[],
): ExhibitIndex {
  const publicExhibits: Exhibit[] = [];
  const reserveExhibits: Exhibit[] = [];

  for (const template of PUBLIC_EXHIBIT_TEMPLATES) {
    const docMatch = documentMatchesKeywords(document, template.keywords);
    const sectionMatch = clauses.some((c) => sectionMatchesKeywords(c, template.keywords));

    if (docMatch || sectionMatch) {
      publicExhibits.push({
        id: template.id,
        title: template.title,
        type: 'public',
        description: template.description,
        source: document.id,
        restricted: false,
      });
    }
  }

  for (const template of RESERVE_EXHIBIT_TEMPLATES) {
    const docMatch = documentMatchesKeywords(document, template.keywords);
    const sectionMatch = clauses.some((c) => sectionMatchesKeywords(c, template.keywords));

    if (docMatch || sectionMatch) {
      reserveExhibits.push({
        id: template.id,
        title: template.title,
        type: 'reserve',
        description: template.description,
        source: document.id,
        restricted: true,
      });
    }
  }

  // Always include a default public exhibit if nothing matched
  if (publicExhibits.length === 0) {
    publicExhibits.push({
      id: 'Ex-Z',
      title: 'Supporting Document',
      type: 'public',
      description:
        'Document provided as supporting evidence. Review classification before external use.',
      source: document.id,
      restricted: false,
    });
  }

  return { public: publicExhibits, reserve: reserveExhibits };
}
