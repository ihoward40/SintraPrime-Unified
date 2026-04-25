import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Building2,
  Plus,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  Calendar,
  MapPin,
  Users,
  FileText,
  Shield,
  Clock,
} from 'lucide-react';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { clsx } from 'clsx';
import { format } from 'date-fns';

const entities = [
  {
    id: 'e1', name: 'SintraPrime Law & Financial Group LLC', type: 'llc', status: 'active', state: 'New York',
    formation: '2018-03-15', ein: '82-1234567',
    registeredAgent: 'CT Corporation System, 28 Liberty St, New York, NY 10005',
    officers: [{ name: 'Marcus A. Sintra', title: 'Managing Member', ownership: 100 }],
    children: ['e2', 'e3', 'e5'],
    compliance: { nextDue: '2025-03-31', status: 'current' },
  },
  {
    id: 'e2', name: 'Sintra Holdings LLC', type: 'llc', status: 'active', state: 'Delaware',
    formation: '2019-07-22', ein: '84-7654321',
    registeredAgent: 'Registered Agent Solutions, 9 E Loockerman St, Dover, DE 19901',
    officers: [{ name: 'Marcus A. Sintra', title: 'Member', ownership: 100 }],
    children: ['e4'],
    parent: 'e1',
    compliance: { nextDue: '2025-06-01', status: 'current' },
  },
  {
    id: 'e3', name: 'Sintra Consulting LLC', type: 'llc', status: 'active', state: 'Nevada',
    formation: '2020-01-10', ein: '85-9876543',
    registeredAgent: 'Nevada Agency and Transfer Co., 50 W Liberty St, Reno, NV 89501',
    officers: [{ name: 'Marcus A. Sintra', title: 'Member', ownership: 100 }],
    children: [],
    parent: 'e1',
    compliance: { nextDue: '2024-08-31', status: 'due_soon' },
  },
  {
    id: 'e4', name: 'Apex Ventures LLC', type: 'llc', status: 'suspended', state: 'Delaware',
    formation: '2021-04-05', ein: '86-1122334',
    registeredAgent: 'National Registered Agents Inc.',
    officers: [{ name: 'Marcus A. Sintra', title: 'Member', ownership: 75 }, { name: 'James Porter', title: 'Member', ownership: 25 }],
    children: [],
    parent: 'e2',
    compliance: { nextDue: '2024-06-01', status: 'overdue' },
  },
  {
    id: 'e5', name: 'Sintra Family Irrevocable Trust', type: 'trust', status: 'active', state: 'Nevada',
    formation: '2020-09-18', ein: '87-5544332',
    registeredAgent: 'Nevada Trust Company',
    officers: [{ name: 'Marcus A. Sintra', title: 'Trustee', ownership: 0 }, { name: 'Sintra Family Members', title: 'Beneficiaries', ownership: 100 }],
    children: [],
    parent: 'e1',
    compliance: { nextDue: '2025-01-01', status: 'current' },
  },
  {
    id: 'e6', name: 'Sintra Real Estate Corp', type: 'corporation', status: 'active', state: 'New York',
    formation: '2022-02-28', ein: '88-6677889',
    registeredAgent: 'CT Corporation System',
    officers: [{ name: 'Marcus A. Sintra', title: 'President & CEO', ownership: 100 }],
    children: [],
    compliance: { nextDue: '2025-02-28', status: 'current' },
  },
  {
    id: 'e7', name: 'Sintra Charitable Foundation', type: 'nonprofit', status: 'active', state: 'New York',
    formation: '2023-05-15', ein: '89-1234568',
    registeredAgent: 'Foundation Legal Services LLC',
    officers: [{ name: 'Marcus A. Sintra', title: 'Executive Director', ownership: 0 }],
    children: [],
    compliance: { nextDue: '2025-05-15', status: 'current' },
  },
];

const typeColors: Record<string, string> = {
  llc: 'blue',
  corporation: 'gold',
  trust: 'purple',
  nonprofit: 'green',
  partnership: 'amber',
};

const statusColors: Record<string, 'green' | 'amber' | 'red' | 'slate'> = {
  active: 'green',
  suspended: 'red',
  dissolved: 'slate',
  pending: 'amber',
};

const complianceColors: Record<string, 'green' | 'amber' | 'red'> = {
  current: 'green',
  due_soon: 'amber',
  overdue: 'red',
};

