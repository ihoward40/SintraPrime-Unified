import { Shield, TrendingUp, Home, DollarSign, Briefcase } from 'lucide-react';
import { clsx } from 'clsx';

const assetMap = [
  {
    category: 'Real Estate',
    icon: Home,
    color: '#3B82F6',
    totalValue: 840000,
    assets: [
      { name: 'Primary Residence', value: 520000, entity: 'SintraPrime Family Trust', protected: true },
      { name: 'Rental Property #1', value: 320000, entity: 'SintraPrime Holdings LLC', protected: true },
    ],
  },
  {
    category: 'Investments',
    icon: TrendingUp,
    color: '#10B981',
    totalValue: 299700,
    assets: [
      { name: 'Brokerage Account', value: 218500, entity: 'Prime Capital Management LLC', protected: true },
      { name: 'Roth IRA', value: 81200, entity: 'Direct (Exempt)', protected: true },
    ],
  },
  {
    category: 'Business Assets',
    icon: Briefcase,
    color: '#8B5CF6',
    totalValue: 185000,
    assets: [
      { name: 'Law Firm Book of Business', value: 150000, entity: 'SintraPrime Legal PLLC', protected: true },
      { name: 'Equipment & IP', value: 35000, entity: 'SintraPrime Holdings LLC', protected: true },
    ],
  },
  {
    category: 'Cash & Savings',
    icon: DollarSign,
    color: '#D4AF37',
    totalValue: 109850,
    assets: [
      { name: 'High-Yield Savings', value: 85000, entity: 'Direct (Partially Exposed)', protected: false },
      { name: 'Business Checking', value: 24850, entity: 'Direct', protected: false },
    ],
  },
];

const totalProtected = assetMap.flatMap(c => c.assets).filter(a => a.protected).reduce((s, a) => s + a.value, 0);
const totalUnprotected = assetMap.flatMap(c => c.assets).filter(a => !a.protected).reduce((s, a) => s + a.value, 0);
const totalAssets = totalProtected + totalUnprotected;

function fmt(n: number) {
  if (n >= 1000000) return `$${(n / 1000000).toFixed(2)}M`;
  return `$${(n / 1000).toFixed(0)}K`;
}

export default function AssetProtectionMap() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
          <div className="text-xs text-slate-400 mb-0.5">Protected</div>
          <div className="text-sm font-bold text-emerald-400">{fmt(totalProtected)}</div>
          <div className="text-[10px] text-slate-500">{Math.round(totalProtected / totalAssets * 100)}%</div>
        </div>
        <div className="p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-xl">
          <div className="text-xs text-slate-400 mb-0.5">Exposed</div>
          <div className="text-sm font-bold text-amber-400">{fmt(totalUnprotected)}</div>
          <div className="text-[10px] text-slate-500">{Math.round(totalUnprotected / totalAssets * 100)}%</div>
        </div>
        <div className="p-2.5 bg-gold/10 border border-gold/20 rounded-xl">
          <div className="text-xs text-slate-400 mb-0.5">Total</div>
          <div className="text-sm font-bold text-gold">{fmt(totalAssets)}</div>
          <div className="text-[10px] text-slate-500">4 categories</div>
        </div>
      </div>

      <div className="space-y-3">
        {assetMap.map((cat) => {
          const Icon = cat.icon;
          return (
            <div key={cat.category}>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-lg flex items-center justify-center" style={{ background: cat.color + '20' }}>
                  <Icon className="w-3.5 h-3.5" style={{ color: cat.color }} />
                </div>
                <span className="text-xs font-semibold text-slate-300">{cat.category}</span>
                <span className="ml-auto text-xs font-bold" style={{ color: cat.color }}>{fmt(cat.totalValue)}</span>
              </div>
              <div className="space-y-1.5 ml-8">
                {cat.assets.map((asset) => (
                  <div key={asset.name} className="flex items-center gap-2 text-xs">
                    <Shield className={clsx('w-3 h-3 flex-shrink-0', asset.protected ? 'text-emerald-400' : 'text-amber-400')} />
                    <span className="text-slate-400 flex-1 truncate">{asset.name}</span>
                    <span className="text-slate-500 text-[10px] truncate">{asset.entity}</span>
                    <span className="text-slate-300 font-medium">{fmt(asset.value)}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
