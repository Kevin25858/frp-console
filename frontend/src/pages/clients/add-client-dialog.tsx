import { useState } from "react";
import { useTranslation } from "react-i18next";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ClipboardPaste, FileText } from "lucide-react";

interface AddClientDialogProps {
    onClientAdded: () => void;
}

export function AddClientDialog({ onClientAdded }: AddClientDialogProps) {
    const { t } = useTranslation();
    const { success, error: toastError } = useToast();
    const [open, setOpen] = useState(false);
    const [configText, setConfigText] = useState("");
    const [name, setName] = useState("");
    const [alwaysOn, setAlwaysOn] = useState(false);

    // 从剪贴板粘贴
    const pasteFromClipboard = async () => {
        try {
            const text = await navigator.clipboard.readText();
            setConfigText(text);
        } catch (_err) {
            toastError(t('clients.clipboardError'));
        }
    };

    const handleSubmit = async () => {
        if (!configText.trim()) {
            toastError(t('clients.form.configRequired'));
            return;
        }
        if (!name.trim()) {
            toastError(t('clients.form.nameRequired'));
            return;
        }

        try {
            await apiFetch("/clients", {
                method: 'POST',
                body: JSON.stringify({
                    name: name.trim(),
                    config_content: configText.trim(),
                    always_on: alwaysOn,
                }),
            });
            onClientAdded();
            setOpen(false);
            // 重置表单
            setConfigText("");
            setName("");
            setAlwaysOn(false);
            success(t('clients.addSuccess'));
        } catch (error) {
            console.error("Failed to add client:", error);
            toastError(t('clients.addError'));
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button>{t('clients.addClient')}</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-auto">
                <DialogHeader>
                    <DialogTitle>{t('clients.dialog.addTitle')}</DialogTitle>
                    <DialogDescription>
                        {t('clients.dialog.addDesc')}
                    </DialogDescription>
                </DialogHeader>
                
                <div className="space-y-4 py-4">
                    {/* 客户端名称 */}
                    <div className="space-y-2">
                        <Label htmlFor="name">{t('clients.form.nameLabel')} *</Label>
                        <Input 
                            id="name" 
                            value={name} 
                            onChange={(e) => setName(e.target.value)}
                            placeholder={t('clients.form.namePlaceholder')}
                        />
                    </div>

                    {/* 配置文件 */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label className="flex items-center gap-2">
                                <FileText className="h-4 w-4" />
                                {t('clients.form.configLabel')} *
                            </Label>
                            <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={pasteFromClipboard}
                                className="gap-1"
                            >
                                <ClipboardPaste className="h-4 w-4" />
                                {t('clients.pasteFromClipboard')}
                            </Button>
                        </div>
                        <Textarea
                            value={configText}
                            onChange={(e) => setConfigText(e.target.value)}
                            placeholder={t('clients.form.configPlaceholder')}
                            className="font-mono text-xs min-h-[300px] bg-slate-950 text-slate-50 border-slate-700"
                            spellCheck={false}
                        />
                    </div>

                    {/* Always On */}
                    <div className="flex items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                            <Label htmlFor="always_on" className="text-base">{t('clients.form.alwaysOnLabel')}</Label>
                            <p className="text-sm text-muted-foreground">
                                {t('clients.form.alwaysOnDesc')}
                            </p>
                        </div>
                        <Switch
                            id="always_on"
                            checked={alwaysOn}
                            onCheckedChange={(checked) => setAlwaysOn(checked)}
                        />
                    </div>
                </div>

                <DialogFooter>
                    <Button 
                        type="submit" 
                        onClick={handleSubmit}
                        disabled={!name.trim() || !configText.trim()}
                    >
                        {t('clients.form.submit')}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
