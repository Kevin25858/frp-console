import { useState } from "react";
import { apiFetch } from "@/lib/api.ts";
import { useToast } from "@/contexts/toast-context.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Input } from "@/components/ui/input.tsx";
import { Label } from "@/components/ui/label.tsx";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card.tsx";
import { Loader2, Settings } from "lucide-react";

export default function SettingsPage() {
    const { success, error: toastError } = useToast();

    const [formData, setFormData] = useState({
        old_password: '',
        new_password: '',
        confirm_password: '',
    });
    const [errors, setErrors] = useState<Partial<Record<string, string>>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleChange = (field: string, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: undefined }));
        }
    };

    const validateForm = (): boolean => {
        const newErrors: Partial<Record<string, string>> = {};

        if (!formData.old_password) {
            newErrors.old_password = '请输入当前密码';
        }
        if (!formData.new_password) {
            newErrors.new_password = '请输入新密码';
        } else if (formData.new_password.length < 8) {
            newErrors.new_password = '密码长度至少为 8 个字符';
        }
        if (formData.new_password !== formData.confirm_password) {
            newErrors.confirm_password = '两次输入的密码不一致';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!validateForm()) {
            return;
        }

        setIsSubmitting(true);
        try {
            await apiFetch("/change-password", {
                method: "POST",
                body: JSON.stringify({
                    old_password: formData.old_password,
                    new_password: formData.new_password,
                }),
            });
            success('密码修改成功');
            setFormData({ old_password: '', new_password: '', confirm_password: '' });
            setErrors({});
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : undefined;
            toastError((err as { body?: { error?: string } })?.body?.error || message || '密码修改失败');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="max-w-lg">
            <div className="flex items-center gap-2 mb-4">
                <Settings className="h-6 w-6 text-muted-foreground" />
                <h1 className="text-2xl font-bold">设置</h1>
            </div>

            <Card className="transition-all duration-200 hover:shadow-md">
                <CardHeader>
                    <CardTitle>修改密码</CardTitle>
                    <CardDescription>修改管理员登录密码</CardDescription>
                </CardHeader>
                <form onSubmit={handleSubmit}>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="old-password">当前密码</Label>
                            <Input
                                id="old-password"
                                type="password"
                                value={formData.old_password}
                                onChange={(e) => handleChange('old_password', e.target.value)}
                                required
                            />
                            {errors.old_password && (
                                <p className="text-sm text-destructive">{errors.old_password}</p>
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="new-password">新密码</Label>
                            <Input
                                id="new-password"
                                type="password"
                                value={formData.new_password}
                                onChange={(e) => handleChange('new_password', e.target.value)}
                                required
                            />
                            {errors.new_password && (
                                <p className="text-sm text-destructive">{errors.new_password}</p>
                            )}
                            <p className="text-xs text-muted-foreground">密码长度至少 8 个字符</p>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="confirm-password">确认新密码</Label>
                            <Input
                                id="confirm-password"
                                type="password"
                                value={formData.confirm_password}
                                onChange={(e) => handleChange('confirm_password', e.target.value)}
                                required
                            />
                            {errors.confirm_password && (
                                <p className="text-sm text-destructive">{errors.confirm_password}</p>
                            )}
                        </div>
                    </CardContent>
                    <CardFooter>
                        <Button type="submit" disabled={isSubmitting} className="transition-all active:scale-[0.98]">
                            {isSubmitting ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    保存中...
                                </>
                            ) : (
                                '保存密码'
                            )}
                        </Button>
                    </CardFooter>
                </form>
            </Card>
        </div>
    );
}
