import { useState } from "react";
import { ModeToggle } from "./mode-toggle.tsx";
import { NavLink } from "react-router-dom";
import { Menu, X, LogOut, Radio, LayoutDashboard, Server, Settings } from "lucide-react";
import { Button } from "@/components/ui/button.tsx";
import { useAuth } from "@/contexts/auth-context.tsx";

export function Layout({ children }: { children: React.ReactNode }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { logout } = useAuth();

  const linkClasses = "flex items-center gap-3 px-3 py-2 rounded-md transition-all duration-200";
  const activeLinkClasses = "bg-primary text-primary-foreground shadow-sm";
  const inactiveLinkClasses = "text-muted-foreground hover:bg-muted hover:text-foreground";

  const navLinks = [
    { to: "/", label: "仪表盘", icon: LayoutDashboard },
    { to: "/clients", label: "客户端管理", icon: Server },
    { to: "/settings", label: "设置", icon: Settings },
  ];

  const handleLogout = () => {
    logout();
    setMobileMenuOpen(false);
  };

  return (
    <div className="h-screen w-full flex flex-col md:flex-row overflow-hidden">
      {/* 移动端顶部导航栏 */}
      <header className="md:hidden flex items-center justify-between p-4 border-b bg-background flex-shrink-0">
        <div className="flex items-center gap-2">
          <Radio className="h-5 w-5 text-primary" />
          <h1 className="text-xl font-bold">FRP Console</h1>
        </div>
        <div className="flex items-center space-x-2">
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
              <div className="flex items-center gap-2">
                <Radio className="h-6 w-6 text-primary" />
                <h1 className="text-2xl font-bold">FRP Console</h1>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setMobileMenuOpen(false)}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
            <nav className="flex flex-col space-y-1 flex-1">
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
                  <link.icon className="h-4 w-4" />
                  {link.label}
                </NavLink>
              ))}
            </nav>
            <div className="pt-4 border-t space-y-2">
              <p className="text-xs text-muted-foreground text-center">v1.0.0</p>
              <Button
                variant="ghost"
                className="w-full justify-start text-muted-foreground hover:text-destructive"
                onClick={handleLogout}
              >
                <LogOut className="mr-2 h-4 w-4" />
                退出登录
              </Button>
            </div>
          </aside>
        </div>
      )}

      {/* 桌面端侧边栏 */}
      <aside className="hidden md:flex bg-background border-r w-64 p-4 flex-col flex-shrink-0">
        <div className="flex items-center gap-2 mb-8">
          <Radio className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">FRP Console</h1>
        </div>
        <nav className="flex flex-col space-y-1 flex-1">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end
              className={({ isActive }) =>
                `${linkClasses} ${isActive ? activeLinkClasses : inactiveLinkClasses}`
              }
            >
              <link.icon className="h-4 w-4" />
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="pt-4 border-t space-y-2">
          <p className="text-xs text-muted-foreground text-center">v1.0.0</p>
          <Button
            variant="ghost"
            className="w-full justify-start text-muted-foreground hover:text-destructive"
            onClick={handleLogout}
          >
            <LogOut className="mr-2 h-4 w-4" />
            退出登录
          </Button>
        </div>
      </aside>

      {/* 主内容区域 */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <header className="hidden md:flex border-b p-4 justify-end items-center flex-shrink-0 gap-2">
          <ModeToggle />
        </header>
        <main className="flex-1 p-3 md:p-4 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
