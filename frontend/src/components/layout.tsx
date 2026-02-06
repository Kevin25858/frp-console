import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ModeToggle } from "./mode-toggle";
import { LanguageToggle } from "./language-toggle";
import { NavLink } from "react-router-dom";
import { Menu, X, LogOut, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";

export function Layout({ children }: { children: React.ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { logout, userRole } = useAuth();
  const { t } = useTranslation();

  const linkClasses = "p-2 rounded-md transition-colors";
  const activeLinkClasses = "bg-primary text-primary-foreground";
  const inactiveLinkClasses = "text-muted-foreground hover:bg-muted hover:text-foreground";

  const navLinks = [
    { to: "/", label: t("nav.dashboard") },
    { to: "/clients", label: t("nav.clients") },
    { to: "/alerts", label: t("nav.alerts") },
    { to: "/audit-logs", label: t("nav.auditLogs") },
    { to: "/settings", label: t("nav.settings") },
    ...(userRole === 'admin' ? [{ to: "/users", label: t("nav.users"), icon: Users }] : []),
  ];

  const handleLogout = () => {
    logout();
    setMobileMenuOpen(false);
  };

  return (
    <div className="h-screen w-full flex flex-col md:flex-row overflow-hidden">
      {/* 移动端顶部导航栏 */}
      <header className="md:hidden flex items-center justify-between p-4 border-b bg-background flex-shrink-0">
        <h1 className="text-xl font-bold">{t("common.appName")}</h1>
        <div className="flex items-center space-x-2">
          <LanguageToggle />
          <ModeToggle />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </header>

      {/* 移动端侧边栏（抽屉式） */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div 
            className="fixed inset-0 bg-black/50" 
            onClick={() => setMobileMenuOpen(false)}
          />
          <aside className="fixed left-0 top-0 bottom-0 w-64 bg-background border-r p-4 flex flex-col z-10">
            <div className="flex items-center justify-between mb-8">
              <h1 className="text-2xl font-bold">{t("common.appName")}</h1>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setMobileMenuOpen(false)}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
            <nav className="flex flex-col space-y-2 flex-1">
              {navLinks.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `${linkClasses} ${isActive ? activeLinkClasses : inactiveLinkClasses}`
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
            <div className="pt-4 border-t">
              <Button
                variant="ghost"
                className="w-full justify-start text-muted-foreground hover:text-destructive"
                onClick={handleLogout}
              >
                <LogOut className="mr-2 h-4 w-4" />
                {t("nav.logout")}
              </Button>
            </div>
          </aside>
        </div>
      )}

      {/* 桌面端侧边栏 */}
      <aside className="hidden md:flex bg-background border-r w-64 p-4 flex-col flex-shrink-0">
        <h1 className="text-2xl font-bold mb-8">{t("common.appName")}</h1>
        <nav className="flex flex-col space-y-2 flex-1">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end
              className={({ isActive }) =>
                `${linkClasses} ${isActive ? activeLinkClasses : inactiveLinkClasses}`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="pt-4 border-t">
          <Button
            variant="ghost"
            className="w-full justify-start text-muted-foreground hover:text-destructive"
            onClick={handleLogout}
          >
            <LogOut className="mr-2 h-4 w-4" />
            {t("nav.logout")}
          </Button>
        </div>
      </aside>

      {/* 主内容区域 */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* 桌面端顶部栏 */}
        <header className="hidden md:flex border-b p-4 justify-end items-center flex-shrink-0 gap-2">
          <LanguageToggle />
          <ModeToggle />
        </header>
        <main className="flex-1 p-3 md:p-4 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}