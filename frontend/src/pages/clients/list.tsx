import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
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
import { FileText, Trash2, Play, Square, RotateCcw, ScrollText, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import type { Client } from "@/types";

export default function ClientListPage() {
    const { t } = useTranslation();
    const { data: clients, isLoading, error, fetchData: fetchClients } = useApi<Client[]>("/clients");
    const { success, error: toastError } = useToast();
    const [searchTerm, setSearchTerm] = useState("");
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
        try {
            await apiFetch(`/clients/${client.id}/${action}`, {
                method: 'POST',
            });
            success(t(`clients.${action}Success`));
            fetchClients();
        } catch (error) {
            console.error(`Failed to ${action} client ${client.id}:`, error);
            toastError(t(`clients.${action}Error`));
        }
    };

    const handleDelete = async (clientId: number) => {
        try {
            await apiFetch(`/clients/${clientId}`, { method: 'DELETE' });
            fetchClients();
            success(t('clients.deleteSuccess'));
        } catch (error) {
            console.error(`Failed to delete client ${clientId}:`, error);
            toastError(t('clients.deleteError'));
        }
    };

    if (isLoading && !clients) {
        return <div>{t('common.loading')}</div>
    }

    if (error) {
        return <div>{t('clients.loadError')}: {error.message}</div>
    }

    return (
        <div>
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold">{t('clients.title')}</h2>
                <div className="flex items-center space-x-2">
                    <Input
                        placeholder={t('clients.searchPlaceholder')}
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
                            <TableHead>{t('clients.name')}</TableHead>
                            <TableHead className="text-center">{t('common.status')}</TableHead>
                            <TableHead>{t('clients.localPort')}</TableHead>
                            <TableHead>{t('clients.remotePort')}</TableHead>
                            <TableHead>{t('clients.serverAddress')}</TableHead>
                            <TableHead className="text-right">{t('clients.actions')}</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {filteredClients.map((client) => (
                            <TableRow key={client.id}>
                                <TableCell className="font-medium">{client.name}</TableCell>
                                <TableCell className="text-center">
                                    {client.status === 'running' ? (
                                        <Badge className="bg-green-500 hover:bg-green-600 gap-1">
                                            <CheckCircle2 className="h-3 w-3" />
                                            {t('common.running')}
                                        </Badge>
                                    ) : client.status === 'error' ? (
                                        <Badge variant="destructive" className="gap-1">
                                            <AlertCircle className="h-3 w-3" />
                                            {t('common.error')}
                                        </Badge>
                                    ) : (
                                        <Badge variant="secondary" className="gap-1">
                                            <XCircle className="h-3 w-3" />
                                            {t('common.stopped')}
                                        </Badge>
                                    )}
                                </TableCell>
                                <TableCell>{client.local_port}</TableCell>
                                <TableCell>{client.remote_port}</TableCell>
                                <TableCell>{client.server_addr}</TableCell>
                                <TableCell className="text-right">
                                    <div className="flex items-center justify-end gap-1">
                                        {/* 启动/停止/重启按钮 - 始终显示 */}
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            className="h-8 w-8 text-green-600 hover:bg-green-50 hover:text-green-700 border-green-200"
                                            onClick={() => handleClientAction(client, 'start')}
                                            disabled={client.status === 'running'}
                                            title={t('common.start')}
                                        >
                                            <Play className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            className="h-8 w-8 text-orange-600 hover:bg-orange-50 hover:text-orange-700 border-orange-200"
                                            onClick={() => handleClientAction(client, 'stop')}
                                            disabled={client.status !== 'running'}
                                            title={t('common.stop')}
                                        >
                                            <Square className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="icon"
                                            className="h-8 w-8 text-blue-600 hover:bg-blue-50 hover:text-blue-700 border-blue-200"
                                            onClick={() => handleClientAction(client, 'restart')}
                                            title={t('common.restart')}
                                        >
                                            <RotateCcw className="h-4 w-4" />
                                        </Button>

                                        <div className="w-px h-6 bg-border mx-1" />

                                        <ViewConfigDialog clientId={client.id} clientName={client.name} onClientUpdated={fetchClients}>
                                            <Button
                                                type="button"
                                                variant="outline"
                                                size="icon"
                                                className="h-8 w-8"
                                                title={t('clients.viewConfig')}
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
                                                title={t('clients.viewLogs')}
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
                                                    title={t('clients.delete')}
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </AlertDialogTrigger>
                                            <AlertDialogContent>
                                                <AlertDialogHeader>
                                                    <AlertDialogTitle>{t('clients.deleteConfirmTitle')}</AlertDialogTitle>
                                                    <AlertDialogDescription>
                                                        {t('clients.deleteConfirmDesc', { name: client.name })}
                                                    </AlertDialogDescription>
                                                </AlertDialogHeader>
                                                <AlertDialogFooter>
                                                    <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
                                                    <AlertDialogAction
                                                        onClick={() => handleDelete(client.id)}
                                                        className="bg-red-600 hover:bg-red-700"
                                                    >
                                                        {t('common.delete')}
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
                                {client.status === 'running' ? (
                                    <Badge className="bg-green-500 hover:bg-green-600 gap-1">
                                        <CheckCircle2 className="h-3 w-3" />
                                        {t('common.running')}
                                    </Badge>
                                ) : client.status === 'error' ? (
                                    <Badge variant="destructive" className="gap-1">
                                        <AlertCircle className="h-3 w-3" />
                                        {t('common.error')}
                                    </Badge>
                                ) : (
                                    <Badge variant="secondary" className="gap-1">
                                        <XCircle className="h-3 w-3" />
                                        {t('common.stopped')}
                                    </Badge>
                                )}
                            </div>
                            <div className="text-sm text-muted-foreground space-y-1 mb-4">
                                <div>{t('clients.localPort')}: {client.local_port}</div>
                                <div>{t('clients.remotePort')}: {client.remote_port}</div>
                                <div>{t('clients.serverAddress')}: {client.server_addr}</div>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {/* 移动端启动/停止/重启按钮 - 始终显示 */}
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="text-green-600 hover:bg-green-50 border-green-200"
                                    onClick={() => handleClientAction(client, 'start')}
                                    disabled={client.status === 'running'}
                                >
                                    <Play className="h-4 w-4 mr-1" />
                                    {t('common.start')}
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="text-orange-600 hover:bg-orange-50 border-orange-200"
                                    onClick={() => handleClientAction(client, 'stop')}
                                    disabled={client.status !== 'running'}
                                >
                                    <Square className="h-4 w-4 mr-1" />
                                    {t('common.stop')}
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="text-blue-600 hover:bg-blue-50 border-blue-200"
                                    onClick={() => handleClientAction(client, 'restart')}
                                >
                                    <RotateCcw className="h-4 w-4 mr-1" />
                                    {t('common.restart')}
                                </Button>
                                <ViewConfigDialog clientId={client.id} clientName={client.name} onClientUpdated={fetchClients}>
                                    <Button variant="outline" size="sm">
                                        {t('clients.viewConfig')}
                                    </Button>
                                </ViewConfigDialog>
                                <ViewLogsDialog clientId={client.id} clientName={client.name}>
                                    <Button variant="outline" size="sm">
                                        {t('clients.viewLogs')}
                                    </Button>
                                </ViewLogsDialog>
                                <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                        <Button variant="destructive" size="sm">
                                            {t('clients.delete')}
                                        </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                        <AlertDialogHeader>
                                            <AlertDialogTitle>{t('clients.deleteConfirmTitle')}</AlertDialogTitle>
                                            <AlertDialogDescription>
                                                {t('clients.deleteConfirmDesc', { name: client.name })}
                                            </AlertDialogDescription>
                                        </AlertDialogHeader>
                                        <AlertDialogFooter>
                                            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
                                            <AlertDialogAction onClick={() => handleDelete(client.id)}>{t('common.delete')}</AlertDialogAction>
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
