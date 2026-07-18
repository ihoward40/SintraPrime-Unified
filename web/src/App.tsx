import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import Layout from './components/layout/Layout';
import LiveDashboard from './pages/LiveDashboard';
import LiveCaseManagement from './pages/LiveCaseManagement';
import Dashboard from './pages/Dashboard';
import LegalHub from './pages/LegalHub';
import FinancialEmpire from './pages/FinancialEmpire';
import TrustLaw from './pages/TrustLaw';
import CaseManagement from './pages/CaseManagement';
import DocumentVault from './pages/DocumentVault';
import EntityGovernance from './pages/EntityGovernance';
import AIParliament from './pages/AIParliament';
import CaseLawSearch from './pages/CaseLawSearch';
import Settings from './pages/Settings';
import OperationsFloor from './pages/OperationsFloor';
import Login from './pages/Login';
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
        <Route path="/" element={<Layout />}>
          <Route index element={<LiveDashboard />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="legal" element={<LegalHub />} />
          <Route path="financial" element={<FinancialEmpire />} />
          <Route path="trust-law" element={<TrustLaw />} />
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
          <Route path="operations-floor" element={<OperationsFloor />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default function App() {
  return <AppContent />;
}