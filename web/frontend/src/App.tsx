import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from '@/components/layout/Layout';
import { RunsDashboard } from '@/components/run/RunsTable';
import { RunDetailPage } from '@/components/run/RunDetailPage';
import { ReportPage } from '@/components/report/ReportPage';
import { SettingsPage } from '@/components/SettingsPage';
import { LogsPage } from '@/components/LogsPage';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5000,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<RunsDashboard />} />
              <Route path="runs/:runId" element={<RunDetailPage />} />
              <Route path="runs/:runId/report" element={<ReportPage />} />
              <Route path="logs" element={<LogsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
