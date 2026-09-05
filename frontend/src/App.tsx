import React, { useState, useEffect } from 'react';
import { Layout, NavPage } from './components/Layout';
import { api } from './api/client';
import { OverviewKPIs, PolicyControls } from './types';

// Import all 10 Pages
import { OverviewPage } from './pages/OverviewPage';
import { CaseExplorerPage } from './pages/CaseExplorerPage';
import { DecisionIntelligencePage } from './pages/DecisionIntelligencePage';
import { PolicySafetyPage } from './pages/PolicySafetyPage';
import { ReliabilityLabPage } from './pages/ReliabilityLabPage';
import { HumanReviewPage } from './pages/HumanReviewPage';
import { AuditTrailPage } from './pages/AuditTrailPage';
import { ExperimentPage } from './pages/ExperimentPage';
import { FailureTaxonomyPage } from './pages/FailureTaxonomyPage';
import { RazorpayMappingPage } from './pages/RazorpayMappingPage';

export const App: React.FC = () => {
  const [activePage, setActivePage] = useState<NavPage>('overview');
  const [simState, setSimState] = useState<{
    n: number;
    seed: number;
    controls: PolicyControls;
    kpis: OverviewKPIs;
    total_cases: number;
    mock_mode: boolean;
  } | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchSimulationState = async () => {
    try {
      const res = await api.getSimulationState();
      setSimState(res);
    } catch (err) {
      console.error('Failed to load initial simulation state:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSimulationState();
  }, []);

  const renderActivePage = () => {
    switch (activePage) {
      case 'overview':
        return (
          <OverviewPage
            kpis={simState?.kpis || null}
            loading={loading}
            onNavigateToCases={() => setActivePage('cases')}
          />
        );
      case 'cases':
        return <CaseExplorerPage />;
      case 'decision':
        return <DecisionIntelligencePage />;
      case 'policy':
        return <PolicySafetyPage onControlsUpdated={fetchSimulationState} />;
      case 'reliability':
        return <ReliabilityLabPage />;
      case 'hitl':
        return <HumanReviewPage />;
      case 'audit':
        return <AuditTrailPage />;
      case 'experiment':
        return <ExperimentPage />;
      case 'taxonomy':
        return <FailureTaxonomyPage />;
      case 'mapping':
        return <RazorpayMappingPage />;
      default:
        return (
          <OverviewPage
            kpis={simState?.kpis || null}
            loading={loading}
            onNavigateToCases={() => setActivePage('cases')}
          />
        );
    }
  };

  return (
    <Layout
      activePage={activePage}
      onNavigate={setActivePage}
      simulationState={
        simState
          ? {
              n: simState.n,
              seed: simState.seed,
              mock_mode: simState.mock_mode,
            }
          : null
      }
      onRefreshSimulation={fetchSimulationState}
    >
      {renderActivePage()}
    </Layout>
  );
};

export default App;
