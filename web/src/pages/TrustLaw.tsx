import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BookOpen,
  Search,
  Filter,
  Lock,
  Shield,
  Scale,
  FileText,
  Globe,
  ChevronRight,
  Star,
  MapPin,
} from 'lucide-react';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { clsx } from 'clsx';

const trustDoctrines = [
  { id: 1, name: 'Spendthrift Trust', category: 'asset_protection', description: 'Protects trust assets from beneficiary\'s creditors. Beneficiary cannot assign or pledge trust interest.', keyCase: 'Sligh v. First National Bank', uccSection: null },
  { id: 2, name: 'Resulting Trust', category: 'formation', description: 'Implied trust arising when express trust fails or purchase price paid by one party but title in another.', keyCase: 'Restatement (Third) Trusts § 7', uccSection: null },
  { id: 3, name: 'Constructive Trust', category: 'beneficiary', description: 'Equitable remedy imposed to prevent unjust enrichment. Not a true trust — a device to transfer property.', keyCase: 'Beatty v. Guggenheim Exploration Co.', uccSection: null },
  { id: 4, name: 'Charitable Trust', category: 'formation', description: 'Trust for charitable purposes — education, religion, relief of poverty, promotion of health.', keyCase: 'Shenandoah Valley Nat\'l Bank v. Taylor', uccSection: null },
  { id: 5, name: 'Land Trust', category: 'asset_protection', description: 'Holds real property with privacy protection. Beneficiary\'s identity concealed from public records.', keyCase: 'Ill. Land Trust Act', uccSection: null },
  { id: 6, name: 'UCC Article 9 Secured Interest', category: 'ucc', description: 'Security interest in personal property and fixtures. Creation, attachment, and perfection through filing.', keyCase: 'In re Octagon Gas Systems', uccSection: '§ 9-203' },
  { id: 7, name: 'Inter Vivos Trust', category: 'formation', description: 'Living trust created during settlor\'s lifetime. Can be revocable or irrevocable.', keyCase: 'Farkas v. Williams', uccSection: null },
  { id: 8, name: 'Testamentary Trust', category: 'formation', description: 'Trust created by will, taking effect at testator\'s death. Subject to probate.', keyCase: 'Restatement (Second) Trusts § 17', uccSection: null },
  { id: 9, name: 'Discretionary Trust', category: 'trustee', description: 'Trustee has discretion regarding distribution of income or principal to beneficiaries.', keyCase: 'McNeil v. McNeil', uccSection: null },
  { id: 10, name: 'Totten Trust', category: 'formation', description: 'Bank account "In Trust For" — tentative trust revocable by depositor.', keyCase: 'In re Totten, 179 N.Y. 112', uccSection: null },
  { id: 11, name: 'Cy Pres Doctrine', category: 'termination', description: 'Court modifies charitable trust purpose when original purpose becomes impossible or impractical.', keyCase: 'Jackson v. Phillips', uccSection: null },
  { id: 12, name: 'Merger Doctrine', category: 'termination', description: 'Trust terminates when sole trustee is also sole beneficiary — same person cannot hold both interests.', keyCase: 'Restatement (Third) Trusts § 69', uccSection: null },
  { id: 13, name: 'Rule Against Perpetuities', category: 'termination', description: 'No interest in property is valid unless it must vest, if at all, not later than 21 years after a life in being.', keyCase: 'Jee v. Audley (1787)', uccSection: null },
  { id: 14, name: 'Prudent Investor Rule', category: 'trustee', description: 'Trustee must invest as a prudent investor considering risk and return. Portfolio theory applies.', keyCase: 'Harvard College v. Amory (1830)', uccSection: null },
  { id: 15, name: 'Duty of Loyalty', category: 'trustee', description: 'Trustee must administer trust solely in beneficiaries\' interests. No self-dealing.', keyCase: 'Meinhard v. Salmon', uccSection: null },
  { id: 16, name: 'QTIP Trust', category: 'tax', description: 'Qualified Terminable Interest Property trust for marital deduction. Spouse receives all income.', keyCase: 'IRC § 2056(b)(7)', uccSection: null },
  { id: 17, name: 'Generation-Skipping Trust', category: 'tax', description: 'Passes wealth to grandchildren or lower generations, bypassing estate taxes for middle generation.', keyCase: 'IRC § 2601 et seq.', uccSection: null },
  { id: 18, name: 'Asset Protection Trust', category: 'asset_protection', description: 'Self-settled trust in jurisdictions allowing settlor as discretionary beneficiary (Nevada, Delaware, Alaska).', keyCase: 'Mortensen v. Mortensen', uccSection: null },
  { id: 19, name: 'UCC Negotiability', category: 'ucc', description: 'Requirements for negotiable instruments: writing, signed, unconditional promise, fixed amount, payable to bearer or order.', keyCase: 'Holly Hill Acres Ltd. v. Charter Bank', uccSection: '§ 3-104' },
  { id: 20, name: 'Purchase Money Security Interest', category: 'ucc', description: 'PMSI — security interest in goods taken by seller who sold the goods. Super-priority over other secured creditors.', keyCase: 'In re Einoder', uccSection: '§ 9-103' },
  { id: 21, name: 'Equitable Subrogation', category: 'beneficiary', description: 'One who pays debt of another stands in shoes of creditor — follows payment of obligations.', keyCase: 'Bankers Tr. Co. v. Pacific', uccSection: null },
  { id: 22, name: 'Shifting Executory Interest', category: 'formation', description: 'Future interest in a third party that cuts off prior interest upon happening of an event.', keyCase: 'Restatement (First) Property § 25', uccSection: null },
  { id: 23, name: 'Springing Executory Interest', category: 'formation', description: 'Future interest that springs out of grantor\'s possession upon a future event.', keyCase: 'Restatement (First) Property § 25', uccSection: null },
  { id: 24, name: 'Irrevocable Life Insurance Trust', category: 'tax', description: 'ILIT removes life insurance from taxable estate. Trustee owns policy; proceeds bypass estate.', keyCase: 'IRC § 2042', uccSection: null },
  { id: 25, name: 'Blind Trust', category: 'asset_protection', description: 'Beneficiary has no knowledge of or control over trust assets. Used by public officials.', keyCase: 'Ethics in Government Act', uccSection: null },
  { id: 26, name: 'Honorary Trust', category: 'formation', description: 'Trust for non-charitable purposes (e.g., care of animals, maintenance of graves). No human beneficiary.', keyCase: 'Restatement (Third) Trusts § 47', uccSection: null },
  { id: 27, name: 'UCC Perfection by Control', category: 'ucc', description: 'Security interest in deposit accounts, investment property perfected by control — highest priority method.', keyCase: 'In re Centennial Bank', uccSection: '§ 9-314' },
  { id: 28, name: 'Tracing Doctrine', category: 'beneficiary', description: 'Beneficiary may trace trust assets into hands of transferees to recover misappropriated trust property.', keyCase: 'Restatement (Third) Trusts § 80', uccSection: null },
  { id: 29, name: 'Duty to Diversify', category: 'trustee', description: 'Trustee must diversify investments unless under circumstances it is prudent not to.', keyCase: 'Uniform Prudent Investor Act § 3', uccSection: null },
  { id: 30, name: 'Termination by Agreement', category: 'termination', description: 'All beneficiaries may terminate trust if no material purpose remains unaccomplished (Claflin doctrine).', keyCase: 'Claflin v. Claflin (1889)', uccSection: null },
];

