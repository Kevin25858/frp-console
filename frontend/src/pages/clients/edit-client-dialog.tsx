import { useState, useEffect } from "react";
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
import { Checkbox } from "@/components/ui/checkbox";
import { type CheckedState } from "@radix-ui/react-checkbox";
import type { Client } from "@/types";

interface EditClientDialogProps {
    client: Client;
    onClientUpdated: () => void;
    children: React.ReactNode;
}

export function EditClientDialog({ client, onClientUpdated, children }: EditClientDialogProps) {
    const { t } = useTranslation();
    const { success, error: toastError } = useToast();
    const [open, setOpen] = useState(false);
    const [formData, setFormData] = useState(client);

    useEffect(() => {
        setFormData(client);
    }, [client]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { id, value, type } = e.target;
        setFormData(prev => ({
            ...prev,
            [id]: type === 'number' ? parseInt(value) : value,
        }));
    };

    const handleCheckedChange = (checked: CheckedState) => {
        setFormData(prev => ({ ...prev, always_on: !!checked }));
    }

    const handleSubmit = async () => {
        try {
            await apiFetch(`/clients/${client.id}`, {
                method: 'PUT',
                body: JSON.stringify(formData),
            });
            onClientUpdated();
            setOpen(false);
            success(t('clients.updateSuccess'));
        } catch (error) {
            console.error("Failed to update client:", error);
            toastError(t('clients.updateError'));
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>{children}</DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>{t('clients.dialog.editTitle')}</DialogTitle>
                    <DialogDescription>
                        {t('clients.dialog.editDesc')}
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="name" className="text-right">{t('clients.form.nameLabel')}</Label>
                        <Input id="name" value={formData.name} onChange={handleChange} className="col-span-3" />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="local_port" className="text-right">{t('clients.form.localPortLabel')}</Label>
                        <Input id="local_port" type="number" value={formData.local_port} onChange={handleChange} className="col-span-3" />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="remote_port" className="text-right">{t('clients.form.remotePortLabel')}</Label>
                        <Input id="remote_port" type="number" value={formData.remote_port} onChange={handleChange} className="col-span-3" />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="server_addr" className="text-right">{t('clients.form.serverAddrLabel')}</Label>
                        <Input id="server_addr" value={formData.server_addr} onChange={handleChange} className="col-span-3" />
                    </div>
                     <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="server_port" className="text-right">{t('clients.form.serverPortLabel')}</Label>
                        <Input id="server_port" type="number" value={formData.server_port} onChange={handleChange} className="col-span-3" />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="token" className="text-right">{t('clients.form.tokenLabel')}</Label>
                        <Input id="token" value={formData.token} onChange={handleChange} className="col-span-3" />
                    </div>
                     <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="user" className="text-right">{t('clients.form.userLabel')}</Label>
                        <Input id="user" value={formData.user} onChange={handleChange} className="col-span-3" />
                    </div>
                    <div className="flex items-center space-x-2 justify-end">
                        <Checkbox id="always_on" checked={formData.always_on} onCheckedChange={handleCheckedChange} />
                        <Label htmlFor="always_on">{t('clients.form.alwaysOnLabel')}</Label>
                    </div>
                </div>
                <DialogFooter>
                    <Button type="submit" onClick={handleSubmit}>{t('clients.form.save')}</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
