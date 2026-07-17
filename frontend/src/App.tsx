import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { DashboardLayout } from './layouts/DashboardLayout';
import { LandingPage } from './pages/LandingPage';
import { Dashboard } from './pages/Dashboard';
import { InvestigationsQueue } from './pages/InvestigationsQueue';
import { InvestigationDetails } from './pages/InvestigationDetails';
import { EntityDetails } from './pages/EntityDetails';
import { Integrations } from './pages/Integrations';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';
import { AuthGuard } from './components/AuthGuard';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route
            path="/dashboard"
            element={
              <AuthGuard>
                <DashboardLayout>
                  <Dashboard />
                </DashboardLayout>
              </AuthGuard>
            }
          />
          <Route
            path="/investigations"
            element={
              <AuthGuard>
                <DashboardLayout>
                  <InvestigationsQueue />
                </DashboardLayout>
              </AuthGuard>
            }
          />
          <Route
            path="/investigations/:id"
            element={
              <AuthGuard>
                <DashboardLayout>
                  <InvestigationDetails />
                </DashboardLayout>
              </AuthGuard>
            }
          />
          <Route
            path="/entities/:type/:id"
            element={
              <AuthGuard>
                <DashboardLayout>
                  <EntityDetails />
                </DashboardLayout>
              </AuthGuard>
            }
          />
          <Route
            path="/integrations"
            element={
              <AuthGuard>
                <DashboardLayout>
                  <Integrations />
                </DashboardLayout>
              </AuthGuard>
            }
          />
          <Route
            path="/reports"
            element={
              <AuthGuard>
                <DashboardLayout>
                  <Reports />
                </DashboardLayout>
              </AuthGuard>
            }
          />
          <Route
            path="/settings"
            element={
              <AuthGuard>
                <DashboardLayout>
                  <Settings />
                </DashboardLayout>
              </AuthGuard>
            }
          />
          <Route path="*" element={<LandingPage />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;