export default function EntityGovernance() {
  const [selectedEntity, setSelectedEntity] = useState(entities[0]);
  const [expandedEntity, setExpandedEntity] = useState<string | null>('e1');

  const rootEntities = entities.filter((e) => !e.parent);
  const getChildren = (id: string) => entities.filter((e) => e.parent === id);

  function EntityTree({ entity, depth = 0 }: { entity: typeof entities[0]; depth?: number }) {
    const children = getChildren(entity.id);
    const isExpanded = expandedEntity === entity.id || depth === 0;

    return (
      <div>
        <div
          className={clsx(
            'flex items-center gap-2 py-2 px-3 rounded-lg cursor-pointer transition-all',
            selectedEntity.id === entity.id ? 'bg-gold/10 text-gold' : 'hover:bg-slate-800/40 text-slate-400'
          )}
          style={{ paddingLeft: `${12 + depth * 20}px` }}
          onClick={() => setSelectedEntity(entity)}
        >
          {children.length > 0 ? (
            <button
              onClick={(e) => { e.stopPropagation(); setExpandedEntity(expandedEntity === entity.id ? null : entity.id); }}
              className="text-slate-500"
            >
              {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </button>
          ) : (
            <div className="w-3.5" />
          )}
          <div className={`w-5 h-5 rounded-md flex items-center justify-center bg-${typeColors[entity.type] || 'slate'}-500/15`}>
            <Building2 className={`w-3 h-3 text-${typeColors[entity.type] || 'slate'}-400`} />
          </div>
          <span className="text-xs font-medium truncate flex-1">{entity.name}</span>
          <div className={`w-1.5 h-1.5 rounded-full ${entity.compliance.status === 'overdue' ? 'bg-rose-400' : entity.compliance.status === 'due_soon' ? 'bg-amber-400' : 'bg-emerald-400'}`} />
        </div>
        {isExpanded && children.map((child) => (
          <EntityTree key={child.id} entity={child} depth={depth + 1} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Entity Governance</h1>
          <p className="text-slate-500 text-sm mt-1">{entities.length} entities · LLCs, Trusts, Corps, Nonprofits</p>
        </div>
        <Button size="sm" icon={Plus}>New Entity</Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Active Entities', value: entities.filter(e => e.status === 'active').length, color: 'text-emerald-400' },
          { label: 'LLCs', value: entities.filter(e => e.type === 'llc').length, color: 'text-blue-400' },
          { label: 'Due Soon', value: entities.filter(e => e.compliance.status === 'due_soon').length, color: 'text-amber-400' },
          { label: 'Overdue', value: entities.filter(e => e.compliance.status === 'overdue').length, color: 'text-rose-400' },
        ].map((item) => (
          <Card key={item.label} padding="md">
            <div className={clsx('text-2xl font-bold mb-1', item.color)}>{item.value}</div>
            <div className="text-xs text-slate-500">{item.label}</div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Entity tree */}
        <Card padding="md">
          <CardHeader title="Entity Hierarchy" />
          <div className="space-y-0.5">
            {rootEntities.map((entity) => (
              <EntityTree key={entity.id} entity={entity} />
            ))}
          </div>
        </Card>

        {/* Entity detail */}
        <div className="xl:col-span-3 space-y-4">
          <AnimatePresence mode="wait">
            <motion.div
              key={selectedEntity.id}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="space-y-4"
            >
              <Card padding="lg">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant={statusColors[selectedEntity.status]}>
                        {selectedEntity.status}
                      </Badge>
                      <Badge variant="slate">{selectedEntity.type.toUpperCase()}</Badge>
                      <Badge variant="slate"><MapPin className="w-3 h-3 inline mr-1" />{selectedEntity.state}</Badge>
                    </div>
                    <h2 className="text-xl font-bold text-slate-100">{selectedEntity.name}</h2>
                    {selectedEntity.ein && <p className="text-sm text-slate-500 mt-0.5 font-mono">EIN: {selectedEntity.ein}</p>}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" icon={FileText}>Documents</Button>
                    <Button size="sm">Edit Entity</Button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Formation Details</p>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-500">Formation Date</span>
                        <span className="text-slate-200">{format(new Date(selectedEntity.formation), 'MMMM d, yyyy')}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-500">State</span>
                        <span className="text-slate-200">{selectedEntity.state}</span>
                      </div>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Registered Agent</p>
                    <p className="text-sm text-slate-400">{selectedEntity.registeredAgent}</p>
                  </div>
                </div>
              </Card>

              {/* Officers */}
              <Card padding="lg">
                <CardHeader title="Officers & Members" />
                <div className="space-y-2">
                  {selectedEntity.officers.map((officer, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-slate-800/30 rounded-xl">
                      <div className="w-8 h-8 rounded-full bg-gold/15 flex items-center justify-center text-gold font-bold text-sm">
                        {officer.name.charAt(0)}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-200">{officer.name}</p>
                        <p className="text-xs text-slate-500">{officer.title}</p>
                      </div>
                      {officer.ownership > 0 && (
                        <Badge variant="gold">{officer.ownership}% ownership</Badge>
                      )}
                    </div>
                  ))}
                </div>
              </Card>

              {/* Compliance */}
              <Card padding="lg">
                <CardHeader
                  title="Compliance Calendar"
                  action={
                    <Badge variant={complianceColors[selectedEntity.compliance.status]} dot>
                      {selectedEntity.compliance.status === 'current' ? 'Current' :
                       selectedEntity.compliance.status === 'due_soon' ? 'Due Soon' : 'Overdue'}
                    </Badge>
                  }
                />
                <div className="space-y-3">
                  {[
                    {
                      name: 'Annual Report',
                      due: selectedEntity.compliance.nextDue,
                      status: selectedEntity.compliance.status,
                      cost: 50,
                    },
                    { name: 'Registered Agent Fee', due: '2025-01-01', status: 'current', cost: 120 },
                    { name: 'State Franchise Tax', due: '2025-03-15', status: 'current', cost: 800 },
                  ].map((item, i) => {
                    const daysUntil = Math.ceil((new Date(item.due).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
                    return (
                      <div key={i} className="flex items-center gap-4 p-3 bg-slate-800/30 rounded-xl">
                        <div className={clsx(
                          'w-9 h-9 rounded-xl flex items-center justify-center text-xs font-bold',
                          item.status === 'overdue' ? 'bg-rose-500/20 text-rose-400' :
                          item.status === 'due_soon' ? 'bg-amber-500/20 text-amber-400' :
                          'bg-emerald-500/20 text-emerald-400'
                        )}>
                          {daysUntil > 0 ? `${daysUntil}d` : 'OVR'}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-slate-200">{item.name}</p>
                          <p className="text-xs text-slate-500">Due: {format(new Date(item.due), 'MMMM d, yyyy')} · ${item.cost}</p>
                        </div>
                        <Button variant={item.status === 'overdue' ? 'danger' : 'outline'} size="sm">
                          {item.status === 'overdue' ? 'File Now' : 'Schedule'}
                        </Button>
                      </div>
                    );
                  })}
                </div>
              </Card>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
