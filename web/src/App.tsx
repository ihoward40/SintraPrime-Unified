import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import Layout from './components/layout/Layout';
import LiveDashboard from './pages/LiveDashboard';
import LiveCaseManagement from './pages/LiveCaseManagement';
import Dashboard from './pages/Dashboard';
import LegalHub from './pages/LegalHub';
import FinancialEmpire from './pages/FinancialEmpire';
import TrustLaw from './pages/TrustLaw';
import NewJerseyJurisdiction from './pages/NewJerseyJurisdiction';
import NewYorkJurisdiction from './pages/NewYorkJurisdiction';
import PennsylvaniaJurisdiction from './pages/PennsylvaniaJurisdiction';
import DelawareJurisdiction from './pages/DelawareJurisdiction';
import ConnecticutJurisdiction from './pages/ConnecticutJurisdiction';
import NortheastComparison from './pages/NortheastComparison';
import UCCFilingAssessment from './pages/UCCFilingAssessment';
import CaseManagement from './pages/CaseManagement';
import DocumentVault from './pages/DocumentVault';
import EntityGovernance from './pages/EntityGovernance';
import AIParliament from './pages/AIParliament';
import CaseLawSearch from './pages/CaseLawSearch';
import Settings from './pages/Settings';
import OperationsFloor from './pages/OperationsFloor';
import OrchestrationCommandCenter from './pages/OrchestrationCommandCenter';
import Login from './pages/Login';
import Setup from './pages/Setup';
import VoiceConcierge from './pages/VoiceConcierge';
import MatterWorkspace from './pages/MatterWorkspace';
import MissionControlLayout from './pages/mission-control/MissionControlLayout';
import MissionControlHome from './pages/mission-control/MissionControlHome';
import MissionControlSurface from './pages/mission-control/MissionControlSurface';
import { useTheme } from './hooks/useTheme';

function AppContent() {
  useTheme();
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/setup" element={<Setup />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<LiveDashboard />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="legal" element={<LegalHub />} />
          <Route path="financial" element={<FinancialEmpire />} />
          <Route path="trust-law" element={<TrustLaw />} />
          <Route path="jurisdictions/new-jersey" element={<NewJerseyJurisdiction />} />
          <Route path="jurisdictions/new-york" element={<NewYorkJurisdiction />} />
          <Route path="jurisdictions/pennsylvania" element={<PennsylvaniaJurisdiction />} />
          <Route path="jurisdictions/delaware" element={<DelawareJurisdiction />} />
          <Route path="jurisdictions/connecticut" element={<ConnecticutJurisdiction />} />
          <Route path="jurisdictions/northeast-comparison" element={<NortheastComparison />} />
          <Route path="ucc/filing-assessment" element={<UCCFilingAssessment />} />
          <Route path="matters/:matterId" element={<MatterWorkspace />} />
          <Route path="cases" element={<LiveCaseManagement />} />
          <Route path="documents" element={<DocumentVault />} />
          <Route path="entities" element={<EntityGovernance />} />
          <Route path="ai-parliament" element={<AIParliament />} />
          <Route path="caselaw" element={<CaseLawSearch />} />
          <Route path="settings" element={<Settings />} />
          <Route path="mission-control" element={<MissionControlLayout />}>
            <Route index element={<MissionControlHome />} />
            <Route path=":surface" element={<MissionControlSurface />} />
          </Route>
          <Route path="orchestration" element={<OrchestrationCommandCenter />} />
          <Route path="orchestration/runs" element={<OrchestrationCommandCenter />} />
          <Route path="orchestration/runs/:runId" element={<OrchestrationCommandCenter />} />
          <Route path="orchestration/providers" element={<OrchestrationCommandCenter />} />
          <Route path="orchestration/policies" element={<OrchestrationCommandCenter />} />
          <Route path="operations-floor" element={<OperationsFloor />} />
          <Route path="voice-concierge" element={<VoiceConcierge />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default function App() {
  return <AppContent />;
}
