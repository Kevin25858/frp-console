/**
 * 告警页面
 * 显示和管理所有告警信息
 */
import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "@/hooks/useApi.ts";
import { apiFetch } from "@/lib/api.ts";
import { useToast } from "@/contexts/toast-context.tsx";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Badge } from "@/components/ui/badge.tsx";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card.tsx";
import { AlertTriangle, CheckCircle, Trash2, RefreshCw, Bell } from "lucide-react";
import i18n from "@/i18n";
import type { Alert, AlertStats } from "@/types";

export default function AlertsPage() {
    const { t } = useTranslation();
    const { success, error: toastError } = useToast();
    const { data: alerts, isLoading, error, fetchData: fetchAlerts } = useApi<Alert[]>("/alerts");
    const { data: stats, fetchData: fetchStats } = useApi<AlertStats>("/alerts/stats");
    const [filter, setFilter] = useState<'all' | 'unresolved'>('all');
    const [resolving, setResolving] = useState<number | null>(null);
    const [clearing, setClearing] = useState(false);

    // 根据未解决数量动态设置默认过滤器
    useEffect(() => {
        if (stats) {
            if (stats.unresolved > 0) {
                setFilter('unresolved');
            } else {
                setFilter('all');
            }
        }
    }, [stats]);

    const filteredAlerts = Array.isArray(alerts) ? alerts.filter(alert => {
        if (filter === 'unresolved') return !alert.resolved;
        return true;
    }) : [];

    const handleResolve = async (alertId: number) => {
        setResolving(alertId);
        try {
            await apiFetch(`/alerts/${alertId}/resolve`, {
                method: 'POST',
            });
            fetchAlerts();
            fetchStats();
            success(t('alerts.resolveSuccess'));
        } catch (error) {
            toastError(t('alerts.actionError'));
            console.error('Failed to resolve alert:', error);
        } finally {
            setResolving(null);
        }
    };

    const handleClearResolved = async () => {
        setClearing(true);
        try {
            await apiFetch('/alerts/clear', {
                method: 'POST',
            });
            fetchAlerts();
            fetchStats();
            success(t('alerts.clearSuccess'));
        } catch (error) {
            toastError(t('alerts.actionError'));
            console.error('Failed to clear alerts:', error);
        } finally {
            setClearing(false);
        }
    };

    const handleRefresh = () => {
        fetchAlerts();
        fetchStats();
    };

    const formatTime = (timeStr: string) => {
        const date = new Date(timeStr);
        return date.toLocaleString(i18n.language === 'zh' ? 'zh-CN' : 'en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    };

    const getAlertTypeLabel = (type: string) => {
        return t(`alerts.types.${type}` as const) || type;
    };

    const getAlertTypeColor = (type: string) => {
        const colors: Record<string, string> = {
            restart_limit: 'bg-yellow-500',
            always_on_failed: 'bg-red-500',
            offline: 'bg-gray-500',
        };
        return colors[type] || 'bg-gray-500';
    };

    if (isLoading && !alerts) {
        return <div className="flex items-center justify-center h-64">{t('common.loading')}</div>;
    }

    if (error) {
        return <div className="text-destructive">{t('common.error')}: {error.message}</div>;
    }

    const resolvedCount = Array.isArray(alerts) ? alerts.filter(a => a.resolved).length : 0;
    const unresolvedCount = Array.isArray(alerts) ? alerts.filter(a => !a.resolved).length : 0;

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold flex items-center gap-2">
                    <Bell className="h-6 w-6" />
                    {t('alerts.title')}
                </h2>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRefresh}
                        disabled={isLoading}
                    >
                        <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                        {t('alerts.refresh')}
                    </Button>
                    {resolvedCount > 0 && (
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleClearResolved}
                            disabled={clearing}
                        >
                            <Trash2 className="h-4 w-4 mr-2" />
                            {t('alerts.clearResolved')}
                        </Button>
                    )}
                </div>
            </div>

            {/* 统计卡片 */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('alerts.totalAlerts')}</CardTitle>
                        <Bell className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.total ?? 0}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('alerts.unresolved')}</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-red-500">{stats?.unresolved ?? 0}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('alerts.resolved')}</CardTitle>
                        <CheckCircle className="h-4 w-4 text-green-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-500">{stats?.resolved ?? 0}</div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">{t('alerts.restartLimit')}</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-yellow-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats?.by_type?.restart_limit ?? 0}</div>
                    </CardContent>
                </Card>
            </div>

            {/* 过滤器 */}
            <div className="flex gap-2">
                <Button
                    variant={filter === 'all' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFilter('all')}
                >
                    {t('alerts.all')} ({stats?.total ?? 0})
                </Button>
                <Button
                    variant={filter === 'unresolved' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFilter('unresolved')}
                >
                    {t('alerts.unresolvedOnly')} ({unresolvedCount})
                </Button>
            </div>

            {/* 告警列表 */}
            {filteredAlerts.length === 0 ? (
                <Card>
                    <CardContent className="flex items-center justify-center h-48 text-muted-foreground">
                        {filter === 'all' ? t('alerts.noAlerts') : t('alerts.noUnresolved')}
                    </CardContent>
                </Card>
            ) : (
                <Card>
                    <CardContent className="p-0">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>{t('alerts.status')}</TableHead>
                                    <TableHead>{t('alerts.type')}</TableHead>
                                    <TableHead>{t('alerts.client')}</TableHead>
                                    <TableHead>{t('alerts.message')}</TableHead>
                                    <TableHead>{t('alerts.time')}</TableHead>
                                    <TableHead className="text-right">{t('common.actions')}</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredAlerts.map((alert) => (
                                    <TableRow key={alert.id}>
                                        <TableCell>
                                            {alert.resolved ? (
                                                <Badge variant="secondary" className="bg-green-100 text-green-800">
                                                    <CheckCircle className="h-3 w-3 mr-1" />
                                                    {t('alerts.resolvedStatus')}
                                                </Badge>
                                            ) : (
                                                <Badge variant="destructive">
                                                    <AlertTriangle className="h-3 w-3 mr-1" />
                                                    {t('alerts.unresolvedStatus')}
                                                </Badge>
                                            )}
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-2">
                                                <div className={`w-2 h-2 rounded-full ${getAlertTypeColor(alert.alert_type)}`} />
                                                {getAlertTypeLabel(alert.alert_type)}
                                            </div>
                                        </TableCell>
                                        <TableCell>{alert.client_name || '-'}</TableCell>
                                        <TableCell className="max-w-md truncate">{alert.message}</TableCell>
                                        <TableCell className="text-sm text-muted-foreground">
                                            {formatTime(alert.sent_at)}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            {!alert.resolved && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleResolve(alert.id)}
                                                    disabled={resolving === alert.id}
                                                >
                                                    <CheckCircle className="h-4 w-4 mr-1" />
                                                    {resolving === alert.id ? t('alerts.resolving') : t('alerts.resolve')}
                                                </Button>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
