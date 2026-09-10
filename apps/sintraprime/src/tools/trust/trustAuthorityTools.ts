import type { Tool } from '../../types/index.js';
import type { ToolRegistry } from '../toolRegistry.js';

export type PrimaryAuthorityKind =
  | 'statute'
  | 'regulation'
  | 'case'
  | 'official_rule'
  | 'official_guidance';

export interface PrimaryLawAuthority {
  title: string;
  citation: string;
  url: string;
  jurisdiction: string;
  sourceKind: PrimaryAuthorityKind;
  primarySource: boolean;
  effectiveDate?: string;
  checkedAt?: string;
}

export interface PrimaryLawVerificationRequest {
  task: string;
  jurisdiction?: string;
  requirePrimarySources: true;
}

export interface PrimaryLawProviderResult {
  authorities: PrimaryLawAuthority[];
  conflict?: boolean;
  jurisdiction?: string;
}

export interface PrimaryLawProvider {
  verify(request: PrimaryLawVerificationRequest): Promise<PrimaryLawProviderResult>;
}

function isSafeVerifierEndpoint(endpoint: string): boolean {
  try {
    const url = new URL(endpoint);
    return (
      url.protocol === 'https:' ||
      (url.protocol === 'http:' && ['localhost', '127.0.0.1', '::1'].includes(url.hostname))
    );
  } catch {
    return false;
  }
}

export class HttpPrimaryLawProvider implements PrimaryLawProvider {
  constructor(private readonly endpoint?: string) {}

  async verify(request: PrimaryLawVerificationRequest): Promise<PrimaryLawProviderResult> {
    if (!this.endpoint) {
      return { authorities: [], jurisdiction: request.jurisdiction };
    }
    if (!isSafeVerifierEndpoint(this.endpoint)) {
      throw new Error('Current-law verifier endpoint must use HTTPS or localhost HTTP.');
    }

    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error(`Current-law verifier provider returned HTTP ${response.status}.`);
    }

    const payload = (await response.json()) as Partial<PrimaryLawProviderResult>;
    return {
      authorities: Array.isArray(payload.authorities) ? payload.authorities : [],
      conflict: payload.conflict === true,
      jurisdiction: payload.jurisdiction ?? request.jurisdiction,
    };
  }
}

export class TrustInstrumentAuthorityTool implements Tool {
  readonly name = 'trust-instrument-authority';
  readonly description =
    'Returns redacted governing facts from the ISIAH TARIK HOWARD TRUST instrument for internal authority analysis.';

  async execute(args: any): Promise<any> {
    return {
      stage: this.name,
      status: 'GOVERNING_RECORD_FOUND',
      authorityClass: 'TRUST_GOVERNING_RECORD',
      source: 'SPC-NY-Digital - 07-20-22 (1).pdf',
      task: args?.task ?? '',
      provisions: [
        {
          id: 'TRUST-IRREVOCABLE',
          proposition: 'The trust instrument describes the trust as irrevocable.',
        },
        {
          id: 'TRUST-ACCOUNT-CONSENT',
          proposition:
            'The abstract requires unanimous trustee consent to establish an account with respect to trust assets, while one trustee may serve as authorized account manager.',
        },
        {
          id: 'TRUST-PROPER-EXERCISE',
          proposition:
            'The certification states a trustee will not direct a bank to act unless the trustee has the power to act and the power is properly exercised.',
        },
        {
          id: 'TRUST-EXPRESS-POWERS',
          proposition:
            'The certification describes authority concerning banking, power of attorney, encumbrance, borrowing, and appointment of a general manager/signatory.',
        },
        {
          id: 'TRUST-AMENDMENT-APPROVAL',
          proposition:
            'The declaration states amendments may be made only by unanimous approval of the Board of Trustees.',
        },
        {
          id: 'TRUST-RECORDS',
          proposition:
            'The declaration calls for meetings and resolutions to be recorded in a minute book and for proper records and accounts to be kept.',
        },
      ],
      restrictions: [
        'Do not infer powers from silence.',
        'Do not treat the private instrument as overriding applicable external law.',
        'Do not reproduce sensitive identifiers in runtime logs or outputs.',
      ],
      provenance: {
        sourceType: 'executed-trust-record',
        redacted: true,
      },
    };
  }
}

