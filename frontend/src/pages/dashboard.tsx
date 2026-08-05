import { useMemo, useEffect } from "react";
import { useApi } from "@/hooks/useApi.ts";
import { apiFetch } from "@/lib/api.ts";
import { useToast } from "@/contexts/toast-context.tsx";

import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
} from "@/components/ui/card.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Badge } from "@/components/ui/badge.tsx";
import {
    Globe,
    CheckCircle,
    Activity,
    TrendingUp,
    AlertTriangle,
    Play,
    Square,
    Loader2,
    Server,
    Zap,
    XCircle,
} from 'lucide-react';
import type { Client } from "@/types";

export default function DashboardPage() {
    const { data: clients, isLoading, error, fetchData: fetchClients } = useApi<Client[]>("/clients");
    const { toast } = useToast();

    useEffect(() => {
        const interval = setInterval(() => {
            fetchClients();
        }, 30000);
        return () => clearInterval(interval);
    }, [fetchClients]);

    const stats = useMemo(() => {
        if (!Array.isArray(clients)) {
            return { total: 0, enabled: 0, running: 0, error: 0 };
        }
        return {
            total: clients.length,
            enabled: clients.filter(c => c.enabled).length,
            running: clients.filter(c => c.status === 'running').length,
            error: clients.filter(c => c.status === 'error').length,
        };
    }, [clients]);

    const recentClients = useMemo(() => {
        if (!Array.isArray(clients)) return [];
        return clients.slice(0, 8);
    }, [clients]);

    const handleBatchEnable = async (enabled: boolean) => {
        try {
            await apiFetch('/clients/batch-enable', {
                method: 'POST',
                body: JSON.stringify({ enabled }),
            });
            fetchClients();
            toast({
                type: "success",
                message: enabled ? "已启用所有客户端" : "已禁用所有客户端",
            });
        } catch {
            toast({
                type: "error",
                message: "操作失败",
            });
        }
    };

    if (isLoading && !clients) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (error) {
        return (
            <Card className="border-red-200 bg-red-50 dark:bg-red-950/10">
                <CardContent className="p-6">
                    <div className="flex items-center space-x-2 text-red-600">
                        <AlertTriangle className="h-5 w-5" />
                        <span>加载失败: {error.message}</span>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="h-full flex flex-col gap-4">
            <div className="flex-shrink-0">
                <h2 className="text-2xl font-bold tracking-tight">仪表盘</h2>
                <p className="text-muted-foreground text-sm mt-0.5">
                    FRP 客户端配置管理概览
                </p>
            </div>

            {/* 统计卡片 */}
            <div className="grid gap-3 grid-cols-2 md:grid-cols-4 flex-shrink-0">
                <Card className="transition-all duration-200 hover:shadow-md">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-3 px-4">
                        <CardTitle className="text-sm font-medium">客户端总数</CardTitle>
                        <div className="h-9 w-9 rounded-lg bg-blue-500/10 flex items-center justify-center">
                            <Globe className="h-5 w-5 text-blue-500" />
                        </div>
                    </CardHeader>
                    <CardContent className="pb-3 px-4">
                        <div className="text-3xl font-bold text-blue-500">{stats.total}</div>
                        <p className="text-xs text-muted-foreground mt-0.5">所有已配置的客户端</p>
                    </CardContent>
                </Card>
                <Card className="transition-all duration-200 hover:shadow-md">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-3 px-4">
                        <CardTitle className="text-sm font-medium">已启用</CardTitle>
                        <div className="h-9 w-9 rounded-lg bg-green-500/10 flex items-center justify-center">
                            <CheckCircle className="h-5 w-5 text-green-500" />
                        </div>
                    </CardHeader>
                    <CardContent className="pb-3 px-4">
                        <div className="text-3xl font-bold text-green-500">{stats.enabled}</div>
                        <p className="text-xs text-muted-foreground mt-0.5">当前启用的客户端数量</p>
                    </CardContent>
                </Card>
                <Card className="transition-all duration-200 hover:shadow-md">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-3 px-4">
                        <CardTitle className="text-sm font-medium">运行中</CardTitle>
                        <div className="h-9 w-9 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                            <Zap className="h-5 w-5 text-emerald-500" />
                        </div>
                    </CardHeader>
                    <CardContent className="pb-3 px-4">
                        <div className="text-3xl font-bold text-emerald-500">{stats.running}</div>
                        <p className="text-xs text-muted-foreground mt-0.5">正在运行的客户端</p>
                    </CardContent>
                </Card>
                <Card className="transition-all duration-200 hover:shadow-md">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 pt-3 px-4">
                        <CardTitle className="text-sm font-medium">异常</CardTitle>
                        <div className="h-9 w-9 rounded-lg bg-red-500/10 flex items-center justify-center">
                            <XCircle className="h-5 w-5 text-red-500" />
                        </div>
                    </CardHeader>
                    <CardContent className="pb-3 px-4">
                        <div className="text-3xl font-bold text-red-500">{stats.error}</div>
                        <p className="text-xs text-muted-foreground mt-0.5">运行异常的客户端</p>
                    </CardContent>
                </Card>
            </div>

            {/* 快捷操作和最近客户端 */}
            <div className="grid gap-3 md:grid-cols-2 flex-1 min-h-0">
                <Card className="flex flex-col">
                    <CardHeader className="pb-2 pt-4 flex-shrink-0">
                        <CardTitle className="flex items-center gap-2 text-base">
                            <TrendingUp className="h-4 w-4" />
                            快捷操作
                        </CardTitle>
                        <CardDescription className="text-xs">
                            批量启用或禁用所有客户端
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2 pb-4 flex-1">
                        <Button
                            variant="outline"
                            className="w-full justify-start"
                            onClick={() => handleBatchEnable(true)}
                        >
                            <Play className="mr-2 h-4 w-4" />
                            启用全部
                        </Button>
                        <Button
                            variant="outline"
                            className="w-full justify-start"
                            onClick={() => handleBatchEnable(false)}
                        >
                            <Square className="mr-2 h-4 w-4" />
                            禁用全部
                        </Button>
                    </CardContent>
                </Card>

                <Card className="flex flex-col">
                    <CardHeader className="pb-2 pt-4 flex-shrink-0">
                        <CardTitle className="flex items-center gap-2 text-base">
                            <Activity className="h-4 w-4" />
                            最近客户端
                        </CardTitle>
                        <CardDescription className="text-xs">
                            最近创建的 8 个客户端
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="pb-4 flex-1 overflow-auto">
                        {recentClients.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                                <Server className="h-8 w-8 mb-2 opacity-50" />
                                <p className="text-sm">暂无客户端</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {recentClients.map((client) => (
                                    <div
                                        key={client.id}
                                        className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                                    >
                                        <div className="flex items-center space-x-3">
                                            {client.status === 'running' ? (
                                                <Badge className="bg-green-500/80 dark:bg-green-800/50 dark:text-green-300/80 gap-1">
                                                    <Zap className="h-3 w-3" />
                                                    运行中
                                                </Badge>
                                            ) : client.status === 'error' ? (
                                                <Badge variant="destructive" className="gap-1 dark:bg-red-900/40 dark:text-red-300/80">
                                                    <XCircle className="h-3 w-3" />
                                                    异常
                                                </Badge>
                                            ) : (
                                                <Badge variant="secondary" className="gap-1">
                                                    <XCircle className="h-3 w-3" />
                                                    已停止
                                                </Badge>
                                            )}
                                            <span className="font-medium">{client.name}</span>
                                        </div>
                                        <span className="text-sm text-muted-foreground">
                                            {client.server_addr}:{client.remote_port}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
