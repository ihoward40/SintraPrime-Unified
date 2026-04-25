import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const data = [
  { month: 'Jul', value: 320000 },
  { month: 'Aug', value: 335000 },
  { month: 'Sep', value: 318000 },
  { month: 'Oct', value: 352000 },
  { month: 'Nov', value: 368000 },
  { month: 'Dec', value: 375000 },
  { month: 'Jan', value: 389000 },
  { month: 'Feb', value: 402000 },
  { month: 'Mar', value: 395000 },
  { month: 'Apr', value: 421000 },
  { month: 'May', value: 445000 },
  { month: 'Jun', value: 462000 },
];

function formatDollars(v: number) {
  if (v >= 1000000) return `$${(v / 1000000).toFixed(2)}M`;
  if (v >= 1000) return `$${(v / 1000).toFixed(0)}K`;
  return `$${v}`;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-900 border border-slate-700/50 rounded-xl p-3 shadow-xl">
        <p className="text-xs text-slate-400 mb-1">{label}</p>
        <p className="text-base font-bold text-gold">{formatDollars(payload[0].value)}</p>
      </div>
    );
  }
  return null;
};

export default function NetWorthChart({ height = 220 }: { height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 4, left: 4, bottom: 0 }}>
        <defs>
          <linearGradient id="netWorthGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#D4AF37" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#D4AF37" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
        <XAxis
          dataKey="month"
          tick={{ fill: '#64748b', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#64748b', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={formatDollars}
          width={56}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#D4AF37"
          strokeWidth={2}
          fill="url(#netWorthGrad)"
          dot={false}
          activeDot={{ r: 5, fill: '#D4AF37', stroke: '#020617', strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