export class WeissTrusteeHandbookTool implements Tool {
  readonly name = 'weisss-trustee-handbook';
  readonly description =
    'Returns secondary educational trustee-administration guidance from Weiss; never controlling law.';

  async execute(args: any): Promise<any> {
    return {
      stage: this.name,
      status: 'SECONDARY_SOURCE_AVAILABLE',
      authorityClass: 'SECONDARY_EDUCATIONAL',
      controllingLaw: false,
      source: "Weiss's Concise Trustee Handbook, 2d ed. (2007)",
      task: args?.task ?? '',
      usefulTopics: [
        'trustee basics',
        'powers and duties of the trustee',
        'privileges and liabilities',
        'authorized representatives',
        'banking',
        'transferring assets',
        'keeping minutes',
        'legal affairs',
        'IRS relations',
        'sample forms',
      ],
      restrictions: [
        'Use for issue spotting, workflow structure, historical leads, and secondary support only.',
        'Do not use alone to establish tax status, legal immunity, lien validity, debt discharge, jurisdictional defeat, or third-party obligations.',
        'Current enacted law and binding authority control over inconsistent handbook claims.',
      ],
      provenance: {
        sourceType: 'secondary-educational',
        sourceDate: '2007',
      },
    };
  }
}

function admissiblePrimaryAuthority(record: PrimaryLawAuthority): boolean {
  if (
    !record ||
    record.primarySource !== true ||
    !record.title?.trim() ||
    !record.citation?.trim() ||
    !record.jurisdiction?.trim()
  ) {
    return false;
  }
  try {
    return new URL(record.url).protocol === 'https:';
  } catch {
    return false;
  }
}

export class CurrentLawVerifierTool implements Tool {
  readonly name = 'current-law-verifier';
  readonly description =
    'Verifies current legal propositions against structured primary-source authority; fails closed on missing or inadequate evidence.';

  constructor(private readonly provider: PrimaryLawProvider) {}

  async execute(args: any): Promise<any> {
    const task = String(args?.task ?? '').trim();
    const jurisdiction = String(args?.jurisdiction ?? '').trim() || undefined;

    const result = await this.provider.verify({
      task,
      jurisdiction,
      requirePrimarySources: true,
    });

    const primaryAuthorities = (result.authorities ?? []).filter(admissiblePrimaryAuthority);
    const resolvedJurisdiction = result.jurisdiction?.trim() || jurisdiction;
    const checkedAt = new Date().toISOString();

    if (result.conflict === true) {
      return {
        verification: {
          status: 'CONFLICT_FOUND',
          jurisdiction: resolvedJurisdiction,
          authorities: primaryAuthorities.map((a) => `${a.citation} — ${a.url}`),
          authorityRecords: primaryAuthorities,
          verifiedAt: checkedAt,
          verifier: this.name,
        },
      };
    }

    if (!resolvedJurisdiction || primaryAuthorities.length === 0) {
      return {
        verification: {
          status: 'NOT_YET_VERIFIED',
          jurisdiction: resolvedJurisdiction,
          authorities: [],
          authorityRecords: primaryAuthorities,
          verifiedAt: checkedAt,
          verifier: this.name,
        },
      };
    }

    return {
      verification: {
        status: 'VERIFIED_CURRENT',
        jurisdiction: resolvedJurisdiction,
        authorities: primaryAuthorities.map((a) => `${a.citation} — ${a.url}`),
        authorityRecords: primaryAuthorities,
        verifiedAt: checkedAt,
        verifier: this.name,
      },
    };
  }
}

export interface RegisterTrustAuthorityToolsOptions {
  currentLawEndpoint?: string;
  primaryLawProvider?: PrimaryLawProvider;
}

export function registerTrustAuthorityTools(
  registry: ToolRegistry,
  options: RegisterTrustAuthorityToolsOptions = {},
): void {
  const provider =
    options.primaryLawProvider ?? new HttpPrimaryLawProvider(options.currentLawEndpoint);

  registry.registerTool(new TrustInstrumentAuthorityTool());
  registry.registerTool(new WeissTrusteeHandbookTool());
  registry.registerTool(new CurrentLawVerifierTool(provider));
}
