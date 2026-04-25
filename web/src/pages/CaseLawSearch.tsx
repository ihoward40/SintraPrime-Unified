import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  BookOpen,
  Star,
  Bell,
  ExternalLink,
  Filter,
  ChevronRight,
  Network,
  Bookmark,
  BookMarked,
  Scale,
  Clock,
  Hash,
} from 'lucide-react';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { useLegalStore } from '../store/legalStore';
import { clsx } from 'clsx';
import type { CaseLaw } from '../types/legal';

// Mock case law results
const mockResults: CaseLaw[] = [
  {
    id: 'cl-001',
    citation: '347 U.S. 483 (1954)',
    title: 'Brown v. Board of Education',
    court: 'U.S. Supreme Court',
    year: 1954,
    jurisdiction: 'Federal',
    practiceAreas: ['civil_rights', 'constitutional'],
    summary: 'Racial segregation in public schools is unconstitutional under the Equal Protection Clause of the Fourteenth Amendment.',
    holding: 'Separate educational facilities are inherently unequal and violate the Equal Protection Clause.',
    relevanceScore: 98,
    citedBy: ['Parents Involved in Community Schools v. Seattle School District', 'Grutter v. Bollinger'],
    cites: ['Plessy v. Ferguson', 'Sweatt v. Painter'],
    tags: ['equal protection', 'segregation', 'education', 'fourteenth amendment'],
    bookmarked: false,
  },
  {
    id: 'cl-002',
    citation: '384 U.S. 436 (1966)',
    title: 'Miranda v. Arizona',
    court: 'U.S. Supreme Court',
    year: 1966,
    jurisdiction: 'Federal',
    practiceAreas: ['criminal_defense', 'constitutional'],
    summary: 'The prosecution may not use statements stemming from custodial interrogation of the defendant unless it demonstrates the use of procedural safeguards to secure the privilege against self-incrimination.',
    holding: 'Suspects must be informed of their rights before custodial interrogation.',
    relevanceScore: 95,
    citedBy: ['Berghuis v. Thompkins', 'Salinas v. Texas'],
    cites: ['Escobedo v. Illinois', 'Malloy v. Hogan'],
    tags: ['miranda rights', 'fifth amendment', 'custody', 'interrogation'],
    bookmarked: true,
  },
  {
    id: 'cl-003',
    citation: '42 U.S.C. § 3604',
    title: 'Texas Dept. of Housing v. Inclusive Communities Project',
    court: 'U.S. Supreme Court',
    year: 2015,
    jurisdiction: 'Federal',
    practiceAreas: ['civil_rights'],
    summary: 'Disparate impact claims are cognizable under the Fair Housing Act.',
    holding: 'Statistical evidence of discriminatory effect sufficient to establish FHA violation without discriminatory intent.',
    relevanceScore: 91,
    citedBy: ['Avenue 6E Investments v. City of Yuma', 'Reinhart v. Lincoln County'],
    cites: ['Griggs v. Duke Power Co.', 'Smith v. City of Jackson'],
    tags: ['fair housing', 'disparate impact', 'discrimination', 'housing'],
    bookmarked: false,
  },
  {
    id: 'cl-004',
    citation: '438 U.S. 104 (1978)',
    title: 'Penn Central Transportation Co. v. New York City',
    court: 'U.S. Supreme Court',
    year: 1978,
    jurisdiction: 'Federal',
    practiceAreas: ['constitutional', 'property'],
    summary: 'Three-factor test for regulatory takings: economic impact, interference with investment-backed expectations, character of government action.',
    holding: 'Landmark preservation law applied to Grand Central Terminal did not constitute a taking.',
    relevanceScore: 87,
    citedBy: ['Lucas v. South Carolina Coastal Council', 'Palazzolo v. Rhode Island'],
    cites: ['Euclid v. Ambler Realty', 'Nectow v. City of Cambridge'],
    tags: ['takings', 'regulatory', 'property rights', 'fifth amendment'],
    bookmarked: false,
  },
  {
    id: 'cl-005',
    citation: '126 S. Ct. 2749 (2006)',
    title: 'Hamdan v. Rumsfeld',
    court: 'U.S. Supreme Court',
    year: 2006,
    jurisdiction: 'Federal',
    practiceAreas: ['constitutional', 'criminal_defense'],
    summary: 'Military commissions established to try detainees at Guantanamo Bay violated the UCMJ and Geneva Conventions.',
    holding: 'President lacks authority to establish military commissions without Congressional authorization.',
    relevanceScore: 82,
    citedBy: ['Boumediene v. Bush', 'Al-Bihani v. Obama'],
    cites: ['Ex parte Quirin', 'Hamdi v. Rumsfeld'],
    tags: ['habeas corpus', 'military commissions', 'war on terror', 'separation of powers'],
    bookmarked: false,
  },
  {
    id: 'cl-006',
    citation: '17 N.Y.2d 460 (1966)',
    title: 'Henningsen v. Bloomfield Motors',
    court: 'New Jersey Supreme Court',
    year: 1966,
    jurisdiction: 'New Jersey',
    practiceAreas: ['tort', 'contract'],
    summary: 'Manufacturer warranty disclaimer in automobile sales contract was unconscionable and unenforceable on public policy grounds.',
    holding: 'Implied warranty of merchantability runs to ultimate purchaser; disclaimer void.',
    relevanceScore: 79,
    citedBy: ['MacPherson v. Buick Motor Co.', 'Greenman v. Yuba Power Products'],
    cites: ['MacPherson v. Buick Motor Co.'],
    tags: ['products liability', 'warranty', 'unconscionability', 'automobile'],
    bookmarked: false,
  },
];

