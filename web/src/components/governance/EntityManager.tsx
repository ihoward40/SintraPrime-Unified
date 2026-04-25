import { useState } from 'react';
import { Building2, ChevronRight, Plus, CheckCircle, AlertCircle } from 'lucide-react';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import { clsx } from 'clsx';
import type { Entity } from '../../types/governance';

const mockEntities: Entity[] = [
  {
    id: 'e1',
    name: 'SintraPrime Holdings LLC',
    type: 'LLC',
    state: 'Delaware',
    formed: '2020-03-15',
    status: 'active',
    registeredAgent: 'CT Corporation System',
    ein: '84-XXXXXXX',
    parentEntityId: undefined,
    childEntityIds: ['e2', 'e3', 'e4'],
    nextFilingDue: '2025-03-01',
    officers: [
      { name: 'John D. Plaintiff', title: 'Manager', since: '2020-03-15' },
    ],
    assets: [],
    complianceStatus: 'compliant',
    annualReportFiled: true,
  },
  {
    id: 'e2',
    name: 'SintraPrime Legal PLLC',
    type: 'PLLC',
    state: 'New York',
    formed: '2020-06-01',
    status: 'active',
    registeredAgent: 'John D. Plaintiff',
    ein: '85-XXXXXXX',
    parentEntityId: 'e1',
    childEntityIds: [],
    nextFilingDue: '2025-06-30',
    officers: [
      { name: 'John D. Plaintiff', title: 'Managing Member', since: '2020-06-01' },
    ],
    assets: [],
    complianceStatus: 'compliant',
    annualReportFiled: true,
  },
  {
    id: 'e3',
    name: 'Prime Capital Management LLC',
    type: 'LLC',
    state: 'Wyoming',
    formed: '2021-01-20',
    status: 'active',
    registeredAgent: 'Wyoming Registered Agent',
    ein: '86-XXXXXXX',
    parentEntityId: 'e1',
    childEntityIds: [],
    nextFilingDue: '2025-01-31',
    officers: [],
    assets: [],
    complianceStatus: 'attention_needed',
    annualReportFiled: false,
  },
  {
    id: 'e4',
    name: 'SintraPrime Family Trust',
    type: 'Trust',
    state: 'Nevada',
    formed: '2022-07-10',
    status: 'active',
    registeredAgent: 'N/A',
    ein: '87-XXXXXXX',
    parentEntityId: 'e1',
    childEntityIds: [],
    nextFilingDue: '2025-04-15',
    officers: [
      { name: 'John D. Plaintiff', title: 'Trustee', since: '2022-07-10' },
    ],
    assets: [],
    complianceStatus: 'compliant',
    annualReportFiled: true,
  },
];

const typeColors: Record<string, string> = {
  LLC: 'blue',
  PLLC: 'purple',
  Corp: 'gold',
  Trust: 'amber',
  LP: 'green',
  LLP: 'slate',
};

interface EntityManagerProps {
  onSelect?: (entity: Entity) => void;
}

export default function EntityManager({ onSelect }: EntityManagerProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const handleSelect = (entity: Entity) => {
    setSelected(entity.id);
    onSelect?.(entity);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500">{mockEntities.length} entities under management</p>
        <Button size="sm" icon={Plus} variant="outline">Add Entity</Button>
      </div>

      <div className="space-y-2">
        {mockEntities.map((entity) => (
          <button
            key={entity.id}
            onClick={() => handleSelect(entity)}
            className={clsx(
              'w-full text-left p-3.5 rounded-xl border transition-all group',
              selected === entity.id
                ? 'border-gold/40 bg-gold/5'
                : 'border-slate-700/30 hover:border-slate-600/50 bg-slate-800/20'
            )}
          >
            <div className="flex items-center gap-3">
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ paddingLeft: entity.parentEntityId ? 8 : 0 }}
              >
                {entity.parentEntityId ? (
                  <div className="w-9 h-9 rounded-xl bg-slate-700/50 flex items-center justify-center">
                    <Building2 className="w-4 h-4 text-slate-400" />
                  </div>
                ) : (
                  <div className="w-9 h-9 rounded-xl bg-gold/15 flex items-center justify-center">
                    <Building2 className="w-4 h-4 text-gold" />
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-sm font-semibold text-slate-200">{entity.name}</p>
                  <Badge variant={typeColors[entity.type] as any} size="sm">{entity.type}</Badge>
                </div>
                <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-500">
                  <span>{entity.state}</span>
                  <span>·</span>
                  <span>EIN: {entity.ein}</span>
                  {entity.nextFilingDue && (
                    <>
                      <span>·</span>
                      <span>Due: {new Date(entity.nextFilingDue).toLocaleDateString()}</span>
                    </>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {entity.complianceStatus === 'compliant' ? (
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-amber-400" />
                )}
                <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors" />
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