const jurisdictions = [
  'Federal', 'Alabama', 'Alaska', 'Arizona', 'California', 'Colorado', 'Connecticut',
  'Delaware', 'Florida', 'Georgia', 'Illinois', 'Nevada', 'New York',
  'Ohio', 'South Dakota', 'Texas', 'Utah', 'Virginia', 'Wyoming',
];

const categoryColors: Record<string, string> = {
  asset_protection: 'gold',
  formation: 'blue',
  termination: 'red',
  beneficiary: 'purple',
  trustee: 'emerald',
  tax: 'amber',
  ucc: 'slate',
};

const categoryLabels: Record<string, string> = {
  asset_protection: 'Asset Protection',
  formation: 'Formation',
  termination: 'Termination',
  beneficiary: 'Beneficiary Rights',
  trustee: 'Trustee Duties',
  tax: 'Tax Planning',
  ucc: 'UCC / Secured',
};

export default function TrustLaw() {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedJurisdiction, setSelectedJurisdiction] = useState('Federal');
  const [expandedDoctrine, setExpandedDoctrine] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'doctrines' | 'ucc' | 'generator'>('doctrines');

  const filtered = trustDoctrines.filter((d) => {
    const matchSearch = !search || d.name.toLowerCase().includes(search.toLowerCase()) || d.description.toLowerCase().includes(search.toLowerCase());
    const matchCat = selectedCategory === 'all' || d.category === selectedCategory;
    return matchSearch && matchCat;
  });

  const categories = ['all', ...Array.from(new Set(trustDoctrines.map((d) => d.category)))];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Trust Law Explorer</h1>
          <p className="text-slate-500 text-sm mt-1">30 trust doctrines · UCC Articles 1-9 · 19 jurisdictions</p>
        </div>
        <div className="flex gap-3">
          <select
            value={selectedJurisdiction}
            onChange={(e) => setSelectedJurisdiction(e.target.value)}
            className="input-dark w-auto"
          >
            {jurisdictions.map((j) => <option key={j} value={j}><MapPin className="w-3 h-3" /> {j}</option>)}
          </select>
          <Button size="sm" icon={FileText}>Generate Document</Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-slate-900/60 border border-slate-700/40 rounded-xl w-fit">
        {[
          { id: 'doctrines', label: 'Trust Doctrines (30)' },
          { id: 'ucc', label: 'UCC Tracker' },
          { id: 'generator', label: 'Document Generator' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab.id ? 'bg-gold/15 text-gold border border-gold/30' : 'text-slate-400 hover:text-slate-200'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'doctrines' && (
          <motion.div key="doctrines" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-4">
            {/* Search and filter */}
            <div className="flex flex-wrap gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search doctrines..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="input-dark pl-10 w-64"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={clsx(
                      'px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                      selectedCategory === cat
                        ? 'bg-gold/15 text-gold border border-gold/30'
                        : 'bg-slate-800/40 text-slate-400 hover:text-slate-200 border border-transparent'
                    )}
                  >
                    {cat === 'all' ? 'All Doctrines' : categoryLabels[cat] || cat}
                  </button>
                ))}
              </div>
            </div>

            <div className="text-xs text-slate-500">{filtered.length} doctrines shown · Jurisdiction: {selectedJurisdiction}</div>

            {/* Doctrine grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filtered.map((doctrine, i) => (
                <motion.div
                  key={doctrine.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className={clsx(
                    'glass-card p-4 cursor-pointer transition-all duration-200',
                    expandedDoctrine === doctrine.id && 'border-gold/30'
                  )}
                  onClick={() => setExpandedDoctrine(expandedDoctrine === doctrine.id ? null : doctrine.id)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-lg bg-gold/10 flex items-center justify-center">
                        <span className="text-[10px] font-bold text-gold">{doctrine.id}</span>
                      </div>
                      <Badge variant={(categoryColors[doctrine.category] as 'gold' | 'blue' | 'red' | 'purple' | 'green' | 'amber' | 'slate') || 'slate'} size="sm">
                        {categoryLabels[doctrine.category] || doctrine.category}
                      </Badge>
                    </div>
                    {doctrine.uccSection && (
                      <Badge variant="amber" size="sm">UCC {doctrine.uccSection}</Badge>
                    )}
                  </div>
                  <h3 className="text-sm font-semibold text-slate-200 mb-1">{doctrine.name}</h3>
                  <p className={clsx('text-xs text-slate-500 leading-relaxed', expandedDoctrine !== doctrine.id && 'line-clamp-2')}>
                    {doctrine.description}
                  </p>
                  <AnimatePresence>
                    {expandedDoctrine === doctrine.id && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-3 space-y-2"
                      >
                        <div className="p-2 bg-slate-800/40 rounded-lg">
                          <p className="text-[10px] text-slate-500 uppercase font-semibold mb-0.5">Key Case</p>
                          <p className="text-xs text-gold font-medium">{doctrine.keyCase}</p>
                        </div>
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm" fullWidth>View Cases</Button>
                          <Button size="sm" fullWidth>Apply Now</Button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {activeTab === 'ucc' && (
          <motion.div key="ucc" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Card padding="lg">
              <CardHeader title="UCC Filing Tracker" subtitle="Active secured transactions" />
              <div className="space-y-3">
                {[
                  { number: 'UCC-2024-001847', debtor: 'Sintra Holdings LLC', party: 'First National Bank', collateral: 'All assets including accounts receivable and inventory', filed: '2024-01-15', expires: '2029-01-15', status: 'active' },
                  { number: 'UCC-2023-098432', debtor: 'Marcus A. Sintra', party: 'Business Capital LLC', collateral: 'Computer equipment, furniture, office fixtures', filed: '2023-06-01', expires: '2028-06-01', status: 'active' },
                  { number: 'UCC-2022-034912', debtor: 'Sintra Consulting LLC', party: 'Tech Vendors Corp', collateral: 'Software licenses and intellectual property rights', filed: '2022-03-20', expires: '2027-03-20', status: 'active' },
                ].map((filing) => (
                  <div key={filing.number} className="p-4 bg-slate-800/30 rounded-xl border border-slate-700/30">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-gold">{filing.number}</span>
                          <Badge variant="green" size="sm" dot>Active</Badge>
                        </div>
                        <p className="text-sm font-medium text-slate-200">{filing.debtor}</p>
                        <p className="text-xs text-slate-500 mt-0.5">Secured Party: {filing.party}</p>
                        <p className="text-xs text-slate-400 mt-1">Collateral: {filing.collateral}</p>
                      </div>
                      <div className="text-right text-xs text-slate-500">
                        <div>Filed: {filing.filed}</div>
                        <div>Expires: {filing.expires}</div>
                      </div>
                    </div>
                    <div className="flex gap-2 mt-3">
                      <Button variant="outline" size="sm">Amend</Button>
                      <Button variant="outline" size="sm">Continue</Button>
                      <Button variant="danger" size="sm">Terminate</Button>
                    </div>
                  </div>
                ))}
                <Button icon={FileText} variant="outline" fullWidth>File New UCC-1</Button>
              </div>
            </Card>
          </motion.div>
        )}

        {activeTab === 'generator' && (
          <motion.div key="generator" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <Card padding="lg">
                <CardHeader title="Trust Document Wizard" subtitle="Generate customized trust documents" />
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Trust Type</label>
                    <select className="input-dark">
                      <option>Revocable Living Trust</option>
                      <option>Irrevocable Asset Protection Trust</option>
                      <option>Charitable Remainder Trust</option>
                      <option>Special Needs Trust</option>
                      <option>Spendthrift Trust</option>
                      <option>Land Trust</option>
                      <option>Business Trust</option>
                      <option>QTIP Marital Trust</option>
                      <option>Generation-Skipping Trust</option>
                      <option>ILIT (Life Insurance Trust)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Governing Jurisdiction</label>
                    <select className="input-dark">
                      {jurisdictions.map((j) => <option key={j} value={j}>{j}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Settlor Name</label>
                    <input type="text" className="input-dark" placeholder="Marcus A. Sintra" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Trustee Name</label>
                    <input type="text" className="input-dark" placeholder="Trustee name..." />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Beneficiaries</label>
                    <textarea rows={3} className="input-dark resize-none" placeholder="List beneficiaries and their shares..." />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Trust Assets</label>
                    <textarea rows={2} className="input-dark resize-none" placeholder="Real property, bank accounts, investments..." />
                  </div>
                  <Button fullWidth icon={FileText}>Generate Trust Document</Button>
                </div>
              </Card>

              <Card padding="lg">
                <CardHeader title="Asset Protection Strategy" subtitle="Recommended structure for your situation" />
                <div className="space-y-3">
                  {[
                    { level: 'Layer 1', name: 'Operating LLCs', description: 'Separate operating entities for each business activity', protection: 'High', color: 'gold' },
                    { level: 'Layer 2', name: 'Holding Company', description: 'Single-member LLC or corporation owning operating entities', protection: 'High', color: 'blue' },
                    { level: 'Layer 3', name: 'Irrevocable Trust', description: 'Asset Protection Trust (Nevada/Delaware) owning holding company', protection: 'Maximum', color: 'emerald' },
                    { level: 'Layer 4', name: 'Offshore Structure', description: 'Optional: Nevis/Cook Islands trust for additional protection', protection: 'Maximum', color: 'purple' },
                  ].map((layer, i) => (
                    <motion.div
                      key={layer.level}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.1 }}
                      className="flex items-start gap-3 p-3 bg-slate-800/30 rounded-xl border border-slate-700/20"
                    >
                      <div className={`w-16 text-center px-2 py-1 rounded-lg text-xs font-bold bg-${layer.color}/10 text-${layer.color}-400`}>
                        {layer.level}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-slate-200">{layer.name}</p>
                          <Badge variant={layer.protection === 'Maximum' ? 'green' : 'gold'} size="sm">{layer.protection}</Badge>
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">{layer.description}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
                <div className="mt-4 pt-4 border-t border-slate-700/40">
                  <Button variant="outline" fullWidth icon={Shield}>Implement This Strategy</Button>
                </div>
              </Card>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
