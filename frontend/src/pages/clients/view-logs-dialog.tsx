import { useState, useEffect, useRef, useMemo, ReactNode } from "react";
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
import { Alert, AlertDescription } from "@/components/ui/alert.tsx";
import { Trash2, Loader2, X, AlertTriangle, XCircle } from "lucide-react";

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

    // 统计日志中的错误 / 警告，用于顶部提示
    const logStats = useMemo(() => {
        // eslint-disable-next-line no-control-regex
        const plain = logs.replace(/\x1b\[[0-9;]*m/g, '');
        const errors = (plain.match(/\[E\]/g) || []).length;
        const warnings = (plain.match(/\[W\]/g) || []).length;
        const hasErrorKeyword = /error|错误|失败|exception|panic/i.test(plain);
        return { errors, warnings, hasErrorKeyword };
    }, [logs]);

    // 日志级别内联 SVG 图标（lucide 同款路径，避免 emoji）
    // 显式设置 width/height，防止 CSS 失效时按默认尺寸渲染成巨大图标
    const LEVEL_ICONS: Record<string, string> = {
        error: '<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>',
        warn: '<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
        info: '<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
        debug: '<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10" fill="currentColor"/></svg>',
    };

    const processLogs = (logContent: string): string => {
        if (!logContent) return '';
        return logContent.split('\n').map(line => {
            // frpc 日志格式: date host frpc[pid]: timestamp [LEVEL] [file:line] message
            // systemd journal 格式: May 01 19:04:45 host frpc[pid]: ...

            // 去掉 ANSI 颜色转义码（\x1b[1;34m 等），避免终端颜色码污染显示
            // eslint-disable-next-line no-control-regex
            const clean = line.replace(/\x1b\[[0-9;]*m/g, '');

            // 转义 HTML
            let html = clean
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');

            // 级别标记替换为带颜色的图标
            html = html.replace(
                /\[E\]/g,
                `<span class="log-level log-level-error">${LEVEL_ICONS.error}</span>`
            );
            html = html.replace(
                /\[W\]/g,
                `<span class="log-level log-level-warn">${LEVEL_ICONS.warn}</span>`
            );
            html = html.replace(
                /\[I\]/g,
                `<span class="log-level log-level-info">${LEVEL_ICONS.info}</span>`
            );
            html = html.replace(
                /\[D\]/g,
                `<span class="log-level log-level-debug">${LEVEL_ICONS.debug}</span>`
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
                {logStats.hasErrorKeyword || logStats.errors > 0 ? (
                    <Alert variant="destructive" className="mb-3 gap-2">
                        <XCircle className="h-4 w-4" />
                        <AlertDescription>
                            检测到{logStats.errors > 0 ? ` ${logStats.errors} 条错误日志，` : ' '}frpc 运行异常，请检查配置文件后重启客户端。
                        </AlertDescription>
                    </Alert>
                ) : logStats.warnings > 0 ? (
                    <Alert className="mb-3 gap-2 border-yellow-500/50 text-yellow-600 dark:text-yellow-500">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription>检测到 {logStats.warnings} 条警告日志，请留意运行状态。</AlertDescription>
                    </Alert>
                ) : null}
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
                .log-level {
                    display: inline-flex;
                    align-items: center;
                    vertical-align: middle;
                    margin-right: 4px;
                }
                .log-level svg {
                    width: 10px;
                    height: 10px;
                }
                .log-level-error { color: #ff6b6b; }
                .log-level-warn { color: #fcc419; }
                .log-level-info { color: #51cf66; }
                .log-level-debug { color: #868e96; }
                .log-error-text {
                    color: #ff6b6b;
                }
            `}</style>
        </Dialog>
    );
}
