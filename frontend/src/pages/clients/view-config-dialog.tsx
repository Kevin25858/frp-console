import { useState, useEffect, ReactNode, useCallback, useRef } from "react";
import { useTranslation } from "react-i18next";
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
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog.tsx";
import { FileText, Copy, RotateCcw, Save, Check, Undo, Redo } from "lucide-react";

interface ViewConfigDialogProps {
    clientId: number;
    clientName: string;
    children?: ReactNode;
}

interface ConfigResponse {
    config: string;
}

// 语法高亮组件
function HighlightedEditor({ 
    value, 
    onChange, 
    disabled,
    placeholder
}: { 
    value: string; 
    onChange: (value: string) => void;
    disabled?: boolean;
    placeholder?: string;
}) {
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const highlightRef = useRef<HTMLDivElement>(null);

    // 同步滚动
    const handleScroll = () => {
        if (textareaRef.current && highlightRef.current) {
            highlightRef.current.scrollTop = textareaRef.current.scrollTop;
            highlightRef.current.scrollLeft = textareaRef.current.scrollLeft;
        }
    };

    // 渲染高亮内容
    const renderHighlightedContent = (content: string) => {
        if (!content) return null;

        return content.split('\n').map((line, index) => {
            // 节标题 [section]
            if (line.trim().startsWith('[') && line.trim().endsWith(']')) {
                return (
                    <div key={index} className="text-pink-400 font-bold">
                        {line}
                    </div>
                );
            }
            // 注释行
            if (line.trim().startsWith('#')) {
                return (
                    <div key={index} className="text-gray-500 italic">
                        {line}
                    </div>
                );
            }
            // 键值对 key = value
            const match = line.match(/^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.*)$/);
            if (match) {
                const [, key, value] = match;
                return (
                    <div key={index}>
                        <span className="text-blue-400">{key}</span>
                        <span className="text-slate-300"> = </span>
                        <span className="text-lime-400">{value}</span>
                    </div>
                );
            }
            // 空行或其他
            return <div key={index}>{line || ' '}</div>;
        });
    };

    return (
        <div className="relative flex-1 min-h-0">
            {/* 高亮层（底层） */}
            <div
                ref={highlightRef}
                className="absolute inset-0 p-4 font-mono text-sm leading-relaxed overflow-auto pointer-events-none whitespace-pre-wrap break-words bg-slate-950 text-slate-50 rounded-md border border-slate-700"
                style={{ 
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                    lineHeight: '1.5',
                }}
            >
                {renderHighlightedContent(value)}
            </div>
            
            {/* 编辑层（透明，可交互） */}
            <textarea
                ref={textareaRef}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onScroll={handleScroll}
                disabled={disabled}
                className="absolute inset-0 w-full h-full p-4 font-mono text-sm leading-relaxed resize-none bg-transparent text-transparent caret-slate-50 overflow-auto whitespace-pre-wrap break-words focus:outline-none"
                style={{ 
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                    lineHeight: '1.5',
                }}
                spellCheck={false}
                placeholder={placeholder}
            />
        </div>
    );
}

