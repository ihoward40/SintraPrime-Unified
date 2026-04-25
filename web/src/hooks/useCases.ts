import { useLegalStore } from '../store/legalStore';
import type { Case, CaseStatus } from '../types/legal';

export function useCases() {
  const { cases, activeCaseId, setActiveCase, updateCase } = useLegalStore();

  const getCase = (id: string) => cases.find((c) => c.id === id);
  const activeCase = activeCaseId ? getCase(activeCaseId) : null;

  const casesByStatus = (status: CaseStatus) => cases.filter((c) => c.status === status);

  const upcomingDeadlines = cases
    .filter((c) => c.nextDeadline && c.status !== 'closed')
    .sort((a, b) => {
      if (!a.nextDeadline || !b.nextDeadline) return 0;
      return new Date(a.nextDeadline).getTime() - new Date(b.nextDeadline).getTime();
    })
    .slice(0, 5);

  const stats = {
    total: cases.length,
    active: cases.filter((c) => c.status !== 'closed').length,
    byStatus: {
      intake: casesByStatus('intake').length,
      research: casesByStatus('research').length,
      drafting: casesByStatus('drafting').length,
      filing: casesByStatus('filing').length,
      monitoring: casesByStatus('monitoring').length,
      closed: casesByStatus('closed').length,
    },
    critical: cases.filter((c) => c.priority === 'critical').length,
    highValue: cases.filter((c) => (c.estimatedValue || 0) > 1000000).length,
  };

  const moveCase = (id: string, newStatus: CaseStatus) => {
    updateCase(id, { status: newStatus });
  };

  return {
    cases,
    activeCase,
    activeCaseId,
    setActiveCase,
    getCase,
    casesByStatus,
    upcomingDeadlines,
    stats,
    moveCase,
  };
}

export function useCaseSearch(query: string, filters?: { status?: CaseStatus; practiceArea?: string }) {
  const { cases } = useLegalStore();

  const filtered = cases.filter((c: Case) => {
    const matchesQuery =
      !query ||
      c.title.toLowerCase().includes(query.toLowerCase()) ||
      c.caseNumber.toLowerCase().includes(query.toLowerCase()) ||
      c.description?.toLowerCase().includes(query.toLowerCase());

    const matchesStatus = !filters?.status || c.status === filters.status;
    const matchesPracticeArea = !filters?.practiceArea || c.practiceArea === filters.practiceArea;

    return matchesQuery && matchesStatus && matchesPracticeArea;
  });

  return filtered;
}
