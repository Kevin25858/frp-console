import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "@/hooks/useApi";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Search, Shield, Download, Calendar, RefreshCw, Activity, User, AlertTriangle } from "lucide-react";

interface AuditLog {
  id: number;
  action: string;
  details: string;
  level: string;
  user: string;
  ip_address: string;
  user_agent: string;
  created_at: string;
}

interface AuditStats {
  total: number;
  actions: Array<{ action: string; count: number }>;
  users: Array<{ user: string; count: number }>;
  levels: Array<{ level: string; count: number }>;
  period_days: number;
}

export default function AuditLogsPage() {
  const { t } = useTranslation();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [levelFilter, setLevelFilter] = useState("");

  const { data: logsData, error: logsError, fetchData: fetchLogs } = useApi<{success: boolean; logs: AuditLog[]; count: number}>("/audit-logs");
  const { data: statsData } = useApi<{success: boolean; statistics: AuditStats}>("/audit-logs/statistics");

  // 当数据加载完成时更新状态
  useMemo(() => {
    if (logsData?.success && Array.isArray(logsData.logs)) {
      setLogs(logsData.logs);
      setIsLoading(false);
      setError(null);
    }
  }, [logsData]);

  // 处理错误状态
  useMemo(() => {
    if (logsError) {
      setIsLoading(false);
      setError(logsError.body?.error || logsError.message || t('auditLogs.loadError'));
    }
  }, [logsError, t]);

  useMemo(() => {
    if (statsData?.success && statsData.statistics) {
      setStats(statsData.statistics);
    }
  }, [statsData]);

  // 过滤日志
  const filteredLogs = useMemo(() => {
    if (!Array.isArray(logs)) return [];
    return logs.filter((log) => {
      const matchesSearch =
        searchTerm === "" ||
        log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.ip_address.includes(searchTerm);

      const matchesAction = actionFilter === "" || log.action === actionFilter;
      const matchesLevel = levelFilter === "" || log.level === levelFilter;

      return matchesSearch && matchesAction && matchesLevel;
    });
  }, [logs, searchTerm, actionFilter, levelFilter]);

  // 获取唯一操作类型
  const uniqueActions = useMemo(() => {
    if (!Array.isArray(logs)) return [];
    const actions = new Set(logs.map((log) => log.action));
    return Array.from(actions).sort();
  }, [logs]);

  // 获取唯一日志级别
  const uniqueLevels = useMemo(() => {
    if (!Array.isArray(logs)) return [];
    const levels = new Set(logs.map((log) => log.level));
    return Array.from(levels).sort();
  }, [logs]);

  const getLevelBadgeVariant = (level: string) => {
    switch (level) {
      case "INFO":
        return "default";
      case "WARNING":
        return "secondary";
      case "ERROR":
        return "destructive";
      case "CRITICAL":
        return "destructive";
      default:
        return "secondary";
    }
  };

  const handleExport = () => {
    const data = filteredLogs.map((log) => ({
      [t('auditLogs.time')]: log.created_at,
      [t('auditLogs.action')]: log.action,
      [t('auditLogs.user')]: log.user,
      [t('auditLogs.level')]: log.level,
      IP: log.ip_address,
      [t('auditLogs.details')]: log.details,
    }));

    const headers = Object.keys(data[0] || {}).join(",");
    const rows = data.map((row) => Object.values(row).join(","));

    const csv = [headers, ...rows].join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `audit-logs-${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">{t('auditLogs.loading')}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <div className="text-destructive font-medium">{error}</div>
        <Button variant="outline" onClick={fetchLogs}>
          <RefreshCw className="mr-2 h-4 w-4" />
          {t('common.retry')}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">{t('auditLogs.title')}</h2>
        <p className="text-muted-foreground mt-1">
          {t('auditLogs.subtitle')}
        </p>
      </div>

      {/* 统计信息 */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('auditLogs.totalActions')}</CardTitle>
              <Shield className="h-5 w-5 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {t('auditLogs.lastDays', { days: stats.period_days })}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('auditLogs.commonActions')}</CardTitle>
              <Activity className="h-5 w-5 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats.actions.length > 0 ? stats.actions[0].action : '-'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {stats.actions.length > 0 ? t('auditLogs.actionCount', { count: stats.actions[0].count }) : t('auditLogs.noData')}
              </p>
              <div className="space-y-2 mt-3 pt-3 border-t">
                {stats.actions.slice(0, 3).map((action) => (
                  <div key={action.action} className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{action.action}</span>
                    <span className="font-medium">{action.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('auditLogs.activeUsers')}</CardTitle>
              <User className="h-5 w-5 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.users.length}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {t('auditLogs.lastDays', { days: stats.period_days })}
              </p>
              <div className="space-y-2 mt-3 pt-3 border-t">
                {stats.users.slice(0, 3).map((user) => (
                  <div key={user.user} className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{user.user}</span>
                    <span className="font-medium">{user.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{t('auditLogs.logLevels')}</CardTitle>
              <AlertTriangle className="h-5 w-5 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats.levels
                  .filter(l => l.level === 'WARNING' || l.level === 'ERROR' || l.level === 'CRITICAL')
                  .reduce((sum, l) => sum + l.count, 0)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {t('auditLogs.warningErrorCritical')}
              </p>
              <div className="space-y-2 mt-3 pt-3 border-t">
                {stats.levels.map((level) => (
                  <div key={level.level} className="flex justify-between text-sm">
                    <Badge variant={getLevelBadgeVariant(level.level)}>
                      {level.level}
                    </Badge>
                    <span className="font-medium">{level.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 过滤器 */}
      <Card>
        <CardHeader>
          <CardTitle>{t('auditLogs.filters')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="search">{t('common.search')}</Label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder={t('auditLogs.searchPlaceholder')}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="action">{t('auditLogs.actionType')}</Label>
              <select
                id="action"
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                <option value="">{t('auditLogs.allActions')}</option>
                {uniqueActions.map((action) => (
                  <option key={action} value={action}>
                    {action}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="level">{t('auditLogs.logLevel')}</Label>
              <select
                id="level"
                value={levelFilter}
                onChange={(e) => setLevelFilter(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                <option value="">{t('auditLogs.allLevels')}</option>
                {uniqueLevels.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>{t('common.actions')}</Label>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchLogs}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  {t('common.refresh')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExport}
                >
                  <Download className="mr-2 h-4 w-4" />
                  {t('common.export')}
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 日志列表 */}
      <Card>
        <CardHeader>
          <CardTitle>{t('auditLogs.logList')}</CardTitle>
          <CardDescription>
            {t('auditLogs.showingRecords', { count: filteredLogs.length })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('auditLogs.time')}</TableHead>
                  <TableHead>{t('auditLogs.action')}</TableHead>
                  <TableHead>{t('auditLogs.user')}</TableHead>
                  <TableHead>{t('auditLogs.level')}</TableHead>
                  <TableHead>{t('auditLogs.ipAddress')}</TableHead>
                  <TableHead>{t('auditLogs.details')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="text-sm">
                      <div className="flex items-center space-x-2">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        <span>{log.created_at}</span>
                      </div>
                    </TableCell>
                    <TableCell className="font-medium">{log.action}</TableCell>
                    <TableCell>{log.user}</TableCell>
                    <TableCell>
                      <Badge variant={getLevelBadgeVariant(log.level)}>
                        {log.level}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{log.ip_address}</TableCell>
                    <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                      {log.details || "-"}
                    </TableCell>
                  </TableRow>
                ))}
                {filteredLogs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                      {t('auditLogs.noLogs')}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