export function ViewConfigDialog({ clientId, clientName, children }: ViewConfigDialogProps) {
    const { t } = useTranslation();
    const [open, setOpen] = useState(false);
    const [showConfirmDialog, setShowConfirmDialog] = useState(false);
    const [configContent, setConfigContent] = useState("");
    const [originalContent, setOriginalContent] = useState("");
    const [isSaving, setIsSaving] = useState(false);
    const [isCopied, setIsCopied] = useState(false);
    const [history, setHistory] = useState<string[]>([]);
    const [historyIndex, setHistoryIndex] = useState(-1);
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
            setOriginalContent(configData.config);
            // 初始化历史记录
            setHistory([configData.config]);
            setHistoryIndex(0);
        }
    }, [configData]);

    // 添加历史记录
    const addToHistory = useCallback((content: string) => {
        setHistory(prev => {
            const newHistory = prev.slice(0, historyIndex + 1);
            newHistory.push(content);
            // 限制历史记录长度
            if (newHistory.length > 50) {
                newHistory.shift();
            }
            return newHistory;
        });
        setHistoryIndex(prev => Math.min(prev + 1, 49));
    }, [historyIndex]);

    // 处理内容变化
    const handleContentChange = (newContent: string) => {
        setConfigContent(newContent);
        addToHistory(newContent);
    };

    // 撤回
    const handleUndo = () => {
        if (historyIndex > 0) {
            const newIndex = historyIndex - 1;
            setHistoryIndex(newIndex);
            setConfigContent(history[newIndex]);
        }
    };

    // 恢复
    const handleRedo = () => {
        if (historyIndex < history.length - 1) {
            const newIndex = historyIndex + 1;
            setHistoryIndex(newIndex);
            setConfigContent(history[newIndex]);
        }
    };

    // 复制配置到剪贴板
    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(configContent);
            setIsCopied(true);
            setTimeout(() => setIsCopied(false), 2000);
            success(t('clients.config.copySuccess'));
        } catch (_err) {
            toastError(t('clients.config.copyError'));
        }
    };

    // 重启客户端
    const handleRestart = async () => {
        try {
            await apiFetch(`/clients/${clientId}/restart`, {
                method: 'POST',
            });
            success(t('clients.restartSuccess'));
            setOpen(false); // 关闭对话框
        } catch (_error) {
            toastError(t('clients.restartError'));
        }
    };

    // 保存配置
    const handleSave = async () => {
        setIsSaving(true);
        try {
            await apiFetch(`/clients/${clientId}/config`, {
                method: 'PUT',
                body: JSON.stringify({ config: configContent }),
            });
            success(t('clients.config.saveSuccess'));
            setOriginalContent(configContent);
            setOpen(false); // 关闭对话框
        } catch (error: unknown) {
            console.error("Failed to save config:", error);
            const errorMsg = (error as { body?: { error?: string }; message?: string })?.body?.error || (error as { message?: string })?.message || t('clients.config.saveError');
            toastError(`${t('clients.config.saveError')}: ${errorMsg}`);
        } finally {
            setIsSaving(false);
        }
    };

    const canUndo = historyIndex > 0;
    const canRedo = historyIndex < history.length - 1;
    const hasChanges = configContent !== originalContent;

    // 处理对话框关闭
    const handleOpenChange = (newOpen: boolean) => {
        if (!newOpen && hasChanges) {
            // 有未保存的更改，显示确认对话框
            setShowConfirmDialog(true);
        } else {
            setOpen(newOpen);
        }
    };

    // 确认关闭（放弃更改）
    const handleConfirmClose = () => {
        setShowConfirmDialog(false);
        setOpen(false);
    };

    // 取消关闭（继续编辑）
    const handleCancelClose = () => {
        setShowConfirmDialog(false);
    };

    return (
        <>
            <Dialog open={open} onOpenChange={handleOpenChange}>
                <DialogTrigger asChild>
                    {children || (
                        <Button variant="outline" size="icon" className="h-8 w-8">
                            <FileText className="h-4 w-4" />
                        </Button>
                    )}
                </DialogTrigger>
                <DialogContent className="max-w-4xl h-[85vh] flex flex-col">
                    <DialogHeader>
                        <DialogTitle>{t('clients.config.title')} - {clientName}</DialogTitle>
                    </DialogHeader>

                {/* 工具栏 */}
                <div className="flex items-center gap-2 py-2 border-b">
                    <Button
                        size="sm"
                        onClick={handleSave}
                        disabled={isSaving || isLoading || !hasChanges}
                        className="gap-1"
                    >
                        <Save className="h-4 w-4" />
                        {isSaving ? t('clients.config.saving') : t('clients.config.save')}
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={handleUndo}
                        disabled={!canUndo || isLoading}
                        className="gap-1"
                        title={t('clients.config.undo')}
                    >
                        <Undo className="h-4 w-4" />
                        {t('clients.config.undo')}
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={handleRedo}
                        disabled={!canRedo || isLoading}
                        className="gap-1"
                        title={t('clients.config.redo')}
                    >
                        <Redo className="h-4 w-4" />
                        {t('clients.config.redo')}
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={handleCopy}
                        disabled={isLoading}
                        className="gap-1"
                    >
                        {isCopied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                        {isCopied ? t('clients.config.copied') : t('clients.config.copy')}
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={handleRestart}
                        disabled={isLoading}
                        className="gap-1 text-blue-600 hover:text-blue-700"
                    >
                        <RotateCcw className="h-4 w-4" />
                        {t('clients.restart')}
                    </Button>
                </div>

                {/* 编辑器区域（带实时语法高亮） */}
                <div className="flex-1 mt-2 min-h-0 flex flex-col">
                    {isLoading && <p className="text-muted-foreground">{t('common.loading')}</p>}
                    {error && <p className="text-red-500">{t('common.error')}: {error.message}</p>}
                    {!isLoading && !error && (
                        <HighlightedEditor
                            value={configContent}
                            onChange={handleContentChange}
                            disabled={isLoading}
                            placeholder={t('clients.config.placeholder')}
                        />
                    )}
                </div>
                
                {/* 状态栏 */}
                <div className="flex items-center justify-between py-2 text-xs text-muted-foreground border-t mt-2">
                    <div>
                        {hasChanges && <span className="text-orange-500">● {t('clients.config.unsavedChanges')}</span>}
                    </div>
                    <div>
                        {t('clients.config.lines')}: {configContent.split('\n').length} | {t('clients.config.chars')}: {configContent.length}
                    </div>
                </div>
            </DialogContent>
            </Dialog>

            {/* 未保存更改确认对话框 */}
            <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>{t('clients.config.unsavedTitle')}</AlertDialogTitle>
                        <AlertDialogDescription>
                            {t('clients.config.unsavedDesc')}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={handleCancelClose}>{t('clients.config.continueEdit')}</AlertDialogCancel>
                        <AlertDialogAction onClick={handleConfirmClose} className="bg-red-600 hover:bg-red-700">
                            {t('clients.config.discardChanges')}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}
