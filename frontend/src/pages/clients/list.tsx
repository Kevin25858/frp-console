import { useState, useMemo, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "@/hooks/useApi.ts";
import { apiFetch } from "@/lib/api.ts";
import { useToast } from "@/contexts/toast-context.tsx";
import { AddClientDialog } from "./add-client-dialog.tsx";
import { ViewLogsDialog } from "./view-logs-dialog.tsx";
import { ViewConfigDialog } from "./view-config-dialog.tsx";
import { EditClientDialog } from "./edit-client-dialog.tsx";
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
import { Play, Square, RotateCcw, FileText, Edit3, ScrollText, Trash2 } from "lucide-react";
import { Switch } from "@/components/ui/switch.tsx";
import type { Client } from "@/types";

export default function ClientListPage() {
    const { t } = useTranslation();
    const { data: clients, isLoading, error, fetchData: fetchClients } = useApi<Client[]>("/clients");
    const { success, error: toastError } = useToast();
    const [searchTerm, setSearchTerm] = useState("");

    const filteredClients = useMemo(() => {
        if (!Array.isArray(clients)) return [];
        return clients.filter(client =>
            client.name.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }, [clients, searchTerm]);

    const handleAction = async (clientId: number, action: string) => {
        try {
            await apiFetch(`/clients/${clientId}/${action}` , {
                method: 'POST',
            });
            fetchClients();
            const actionKey = action === 'start' ? 'startSuccess' : action === 'stop' ? 'stopSuccess' : 'restartSuccess';
            success(t(`clients.${actionKey}`));
        } catch (error) {
            console.error(`Failed to ${action} client ${clientId}:`, error);
            toastError(t('clients.actionError'));
        }
    };

    const handleDelete = async (clientId: number) => {
        try {
            await apiFetch(`/clients/${clientId}` , {
                method: 'DELETE',
            });
            fetchClients();
            success(t('clients.deleteSuccess'));
        } catch (error) {
            console.error(`Failed to delete client ${clientId}:`, error);
            toastError(t('clients.deleteError'));
        }
    };

    // 本地状态存储 always_on 状态，用于快速响应
    const [alwaysOnStates, setAlwaysOnStates] = useState<Record<number, boolean>>({});

    const handleAlwaysOnChange = useCallback(async (clientId: number, newValue: boolean) => {
        // 立即更新本地状态，提供即时反馈
        setAlwaysOnStates(prev => ({ ...prev, [clientId]: newValue }));
        
        try {
            await apiFetch(`/clients/${clientId}/always-on`, {
                method: 'POST',
                body: JSON.stringify({ always_on: newValue }),
            });
            // 成功后刷新数据
            fetchClients();
            success(newValue ? t('clients.alwaysOnEnabled') : t('clients.alwaysOnDisabled'));
        } catch (_error) {
            // 失败时恢复本地状态
            setAlwaysOnStates(prev => ({ ...prev, [clientId]: !newValue }));
            toastError(t('clients.alwaysOnError'));
        }
    }, [fetchClients, success, toastError, t]);

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
                        <TableHead>{t('clients.status')}</TableHead>
                        <TableHead>{t('clients.alwaysOn')}</TableHead>
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
                            <TableCell><Badge variant={client.status === "running" ? "default" : client.status === "stopped" ? "secondary" : "destructive"}>{client.status}</Badge></TableCell>
                            <TableCell>
                                <Switch
                                    checked={alwaysOnStates[client.id] !== undefined ? alwaysOnStates[client.id] : Boolean(client.always_on)}
                                    onCheckedChange={(checked) => handleAlwaysOnChange(client.id, checked)}
                                    title={t('clients.alwaysOn')}
                                />
                            </TableCell>
                            <TableCell>{client.local_port}</TableCell>
                            <TableCell>{client.remote_port}</TableCell>
                            <TableCell>{client.server_addr}</TableCell>
                            <TableCell className="text-right">
                                <div className="flex items-center justify-end gap-1">
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="icon"
                                            className="h-8 w-8 text-green-600 hover:bg-green-50 hover:text-green-700 border-green-200"
                                            onClick={() => handleAction(client.id, 'start')}
                                            title={t('clients.start')}
                                        >
                                            <Play className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="icon"
                                            className="h-8 w-8 text-orange-600 hover:bg-orange-50 hover:text-orange-700 border-orange-200"
                                            onClick={() => handleAction(client.id, 'stop')}
                                            title={t('clients.stop')}
                                        >
                                            <Square className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="icon"
                                            className="h-8 w-8 text-blue-600 hover:bg-blue-50 hover:text-blue-700 border-blue-200"
                                            onClick={() => handleAction(client.id, 'restart')}
                                            title={t('clients.restart')}
                                        >
                                            <RotateCcw className="h-4 w-4" />
                                        </Button>

                                        {/* 分隔线 */}
                                        <div className="w-px h-6 bg-border mx-1" />

                                        {/* 管理按钮组 */}
                                        <ViewConfigDialog clientId={client.id} clientName={client.name}>
                                            <Button
                                                type="button"
                                                variant="outline"
                                                size="icon"
                                                className="h-8 w-8"
                                                title={t('clients.config')}
                                            >
                                                <FileText className="h-4 w-4" />
                                            </Button>
                                        </ViewConfigDialog>
                                        <EditClientDialog client={client} onClientUpdated={fetchClients}>
                                            <Button
                                                type="button"
                                                variant="outline"
                                                size="icon"
                                                className="h-8 w-8"
                                                title={t('clients.edit')}
                                            >
                                                <Edit3 className="h-4 w-4" />
                                            </Button>
                                        </EditClientDialog>
                                        <ViewLogsDialog clientId={client.id} clientName={client.name}>
                                            <Button
                                                type="button"
                                                variant="outline"
                                                size="icon"
                                                className="h-8 w-8"
                                                title={t('clients.logs')}
                                            >
                                                <ScrollText className="h-4 w-4" />
                                            </Button>
                                        </ViewLogsDialog>

                                        {/* 分隔线 */}
                                        <div className="w-px h-6 bg-border mx-1" />

                                        {/* 删除按钮 */}
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
                                <div className="flex items-center space-x-2">
                                    <Badge variant={client.status === "running" ? "default" : client.status === "stopped" ? "secondary" : "destructive"}>
                                        {client.status}
                                    </Badge>
                                    <span className="font-medium">{client.name}</span>
                                </div>
                                {client.always_on && (
                                    <Badge variant="outline" className="text-xs">Always-On</Badge>
                                )}
                            </div>
                            <div className="text-sm text-muted-foreground space-y-1 mb-4">
                                <div>{t('clients.localPort')}: {client.local_port}</div>
                                <div>{t('clients.remotePort')}: {client.remote_port}</div>
                                <div>{t('clients.serverAddress')}: {client.server_addr}</div>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <Button variant="outline" size="sm" onClick={() => handleAction(client.id, 'start')}>
                                    {t('clients.start')}
                                </Button>
                                <Button variant="outline" size="sm" onClick={() => handleAction(client.id, 'stop')}>
                                    {t('clients.stop')}
                                </Button>
                                <Button variant="outline" size="sm" onClick={() => handleAction(client.id, 'restart')}>
                                    {t('clients.restart')}
                                </Button>
                                <Button variant="outline" size="sm">
                                    {t('clients.config')}
                                </Button>
                                <EditClientDialog client={client} onClientUpdated={fetchClients}>
                                    <Button variant="outline" size="sm">
                                        {t('clients.edit')}
                                    </Button>
                                </EditClientDialog>
                                <ViewLogsDialog clientId={client.id} clientName={client.name} />
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
