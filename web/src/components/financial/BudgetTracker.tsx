import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const expenses = [
  { name: 'Housing', value: 3200, color: '#3B82F6' },
  { name: 'Legal Costs', value: 2100, color: '#D4AF37' },
  { name: 'Investments', value: 4500, color: '#10B981' },
  { name: 'Food & Living', value: 1800, color: '#F59E0B' },
  { name: 'Business', value: 2800, color: '#8B5CF6' },
  { name: 'Other', value: 950, color: '#64748B' },
];

const totalIncome = 18500;
const totalExpenses = expenses.reduce((s, e) => s + e.value, 0);
const savings = totalIncome - totalExpenses;
const savingsRate = ((savings / totalIncome) * 100).toFixed(1);

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-900 border border-slate-700/50 rounded-xl p-3 shadow-xl">
        <p className="text-xs text-slate-400 mb-1">{payload[0].name}</p>
        <p className="text-sm font-bold text-white">${payload[0].value.toLocaleString()}</p>
      </div>
    );
  }
  return null;
};

export default function BudgetTracker() {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between text-sm">
        <div>
          <div className="text-slate-500 text-xs mb-0.5">Monthly Income</div>
          <div className="text-emerald-400 font-bold text-lg">${totalIncome.toLocaleString()}</div>
        </div>
        <div className="text-right">
          <div className="text-slate-500 text-xs mb-0.5">Total Expenses</div>
          <div className="text-rose-400 font-bold text-lg">${totalExpenses.toLocaleString()}</div>
        </div>
      </div>

      <div className="relative h-36">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={expenses}
              cx="50%"
              cy="50%"
              innerRadius={44}
              outerRadius={68}
              paddingAngle={2}
              dataKey="value"
            >
              {expenses.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-gold font-bold text-xl">{savingsRate}%</div>
          <div className="text-slate-500 text-[10px]">Savings Rate</div>
        </div>
      </div>

      <div className="space-y-1.5">
        {expenses.map((item) => (
          <div key={item.name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full" style={{ background: item.color }} />
              <span className="text-xs text-slate-400">{item.name}</span>
            </div>
            <span className="text-xs font-medium text-slate-200">${item.value.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
