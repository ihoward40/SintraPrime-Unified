import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  Search,
  Upload,
  Grid3X3,
  List,
  Filter,
  Eye,
  Download,
  Share2,
  Trash2,
  Lock,
  File,
  FileCheck,
  FileCog,
  FolderOpen,
  Clock,
  Star,
} from 'lucide-react';
import Card, { CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { clsx } from 'clsx';
import { format } from 'date-fns';

const mockDocuments = [
  { id: 'd1', name: 'Sintra Family Trust Declaration', type: 'trust', category: 'trust', size: 245760, uploadedAt: '2024-01-15', tags: ['trust', 'family', 'irrevocable'], isConfidential: true, version: 3 },
  { id: 'd2', name: 'LLC Operating Agreement - Sintra Holdings', type: 'contract', category: 'corporate', size: 184320, uploadedAt: '2024-02-20', tags: ['LLC', 'operating agreement', 'Delaware'], isConfidential: true, version: 2 },
  { id: 'd3', name: 'Motion to Dismiss - Case 2024-CV-1847', type: 'motion', category: 'legal', size: 98304, uploadedAt: '2024-06-10', tags: ['motion', 'dismiss', 'housing'], isConfidential: false, version: 1 },
  { id: 'd4', name: 'Investment Portfolio Statement Q2 2024', type: 'other', category: 'financial', size: 327680, uploadedAt: '2024-07-01', tags: ['portfolio', 'investments', 'quarterly'], isConfidential: true, version: 1 },
  { id: 'd5', name: 'Last Will and Testament', type: 'will', category: 'estate', size: 163840, uploadedAt: '2023-11-05', tags: ['will', 'estate', 'testamentary'], isConfidential: true, version: 4 },
  { id: 'd6', name: 'UCC-1 Financing Statement #2024-001847', type: 'other', category: 'legal', size: 40960, uploadedAt: '2024-01-20', tags: ['UCC', 'secured', 'financing'], isConfidential: false, version: 1 },
  { id: 'd7', name: 'Chapter 11 Reorganization Plan', type: 'brief', category: 'legal', size: 491520, uploadedAt: '2024-03-15', tags: ['bankruptcy', 'reorganization', 'chapter 11'], isConfidential: false, version: 2 },
  { id: 'd8', name: 'Residential Property Deed - 123 Main St', type: 'deed', category: 'estate', size: 122880, uploadedAt: '2022-08-10', tags: ['deed', 'real estate', 'property'], isConfidential: true, version: 1 },
  { id: 'd9', name: 'Employment Agreement - Senior Counsel', type: 'contract', category: 'corporate', size: 204800, uploadedAt: '2024-05-01', tags: ['employment', 'contract', 'counsel'], isConfidential: true, version: 1 },
  { id: 'd10', name: 'IRS Form 1065 - Partnership Return 2023', type: 'other', category: 'financial', size: 786432, uploadedAt: '2024-04-15', tags: ['tax', 'IRS', 'partnership'], isConfidential: true, version: 1 },
  { id: 'd11', name: 'PACER Filing Receipt - Case 2024-BK-0394', type: 'other', category: 'legal', size: 20480, uploadedAt: '2024-03-05', tags: ['PACER', 'bankruptcy', 'receipt'], isConfidential: false, version: 1 },
  { id: 'd12', name: 'Settlement Agreement - Case 2023-CV-4412', type: 'contract', category: 'legal', size: 143360, uploadedAt: '2024-06-20', tags: ['settlement', 'agreement', 'civil'], isConfidential: true, version: 2 },
];

const categories = ['all', 'legal', 'financial', 'estate', 'trust', 'corporate', 'personal'];

const categoryIcons: Record<string, React.ElementType> = {
  legal: Scale_,
  financial: DollarSign_,
  estate: Home_,
  trust: Lock,
  corporate: Building_,
  personal: User_,
};

const typeIcons: Record<string, React.ElementType> = {
  motion: FileText,
  brief: FileText,
  contract: FileCheck,
  trust: Lock,
  will: FileCog,
  deed: File,
  other: File,
};

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function Scale_({ className }: { className?: string }) { return <FileText className={className} />; }
function DollarSign_({ className }: { className?: string }) { return <FileCheck className={className} />; }
function Home_({ className }: { className?: string }) { return <FolderOpen className={className} />; }
function Building_({ className }: { className?: string }) { return <FileCog className={className} />; }
function User_({ className }: { className?: string }) { return <File className={className} />; }

export default function DocumentVault() {
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedDoc, setSelectedDoc] = useState<typeof mockDocuments[0] | null>(null);

  const filtered = mockDocuments.filter((d) => {
    const matchSearch = !search || d.name.toLowerCase().includes(search.toLowerCase()) || d.tags.some((t) => t.includes(search.toLowerCase()));
    const matchCat = selectedCategory === 'all' || d.category === selectedCategory;
    return matchSearch && matchCat;
  });

  const categoryCounts = categories.reduce((acc, cat) => {
    acc[cat] = cat === 'all' ? mockDocuments.length : mockDocuments.filter((d) => d.category === cat).length;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Document Vault</h1>
          <p className="text-slate-500 text-sm mt-1">{mockDocuments.length} documents · Encrypted & Secure</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" icon={Upload}>Upload</Button>
        </div>
      </div>

      {/* Search + view toggle */}
      <div className="flex gap-3 items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search documents, tags, contents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-dark pl-10 py-2 text-sm"
          />
        </div>
        <div className="flex items-center gap-1 p-1 bg-slate-800/60 rounded-lg border border-slate-700/40">
          <button
            onClick={() => setView('grid')}
            className={clsx('p-1.5 rounded-md transition-colors', view === 'grid' ? 'bg-gold/20 text-gold' : 'text-slate-500 hover:text-slate-300')}
          >
            <Grid3X3 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setView('list')}
            className={clsx('p-1.5 rounded-md transition-colors', view === 'list' ? 'bg-gold/20 text-gold' : 'text-slate-500 hover:text-slate-300')}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* Sidebar categories */}
        <div className="xl:col-span-1">
          <Card padding="sm">
            <div className="space-y-0.5">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={clsx(
                    'w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm transition-all',
                    selectedCategory === cat
                      ? 'bg-gold/10 text-gold'
                      : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200'
                  )}
                >
                  <div className="flex items-center gap-2">
                    {cat === 'all' ? <FolderOpen className="w-4 h-4" /> : (categoryIcons[cat] && <categoryIcons[cat] className="w-4 h-4" /> || <File className="w-4 h-4" />)}
                    <span className="capitalize">{cat}</span>
                  </div>
                  <span className="text-xs bg-slate-700/50 px-1.5 py-0.5 rounded-md">
                    {categoryCounts[cat]}
                  </span>
                </button>
              ))}
            </div>
          </Card>
        </div>

        {/* Document grid/list */}
        <div className="xl:col-span-4">
          <p className="text-xs text-slate-500 mb-3">{filtered.length} documents</p>

          {view === 'grid' ? (
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
              {filtered.map((doc, i) => {
                const DocIcon = typeIcons[doc.type] || File;
                return (
                  <motion.div
                    key={doc.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    onClick={() => setSelectedDoc(selectedDoc?.id === doc.id ? null : doc)}
                    className={clsx(
                      'glass-card p-3 cursor-pointer transition-all duration-200 hover:-translate-y-1 group',
                      selectedDoc?.id === doc.id && 'border-gold/40'
                    )}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="w-9 h-9 bg-slate-800/60 rounded-xl flex items-center justify-center">
                        <DocIcon className="w-5 h-5 text-gold" />
                      </div>
                      <div className="flex items-center gap-1">
                        {doc.isConfidential && <Lock className="w-3 h-3 text-slate-500" />}
                        <span className="text-[10px] text-slate-600">v{doc.version}</span>
                      </div>
                    </div>
                    <p className="text-xs font-medium text-slate-200 leading-snug line-clamp-2 mb-2">{doc.name}</p>
                    <div className="flex items-center justify-between text-[10px] text-slate-500">
                      <Badge variant="slate" size="sm" className="capitalize">{doc.category}</Badge>
                      <span>{formatBytes(doc.size)}</span>
                    </div>
                    <div className="flex gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-1 rounded hover:bg-slate-700/50 text-slate-500 hover:text-slate-300 transition-colors">
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button className="p-1 rounded hover:bg-slate-700/50 text-slate-500 hover:text-slate-300 transition-colors">
                        <Download className="w-3.5 h-3.5" />
                      </button>
                      <button className="p-1 rounded hover:bg-slate-700/50 text-slate-500 hover:text-slate-300 transition-colors">
                        <Share2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((doc, i) => {
                const DocIcon = typeIcons[doc.type] || File;
                return (
                  <motion.div
                    key={doc.id}
                    initial={{ opacity: 0, x: -5 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="flex items-center gap-4 p-3 glass-card hover:border-slate-600/60 transition-all cursor-pointer group"
                    onClick={() => setSelectedDoc(selectedDoc?.id === doc.id ? null : doc)}
                  >
                    <div className="w-8 h-8 bg-slate-800/60 rounded-lg flex items-center justify-center flex-shrink-0">
                      <DocIcon className="w-4 h-4 text-gold" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-200 truncate">{doc.name}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-slate-500 capitalize">{doc.category}</span>
                        <span className="text-slate-700">·</span>
                        <span className="text-xs text-slate-500">{formatBytes(doc.size)}</span>
                        <span className="text-slate-700">·</span>
                        <span className="text-xs text-slate-500">{format(new Date(doc.uploadedAt), 'MMM d, yyyy')}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {doc.isConfidential && <Lock className="w-3.5 h-3.5 text-slate-600" />}
                      <span className="text-xs text-slate-600">v{doc.version}</span>
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {[Eye, Download, Share2, Trash2].map((Icon, idx) => (
                        <button key={idx} className="p-1.5 rounded-lg hover:bg-slate-700/50 text-slate-500 hover:text-slate-300 transition-colors">
                          <Icon className="w-3.5 h-3.5" />
                        </button>
                      ))}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
