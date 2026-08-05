import { useEffect, useState } from "react";
import { Navigate, useNavigate, useRouteError, isRouteErrorResponse } from "react-router-dom";
import { useAuth } from "@/contexts/auth-context.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Home, ArrowLeft, AlertCircle } from "lucide-react";

export default function NotFoundPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const error = useRouteError();
  const [countdown, setCountdown] = useState(3);

  const is404 = isRouteErrorResponse(error) && error.status === 404;

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    } else {
      navigate(isAuthenticated ? "/" : "/login", { replace: true });
    }
  }, [countdown, isAuthenticated, navigate]);

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
          <h1 className="text-4xl font-bold tracking-tight">404</h1>
          <p className="text-xl text-muted-foreground">
            {is404 ? "页面不存在" : "发生错误"}
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button onClick={() => navigate("/", { replace: true })}>
            <Home className="w-4 h-4 mr-2" />
            返回首页
          </Button>
          <Button variant="outline" onClick={() => navigate(-1)}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          {countdown} 秒后自动跳转
        </p>
      </div>
    </div>
  );
}
