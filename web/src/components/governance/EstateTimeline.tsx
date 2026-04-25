import { CheckCircle, Clock, AlertCircle, Circle } from 'lucide-react';
import { clsx } from 'clsx';

const milestones = [
  { label: 'Last Will & Testament', date: '2022-04-12', status: 'completed', description: 'Drafted, witnessed, and notarized. Stored in Document Vault.' },
  { label: 'Revocable Living Trust', date: '2022-07-10', status: 'completed', description: 'SintraPrime Family Trust established. Funded with primary residence.' },
  { label: 'Durable Power of Attorney', date: '2022-07-10', status: 'completed', description: 'Financial POA executed. Health care proxy designated.' },
  { label: 'Advance Healthcare Directive', date: '2022-08-01', status: 'completed', description: 'Living will and DNR filed with primary care provider.' },
  { label: 'Life Insurance Review', date: '2023-12-01', status: 'completed', description: '3 policies reviewed. Beneficiaries updated to trust.' },
  { label: 'Annual Trust Funding Review', date: '2024-07-01', status: 'upcoming', description: 'Verify all assets properly titled in trust name.' },
  { label: 'Irrevocable Trust Setup', date: '2024-10-01', status: 'pending', description: 'Transfer high-value assets to irrevocable structure for estate tax planning.' },
  { label: 'Business Succession Plan', date: '2025-01-01', status: 'pending', description: 'Define succession for SintraPrime Legal PLLC. Buy-sell agreement.' },
  { label: 'Dynasty Trust Creation', date: '2025-06-01', status: 'pending', description: 'Multi-generational wealth transfer structure. Nevada situs.' },
];

const statusConfig = {
  completed: { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-400/10', label: 'Done' },
  upcoming: { icon: Clock, color: 'text-amber-400', bg: 'bg-amber-400/10', label: 'Upcoming' },
  pending: { icon: Circle, color: 'text-slate-500', bg: 'bg-slate-500/10', label: 'Planned' },
  overdue: { icon: AlertCircle, color: 'text-rose-400', bg: 'bg-rose-400/10', label: 'Overdue' },
};

export default function EstateTimeline() {
  return (
    <div className="space-y-1">
      {milestones.map((item, i) => {
        const config = statusConfig[item.status as keyof typeof statusConfig];
        const Icon = config.icon;
        return (
          <div key={i} className="flex items-start gap-3">
            <div className="flex flex-col items-center">
              <div className={clsx('w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0', config.bg)}>
                <Icon className={clsx('w-3.5 h-3.5', config.color)} />
              </div>
              {i < milestones.length - 1 && (
                <div className={clsx('w-px flex-1 my-1', item.status === 'completed' ? 'bg-emerald-400/30' : 'bg-slate-700/50')} style={{ minHeight: 20 }} />
              )}
            </div>
            <div className={clsx('flex-1 pb-3', i < milestones.length - 1 && '')}>
              <div className="flex items-center gap-2 flex-wrap">
                <p className={clsx('text-xs font-semibold', item.status === 'completed' ? 'text-slate-300' : item.status === 'upcoming' ? 'text-amber-300' : 'text-slate-500')}>
                  {item.label}
                </p>
                <span className={clsx('text-[9px] font-medium px-1.5 py-0.5 rounded-full', config.bg, config.color)}>{config.label}</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5">{new Date(item.date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</p>
              {item.status !== 'pending' && (
                <p className="text-[10px] text-slate-600 mt-0.5 leading-relaxed">{item.description}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
