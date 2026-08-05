import { useState } from "react";
import { apiFetch } from "@/lib/api.ts";
import { useToast } from "@/contexts/toast-context.tsx";
import { Button } from "@/components/ui/button.tsx";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog.tsx";
import { Input } from "@/components/ui/input.tsx";
import { Label } from "@/components/ui/label.tsx";
import { Textarea } from "@/components/ui/textarea.tsx";
import { ClipboardPaste, FileText } from "lucide-react";

interface AddClientDialogProps {
    onClientAdded: () => void;
}

export function AddClientDialog({ onClientAdded }: AddClientDialogProps) {
    const { success, error: toastError } = useToast();
    const [open, setOpen] = useState(false);
    const [configText, setConfigText] = useState("");
    const [name, setName] = useState("");

    const pasteFromClipboard = async () => {
        try {
            const text = await navigator.clipboard.readText();
            setConfigText(text);
        } catch {
            toastError('无法读取剪贴板');
        }
    };

    const handleSubmit = async () => {
        if (!configText.trim()) {
            toastError('请输入配置内容');
            return;
        }
        if (!name.trim()) {
            toastError('请输入客户端名称');
            return;
        }

        try {
            await apiFetch("/clients", {
                method: 'POST',
                body: JSON.stringify({
                    name: name.trim(),
                    config_content: configText.trim(),
                }),
            });
            onClientAdded();
            setOpen(false);
            setConfigText("");
            setName("");
            success('客户端创建成功');
        } catch (error) {
            console.error("Failed to add client:", error);
            toastError('创建失败');
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button>添加客户端</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-auto">
                <DialogHeader>
                    <DialogTitle>添加客户端</DialogTitle>
                    <DialogDescription>
                        粘贴 frpc TOML 配置内容
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="name">客户端名称 *</Label>
                        <Input
                            id="name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="my-client"
                        />
                    </div>

                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label className="flex items-center gap-2">
                                <FileText className="h-4 w-4" />
                                配置内容 *
                            </Label>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={pasteFromClipboard}
                                className="gap-1"
                            >
                                <ClipboardPaste className="h-4 w-4" />
                                从剪贴板粘贴
                            </Button>
                        </div>
                        <Textarea
                            value={configText}
                            onChange={(e) => setConfigText(e.target.value)}
                            placeholder={`[common]\nserver_addr = 0.0.0.0\nserver_port = 7000\n\n[proxy]\ntype = tcp\nlocal_ip = 127.0.0.1\nlocal_port = 22\nremote_port = 6000`}
                            className="font-mono text-xs min-h-[300px] bg-slate-950 text-slate-50 border-slate-700"
                            spellCheck={false}
                        />
                    </div>
                </div>

                <DialogFooter>
                    <Button
                        type="submit"
                        onClick={handleSubmit}
                        disabled={!name.trim() || !configText.trim()}
                    >
                        创建
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
