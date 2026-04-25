import { useState } from 'react';
import { DollarSign, ExternalLink, Filter, Star } from 'lucide-react';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import { clsx } from 'clsx';

export interface FundingOpportunity {
  id: string;
  name: string;
  type: 'grant' | 'loan' | 'sbir' | 'vc' | 'sba' | 'cdfis' | 'angel' | 'crowdfunding';
  amount: { min: number; max: number };
  deadline?: string;
  eligibility: string[];
  description: string;
  match: number;
  isBookmarked?: boolean;
}

const fundingTypes = ['all', 'grant', 'loan', 'sbir', 'sba', 'vc', 'angel'];

const typeColors: Record<string, string> = {
  grant: 'green',
  loan: 'blue',
  sbir: 'purple',
  vc: 'gold',
  sba: 'amber',
  cdfis: 'blue',
  angel: 'purple',
  crowdfunding: 'slate',
};

function formatAmount(min: number, max: number) {
  const fmt = (n: number) => n >= 1000000 ? `$${(n / 1000000).toFixed(1)}M` : `$${(n / 1000).toFixed(0)}K`;
  if (min === max) return fmt(min);
  return `${fmt(min)} - ${fmt(max)}`;
}

export default function FundingOpportunities({ opportunities }: { opportunities: FundingOpportunity[] }) {
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  const filtered = opportunities.filter((opp) => {
    const matchType = filter === 'all' || opp.type === filter;
    const matchSearch = !search || opp.name.toLowerCase().includes(search.toLowerCase());
    return matchType && matchSearch;
  });

  return (
    <div className="space-y-3">
      {/* Controls */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Search opportunities..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-dark flex-1 py-1.5 text-sm"
        />
      </div>

      <div className="flex gap-1.5 flex-wrap">
        {fundingTypes.map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={clsx(
              'px-2.5 py-1 rounded-lg text-xs font-medium transition-all capitalize',
              filter === t
                ? 'bg-gold/20 text-gold border border-gold/40'
                : 'bg-slate-800/50 text-slate-400 hover:text-slate-200 border border-transparent'
            )}
          >
            {t === 'sbir' ? 'SBIR' : t === 'sba' ? 'SBA' : t}
          </button>
        ))}
      </div>

      <p className="text-xs text-slate-500">{filtered.length} opportunities found</p>

      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
        {filtered.map((opp) => (
          <div
            key={opp.id}
            className="p-3 bg-slate-800/30 rounded-xl border border-slate-700/30 hover:border-slate-600/50 transition-all group"
          >
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-gold/10 flex items-center justify-center flex-shrink-0">
                <DollarSign className="w-4 h-4 text-gold" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200 leading-tight">{opp.name}</h4>
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{opp.description}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-sm font-bold text-emerald-400 whitespace-nowrap">
                      {formatAmount(opp.amount.min, opp.amount.max)}
                    </div>
                    {opp.deadline && (
                      <div className="text-[10px] text-slate-500 mt-0.5">Due: {opp.deadline}</div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <Badge variant={typeColors[opp.type] as any} size="sm" className="capitalize">{opp.type}</Badge>
                  <div className="flex items-center gap-1">
                    <div className="h-1 w-16 bg-slate-700 rounded-full overflow-hidden">
                      <div className="h-full bg-gold rounded-full" style={{ width: `${opp.match}%` }} />
                    </div>
                    <span className="text-[10px] text-slate-500">{opp.match}% match</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-2 mt-2 pt-2 border-t border-slate-700/30">
              <Button size="sm" variant="outline" className="flex-1 text-xs">Apply Now</Button>
              <button className="p-1.5 rounded-lg hover:bg-slate-700/50 text-slate-500 hover:text-gold transition-colors">
                <Star className="w-3.5 h-3.5" />
              </button>
              <button className="p-1.5 rounded-lg hover:bg-slate-700/50 text-slate-500 hover:text-slate-300 transition-colors">
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
