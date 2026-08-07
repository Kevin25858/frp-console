import { useState, useMemo, useEffect, useRef } from "react";
import { useApi } from "@/hooks/useApi.ts";
import { apiFetch } from "@/lib/api.ts";
import { useToast } from "@/contexts/toast-context.tsx";
import { AddClientDialog } from "./add-client-dialog.tsx";
import { ViewConfigDialog } from "./view-config-dialog.tsx";
import { ViewLogsDialog } from "./view-logs-dialog.tsx";
import { Input } from "@/components/ui/input.tsx";
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
import { Card, CardContent } from "@/components/ui/card.tsx";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog.tsx";
import { FileText, Trash2, Play, Square, RotateCcw, ScrollText, CheckCircle2, XCircle, AlertCircle, Loader2 } from "lucide-react";
import type { Client } from "@/types";

export default function ClientListPage() {
    const { data: clients, isLoading, error, fetchData: fetchClients } = useApi<Client[]>("/clients");
    const { success, error: toastError } = useToast();
    const [searchTerm, setSearchTerm] = useState("");
    const [actionLoading, setActionLoading] = useState<{ id: number; action: string } | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const isFetchingRef = useRef(false);

    // 自动刷新数据 - 带防抖和取消机制
    useEffect(() => {
        const interval = setInterval(() => {
            // 如果上一次请求还在进行中，取消它
            if (isFetchingRef.current && abortControllerRef.current) {
                abortControllerRef.current.abort();
            }

            // 创建新的 AbortController
            abortControllerRef.current = new AbortController();
            isFetchingRef.current = true;

            fetchClients(abortControllerRef.current.signal).finally(() => {
                isFetchingRef.current = false;
            });
        }, 5000); // 每5秒刷新一次

        return () => {
            clearInterval(interval);
            // 清理时取消正在进行的请求
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, [fetchClients]);

    const filteredClients = useMemo(() => {
        if (!Array.isArray(clients)) return [];
        return clients.filter(client =>
            client.name.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }, [clients, searchTerm]);

    // 客户端启动/停止/重启
    const handleClientAction = async (client: Client, action: 'start' | 'stop' | 'restart') => {
        const actionLabel = { start: '启动', stop: '停止', restart: '重启' }[action];
        setActionLoading({ id: client.id, action });
        try {
            await apiFetch(`/clients/${client.id}/${action}`, {
                method: 'POST',
            });
            success(`${actionLabel}成功`);
            fetchClients();
        } catch (error) {
            console.error(`Failed to ${action} client ${client.id}:`, error);
            toastError(`${actionLabel}失败`);
        } finally {
            setActionLoading(null);
        }
    };

    // 判断指定按钮是否处于加载中
    const isActionLoading = (client: Client, action: 'start' | 'stop' | 'restart') =>
        actionLoading?.id === client.id && actionLoading?.action === action;

    // 加载中显示的旋转图标
    const LoadingIcon = () => <Loader2 className="h-4 w-4 animate-spin" />;

    const handleDelete = async (clientId: number) => {
        try {
            await apiFetch(`/clients/${clientId}`, { method: 'DELETE' });
            fetchClients();
            success('删除成功');
        } catch (error) {
            console.error(`Failed to delete client ${clientId}:`, error);
            toastError('删除失败');
        }
    };

    if (isLoading && !clients) {
        return <div>加载中...</div>
    }

    if (error) {
        return <div>加载失败: {error.message}</div>
    }

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">客户端列表</h2>
                <div className="flex items-center space-x-2">
                    <Input
                        placeholder="搜索客户端名称..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-64"
                    />
                    <AddClientDialog onClientAdded={fetchClients} />
                </div>
            </div>

            <div className="border rounded-lg">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>名称</TableHead>
                            <TableHead className="text-center">状态</TableHead>
                            <TableHead>本地端口</TableHead>
                            <TableHead>远程端口</TableHead>
                            <TableHead>服务器地址</TableHead>
                            <TableHead className="text-right">操作</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {filteredClients.map((client) => (
                            <TableRow key={client.id}>
                                <TableCell className="font-medium">{client.name}</TableCell>
                                <TableCell className="text-center">
                                    {actionLoading?.id === client.id ? (
                                        <Badge variant="secondary" className="gap-1">
                                            <Loader2 className="h-3 w-3 animate-spin" />
                                            处理中
                                        </Badge>
                                    ) : client.status === 'running' ? (
                                        <Badge className="bg-green-500 hover:bg-green-600 gap-1">
                                            <CheckCircle2 className="h-3 w-3" />
                                            运行中
                                        </Badge>
                                    ) : client.status === 'error' ? (
                                        <Badge variant="destructive" className="gap-1">
                                            <AlertCircle className="h-3 w-3" />
                                            异常
                                        </Badge>
                                    ) : (
                                        <Badge variant="secondary" className="gap-1">
                                            <XCircle className="h-3 w-3" />
                                            已停止
                                        </Badge>
                                    )}
                                </TableCell>
                                <TableCell>{client.local_port}</TableCell>
                                <TableCell>{client.remote_port}</TableCell>
                                <TableCell>{client.server_addr}</TableCell>
                                <TableCell className="text-right">
                                    <div className="flex items-center justify-end gap-1">
                                        {/* 启动按钮 - 仅在未运行时显示 */}
                                        {client.status !== 'running' && (
                                            <Button
                                                variant="outline"
                                                size="icon"
                                                className="h-8 w-8 text-green-600 hover:bg-green-50 hover:text-green-700 border-green-200"
                                                onClick={() => handleClientAction(client, 'start')}
                                                disabled={isActionLoading(client, 'start')}
                                                title="启动"
                                            >
                                                {isActionLoading(client, 'start') ? <LoadingIcon /> : <Play className="h-4 w-4" />}
                                            </Button>
                                        )}
                                        {/* 停止/重启按钮 - 仅在运行时显示 */}
                                        {client.status === 'running' && (
                                            <>
                                                <Button
                                                    variant="outline"
                                                    size="icon"
                                                    className="h-8 w-8 text-orange-600 hover:bg-orange-50 hover:text-orange-700 border-orange-200"
                                                    onClick={() => handleClientAction(client, 'stop')}
                                                    disabled={isActionLoading(client, 'stop')}
                                                    title="停止"
                                                >
                                                    {isActionLoading(client, 'stop') ? <LoadingIcon /> : <Square className="h-4 w-4" />}
                                                </Button>
                                                <Button
                                                    variant="outline"
                                                    size="icon"
                                                    className="h-8 w-8 text-blue-600 hover:bg-blue-50 hover:text-blue-700 border-blue-200"
                                                    onClick={() => handleClientAction(client, 'restart')}
                                                    disabled={isActionLoading(client, 'restart')}
                                                    title="重启"
                                                >
                                                    {isActionLoading(client, 'restart') ? <LoadingIcon /> : <RotateCcw className="h-4 w-4" />}
                                                </Button>
                                            </>
                                        )}

                                        <div className="w-px h-6 bg-border mx-1" />

                                        <ViewConfigDialog clientId={client.id} clientName={client.name}>
                                            <Button
                                                type="button"
                                                variant="outline"
                                                size="icon"
                                                className="h-8 w-8"
                                                title="查看/编辑配置"
                                            >
                                                <FileText className="h-4 w-4" />
                                            </Button>
                                        </ViewConfigDialog>
                                        <ViewLogsDialog clientId={client.id} clientName={client.name}>
                                            <Button
                                                type="button"
                                                variant="outline"
                                                size="icon"
                                                className="h-8 w-8"
                                                title="查看日志"
                                            >
                                                <ScrollText className="h-4 w-4" />
                                            </Button>
                                        </ViewLogsDialog>

                                        <div className="w-px h-6 bg-border mx-1" />

                                        <AlertDialog>
                                            <AlertDialogTrigger asChild>
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    size="icon"
                                                    className="h-8 w-8 text-red-600 hover:bg-red-50 hover:text-red-700 border-red-200"
                                                    title="删除"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </AlertDialogTrigger>
                                            <AlertDialogContent>
                                                <AlertDialogHeader>
                                                    <AlertDialogTitle>确认删除</AlertDialogTitle>
                                                    <AlertDialogDescription>
                                                        确定要删除客户端「{client.name}」吗？此操作将同时移除容器与配置文件，且不可恢复。
                                                    </AlertDialogDescription>
                                                </AlertDialogHeader>
                                                <AlertDialogFooter>
                                                    <AlertDialogCancel>取消</AlertDialogCancel>
                                                    <AlertDialogAction
                                                        onClick={() => handleDelete(client.id)}
                                                        className="bg-red-600 hover:bg-red-700"
                                                    >
                                                        删除
                                                    </AlertDialogAction>
                                                </AlertDialogFooter>
                                            </AlertDialogContent>
                                        </AlertDialog>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>

            {/* 移动端卡片视图 */}
            <div className="md:hidden space-y-4">
                {filteredClients.map((client) => (
                    <Card key={client.id}>
                        <CardContent className="p-4">
                            <div className="flex items-center justify-between mb-3">
                                <span className="font-medium">{client.name}</span>
                                {actionLoading?.id === client.id ? (
                                    <Badge variant="secondary" className="gap-1">
                                        <Loader2 className="h-3 w-3 animate-spin" />
                                        处理中
                                    </Badge>
                                ) : client.status === 'running' ? (
                                    <Badge className="bg-green-500 hover:bg-green-600 gap-1">
                                        <CheckCircle2 className="h-3 w-3" />
                                        运行中
                                    </Badge>
                                ) : client.status === 'error' ? (
                                    <Badge variant="destructive" className="gap-1">
                                        <AlertCircle className="h-3 w-3" />
                                        异常
                                    </Badge>
                                ) : (
                                    <Badge variant="secondary" className="gap-1">
                                        <XCircle className="h-3 w-3" />
                                        已停止
                                    </Badge>
                                )}
                            </div>
                            <div className="text-sm text-muted-foreground space-y-1 mb-4">
                                <div>本地端口: {client.local_port}</div>
                                <div>远程端口: {client.remote_port}</div>
                                <div>服务器地址: {client.server_addr}</div>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                    {/* 启动按钮 - 仅在未运行时显示 */}
                                    {client.status !== 'running' && (
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="text-green-600 hover:bg-green-50 border-green-200"
                                            onClick={() => handleClientAction(client, 'start')}
                                            disabled={isActionLoading(client, 'start')}
                                        >
                                            {isActionLoading(client, 'start') ? <LoadingIcon /> : <Play className="h-4 w-4 mr-1" />}
                                            启动
                                        </Button>
                                    )}
                                    {/* 停止/重启按钮 - 仅在运行时显示 */}
                                    {client.status === 'running' && (
                                        <>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="text-orange-600 hover:bg-orange-50 border-orange-200"
                                                onClick={() => handleClientAction(client, 'stop')}
                                                disabled={isActionLoading(client, 'stop')}
                                            >
                                                {isActionLoading(client, 'stop') ? <LoadingIcon /> : <Square className="h-4 w-4 mr-1" />}
                                                停止
                                            </Button>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="text-blue-600 hover:bg-blue-50 border-blue-200"
                                                onClick={() => handleClientAction(client, 'restart')}
                                                disabled={isActionLoading(client, 'restart')}
                                            >
                                                {isActionLoading(client, 'restart') ? <LoadingIcon /> : <RotateCcw className="h-4 w-4 mr-1" />}
                                                重启
                                            </Button>
                                        </>
                                    )}
                                <ViewConfigDialog clientId={client.id} clientName={client.name}>
                                    <Button variant="outline" size="sm">
                                        配置
                                    </Button>
                                </ViewConfigDialog>
                                <ViewLogsDialog clientId={client.id} clientName={client.name}>
                                    <Button variant="outline" size="sm">
                                        日志
                                    </Button>
                                </ViewLogsDialog>
                                <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                        <Button variant="destructive" size="sm">
                                            删除
                                        </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                        <AlertDialogHeader>
                                            <AlertDialogTitle>确认删除</AlertDialogTitle>
                                            <AlertDialogDescription>
                                                确定要删除客户端「{client.name}」吗？此操作将同时移除容器与配置文件，且不可恢复。
                                            </AlertDialogDescription>
                                        </AlertDialogHeader>
                                        <AlertDialogFooter>
                                            <AlertDialogCancel>取消</AlertDialogCancel>
                                            <AlertDialogAction onClick={() => handleDelete(client.id)}>删除</AlertDialogAction>
                                        </AlertDialogFooter>
                                    </AlertDialogContent>
                                </AlertDialog>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    )
}
