import { useState } from 'react';
import { Search, BookOpen, ChevronRight } from 'lucide-react';
import { clsx } from 'clsx';
import Badge from '../ui/Badge';

const trustDoctrines = [
  { name: 'Express Trust', category: 'Formation', description: 'Trust created by explicit declaration of intent. Requires settlor, trustee, beneficiary, and corpus.' },
  { name: 'Resulting Trust', category: 'Implied', description: 'Arises by operation of law when circumstances imply the parties intended a trust.' },
  { name: 'Constructive Trust', category: 'Equitable', description: 'Imposed by equity to prevent unjust enrichment. Not a true trust but an equitable remedy.' },
  { name: 'Charitable Trust', category: 'Purpose', description: 'Established for charitable purposes. Must benefit the public. Cy-pres doctrine applies.' },
  { name: 'Spendthrift Trust', category: 'Asset Protection', description: 'Prevents beneficiaries from transferring interest; protects against creditors. Widely recognized.' },
  { name: 'Discretionary Trust', category: 'Administration', description: 'Trustee has discretion over distributions. Strong protection from beneficiary creditors.' },
  { name: 'Revocable Living Trust', category: 'Estate Planning', description: 'Settlor retains right to revoke. Avoids probate. No asset protection during settlor lifetime.' },
  { name: 'Irrevocable Trust', category: 'Asset Protection', description: 'Cannot be changed once created. Provides tax benefits and creditor protection for settlor.' },
  { name: 'Dynasty Trust', category: 'Perpetual', description: 'Long-term trust designed to hold wealth for multiple generations. Avoids estate tax at each transfer.' },
  { name: 'Asset Protection Trust', category: 'Asset Protection', description: 'Self-settled trust in permitted jurisdictions. Protects settlor assets from future creditors.' },
  { name: 'Special Needs Trust', category: 'Special Purpose', description: 'Benefits disabled persons without disqualifying from government benefits. First-party and third-party.' },
  { name: 'Land Trust', category: 'Real Property', description: 'Holds title to real property. Provides privacy and facilitates transfers.' },
  { name: 'Business Trust (UBO)', category: 'Commercial', description: 'Trust formed to carry on business. May be taxed as corporation or partnership.' },
  { name: 'Totten Trust', category: 'Banking', description: 'Payable-on-death bank account. Revocable during lifetime, transfers at death without probate.' },
  { name: 'Blind Trust', category: 'Conflict Avoidance', description: 'Trustee manages assets without beneficiary direction. Used by public officials.' },
];

const categoryColors: Record<string, string> = {
  Formation: 'blue',
  Implied: 'amber',
  Equitable: 'purple',
  Purpose: 'green',
  'Asset Protection': 'gold',
  Administration: 'slate',
  'Estate Planning': 'gold',
  Perpetual: 'blue',
  'Special Purpose': 'green',
  'Real Property': 'amber',
  Commercial: 'purple',
  Banking: 'slate',
  'Conflict Avoidance': 'red',
};

interface TrustLawExplorerProps {
  compact?: boolean;
}

export default function TrustLawExplorer({ compact }: TrustLawExplorerProps) {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedDoctrine, setSelectedDoctrine] = useState<string | null>(null);

  const categories = [...new Set(trustDoctrines.map((d) => d.category))];

  const filtered = trustDoctrines.filter((d) => {
    const matchSearch = !search || d.name.toLowerCase().includes(search.toLowerCase()) || d.description.toLowerCase().includes(search.toLowerCase());
    const matchCat = !selectedCategory || d.category === selectedCategory;
    return matchSearch && matchCat;
  });

  const selected = trustDoctrines.find((d) => d.name === selectedDoctrine);

  return (
    <div>
      <div className="flex gap-2 mb-3">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search doctrines..."
            className="input-dark pl-8 py-1.5 text-sm"
          />
        </div>
      </div>

      {!compact && (
        <div className="flex gap-1.5 flex-wrap mb-3">
          <button
            onClick={() => setSelectedCategory(null)}
            className={clsx(
              'px-2 py-1 rounded-lg text-[10px] font-medium transition-all',
              !selectedCategory ? 'bg-gold/20 text-gold' : 'bg-slate-800/50 text-slate-500 hover:text-slate-300'
            )}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
              className={clsx(
                'px-2 py-1 rounded-lg text-[10px] font-medium transition-all',
                selectedCategory === cat ? 'bg-gold/20 text-gold' : 'bg-slate-800/50 text-slate-500 hover:text-slate-300'
              )}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-2 max-h-80 overflow-y-auto pr-1">
        {filtered.map((doctrine) => (
          <button
            key={doctrine.name}
            onClick={() => setSelectedDoctrine(selectedDoctrine === doctrine.name ? null : doctrine.name)}
            className={clsx(
              'text-left p-3 rounded-xl border transition-all',
              selectedDoctrine === doctrine.name
                ? 'border-gold/40 bg-gold/5'
                : 'border-slate-700/30 hover:border-slate-600/50 bg-slate-800/20'
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BookOpen className="w-3.5 h-3.5 text-gold" />
                <span className="text-xs font-semibold text-slate-200">{doctrine.name}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Badge variant={categoryColors[doctrine.category] as any} size="sm">{doctrine.category}</Badge>
                <ChevronRight className={clsx('w-3.5 h-3.5 text-slate-600 transition-transform', selectedDoctrine === doctrine.name && 'rotate-90')} />
              </div>
            </div>
            {selectedDoctrine === doctrine.name && (
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">{doctrine.description}</p>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
