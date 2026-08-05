import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import DashboardPage from "@/pages/dashboard.tsx";
import ClientListPage from "@/pages/clients/list.tsx";
import LoginPage from "@/pages/login.tsx";
import SettingsPage from "@/pages/settings.tsx";
import NotFoundPage from "@/pages/not-found.tsx";
import { ProtectedRoute } from "@/components/protected-route.tsx";
import { ToastProvider } from "@/contexts/toast-context.tsx";
import { AuthProvider } from "@/contexts/auth-context.tsx";
import { Toaster } from "@/components/toaster.tsx";
import { ErrorBoundary, PageErrorBoundary } from "@/components/error-boundary.tsx";

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
        path: "settings",
        element: (
          <PageErrorBoundary>
            <SettingsPage />
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
