import { useState } from "react";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { apiFetch } from "@/lib/api";
import { useToast } from "@/contexts/toast-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { changePasswordSchema, type ChangePasswordFormData } from "@/lib/validations";

export default function SettingsPage() {
    const { t } = useTranslation();
    const { success, error: toastError } = useToast();
    const [formData, setFormData] = useState<ChangePasswordFormData>({
        old_password: '',
        new_password: '',
        confirm_password: '',
    });
    const [errors, setErrors] = useState<Partial<Record<keyof ChangePasswordFormData, string>>>({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleChange = (field: keyof ChangePasswordFormData, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        // 清除该字段的错误
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: undefined }));
        }
    };

    const validateForm = (): boolean => {
        try {
            changePasswordSchema.parse(formData);
            setErrors({});
            return true;
        } catch (error) {
            if (error instanceof z.ZodError) {
                const fieldErrors: Partial<Record<keyof ChangePasswordFormData, string>> = {};
                error.issues.forEach((issue: z.ZodIssue) => {
                    if (issue.path[0]) {
                        fieldErrors[issue.path[0] as keyof ChangePasswordFormData] = issue.message;
                    }
                });
                setErrors(fieldErrors);
            }
            return false;
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!validateForm()) {
            toastError(t('settings.validationError'));
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
            success(t('settings.passwordChanged'));
            setFormData({
                old_password: '',
                new_password: '',
                confirm_password: '',
            });
            setErrors({});
        } catch (err: any) {
            toastError(err?.data?.error || t('settings.passwordError'));
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="max-w-2xl">
            <h1 className="text-2xl font-bold mb-4">{t('settings.title')}</h1>
            <Card>
                <CardHeader>
                    <CardTitle>{t('settings.changePassword')}</CardTitle>
                    <CardDescription>{t('settings.changePasswordDesc')}</CardDescription>
                </CardHeader>
                <form onSubmit={handleSubmit}>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="old-password">{t('settings.currentPassword')}</Label>
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
                            <Label htmlFor="new-password">{t('settings.newPassword')}</Label>
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
                            <p className="text-xs text-muted-foreground">{t('settings.passwordHint')}</p>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="confirm-password">{t('settings.confirmPassword')}</Label>
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
                        <Button type="submit" disabled={isSubmitting}>
                            {isSubmitting ? t('settings.saving') : t('settings.savePassword')}
                        </Button>
                    </CardFooter>
                </form>
            </Card>
        </div>
    );
}
