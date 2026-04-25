import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Case, Motion, CaseLaw, LegalAlert } from '../types/legal';

interface LegalState {
  cases: Case[];
  activeCaseId: string | null;
  motions: Motion[];
  caseLawResults: CaseLaw[];
  bookmarkedCases: CaseLaw[];
  alerts: LegalAlert[];
  caseLawQuery: string;
  selectedPracticeAreas: string[];
  selectedJurisdiction: string;
  isLoadingCases: boolean;
  isLoadingCaseLaw: boolean;

  // Actions
  setCases: (cases: Case[]) => void;
  addCase: (c: Case) => void;
  updateCase: (id: string, updates: Partial<Case>) => void;
  setActiveCase: (id: string | null) => void;
  setMotions: (motions: Motion[]) => void;
  addMotion: (motion: Motion) => void;
  updateMotion: (id: string, updates: Partial<Motion>) => void;
  setCaseLawResults: (results: CaseLaw[]) => void;
  toggleBookmark: (caseLaw: CaseLaw) => void;
  setAlerts: (alerts: LegalAlert[]) => void;
  markAlertRead: (id: string) => void;
  setCaseLawQuery: (query: string) => void;
  setSelectedPracticeAreas: (areas: string[]) => void;
  setSelectedJurisdiction: (jurisdiction: string) => void;
  setLoadingCases: (loading: boolean) => void;
  setLoadingCaseLaw: (loading: boolean) => void;
}

// Mock data
const mockCases: Case[] = [
  {
    id: 'case-001',
    caseNumber: '2024-CV-1847',
    title: 'Sintra v. Metropolitan Housing Authority',
    description: 'Civil rights violation regarding discriminatory housing practices',
    status: 'drafting',
    priority: 'high',
    practiceArea: 'civil_rights',
    court: 'U.S. District Court, S.D.N.Y.',
    courtLevel: 'federal_district',
    judge: 'Hon. Sandra Williams',
    filingDate: '2024-01-15',
    nextDeadline: '2024-07-30',
    parties: [
      { id: 'p1', name: 'Marcus Sintra', role: 'plaintiff' },
      { id: 'p2', name: 'Metropolitan Housing Authority', role: 'defendant', attorney: 'Smith & Associates' },
    ],
    documents: [],
    courtDates: [
      { id: 'cd1', caseId: 'case-001', date: '2024-08-15', type: 'hearing', court: 'S.D.N.Y.', completed: false },
    ],
    motions: [],
    assignedAttorney: 'Marcus A. Sintra',
    estimatedValue: 500000,
    tags: ['civil rights', 'housing', 'discrimination'],
    aiAnalysis: {
      caseId: 'case-001',
      generatedAt: new Date().toISOString(),
      successProbability: 0.73,
      keyIssues: ['Fair Housing Act violation', '42 U.S.C. § 1983 claim', 'Equal Protection Clause'],
      recommendedActions: ['File motion for preliminary injunction', 'Request discovery on policy documents', 'Identify class members'],
      relevantCases: ['Griggs v. Duke Power Co.', 'Texas Dept. of Housing v. Inclusive Communities'],
      riskFactors: ['Statute of limitations question', 'Standing issues for prospective tenants'],
      strategyNotes: 'Strong disparate impact claim. Focus on statistical evidence showing discriminatory effect.',
    },
  },
  {
    id: 'case-002',
    caseNumber: '2024-BK-0394',
    title: 'In re: Apex Ventures LLC Chapter 11',
    description: 'Corporate bankruptcy reorganization and asset protection',
    status: 'monitoring',
    priority: 'critical',
    practiceArea: 'bankruptcy',
    court: 'U.S. Bankruptcy Court, D. Del.',
    courtLevel: 'federal_bankruptcy',
    judge: 'Hon. Robert Chen',
    filingDate: '2024-03-01',
    nextDeadline: '2024-07-15',
    parties: [
      { id: 'p3', name: 'Apex Ventures LLC', role: 'petitioner' },
    ],
    documents: [],
    courtDates: [],
    motions: [],
    assignedAttorney: 'Marcus A. Sintra',
    estimatedValue: 2500000,
    tags: ['bankruptcy', 'chapter 11', 'reorganization'],
  },
  {
    id: 'case-003',
    caseNumber: '2024-TR-0088',
    title: 'Sintra Family Trust - UCC Article 9 Dispute',
    description: 'Secured transaction dispute regarding trust assets',
    status: 'research',
    priority: 'medium',
    practiceArea: 'trust',
    court: 'Superior Court, NY',
    courtLevel: 'state_trial',
    filingDate: '2024-05-10',
    nextDeadline: '2024-08-01',
    parties: [
      { id: 'p5', name: 'Sintra Family Trust', role: 'petitioner' },
      { id: 'p6', name: 'First National Bank', role: 'respondent', attorney: 'BigLaw Partners' },
    ],
    documents: [],
    courtDates: [],
    motions: [],
    assignedAttorney: 'Marcus A. Sintra',
    tags: ['trust', 'UCC', 'secured transactions'],
  },
  {
    id: 'case-004',
    caseNumber: '2024-CR-2211',
    title: 'People v. Johnson - Criminal Defense',
    description: 'Defense representation in felony fraud charges',
    status: 'intake',
    priority: 'high',
    practiceArea: 'criminal_defense',
    court: 'New York Supreme Court, Criminal Term',
    courtLevel: 'state_trial',
    filingDate: '2024-06-01',
    parties: [
      { id: 'p7', name: 'David Johnson', role: 'defendant' },
      { id: 'p8', name: 'People of New York', role: 'plaintiff' },
    ],
    documents: [],
    courtDates: [],
    motions: [],
    assignedAttorney: 'Marcus A. Sintra',
    tags: ['criminal', 'fraud', 'defense'],
  },
  {
    id: 'case-005',
    caseNumber: '2023-CV-5512',
    title: 'TechCorp v. Sintra Consulting - IP Dispute',
    description: 'Intellectual property infringement counterclaim',
    status: 'filing',
    priority: 'medium',
    practiceArea: 'ip',
    court: 'U.S. District Court, E.D.N.Y.',
    courtLevel: 'federal_district',
    filingDate: '2023-11-20',
    nextDeadline: '2024-07-25',
    parties: [
      { id: 'p9', name: 'TechCorp Inc.', role: 'plaintiff', attorney: 'Wilson & Gates LLP' },
      { id: 'p10', name: 'Sintra Consulting LLC', role: 'defendant' },
    ],
    documents: [],
    courtDates: [],
    motions: [],
    assignedAttorney: 'Marcus A. Sintra',
    tags: ['IP', 'patent', 'trade secret'],
  },
];

