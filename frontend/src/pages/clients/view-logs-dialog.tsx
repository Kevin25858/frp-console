import { useState, useEffect, useRef, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "@/hooks/useApi";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";

interface ViewLogsDialogProps {
    clientId: number;
    clientName: string;
    children?: ReactNode;
}

interface LogsResponse {
    logs: string;
}

export function ViewLogsDialog({ clientId, clientName, children }: ViewLogsDialogProps) {
    const { t } = useTranslation();
    const [open, setOpen] = useState(false);
    const { data: logsData, isLoading, error, fetchData } = useApi<LogsResponse>(
        `/clients/${clientId}/logs`,
        {},
        false // Disable auto-fetching
    );
    const logsContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (open) {
            fetchData();
        }
    }, [open, fetchData]);

    // 自动滚动到底部
    useEffect(() => {
        if (logsContainerRef.current && logsData?.logs && !isLoading) {
            logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
        }
    }, [logsData, isLoading]);

    const logs = logsData?.logs || '';

    // 处理日志内容，高亮时间戳
    const processLogs = (logContent: string): string => {
        if (!logContent) return '';

        // 高亮时间戳格式: [2026-02-04 23:35:02.319]
        // 使用正则表达式匹配时间戳并添加高亮样式
        return logContent.replace(
            /(\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\])/g,
            '<span class="log-timestamp">$1</span>'
        );
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                {children || (
                    <Button variant="ghost" size="sm">{t('clients.viewLogs')}</Button>
                )}
            </DialogTrigger>
            <DialogContent className="max-w-4xl">
                <DialogHeader>
                    <DialogTitle>{t('clients.logs.title')} {clientName}</DialogTitle>
                </DialogHeader>
                <div
                    ref={logsContainerRef}
                    className="mt-4 bg-muted text-muted-foreground rounded-md p-4 h-96 overflow-auto font-mono text-sm"
                >
                    {isLoading && <p>{t('clients.logs.loading')}</p>}
                    {error && <p className="text-red-500">{t('clients.logs.error')}: {error.message}</p>}
                    {!isLoading && !error && (
                        logs ? (
                            <div
                                className="whitespace-pre-wrap"
                                dangerouslySetInnerHTML={{ __html: processLogs(logs) }}
                            />
                        ) : (
                            <p className="text-muted-foreground">{t('clients.logs.noLogs')}</p>
                        )
                    )}
                </div>
            </DialogContent>
            <style>{`
                .log-timestamp {
                    color: #4dabf7;
                    font-weight: bold;
                }
            `}</style>
        </Dialog>
    );
}
