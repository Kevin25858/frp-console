import { useState, useEffect, ReactNode } from "react";
import { useApi } from "@/hooks/useApi";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/contexts/toast-context";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Edit3 } from "lucide-react";

interface EditConfigDialogProps {
    clientId: number;
    clientName: string;
    children?: ReactNode;
}

interface ConfigResponse {
    config: string;
}

export function EditConfigDialog({ clientId, clientName, children }: EditConfigDialogProps) {
    const [open, setOpen] = useState(false);
    const [configContent, setConfigContent] = useState("");
    const [isSaving, setIsSaving] = useState(false);
    const { success, error: toastError } = useToast();

    const { data: configData, isLoading, error, fetchData } = useApi<ConfigResponse>(
        `/clients/${clientId}/config`,
        {},
        false
    );

    useEffect(() => {
        if (open) {
            fetchData();
        }
    }, [open, fetchData]);

    useEffect(() => {
        if (configData?.config) {
            setConfigContent(configData.config);
        }
    }, [configData]);

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await apiFetch(`/clients/${clientId}/config`, {
                method: 'PUT',
                body: JSON.stringify({ config: configContent }),
            });
            success('配置文件已保存');
            setOpen(false);
        } catch (error) {
            console.error("Failed to save config:", error);
            toastError('保存失败，请重试');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                {children || (
                    <Button variant="outline" size="icon" className="h-8 w-8">
                        <Edit3 className="h-4 w-4" />
                    </Button>
                )}
            </DialogTrigger>
            <DialogContent className="max-w-4xl">
                <DialogHeader>
                    <DialogTitle>Edit Configuration for {clientName}</DialogTitle>
                    <DialogDescription>
                        编辑 frpc 配置文件。修改后需要重启客户端才能生效。
                    </DialogDescription>
                </DialogHeader>
                <div className="mt-4">
                    {isLoading && <p className="text-muted-foreground">Loading configuration...</p>}
                    {error && <p className="text-red-500">Error loading config: {error.message}</p>}
                    {!isLoading && !error && (
                        <Textarea
                            value={configContent}
                            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setConfigContent(e.target.value)}
                            className="font-mono text-sm min-h-[400px] bg-slate-950 text-slate-50 border-slate-700"
                            placeholder="Enter configuration..."
                        />
                    )}
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => setOpen(false)}>
                        取消
                    </Button>
                    <Button onClick={handleSave} disabled={isLoading || isSaving}>
                        {isSaving ? '保存中...' : '保存配置'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
