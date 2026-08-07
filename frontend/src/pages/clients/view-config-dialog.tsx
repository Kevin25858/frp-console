import { useState, useEffect, ReactNode, useRef } from "react";
import { EditorView, keymap, placeholder as cmPlaceholder } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { StreamLanguage, type StringStream } from "@codemirror/language";
import { oneDark } from "@codemirror/theme-one-dark";
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
import { FileText, Copy, Save, Check } from "lucide-react";

// TOML 语法高亮
const tomlLanguage = StreamLanguage.define({
    token(stream: StringStream) {
        if (stream.match(/^#.*/)) return "comment";
        if (stream.match(/^\[[\w.-]+\]/)) return "keyword";
        if (stream.match(/^\[\[[\w.-]+\]\]/)) return "keyword";
        if (stream.match(/^[\w.-]+\s*(?==)/)) return "variableName";
        if (stream.match(/"([^"\\]|\\.)*"/)) return "string";
        if (stream.match(/'([^'\\]|\\.)*'/)) return "string";
        if (stream.match(/\b(true|false)\b/)) return "bool";
        if (stream.match(/\b\d+(\.\d+)?\b/)) return "number";
        if (stream.match(/=/)) return "operator";
        stream.next();
        return null;
    },
    startState() { return {}; }
});

interface ViewConfigDialogProps {
    clientId: number;
    clientName: string;
    children?: ReactNode;
}

interface ConfigResponse {
    config: string;
}

function CodeEditor({
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
    const containerRef = useRef<HTMLDivElement>(null);
    const viewRef = useRef<EditorView | null>(null);
    const onChangeRef = useRef(onChange);
    onChangeRef.current = onChange;

    useEffect(() => {
        if (!containerRef.current) return;

        const updateListener = EditorView.updateListener.of((update) => {
            if (update.docChanged) {
                onChangeRef.current(update.state.doc.toString());
            }
        });

        const state = EditorState.create({
            doc: value,
            extensions: [
                history(),
                keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
                tomlLanguage,
                oneDark,
                updateListener,
                cmPlaceholder(placeholder || ""),
                EditorView.lineWrapping,
                EditorView.theme({
                    "&": { height: "100%" },
                    ".cm-scroller": { overflow: "auto" },
                    ".cm-content": { fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace' },
                    ".cm-gutters": { display: "none" },
                }),
            ],
        });

        const view = new EditorView({
            state,
            parent: containerRef.current,
        });

        viewRef.current = view;

        return () => {
            view.destroy();
            viewRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps -- 仅在挂载时初始化编辑器，value 由下方 useEffect 同步，placeholder 不变
    }, []);

    useEffect(() => {
        const view = viewRef.current;
        if (!view) return;
        const current = view.state.doc.toString();
        if (current !== value) {
            view.dispatch({
                changes: { from: 0, to: current.length, insert: value },
            });
        }
    }, [value]);

    return (
        <div
            ref={containerRef}
            className={`flex-1 min-h-0 rounded-md border overflow-hidden ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
        />
    );
}

export function ViewConfigDialog({ clientId, clientName, children }: ViewConfigDialogProps) {
    const [open, setOpen] = useState(false);
    const [showConfirmDialog, setShowConfirmDialog] = useState(false);
    const [configContent, setConfigContent] = useState("");
    const [originalContent, setOriginalContent] = useState("");
    const [isSaving, setIsSaving] = useState(false);
    const [isCopied, setIsCopied] = useState(false);
    const { success, error: toastError } = useToast();

    const { data: configData, isLoading, error, fetchData } = useApi<ConfigResponse>(
        `/clients/${clientId}/config`,
        {},
        false
    );

    useEffect(() => {
        if (open) fetchData();
    }, [open, fetchData]);

    useEffect(() => {
        if (configData?.config) {
            setConfigContent(configData.config);
            setOriginalContent(configData.config);
        }
    }, [configData]);

    const handleContentChange = (newContent: string) => {
        setConfigContent(newContent);
    };

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(configContent);
            setIsCopied(true);
            setTimeout(() => setIsCopied(false), 2000);
            success('已复制到剪贴板');
        } catch {
            toastError('复制失败');
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await apiFetch(`/clients/${clientId}/config`, {
                method: 'PUT',
                body: JSON.stringify({ config: configContent }),
            });
            success('配置已保存');
            setOriginalContent(configContent);
            setOpen(false);
        } catch (error: unknown) {
            console.error("Failed to save config:", error);
            const errorMsg = (error as { body?: { error?: string }; message?: string })?.body?.error || (error as { message?: string })?.message || '保存失败';
            toastError(`保存失败: ${errorMsg}`);
        } finally {
            setIsSaving(false);
        }
    };

    const hasChanges = configContent !== originalContent;

    const handleOpenChange = (newOpen: boolean) => {
        if (!newOpen && hasChanges) {
            setShowConfirmDialog(true);
        } else {
            setOpen(newOpen);
        }
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
                        <DialogTitle>配置编辑 - {clientName}</DialogTitle>
                    </DialogHeader>

                    <div className="flex items-center gap-2 py-2 border-b">
                        <Button
                            size="sm"
                            onClick={handleSave}
                            disabled={isSaving || isLoading || !hasChanges}
                            className="gap-1"
                        >
                            <Save className="h-4 w-4" />
                            {isSaving ? "保存中..." : "保存"}
                        </Button>
                        <Button size="sm" variant="outline" onClick={handleCopy} disabled={isLoading} className="gap-1">
                            {isCopied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                            {isCopied ? "已复制" : "复制"}
                        </Button>
                    </div>

                    <div className="flex-1 mt-2 min-h-0 flex flex-col">
                        {isLoading && <p className="text-muted-foreground">加载中...</p>}
                        {error && <p className="text-red-500">加载失败: {error.message}</p>}
                        {!isLoading && !error && (
                            <CodeEditor
                                value={configContent}
                                onChange={handleContentChange}
                                disabled={isLoading}
                                placeholder="粘贴 frpc TOML 配置..."
                            />
                        )}
                    </div>

                    <div className="flex items-center justify-between py-2 text-xs text-muted-foreground border-t mt-2">
                        <div>
                            {hasChanges && <span className="text-orange-500">● 有未保存的更改</span>}
                        </div>
                        <div>
                            行数: {configContent.split('\n').length} | 字符: {configContent.length}
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>有未保存的更改</AlertDialogTitle>
                        <AlertDialogDescription>
                            当前配置有未保存的更改，确定要关闭吗？更改将丢失。
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setShowConfirmDialog(false)}>继续编辑</AlertDialogCancel>
                        <AlertDialogAction onClick={() => { setShowConfirmDialog(false); setOpen(false); }} className="bg-red-600 hover:bg-red-700">
                            放弃更改
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}
