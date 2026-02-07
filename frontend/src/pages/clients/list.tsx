import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "@/hooks/useApi.ts";
import { apiFetch } from "@/lib/api.ts";
import { useToast } from "@/contexts/toast-context.tsx";
import { AddClientDialog } from "./add-client-dialog.tsx";
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
import { Play, Square, RotateCcw, FileText, Edit3, Trash2 } from "lucide-react";
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

    // 控制 frpc 服务（通过后端调用 systemctl）
    const handleServiceAction = async (action: string) => {
        try {
            await apiFetch(`/service/${action}`, { method: 'POST' });
            const actionText = action === 'start' ? '启动' : action === 'stop' ? '停止' : '重启';
            success(`frpc 服务${actionText}成功`);
        } catch (error) {
            console.error(`Failed to ${action} service:`, error);
            toastError(`操作失败: ${error}`);
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
            {/* 服务控制栏 */}
            <div className="flex justify-between items-center mb-4 p-4 bg-muted rounded-lg">
                <div>
                    <h3 className="font-semibold">frpc 服务控制</h3>
                    <p className="text-sm text-muted-foreground">控制 frpc 服务的启动、停止和重启</p>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleServiceAction('start')}
                        className="text-green-600 hover:bg-green-50"
                    >
                        <Play className="h-4 w-4 mr-1" />
                        启动
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleServiceAction('stop')}
                        className="text-orange-600 hover:bg-orange-50"
                    >
                        <Square className="h-4 w-4 mr-1" />
                        停止
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleServiceAction('restart')}
                        className="text-blue-600 hover:bg-blue-50"
                    >
                        <RotateCcw className="h-4 w-4 mr-1" />
                        重启
                    </Button>
                </div>
            </div>

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
                                <TableCell>{client.local_port}</TableCell>
                                <TableCell>{client.remote_port}</TableCell>
                                <TableCell>{client.server_addr}</TableCell>
                                <TableCell className="text-right">
                                    <div className="flex items-center justify-end gap-1">
                                        <ViewConfigDialog clientId={client.id} clientName={client.name}>
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
                            </div>
                            <div className="text-sm text-muted-foreground space-y-1 mb-4">
                                <div>{t('clients.localPort')}: {client.local_port}</div>
                                <div>{t('clients.remotePort')}: {client.remote_port}</div>
                                <div>{t('clients.serverAddress')}: {client.server_addr}</div>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <ViewConfigDialog clientId={client.id} clientName={client.name}>
                                    <Button variant="outline" size="sm">
                                        {t('clients.viewConfig')}
                                    </Button>
                                </ViewConfigDialog>
                                <EditClientDialog client={client} onClientUpdated={fetchClients}>
                                    <Button variant="outline" size="sm">
                                        {t('clients.edit')}
                                    </Button>
                                </EditClientDialog>
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