const practiceAreaOptions = [
  { value: 'all', label: 'All Areas' },
  { value: 'civil_rights', label: 'Civil Rights' },
  { value: 'criminal_defense', label: 'Criminal Defense' },
  { value: 'constitutional', label: 'Constitutional' },
  { value: 'contract', label: 'Contract' },
  { value: 'tort', label: 'Tort' },
  { value: 'property', label: 'Property' },
  { value: 'trust', label: 'Trust Law' },
  { value: 'bankruptcy', label: 'Bankruptcy' },
  { value: 'ip', label: 'IP' },
];

const jurisdictionOptions = [
  'All Jurisdictions', 'Federal', 'U.S. Supreme Court', '1st Circuit', '2nd Circuit',
  '9th Circuit', 'New York', 'California', 'Texas', 'Delaware', 'Florida',
];

export default function CaseLawSearch() {
  const { bookmarkedCases, toggleBookmark } = useLegalStore();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<CaseLaw[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedCase, setSelectedCase] = useState<CaseLaw | null>(null);
  const [practiceArea, setPracticeArea] = useState('all');
  const [jurisdiction, setJurisdiction] = useState('All Jurisdictions');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [sortBy, setSortBy] = useState<'relevance' | 'date' | 'citations'>('relevance');
  const [activeTab, setActiveTab] = useState<'search' | 'bookmarks'>('search');
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);
    setHasSearched(true);
    setSelectedCase(null);
    await new Promise((r) => setTimeout(r, 900));
    let filtered = mockResults.filter((c) =>
      c.title.toLowerCase().includes(query.toLowerCase()) ||
      c.summary.toLowerCase().includes(query.toLowerCase()) ||
      c.tags.some((t) => t.toLowerCase().includes(query.toLowerCase())) ||
      c.citation.toLowerCase().includes(query.toLowerCase())
    );
    if (practiceArea !== 'all') {
      filtered = filtered.filter((c) => c.practiceAreas.includes(practiceArea as CaseLaw['practiceAreas'][0]));
    }
    if (jurisdiction !== 'All Jurisdictions') {
      filtered = filtered.filter((c) => c.jurisdiction === jurisdiction || c.court.includes(jurisdiction));
    }
    setResults(filtered.length > 0 ? filtered : mockResults);
    setIsSearching(false);
  };

  const isBookmarked = (id: string) => bookmarkedCases.some((c) => c.id === id);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Case Law Search</h1>
          <p className="text-slate-500 text-sm mt-1">Search millions of federal and state court decisions</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="green" dot>CourtListener: Connected</Badge>
          <Badge variant="blue" dot>PACER: Active</Badge>
        </div>
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch}>
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Search by case name, citation, topic, or legal concept... e.g. "disparate impact housing discrimination"'
            className="input-dark pl-12 pr-32 py-3.5 text-base"
          />
          <button
            type="submit"
            className="absolute right-2 top-1/2 -translate-y-1/2 btn-gold text-sm px-4 py-2"
          >
            Search
          </button>
        </div>
      </form>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <select value={practiceArea} onChange={(e) => setPracticeArea(e.target.value)} className="input-dark w-auto text-sm py-2">
          {practiceAreaOptions.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} className="input-dark w-auto text-sm py-2">
          {jurisdictionOptions.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <input type="number" placeholder="From year" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="input-dark w-28 text-sm py-2" />
        <input type="number" placeholder="To year" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="input-dark w-28 text-sm py-2" />
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value as typeof sortBy)} className="input-dark w-auto text-sm py-2">
          <option value="relevance">Sort: Relevance</option>
          <option value="date">Sort: Newest</option>
          <option value="citations">Sort: Most Cited</option>
        </select>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-slate-900/60 border border-slate-700/40 rounded-xl w-fit">
        {[
          { id: 'search', label: 'Search Results' },
          { id: 'bookmarks', label: `Saved (${bookmarkedCases.length})` },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab.id ? 'bg-gold/15 text-gold border border-gold/30' : 'text-slate-400 hover:text-slate-200'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main content */}
      {isSearching ? (
        <div className="flex items-center justify-center h-48">
          <LoadingSpinner size="lg" label="Searching case law databases..." />
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
          {/* Results list */}
          <div className="xl:col-span-2 space-y-3">
            {activeTab === 'search' && (
              <>
                {hasSearched && (
                  <p className="text-sm text-slate-500">{results.length} results for "{query}"</p>
                )}
                {!hasSearched && (
                  <div className="space-y-3">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Featured Cases</p>
                    {mockResults.slice(0, 4).map((c, i) => (
                      <ResultCard key={c.id} c={c} i={i} onSelect={setSelectedCase} selected={selectedCase?.id === c.id} bookmarked={isBookmarked(c.id)} onBookmark={() => toggleBookmark(c)} />
                    ))}
                  </div>
                )}
                {hasSearched && results.map((c, i) => (
                  <ResultCard key={c.id} c={c} i={i} onSelect={setSelectedCase} selected={selectedCase?.id === c.id} bookmarked={isBookmarked(c.id)} onBookmark={() => toggleBookmark(c)} />
                ))}
                {hasSearched && results.length === 0 && (
                  <div className="py-12 text-center text-slate-500">
                    <Search className="w-10 h-10 mx-auto mb-3 opacity-30" />
                    <p>No results found for "{query}"</p>
                  </div>
                )}
              </>
            )}
            {activeTab === 'bookmarks' && (
              <>
                {bookmarkedCases.length === 0 ? (
                  <div className="py-12 text-center text-slate-500">
                    <Bookmark className="w-10 h-10 mx-auto mb-3 opacity-30" />
                    <p>No saved cases yet</p>
                    <p className="text-xs mt-1">Bookmark cases from search results</p>
                  </div>
                ) : (
                  bookmarkedCases.map((c, i) => (
                    <ResultCard key={c.id} c={c} i={i} onSelect={setSelectedCase} selected={selectedCase?.id === c.id} bookmarked={true} onBookmark={() => toggleBookmark(c)} />
                  ))
                )}
              </>
            )}
          </div>

          {/* Case detail */}
          <div className="xl:col-span-3">
            <AnimatePresence mode="wait">
              {selectedCase ? (
                <motion.div
                  key={selectedCase.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className="sticky top-6"
                >
                  <Card padding="lg">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <div className="flex flex-wrap gap-2 mb-2">
                          {selectedCase.practiceAreas.map((area) => (
                            <Badge key={area} variant="gold" size="sm">{area.replace(/_/g, ' ')}</Badge>
                          ))}
                          <Badge variant="slate" size="sm">{selectedCase.jurisdiction}</Badge>
                        </div>
                        <h2 className="text-lg font-bold text-slate-100">{selectedCase.title}</h2>
                        <p className="text-sm text-gold font-mono mt-1">{selectedCase.citation}</p>
                        <p className="text-sm text-slate-500 mt-0.5">{selectedCase.court} · {selectedCase.year}</p>
                      </div>
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => toggleBookmark(selectedCase)}
                          className={clsx('p-2 rounded-lg transition-colors', isBookmarked(selectedCase.id) ? 'text-gold bg-gold/10' : 'text-slate-500 hover:text-gold hover:bg-gold/5')}
                        >
                          <BookMarked className={clsx('w-4 h-4', isBookmarked(selectedCase.id) && 'fill-gold')} />
                        </button>
                        <button className="p-2 rounded-lg text-slate-500 hover:text-blue-400 hover:bg-blue-500/5 transition-colors">
                          <Bell className="w-4 h-4" />
                        </button>
                        <button className="p-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-700/30 transition-colors">
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {selectedCase.relevanceScore && (
                      <div className="flex items-center gap-2 mb-4 p-2 bg-gold/5 border border-gold/20 rounded-lg">
                        <Scale className="w-4 h-4 text-gold" />
                        <span className="text-xs text-gold font-medium">Relevance Score: {selectedCase.relevanceScore}%</span>
                      </div>
                    )}

                    <div className="space-y-4">
                      <div>
                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Holding</h4>
                        <p className="text-sm text-slate-200 leading-relaxed font-medium">{selectedCase.holding}</p>
                      </div>
                      <div>
                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Summary</h4>
                        <p className="text-sm text-slate-400 leading-relaxed">{selectedCase.summary}</p>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Cited By ({selectedCase.citedBy.length})</h4>
                          <ul className="space-y-1">
                            {selectedCase.citedBy.map((c) => (
                              <li key={c} className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 cursor-pointer">
                                <ChevronRight className="w-3 h-3 flex-shrink-0" />
                                <span className="truncate">{c}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Cites ({selectedCase.cites.length})</h4>
                          <ul className="space-y-1">
                            {selectedCase.cites.map((c) => (
                              <li key={c} className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 cursor-pointer">
                                <ChevronRight className="w-3 h-3 flex-shrink-0" />
                                <span className="truncate">{c}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      <div>
                        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Tags</h4>
                        <div className="flex flex-wrap gap-1.5">
                          {selectedCase.tags.map((tag) => (
                            <Badge key={tag} variant="slate" size="sm">{tag}</Badge>
                          ))}
                        </div>
                      </div>

                      <div className="flex gap-2 pt-2">
                        <Button fullWidth variant="gold" icon={Scale}>Apply to Case</Button>
                        <Button fullWidth variant="outline" icon={Network}>Citation Network</Button>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="h-64 flex items-center justify-center border border-dashed border-slate-800 rounded-2xl"
                >
                  <div className="text-center text-slate-600">
                    <BookOpen className="w-10 h-10 mx-auto mb-3 opacity-30" />
                    <p className="text-sm">Select a case to view details</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      )}
    </div>
  );
}

function ResultCard({
  c,
  i,
  onSelect,
  selected,
  bookmarked,
  onBookmark,
}: {
  c: CaseLaw;
  i: number;
  onSelect: (c: CaseLaw) => void;
  selected: boolean;
  bookmarked: boolean;
  onBookmark: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.05 }}
      onClick={() => onSelect(c)}
      className={clsx(
        'glass-card p-4 cursor-pointer transition-all duration-200 hover:-translate-y-0.5',
        selected && 'border-gold/40 bg-gold/5'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {c.relevanceScore && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 bg-gold/15 text-gold rounded-md">{c.relevanceScore}%</span>
            )}
            <span className="text-[10px] text-slate-500 font-mono truncate">{c.citation}</span>
          </div>
          <h3 className="text-sm font-semibold text-slate-200 leading-snug">{c.title}</h3>
          <p className="text-xs text-slate-500 mt-0.5">{c.court} · {c.year}</p>
          <p className="text-xs text-slate-400 mt-1.5 line-clamp-2">{c.summary}</p>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onBookmark(); }}
          className={clsx('flex-shrink-0 p-1 rounded-md transition-colors', bookmarked ? 'text-gold' : 'text-slate-600 hover:text-gold')}
        >
          <BookMarked className={clsx('w-3.5 h-3.5', bookmarked && 'fill-gold')} />
        </button>
      </div>
      <div className="flex flex-wrap gap-1 mt-2">
        {c.practiceAreas.slice(0, 2).map((area) => (
          <Badge key={area} variant="slate" size="sm">{area.replace(/_/g, ' ')}</Badge>
        ))}
        {c.practiceAreas.length > 2 && (
          <Badge variant="slate" size="sm">+{c.practiceAreas.length - 2}</Badge>
        )}
      </div>
    </motion.div>
  );
}
