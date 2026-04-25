import { create } from 'zustand';

export type CaseStatus = 'active' | 'pending' | 'closed' | 'on_hold' | 'won' | 'settled';
export type CaseType =
  | 'civil'
  | 'criminal'
  | 'family'
  | 'immigration'
  | 'corporate'
  | 'real_estate'
  | 'intellectual_property'
  | 'employment'
  | 'trust_estate';

export interface CaseEvent {
  id: string;
  date: string;
  title: string;
  description: string;
  type: 'filing' | 'hearing' | 'deadline' | 'note' | 'decision';
}

export interface LegalCase {
  id: string;
  title: string;
  caseNumber: string;
  type: CaseType;
  status: CaseStatus;
  openedDate: string;
  deadlineDate?: string;
  opposingParty?: string;
  court?: string;
  judge?: string;
  nextHearing?: string;
  summary: string;
  events: CaseEvent[];
  documentCount: number;
  priority: 'high' | 'medium' | 'low';
}

interface CaseState {
  cases: LegalCase[];
  activeCaseId: string | null;
  isLoading: boolean;
  lastSynced: Date | null;

  // Actions
  setCases: (cases: LegalCase[]) => void;
  setActiveCase: (id: string) => void;
  addCase: (legalCase: LegalCase) => void;
  updateCase: (id: string, updates: Partial<LegalCase>) => void;
  getCaseById: (id: string) => LegalCase | undefined;
  getActiveCases: () => LegalCase[];
  setLoading: (loading: boolean) => void;
  setLastSynced: (date: Date) => void;
}

// Mock data for development
const mockCases: LegalCase[] = [
  {
    id: 'case-001',
    title: 'Johnson v. Meridian Corp',
    caseNumber: 'CV-2026-00147',
    type: 'employment',
    status: 'active',
    openedDate: '2026-01-15',
    deadlineDate: '2026-05-30',
    opposingParty: 'Meridian Corp',
    court: 'U.S. District Court, S.D.N.Y.',
    judge: 'Hon. Patricia Walsh',
    nextHearing: '2026-05-02',
    summary: 'Wrongful termination and discrimination claim against Meridian Corp. Client seeks $2.4M in damages.',
    events: [
      {
        id: 'ev-001',
        date: '2026-01-15',
        title: 'Case Filed',
        description: 'Complaint filed in S.D.N.Y.',
        type: 'filing',
      },
      {
        id: 'ev-002',
        date: '2026-02-20',
        title: 'Answer Filed',
        description: 'Defendant filed answer denying all claims.',
        type: 'filing',
      },
      {
        id: 'ev-003',
        date: '2026-04-10',
        title: 'Discovery Deadline',
        description: 'All discovery materials due.',
        type: 'deadline',
      },
    ],
    documentCount: 34,
    priority: 'high',
  },
  {
    id: 'case-002',
    title: 'Estate of Williams — Trust Administration',
    caseNumber: 'PRO-2026-00892',
    type: 'trust_estate',
    status: 'active',
    openedDate: '2026-03-01',
    deadlineDate: '2026-07-01',
    court: 'Probate Court, Cook County',
    summary: 'Administration of $4.2M estate trust with contested beneficiary claims.',
    events: [],
    documentCount: 18,
    priority: 'medium',
  },
];

export const useCaseStore = create<CaseState>((set, get) => ({
  cases: mockCases,
  activeCaseId: null,
  isLoading: false,
  lastSynced: null,

  setCases: (cases) => set({ cases }),
  setActiveCase: (id) => set({ activeCaseId: id }),
  addCase: (legalCase) =>
    set((state) => ({ cases: [legalCase, ...state.cases] })),
  updateCase: (id, updates) =>
    set((state) => ({
      cases: state.cases.map((c) => (c.id === id ? { ...c, ...updates } : c)),
    })),
  getCaseById: (id) => get().cases.find((c) => c.id === id),
  getActiveCases: () => get().cases.filter((c) => c.status === 'active'),
  setLoading: (isLoading) => set({ isLoading }),
  setLastSynced: (date) => set({ lastSynced: date }),
}));
