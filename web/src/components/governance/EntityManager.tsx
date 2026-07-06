import { useState } from 'react';
import { Building2, ChevronRight, Plus, CheckCircle, AlertCircle } from 'lucide-react';
import Badge, { type BadgeVariant } from '../ui/Badge';
import Button from '../ui/Button';
import { clsx } from 'clsx';
import type { Entity, EntityType } from '../../types/governance';

const mockEntities: Entity[] = [
  {
    id: 'e1',
    name: 'SintraPrime Holdings LLC',
    type: 'llc',
    state: 'Delaware',
    formationDate: '2020-03-15',
    status: 'active',
    registeredAgent: {
      name: 'CT Corporation System',
      address: '1209 Orange Street',
      city: 'Wilmington',
      state: 'DE',
      zip: '19801',
    },
    ein: '84-XXXXXXX',
    parentId: undefined,
    subsidiaries: ['e2', 'e3', 'e4'],
    officers: [
      { id: 'o1', name: 'John D. Plaintiff', title: 'Manager', startDate: '2020-03-15' },
    ],
    assets: [],
    complianceItems: [],
    filings: [],
    documents: [],
    notes: 'Parent holding entity',
  },
  {
    id: 'e2',
    name: 'SintraPrime Legal PLLC',
    type: 'llc',
    state: 'New York',
    formationDate: '2020-06-01',
    status: 'active',
    registeredAgent: {
      name: 'John D. Plaintiff',
      address: 'One Liberty Plaza',
      city: 'New York',
      state: 'NY',
      zip: '10006',
    },
    ein: '85-XXXXXXX',
    parentId: 'e1',
    subsidiaries: [],
    officers: [
      { id: 'o2', name: 'John D. Plaintiff', title: 'Managing Member', startDate: '2020-06-01' },
    ],
    assets: [],
    complianceItems: [],
    filings: [],
    documents: [],
    notes: 'Law practice subsidiary',
  },
  {
    id: 'e3',
    name: 'Prime Capital Management LLC',
    type: 'llc',
    state: 'Wyoming',
    formationDate: '2021-01-20',
    status: 'active',
    registeredAgent: {
      name: 'Wyoming Registered Agent',
      address: '1623 Central Avenue',
      city: 'Cheyenne',
      state: 'WY',
      zip: '82001',
    },
    ein: '86-XXXXXXX',
    parentId: 'e1',
    subsidiaries: [],
    officers: [],
    assets: [],
    complianceItems: [],
    filings: [],
    documents: [],
    notes: 'Compliance attention needed',
  },
  {
    id: 'e4',
    name: 'SintraPrime Family Trust',
    type: 'trust',
    state: 'Nevada',
    formationDate: '2022-07-10',
    status: 'active',
    registeredAgent: {
      name: 'N/A',
      address: '123 Las Vegas Blvd',
      city: 'Las Vegas',
      state: 'NV',
      zip: '89101',
    },
    ein: '87-XXXXXXX',
    parentId: 'e1',
    subsidiaries: [],
    officers: [
      { id: 'o3', name: 'John D. Plaintiff', title: 'Trustee', startDate: '2022-07-10' },
    ],
    assets: [],
    complianceItems: [],
    filings: [],
    documents: [],
    notes: 'Family trust subsidiary',
  },
];

const typeColors: Record<EntityType, BadgeVariant> = {
  llc: 'blue',
  corporation: 'gold',
  trust: 'amber',
  partnership: 'green',
  sole_proprietorship: 'slate',
  nonprofit: 'green',
  foundation: 'purple',
  land_trust: 'amber',
  business_trust: 'amber',
  statutory_trust: 'amber',
};

interface EntityManagerProps {
  onSelect?: (entity: Entity) => void;
}

const getComplianceStatus = (entity: Entity): 'compliant' | 'attention_needed' => {
  return entity.notes?.toLowerCase().includes('attention needed') ? 'attention_needed' : 'compliant';
};

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
                style={{ paddingLeft: entity.parentId ? 8 : 0 }}
              >
                {entity.parentId ? (
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
                  <Badge variant={typeColors[entity.type]} size="sm">{entity.type}</Badge>
                </div>
                <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-500">
                  <span>{entity.state}</span>
                  <span>·</span>
                  <span>EIN: {entity.ein}</span>
                  <span>·</span>
                  <span>Formed: {new Date(entity.formationDate).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {getComplianceStatus(entity) === 'compliant' ? (
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
