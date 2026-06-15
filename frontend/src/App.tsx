import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { DashboardLayout } from './layouts/DashboardLayout';
import { Dashboard } from './pages/Dashboard';
import { InvestigationsQueue } from './pages/InvestigationsQueue';
import { InvestigationDetails } from './pages/InvestigationDetails';
import { EntityDetails } from './pages/EntityDetails';
import { Integrations } from './pages/Integrations';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/dashboard"
            element={
              <DashboardLayout>
                <Dashboard />
              </DashboardLayout>
            }
          />
          <Route
            path="/investigations"
            element={
              <DashboardLayout>
                <InvestigationsQueue />
              </DashboardLayout>
            }
          />
          <Route
            path="/investigations/:id"
            element={
              <DashboardLayout>
                <InvestigationDetails />
              </DashboardLayout>
            }
          />
          <Route
            path="/entities/:type/:id"
            element={
              <DashboardLayout>
                <EntityDetails />
              </DashboardLayout>
            }
          />
          <Route
            path="/integrations"
            element={
              <DashboardLayout>
                <Integrations />
              </DashboardLayout>
            }
          />
          <Route
            path="/reports"
            element={
              <DashboardLayout>
                <Reports />
              </DashboardLayout>
            }
          />
          <Route
            path="/settings"
            element={
              <DashboardLayout>
                <Settings />
              </DashboardLayout>
            }
          />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
