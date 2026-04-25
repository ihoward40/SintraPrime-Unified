import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Scale, Building2, Shield, Home, Gavel, FileText, DollarSign,
  Heart, Globe, Zap, Car, Users, TrendingUp, BookOpen, Flag,
  Lock, Award, Coffee, Landmark, Briefcase,
} from 'lucide-react';
import { clsx } from 'clsx';

const practiceAreas = [
  { id: 'civil_rights', name: 'Civil Rights', icon: Shield, color: '#3B82F6', cases: 12, description: 'Discrimination, due process, equal protection, section 1983 claims, and constitutional violations.' },
  { id: 'housing', name: 'Housing & Tenants', icon: Home, color: '#10B981', cases: 8, description: 'FHA claims, eviction defense, rent control, habitability, landlord-tenant disputes.' },
  { id: 'family', name: 'Family Law', icon: Heart, color: '#F43F5E', cases: 5, description: 'Divorce, custody, child support, adoption, domestic relations, parental rights.' },
  { id: 'criminal', name: 'Criminal Defense', icon: Gavel, color: '#F59E0B', cases: 3, description: 'Constitutional defenses, suppression motions, appellate advocacy, rights violations.' },
  { id: 'business', name: 'Business & Corporate', icon: Briefcase, color: '#8B5CF6', cases: 9, description: 'LLC formation, contracts, shareholder disputes, M&A, corporate governance.' },
  { id: 'estate', name: 'Estate Planning', icon: FileText, color: '#D4AF37', cases: 6, description: 'Wills, trusts, probate, power of attorney, advance directives, asset protection.' },
  { id: 'bankruptcy', name: 'Bankruptcy', icon: DollarSign, color: '#64748B', cases: 4, description: 'Chapter 7, 11, 13 filings, creditor negotiations, debt discharge, reorganization.' },
  { id: 'immigration', name: 'Immigration', icon: Globe, color: '#06B6D4', cases: 2, description: 'Visa petitions, asylum, removal defense, DACA, naturalization, consular processing.' },
  { id: 'employment', name: 'Employment Law', icon: Users, color: '#EC4899', cases: 7, description: 'Wrongful termination, discrimination, wage theft, FLSA, harassment, EEOC claims.' },
  { id: 'consumer', name: 'Consumer Protection', icon: Award, color: '#22C55E', cases: 3, description: 'FDCPA, FCRA, TCPA, predatory lending, class actions, FTC violations.' },
  { id: 'personal_injury', name: 'Personal Injury', icon: Zap, color: '#F97316', cases: 5, description: 'Tort claims, negligence, medical malpractice, premises liability, product liability.' },
  { id: 'real_estate', name: 'Real Estate', icon: Building2, color: '#0EA5E9', cases: 4, description: 'Property transactions, title issues, zoning, commercial leases, development.' },
  { id: 'securities', name: 'Securities & Finance', icon: TrendingUp, color: '#A855F7', cases: 2, description: 'SEC compliance, investment fraud, broker disputes, FINRA arbitration.' },
  { id: 'intellectual', name: 'Intellectual Property', icon: Lock, color: '#14B8A6', cases: 1, description: 'Trademark, copyright, trade secrets, licensing, domain disputes.' },
  { id: 'tax', name: 'Tax Law', icon: BookOpen, color: '#EAB308', cases: 3, description: 'IRS disputes, tax planning, OIC negotiation, penalty abatement, audits.' },
  { id: 'trust', name: 'Trust Law', icon: Landmark, color: '#D4AF37', cases: 11, description: 'Express, constructive, resulting, and statutory trusts. UCC filings. Trust doctrine.' },
  { id: 'admin', name: 'Administrative Law', icon: Flag, color: '#6366F1', cases: 2, description: 'Agency challenges, APA, regulatory compliance, government benefits, appeals.' },
  { id: 'contracts', name: 'Contracts', icon: FileText, color: '#84CC16', cases: 6, description: 'Contract drafting, review, disputes, UCC Article 2, remedies, enforceability.' },
  { id: 'auto', name: 'Auto & Insurance', icon: Car, color: '#F59E0B', cases: 2, description: 'Auto accidents, insurance bad faith, PIP claims, uninsured motorist coverage.' },
  { id: 'nonprofit', name: 'Nonprofit Law', icon: Coffee, color: '#A16207', cases: 1, description: '501(c)(3) formation, governance, compliance, charitable solicitation, bylaws.' },
];

interface PracticeAreaGridProps {
  onSelect?: (id: string) => void;
  selectedId?: string;
}

export default function PracticeAreaGrid({ onSelect, selectedId }: PracticeAreaGridProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-3">
      {practiceAreas.map((area, i) => {
        const Icon = area.icon;
        const isHovered = hoveredId === area.id;
        const isSelected = selectedId === area.id;
        return (
          <motion.div
            key={area.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
            onHoverStart={() => setHoveredId(area.id)}
            onHoverEnd={() => setHoveredId(null)}
            onClick={() => onSelect?.(area.id)}
            className={clsx(
              'relative p-3 rounded-xl border cursor-pointer transition-all overflow-hidden',
              isSelected
                ? 'border-gold/50 bg-gold/5'
                : 'border-slate-700/40 hover:border-slate-600/60 bg-slate-900/40'
            )}
            style={isSelected || isHovered ? { borderColor: area.color + '60' } : {}}
          >
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center mb-2"
              style={{ background: area.color + '20' }}
            >
              <Icon className="w-4 h-4" style={{ color: area.color }} />
            </div>
            <h4 className="text-xs font-semibold text-slate-200 leading-tight mb-1">{area.name}</h4>
            <p className="text-[10px] text-slate-500">{area.cases} active</p>

            <AnimatePresence>
              {isHovered && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  transition={{ duration: 0.15 }}
                  className="absolute inset-0 bg-slate-900/95 rounded-xl p-3 flex flex-col justify-center"
                >
                  <h4 className="text-xs font-bold mb-1" style={{ color: area.color }}>{area.name}</h4>
                  <p className="text-[10px] text-slate-400 leading-relaxed">{area.description}</p>
                  <div className="mt-2 text-[10px] text-slate-500">{area.cases} active cases</div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}
    </div>
  );
}
