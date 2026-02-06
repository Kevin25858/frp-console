import { useEffect, useState } from "react";
import { Navigate, useNavigate, useRouteError, isRouteErrorResponse } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/contexts/auth-context.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Home, ArrowLeft, AlertCircle } from "lucide-react";

export default function NotFoundPage() {
  const { t } = useTranslation();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const error = useRouteError();
  const [countdown, setCountdown] = useState(3);

  const is404 = isRouteErrorResponse(error) && error.status === 404;

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => {
        setCountdown(countdown - 1);
      }, 1000);
      return () => clearTimeout(timer);
    } else {
      // 倒计时结束，自动跳转
      if (isAuthenticated) {
        navigate("/", { replace: true });
      } else {
        navigate("/login", { replace: true });
      }
    }
  }, [countdown, isAuthenticated, navigate]);

  // 如果未登录，直接跳转到登录页
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-6 p-8">
        <div className="flex justify-center">
          <div className="w-20 h-20 rounded-full bg-muted flex items-center justify-center">
            <AlertCircle className="w-10 h-10 text-muted-foreground" />
          </div>
        </div>

        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">{t('notFound.title')}</h1>
          <p className="text-xl text-muted-foreground">
            {is404 ? t('notFound.description') : t('common.error')}
          </p>
        </div>

        <p className="text-sm text-muted-foreground max-w-md mx-auto">
          {is404
            ? t('notFound.description')
            : t('common.error')}
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button onClick={() => navigate("/", { replace: true })}>
            <Home className="w-4 h-4 mr-2" />
            {t('notFound.backHome')}
          </Button>
          <Button variant="outline" onClick={() => navigate(-1)}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            {t('common.back')}
          </Button>
        </div>

        <p className="text-xs text-muted-foreground">
          {countdown} {t('common.seconds')} {t('notFound.autoRedirect')}
        </p>
      </div>
    </div>
  );
}
