import { useState, useEffect, useRef, ReactNode } from "react";
import { useApi } from "@/hooks/useApi.ts";
import { apiFetch } from "@/lib/api.ts";
import { useToast } from "@/contexts/toast-context.tsx";
import { Button } from "@/components/ui/button.tsx";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog.tsx";
import { Trash2, Loader2, X } from "lucide-react";

interface ViewLogsDialogProps {
    clientId: number;
    clientName: string;
    children?: ReactNode;
}

interface LogsResponse {
    logs: string;
}

export function ViewLogsDialog({ clientId, clientName, children }: ViewLogsDialogProps) {
    const [open, setOpen] = useState(false);
    const [isClearing, setIsClearing] = useState(false);
    const { success, error: toastError } = useToast();
    const { data: logsData, isLoading, error, fetchData } = useApi<LogsResponse>(
        `/clients/${clientId}/logs`,
        {},
        false
    );
    const logsContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (open) {
            fetchData();
        }
    }, [open, fetchData]);

    useEffect(() => {
        if (logsContainerRef.current && logsData?.logs && !isLoading) {
            logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
        }
    }, [logsData, isLoading]);

    const logs = logsData?.logs || '';

    const handleClearLogs = async () => {
        setIsClearing(true);
        try {
            const res = await apiFetch(`/clients/${clientId}/clear-logs`, { method: 'POST' });
            success(res.message || '日志已清空');
            // 等待重启完成后重新加载日志
            setTimeout(() => fetchData(), 1000);
        } catch (err: unknown) {
            const msg = (err as { body?: { error?: string } })?.body?.error || '清空日志失败';
            toastError(msg);
        } finally {
            setIsClearing(false);
        }
    };

    const processLogs = (logContent: string): string => {
        if (!logContent) return '';
        return logContent.split('\n').map(line => {
            // frpc 日志格式: date host frpc[pid]: timestamp [LEVEL] [file:line] message
            // systemd journal 格式: May 01 19:04:45 host frpc[pid]: ...

            // 转义 HTML
            let html = line
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');

            // 高亮日志级别
            html = html.replace(
                /\[E\]/g,
                '<span class="log-error">[E]</span>'
            );
            html = html.replace(
                /\[W\]/g,
                '<span class="log-warn">[W]</span>'
            );
            html = html.replace(
                /\[I\]/g,
                '<span class="log-info">[I]</span>'
            );
            html = html.replace(
                /\[D\]/g,
                '<span class="log-debug">[D]</span>'
            );

            // 高亮时间戳 (journal 格式: May 01 19:04:45)
            html = html.replace(
                /^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)/,
                '<span class="log-timestamp">$1</span> <span class="log-host">$2</span>'
            );

            // 高亮错误关键词
            html = html.replace(
                /(failed|error|错误|失败)/gi,
                '<span class="log-error-text">$1</span>'
            );

            return html;
        }).join('\n');
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                {children || (
                    <Button variant="ghost" size="sm">查看日志</Button>
                )}
            </DialogTrigger>
            <DialogContent className="max-w-4xl [&>button]:hidden">
                <DialogHeader>
                    <DialogTitle className="flex items-center justify-between">
                        <span>日志 - {clientName}</span>
                        <div className="flex items-center gap-2">
                            <Button
                                variant="destructive"
                                size="sm"
                                onClick={handleClearLogs}
                                disabled={isClearing || isLoading}
                                className="gap-1"
                            >
                                {isClearing ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Trash2 className="h-4 w-4" />
                                )}
                                {isClearing ? "清空中..." : "清空日志"}
                            </Button>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setOpen(false)}
                                className="gap-1"
                            >
                                <X className="h-4 w-4" />
                                关闭
                            </Button>
                        </div>
                    </DialogTitle>
                </DialogHeader>
                <div
                    ref={logsContainerRef}
                    className="mt-4 bg-muted text-muted-foreground rounded-md p-4 h-96 overflow-auto font-mono text-sm"
                >
                    {isLoading && <p>加载中...</p>}
                    {error && <p className="text-red-500">加载失败: {error.message}</p>}
                    {!isLoading && !error && (
                        logs ? (
                            <div
                                className="whitespace-pre-wrap"
                                dangerouslySetInnerHTML={{ __html: processLogs(logs) }}
                            />
                        ) : (
                            <p className="text-muted-foreground">暂无日志</p>
                        )
                    )}
                </div>
            </DialogContent>
            <style>{`
                .log-timestamp {
                    color: #4dabf7;
                    font-weight: bold;
                }
                .log-host {
                    color: #868e96;
                }
                .log-error {
                    color: #ff6b6b;
                    font-weight: bold;
                }
                .log-warn {
                    color: #fcc419;
                    font-weight: bold;
                }
                .log-info {
                    color: #51cf66;
                    font-weight: bold;
                }
                .log-debug {
                    color: #868e96;
                }
                .log-error-text {
                    color: #ff6b6b;
                }
            `}</style>
        </Dialog>
    );
}