export const useLegalStore = create<LegalState>()(
  devtools(
    (set) => ({
      cases: mockCases,
      activeCaseId: null,
      motions: [],
      caseLawResults: [],
      bookmarkedCases: [],
      alerts: [],
      caseLawQuery: '',
      selectedPracticeAreas: [],
      selectedJurisdiction: 'all',
      isLoadingCases: false,
      isLoadingCaseLaw: false,

      setCases: (cases) => set({ cases }),
      addCase: (c) => set((state) => ({ cases: [c, ...state.cases] })),
      updateCase: (id, updates) =>
        set((state) => ({
          cases: state.cases.map((c) => (c.id === id ? { ...c, ...updates } : c)),
        })),
      setActiveCase: (id) => set({ activeCaseId: id }),
      setMotions: (motions) => set({ motions }),
      addMotion: (motion) => set((state) => ({ motions: [motion, ...state.motions] })),
      updateMotion: (id, updates) =>
        set((state) => ({
          motions: state.motions.map((m) => (m.id === id ? { ...m, ...updates } : m)),
        })),
      setCaseLawResults: (results) => set({ caseLawResults: results }),
      toggleBookmark: (caseLaw) =>
        set((state) => {
          const isBookmarked = state.bookmarkedCases.some((c) => c.id === caseLaw.id);
          return {
            bookmarkedCases: isBookmarked
              ? state.bookmarkedCases.filter((c) => c.id !== caseLaw.id)
              : [...state.bookmarkedCases, { ...caseLaw, bookmarked: true }],
          };
        }),
      setAlerts: (alerts) => set({ alerts }),
      markAlertRead: (id) =>
        set((state) => ({
          alerts: state.alerts.map((a) => (a.id === id ? { ...a, read: true } : a)),
        })),
      setCaseLawQuery: (query) => set({ caseLawQuery: query }),
      setSelectedPracticeAreas: (areas) => set({ selectedPracticeAreas: areas }),
      setSelectedJurisdiction: (jurisdiction) => set({ selectedJurisdiction: jurisdiction }),
      setLoadingCases: (loading) => set({ isLoadingCases: loading }),
      setLoadingCaseLaw: (loading) => set({ isLoadingCaseLaw: loading }),
    }),
    { name: 'SintraPrime LegalStore' }
  )
);
