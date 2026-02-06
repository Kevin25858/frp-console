/**
 * 配置文件编辑器组件
 * 提供配置文件的查看和编辑功能
 */
import React, { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/api.ts';
import { useToast } from '@/contexts/toast-context.tsx';
import { Button } from '@/components/ui/button.tsx';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog.tsx';
import { FileCode, Save, Download } from 'lucide-react';

interface ConfigEditorProps {
    clientId: number;
    clientName: string;
    trigger: React.ReactNode;
    readOnly?: boolean;
}

export function ConfigEditor({ clientId, clientName, trigger, readOnly = false }: ConfigEditorProps) {
    const { success, error: toastError, info } = useToast();
    const [open, setOpen] = useState(false);
    const [config, setConfig] = useState('');
    const [originalConfig, setOriginalConfig] = useState('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [hasChanges, setHasChanges] = useState(false);

    // 加载配置文件
    useEffect(() => {
        if (!open) return;

        const loadConfig = async () => {
            setLoading(true);
            try {
                const response = await apiFetch(`/clients/${clientId}/config`);
                setConfig(response.config || '');
                setOriginalConfig(response.config || '');
                setHasChanges(false);
            } catch (error) {
                toastError('加载配置文件失败');
                console.error('Failed to load config:', error);
            } finally {
                setLoading(false);
            }
        };

        loadConfig();
    }, [clientId, open]);

    const handleConfigChange = (value: string) => {
        setConfig(value);
        setHasChanges(value !== originalConfig);
    };

    const handleSave = async () => {
        if (readOnly) return;

        setSaving(true);
        try {
            // 简单的 TOML 格式验证
            const validationError = validateTOML(config);
            if (validationError) {
                toastError(validationError);
                return;
            }

            await apiFetch(`/clients/${clientId}/config`, {
                method: 'PUT',
                body: JSON.stringify({ config }),
            });

            setOriginalConfig(config);
            setHasChanges(false);
            success('配置文件已保存');

            // 提示用户重启客户端以应用更改
            info('配置已更新，请重启客户端以应用更改');
        } catch (error) {
            toastError('保存配置失败');
            console.error('Failed to save config:', error);
        } finally {
            setSaving(false);
        }
    };

    const handleDownload = () => {
        const blob = new Blob([config], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${clientName}.toml`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        info('配置文件已下载');
    };

    const handleReset = () => {
        setConfig(originalConfig);
        setHasChanges(false);
        info('已恢复原始配置');
    };

    // 简单的 TOML 格式验证
    const validateTOML = (toml: string): string | null => {
        if (!toml.trim()) {
            return '配置不能为空';
        }

        // 检查基本的 TOML 语法
        const lines = toml.split('\n');

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();

            // 跳过注释和空行
            if (!line || line.startsWith('#')) {
                continue;
            }

            // 检查表头
            if (line.startsWith('[') && line.endsWith(']')) {
                continue;
            }

            // 检查键值对
            if (line.includes('=')) {
                const parts = line.split('=');
                if (parts.length !== 2) {
                    return `第 ${i + 1} 行：无效的键值对格式`;
                }
                const key = parts[0].trim();
                if (!key) {
                    return `第 ${i + 1} 行：键不能为空`;
                }
            }
        }

        return null;
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>{trigger}</DialogTrigger>
            <DialogContent className="sm:max-w-[800px] max-h-[90vh] flex flex-col">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <FileCode className="h-5 w-5" />
                        配置文件编辑器 - {clientName}
                    </DialogTitle>
                    <DialogDescription>
                        查看{readOnly ? '' : '和编辑'}客户端的 TOML 配置文件
                    </DialogDescription>
                </DialogHeader>

                <div className="flex-1 overflow-hidden flex flex-col">
                    {loading ? (
                        <div className="flex items-center justify-center h-64">
                            <div className="text-muted-foreground">加载配置文件中...</div>
                        </div>
                    ) : (
                        <textarea
                            value={config}
                            onChange={(e) => handleConfigChange(e.target.value)}
                            readOnly={readOnly}
                            className="flex-1 w-full min-h-[400px] p-4 font-mono text-sm bg-muted border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                            placeholder="# 配置文件内容"
                            spellCheck={false}
                        />
                    )}
                </div>

                <DialogFooter className="gap-2">
                    {!readOnly && (
                        <>
                            {hasChanges && (
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={handleReset}
                                    disabled={saving}
                                >
                                    重置
                                </Button>
                            )}
                            <Button
                                type="button"
                                variant="outline"
                                onClick={handleDownload}
                                disabled={loading || saving}
                            >
                                <Download className="h-4 w-4 mr-2" />
                                下载
                            </Button>
                            <Button
                                type="button"
                                onClick={handleSave}
                                disabled={loading || saving || !hasChanges || readOnly}
                            >
                                <Save className="h-4 w-4 mr-2" />
                                {saving ? '保存中...' : '保存'}
                            </Button>
                        </>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
