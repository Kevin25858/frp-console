import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import DashboardPage from "@/pages/dashboard";
import ClientListPage from "@/pages/clients/list";
import AlertsPage from "@/pages/alerts";
import LoginPage from "@/pages/login";
import SettingsPage from "@/pages/settings";
import AuditLogsPage from "@/pages/audit-logs";
import UsersPage from "@/pages/users";
import NotFoundPage from "@/pages/not-found";
import { ProtectedRoute } from "@/components/protected-route";
import { ToastProvider } from "@/contexts/toast-context";
import { AuthProvider } from "@/contexts/auth-context";
import { Toaster } from "@/components/toaster";
import { ErrorBoundary, PageErrorBoundary } from "@/components/error-boundary";

const router = createBrowserRouter([
  {
    path: "/",
    element: <ProtectedRoute />,
    errorElement: <NotFoundPage />,
    children: [
      {
        index: true,
        element: (
          <PageErrorBoundary>
            <DashboardPage />
          </PageErrorBoundary>
        ),
      },
      {
        path: "clients",
        element: (
          <PageErrorBoundary>
            <ClientListPage />
          </PageErrorBoundary>
        ),
      },
      {
        path: "alerts",
        element: (
          <PageErrorBoundary>
            <AlertsPage />
          </PageErrorBoundary>
        ),
      },
      {
        path: "audit-logs",
        element: (
          <PageErrorBoundary>
            <AuditLogsPage />
          </PageErrorBoundary>
        ),
      },
      {
        path: "settings",
        element: (
          <PageErrorBoundary>
            <SettingsPage />
          </PageErrorBoundary>
        ),
      },
      {
        path: "users",
        element: (
          <PageErrorBoundary>
            <UsersPage />
          </PageErrorBoundary>
        ),
      },
      {
        path: "*",
        element: <NotFoundPage />,
      },
    ],
  },
  {
    path: "/login",
    element: (
      <PageErrorBoundary>
        <LoginPage />
      </PageErrorBoundary>
    ),
  },
  {
    path: "*",
    element: <Navigate to="/login" replace />,
  },
]);

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <RouterProvider router={router} />
          <Toaster />
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
