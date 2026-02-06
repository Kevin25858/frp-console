import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "@/hooks/useApi";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/contexts/toast-context";

import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Globe,
    Server,
    XCircle,
    CheckCircle,
    Activity,
    TrendingUp,
    AlertTriangle,
    Play,
    Square,
    RotateCcw,
} from 'lucide-react';
import type { Client } from "@/types";

export default function DashboardPage() {
    const { t } = useTranslation();
    const { data: clients, isLoading, error, fetchData: fetchClients } = useApi<Client[]>("/clients");
    const { toast } = useToast();

    const stats = useMemo(() => {
        if (!Array.isArray(clients)) {
            return {
                total: 0,
                running: 0,
                stopped: 0,
                error: 0,
                always_on: 0,
            };
        }
        return {
            total: clients.length,
            running: clients.filter(c => c.status === 'running').length,
            stopped: clients.filter(c => c.status === 'stopped').length,
            error: clients.filter(c => c.status === 'error').length,
            always_on: clients.filter(c => c.always_on).length,
        };
    }, [clients]);

    const recentClients = useMemo(() => {
        if (!Array.isArray(clients)) return [];
        return clients.slice(0, 5);
    }, [clients]);

    const handleQuickAction = async (clientId: number, action: string) => {
        try {
            await apiFetch(`/clients/${clientId}/${action}`, {
                method: 'POST',
            });
            fetchClients();
            toast({
                type: "success",
                title: t("dashboard.actionSuccess"),
                message: `${action} ${t("dashboard.actionSuccess")}`,
            });
        } catch (_error) {
            toast({
                type: "error",
                title: t("dashboard.actionError"),
                message: `${action} ${t("dashboard.actionError")}`,
            });
        }
    };

    const statCards = [
        { 
            title: t("dashboard.totalClients"), 
            value: stats.total, 
            icon: <Globe className="h-6 w-6 text-muted-foreground" />,
            description: t("dashboard.totalClientsDesc"),
            color: "text-blue-500"
        },
        { 
            title: t("dashboard.running"), 
            value: stats.running, 
            icon: <CheckCircle className="h-6 w-6 text-green-500" />,
            description: t("dashboard.runningDesc"),
            color: "text-green-500"
        },
        { 
            title: t("dashboard.stopped"), 
            value: stats.stopped, 
            icon: <XCircle className="h-6 w-6 text-gray-500" />,
            description: t("dashboard.stoppedDesc"),
            color: "text-gray-500"
        },
        { 
            title: t("dashboard.error"), 
            value: stats.error, 
            icon: <Server className="h-6 w-6 text-red-500" />,
            description: t("dashboard.errorDesc"),
            color: "text-red-500"
        },
        {
            title: t("dashboard.alwaysOn"),
            value: stats.always_on,
            icon: <Activity className="h-6 w-6 text-purple-500" />,
            description: t("dashboard.alwaysOnDesc"),
            color: "text-purple-500"
        },
    ];

    if (isLoading && !clients) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-muted-foreground">{t("dashboard.loading")}</div>
            </div>
        );
    }

    if (error) {
        return (
            <Card className="border-red-200 bg-red-50 dark:bg-red-950/10">
                <CardContent className="p-6">
                    <div className="flex items-center space-x-2 text-red-600">
                        <AlertTriangle className="h-5 w-5" />
                        <span>{t("dashboard.loadError")}: {error.message}</span>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="h-full flex flex-col gap-4">
            {/* 标题和描述 */}
            <div className="flex-shrink-0">
                <h2 className="text-2xl font-bold tracking-tight">{t("dashboard.title")}</h2>
                <p className="text-muted-foreground text-sm mt-0.5">
                    {t("dashboard.subtitle")}
                </p>
            </div>

            {/* 统计卡片 */}
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5 flex-shrink-0">
                {statCards.map((stat) => (
                    <Card key={stat.title} className="hover:shadow-md transition-shadow">
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-3 px-4">
                            <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                            {stat.icon}
                        </CardHeader>
                        <CardContent className="pb-3 px-4">
                            <div className={`text-xl font-bold ${stat.color}`}>
                                {stat.value}
                            </div>
                            <p className="text-xs text-muted-foreground mt-0.5">
                                {stat.description}
                            </p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* 快捷操作和最近客户端 */}
            <div className="grid gap-3 md:grid-cols-2 flex-1 min-h-0">
                {/* 快捷操作 */}
                <Card className="flex flex-col">
                    <CardHeader className="pb-2 pt-4 flex-shrink-0">
                        <CardTitle className="flex items-center gap-2 text-base">
                            <TrendingUp className="h-4 w-4" />
                            {t("dashboard.quickActions")}
                        </CardTitle>
                        <CardDescription className="text-xs">
                            {t("dashboard.quickActionsDesc")}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2 pb-4 flex-1">
                        <Button 
                            variant="outline" 
                            className="w-full justify-start"
                            onClick={() => {
                                clients?.forEach(c => {
                                    if (c.status !== 'running') {
                                        handleQuickAction(c.id, 'start');
                                    }
                                });
                            }}
                        >
                            <Play className="mr-2 h-4 w-4" />
                            {t("dashboard.startAll")}
                        </Button>
                        <Button 
                            variant="outline" 
                            className="w-full justify-start"
                            onClick={() => {
                                clients?.forEach(c => {
                                    if (c.status === 'running') {
                                        handleQuickAction(c.id, 'stop');
                                    }
                                });
                            }}
                        >
                            <Square className="mr-2 h-4 w-4" />
                            {t("dashboard.stopAll")}
                        </Button>
                        <Button 
                            variant="outline" 
                            className="w-full justify-start"
                            onClick={() => {
                                clients?.forEach(c => {
                                    handleQuickAction(c.id, 'restart');
                                });
                            }}
                        >
                            <RotateCcw className="mr-2 h-4 w-4" />
                            {t("dashboard.restartAll")}
                        </Button>
                    </CardContent>
                </Card>

                {/* 最近客户端 */}
                <Card className="flex flex-col">
                    <CardHeader className="pb-2 pt-4 flex-shrink-0">
                        <CardTitle className="flex items-center gap-2 text-base">
                            <Activity className="h-4 w-4" />
                            {t("dashboard.recentClients")}
                        </CardTitle>
                        <CardDescription className="text-xs">
                            {t("dashboard.recentClientsDesc")}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="pb-4 flex-1 overflow-auto">
                        {recentClients.length === 0 ? (
                            <div className="text-center py-8 text-muted-foreground">
                                {t("dashboard.noClients")}
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {recentClients.map((client) => (
                                    <div 
                                        key={client.id}
                                        className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                                    >
                                        <div className="flex items-center space-x-3">
                                            <Badge 
                                                variant={
                                                    client.status === 'running' ? 'default' : 
                                                    client.status === 'stopped' ? 'secondary' : 
                                                    'destructive'
                                                }
                                            >
                                                {client.status}
                                            </Badge>
                                            <span className="font-medium">{client.name}</span>
                                        </div>
                                        <div className="flex items-center space-x-2">
                                            {client.always_on && (
                                                <Badge variant="outline" className="text-xs">
                                                    Always-On
                                                </Badge>
                                            )}
                                            <span className="text-sm text-muted-foreground">
                                                {client.server_addr}:{client.remote_port}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* 系统健康 */}
            <Card className="flex-shrink-0">
                <CardHeader className="pb-2 pt-4">
                    <CardTitle className="flex items-center gap-2 text-base">
                        <Server className="h-4 w-4" />
                        {t("dashboard.systemHealth")}
                    </CardTitle>
                </CardHeader>
                <CardContent className="pb-4">
                    <div className="grid gap-4 md:grid-cols-3">
                        <div className="flex items-center justify-between p-3 rounded-lg bg-green-50 dark:bg-green-950/10 border border-green-200 dark:border-green-900">
                            <span className="text-sm font-medium">{t("dashboard.apiService")}</span>
                            <div className="flex items-center space-x-2">
                                <CheckCircle className="h-4 w-4 text-green-600" />
                                <span className="text-sm text-green-600">{t("dashboard.healthy")}</span>
                            </div>
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-lg bg-green-50 dark:bg-green-950/10 border border-green-200 dark:border-green-900">
                            <span className="text-sm font-medium">{t("dashboard.database")}</span>
                            <div className="flex items-center space-x-2">
                                <CheckCircle className="h-4 w-4 text-green-600" />
                                <span className="text-sm text-green-600">{t("dashboard.healthy")}</span>
                            </div>
                        </div>
                        <div className="flex items-center justify-between p-3 rounded-lg bg-green-50 dark:bg-green-950/10 border border-green-200 dark:border-green-900">
                            <span className="text-sm font-medium">{t("dashboard.frpcProcess")}</span>
                            <div className="flex items-center space-x-2">
                                <CheckCircle className="h-4 w-4 text-green-600" />
                                <span className="text-sm text-green-600">{stats.running} {t("dashboard.running")}</span>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
