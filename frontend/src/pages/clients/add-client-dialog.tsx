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
import { ClipboardPaste, FileText, Settings2 } from "lucide-react";

interface AddClientDialogProps {
    onClientAdded: () => void;
}

type Mode = "paste" | "form";

export function AddClientDialog({ onClientAdded }: AddClientDialogProps) {
    const { success, error: toastError } = useToast();
    const [open, setOpen] = useState(false);
    const [mode, setMode] = useState<Mode>("paste");

    // 公共字段
    const [name, setName] = useState("");
    const [frpVersion, setFrpVersion] = useState("");

    // 粘贴模式
    const [configText, setConfigText] = useState("");

    // 表单模式
    const [serverAddr, setServerAddr] = useState("");
    const [serverPort, setServerPort] = useState("7000");
    const [token, setToken] = useState("");
    const [user, setUser] = useState("");
    const [proxyName, setProxyName] = useState("");
    const [localPort, setLocalPort] = useState("");
    const [remotePort, setRemotePort] = useState("");

    const resetForm = () => {
        setName("");
        setFrpVersion("");
        setConfigText("");
        setServerAddr("");
        setServerPort("7000");
        setToken("");
        setUser("");
        setProxyName("");
        setLocalPort("");
        setRemotePort("");
        setMode("paste");
    };

    const pasteFromClipboard = async () => {
        try {
            const text = await navigator.clipboard.readText();
            setConfigText(text);
        } catch {
            toastError('无法读取剪贴板');
        }
    };

    const buildPayload = () => {
        const payload: Record<string, string> = { name: name.trim() };
        if (frpVersion.trim()) {
            payload.frp_version = frpVersion.trim();
        }
        if (mode === 'paste') {
            payload.config_content = configText.trim();
        } else {
            payload.server_addr = serverAddr.trim();
            if (serverPort.trim()) payload.server_port = serverPort.trim();
            if (token.trim()) payload.token = token.trim();
            if (user.trim()) payload.user = user.trim();
            if (proxyName.trim()) payload.proxy_name = proxyName.trim();
            if (localPort.trim()) payload.local_port = localPort.trim();
            if (remotePort.trim()) payload.remote_port = remotePort.trim();
        }
        return payload;
    };

    const validate = (): string | null => {
        if (!name.trim()) return '请输入客户端名称';
        if (mode === 'paste') {
            if (!configText.trim()) return '请输入配置内容';
        } else {
            if (!serverAddr.trim()) return '请输入服务器地址';
            if (!localPort.trim()) return '请输入本地端口';
            if (!remotePort.trim()) return '请输入远程端口';
        }
        return null;
    };

    const handleSubmit = async () => {
        const err = validate();
        if (err) {
            toastError(err);
            return;
        }

        try {
            await apiFetch("/clients", {
                method: 'POST',
                body: JSON.stringify(buildPayload()),
            });
            onClientAdded();
            setOpen(false);
            resetForm();
            success('客户端创建成功');
        } catch (error) {
            console.error("Failed to add client:", error);
            const msg = (error as { body?: { error?: string } })?.body?.error || '创建失败';
            toastError(msg);
        }
    };

    const canSubmit = name.trim() && (
        mode === 'paste' ? configText.trim() : (serverAddr.trim() && localPort.trim() && remotePort.trim())
    );

    return (
        <Dialog open={open} onOpenChange={(v) => {
            setOpen(v);
            if (!v) resetForm();
        }}>
            <DialogTrigger asChild>
                <Button>添加客户端</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-auto">
                <DialogHeader>
                    <DialogTitle>添加客户端</DialogTitle>
                    <DialogDescription>
                        选择粘贴现有 frpc TOML 配置，或通过表单生成新配置
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

                    {/* 模式切换 */}
                    <div className="grid grid-cols-2 gap-2 rounded-lg border p-1 bg-muted/40">
                        <button
                            type="button"
                            onClick={() => setMode("paste")}
                            className={`flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                                mode === 'paste'
                                    ? 'bg-background text-foreground shadow-sm'
                                    : 'text-muted-foreground hover:text-foreground'
                            }`}
                        >
                            <ClipboardPaste className="h-4 w-4" />
                            粘贴配置
                        </button>
                        <button
                            type="button"
                            onClick={() => setMode("form")}
                            className={`flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                                mode === 'form'
                                    ? 'bg-background text-foreground shadow-sm'
                                    : 'text-muted-foreground hover:text-foreground'
                            }`}
                        >
                            <Settings2 className="h-4 w-4" />
                            表单生成
                        </button>
                    </div>

                    {mode === 'paste' ? (
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
                                placeholder={`serverAddr = "0.0.0.0"\nserverPort = 7000\n\n[[proxies]]\nname = "ssh"\ntype = "tcp"\nlocalIP = "127.0.0.1"\nlocalPort = 22\nremotePort = 6000`}
                                className="font-mono text-xs min-h-[300px] bg-slate-950 text-slate-50 border-slate-700"
                                spellCheck={false}
                            />
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2 col-span-2">
                                <Label htmlFor="server_addr">服务器地址 *</Label>
                                <Input
                                    id="server_addr"
                                    value={serverAddr}
                                    onChange={(e) => setServerAddr(e.target.value)}
                                    placeholder="example.com 或 1.2.3.4"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="server_port">服务器端口</Label>
                                <Input
                                    id="server_port"
                                    value={serverPort}
                                    onChange={(e) => setServerPort(e.target.value)}
                                    placeholder="7000"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="user">用户名（可选）</Label>
                                <Input
                                    id="user"
                                    value={user}
                                    onChange={(e) => setUser(e.target.value)}
                                    placeholder="留空表示不使用"
                                />
                            </div>
                            <div className="space-y-2 col-span-2">
                                <Label htmlFor="token">Token（可选）</Label>
                                <Input
                                    id="token"
                                    value={token}
                                    onChange={(e) => setToken(e.target.value)}
                                    placeholder="留空表示不使用认证"
                                />
                            </div>
                            <div className="space-y-2 col-span-2">
                                <Label htmlFor="proxy_name">代理名称（可选）</Label>
                                <Input
                                    id="proxy_name"
                                    value={proxyName}
                                    onChange={(e) => setProxyName(e.target.value)}
                                    placeholder="留空则使用客户端名称"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="local_port">本地端口 *</Label>
                                <Input
                                    id="local_port"
                                    value={localPort}
                                    onChange={(e) => setLocalPort(e.target.value)}
                                    placeholder="22"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="remote_port">远程端口 *</Label>
                                <Input
                                    id="remote_port"
                                    value={remotePort}
                                    onChange={(e) => setRemotePort(e.target.value)}
                                    placeholder="6000"
                                />
                            </div>
                        </div>
                    )}

                    <div className="space-y-2">
                        <Label htmlFor="frp_version">frp 版本（可选）</Label>
                        <Input
                            id="frp_version"
                            value={frpVersion}
                            onChange={(e) => setFrpVersion(e.target.value)}
                            placeholder="留空表示自动使用最新版本"
                        />
                        <p className="text-xs text-muted-foreground">
                            留空时启动容器会自动从 GitHub 获取最新版本并回写。可填入如 v0.61.1 指定版本。
                        </p>
                    </div>
                </div>

                <DialogFooter>
                    <Button
                        type="submit"
                        onClick={handleSubmit}
                        disabled={!canSubmit}
                    >
                        创建
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
