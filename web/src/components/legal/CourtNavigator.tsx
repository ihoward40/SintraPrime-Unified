import { useState } from 'react';
import { clsx } from 'clsx';

const courtHierarchy = [
  {
    level: 0,
    name: 'Supreme Court of the United States',
    abbr: 'SCOTUS',
    color: '#D4AF37',
    description: '9 Justices. Final interpreter of federal law and Constitution.',
  },
  {
    level: 1,
    name: 'U.S. Courts of Appeals (13 Circuits)',
    abbr: 'Circuit Courts',
    color: '#8B5CF6',
    description: '1st through 11th Circuits, D.C. Circuit, Federal Circuit. Reviews district court decisions.',
  },
  {
    level: 2,
    name: 'U.S. District Courts (94 Districts)',
    abbr: 'District Courts',
    color: '#3B82F6',
    description: 'General trial courts of the federal system. Original jurisdiction over federal cases.',
  },
  {
    level: 3,
    name: 'Specialized Federal Courts',
    abbr: 'Special Courts',
    color: '#10B981',
    description: 'Bankruptcy courts, tax courts, immigration courts, court of federal claims.',
  },
];

const stateHierarchy = [
  {
    level: 0,
    name: 'State Supreme Court',
    abbr: 'State High Court',
    color: '#F43F5E',
    description: 'Highest court in the state. Final authority on state law.',
  },
  {
    level: 1,
    name: 'Intermediate Appellate Courts',
    abbr: 'Appeals Division',
    color: '#F59E0B',
    description: 'Appellate Division, Appellate Term. Reviews trial court decisions.',
  },
  {
    level: 2,
    name: 'State Trial Courts',
    abbr: 'Supreme Court (NY)',
    color: '#64748B',
    description: 'In NY, the Supreme Court is actually the general trial court. Civil, criminal, family matters.',
  },
  {
    level: 3,
    name: 'Local Courts',
    abbr: 'City / District Courts',
    color: '#475569',
    description: 'Small claims, housing courts, city courts, town/village courts.',
  },
];

export default function CourtNavigator() {
  const [selected, setSelected] = useState<'federal' | 'state'>('federal');
  const hierarchy = selected === 'federal' ? courtHierarchy : stateHierarchy;

  return (
    <div>
      <div className="flex gap-2 mb-4">
        {(['federal', 'state'] as const).map((s) => (
          <button
            key={s}
            onClick={() => setSelected(s)}
            className={clsx(
              'px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all',
              selected === s
                ? 'bg-gold/20 text-gold border border-gold/40'
                : 'bg-slate-800/50 text-slate-400 hover:text-slate-200 border border-transparent'
            )}
          >
            {s} Courts
          </button>
        ))}
      </div>

      <div className="space-y-2">
        {hierarchy.map((court, i) => (
          <div key={i} className="flex items-start gap-3" style={{ paddingLeft: court.level * 16 }}>
            {i < hierarchy.length - 1 && (
              <div className="flex flex-col items-center mt-1">
                <div className="w-2 h-2 rounded-full mt-1.5" style={{ background: court.color }} />
                <div className="w-px flex-1 mt-1" style={{ background: court.color + '30', minHeight: 24 }} />
              </div>
            )}
            {i === hierarchy.length - 1 && (
              <div className="w-2 h-2 rounded-full mt-2.5 flex-shrink-0" style={{ background: court.color }} />
            )}
            <div className="flex-1 p-2.5 rounded-xl border hover:bg-slate-800/30 transition-colors cursor-pointer" style={{ borderColor: court.color + '30' }}>
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-xs font-bold" style={{ color: court.color }}>{court.abbr}</span>
                <div className="text-[10px] font-medium text-slate-400 bg-slate-800/50 px-2 py-0.5 rounded-full">Level {i + 1}</div>
              </div>
              <p className="text-xs font-semibold text-slate-300">{court.name}</p>
              <p className="text-[10px] text-slate-500 mt-0.5">{court.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
