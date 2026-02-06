import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useApi } from "@/hooks/useApi.ts";
import { apiFetch } from "@/lib/api.ts";
import { useToast } from "@/contexts/toast-context.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Input } from "@/components/ui/input.tsx";
import { Label } from "@/components/ui/label.tsx";
import { Badge } from "@/components/ui/badge.tsx";
import { Switch } from "@/components/ui/switch.tsx";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table.tsx";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
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
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog.tsx";
import { Plus, Pencil, Trash2, Key, User as UserIcon, RefreshCw } from "lucide-react";
import type { User } from "@/types";

export default function UsersPage() {
  const { t } = useTranslation();
  const { success, error: toastError } = useToast();
  const { data: users, isLoading, error, fetchData: fetchUsers } = useApi<User[]>("/users");

  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isResetPasswordDialogOpen, setIsResetPasswordDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    role: "operator",
  });
  const [resetPasswordData, setResetPasswordData] = useState({
    new_password: "",
    confirm_password: "",
  });

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiFetch("/users", {
        method: "POST",
        body: JSON.stringify(formData),
      });
      success(t('users.addSuccess'));
      setIsAddDialogOpen(false);
      setFormData({ username: "", password: "", role: "operator" });
      fetchUsers();
    } catch (err: any) {
      toastError(err?.data?.error || t('users.addError'));
    }
  };

  const handleEditUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;

    try {
      await apiFetch(`/users/${selectedUser.id}`, {
        method: "PUT",
        body: JSON.stringify({
          username: formData.username,
          role: formData.role,
        }),
      });
      success(t('users.updateSuccess'));
      setIsEditDialogOpen(false);
      setSelectedUser(null);
      fetchUsers();
    } catch (err: any) {
      toastError(err?.data?.error || t('users.updateError'));
    }
  };

  const handleDeleteUser = async (userId: number) => {
    try {
      await apiFetch(`/users/${userId}`, {
        method: "DELETE",
      });
      success(t('users.deleteSuccess'));
      fetchUsers();
    } catch (err: any) {
      toastError(err?.data?.error || t('users.deleteError'));
    }
  };

  const handleToggleStatus = async (user: User) => {
    try {
      await apiFetch(`/users/${user.id}/status`, {
        method: "PUT",
        body: JSON.stringify({
          is_active: !user.is_active,
        }),
      });
      success(!user.is_active ? t('users.enableSuccess') : t('users.disableSuccess'));
      fetchUsers();
    } catch (err: any) {
      toastError(err?.data?.error || t('users.statusError'));
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;

    if (resetPasswordData.new_password !== resetPasswordData.confirm_password) {
      toastError(t('users.passwordMismatch'));
      return;
    }

    try {
      await apiFetch(`/users/${selectedUser.id}/reset-password`, {
        method: "POST",
        body: JSON.stringify({
          new_password: resetPasswordData.new_password,
        }),
      });
      success(t('users.resetPasswordSuccess'));
      setIsResetPasswordDialogOpen(false);
      setResetPasswordData({ new_password: "", confirm_password: "" });
      setSelectedUser(null);
    } catch (err: any) {
      toastError(err?.data?.error || t('users.resetPasswordError'));
    }
  };

  const openEditDialog = (user: User) => {
    setSelectedUser(user);
    setFormData({
      username: user.username,
      password: "",
      role: user.role,
    });
    setIsEditDialogOpen(true);
  };

  const openResetPasswordDialog = (user: User) => {
    setSelectedUser(user);
    setResetPasswordData({ new_password: "", confirm_password: "" });
    setIsResetPasswordDialogOpen(true);
  };

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case "admin":
        return "destructive";
      case "operator":
        return "default";
      case "viewer":
        return "secondary";
      default:
        return "secondary";
    }
  };

  const getRoleLabel = (role: string) => {
    switch (role) {
      case "admin":
        return t('users.roles.admin');
      case "operator":
        return t('users.roles.operator');
      case "viewer":
        return t('users.roles.viewer');
      default:
        return role;
    }
  };

  if (isLoading && !users) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">{t('common.loading')}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <div className="text-destructive font-medium">{error.message}</div>
        <Button variant="outline" onClick={fetchUsers}>
          <RefreshCw className="mr-2 h-4 w-4" />
          {t('common.retry')}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">{t('users.title')}</h2>
          <p className="text-muted-foreground mt-1">{t('users.subtitle')}</p>
        </div>
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              {t('users.addUser')}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('users.addUser')}</DialogTitle>
              <DialogDescription>{t('users.addUserDesc')}</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddUser}>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="username">{t('users.username')}</Label>
                  <Input
                    id="username"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    placeholder={t('users.usernamePlaceholder')}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">{t('users.password')}</Label>
                  <Input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder={t('users.passwordPlaceholder')}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role">{t('users.role')}</Label>
                  <select
                    id="role"
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full px-3 py-2 border rounded-md bg-background"
                    required
                  >
                    <option value="admin">{t('users.roles.admin')}</option>
                    <option value="operator">{t('users.roles.operator')}</option>
                    <option value="viewer">{t('users.roles.viewer')}</option>
                  </select>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsAddDialogOpen(false)}>
                  {t('common.cancel')}
                </Button>
                <Button type="submit">{t('users.addUser')}</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* 用户列表 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t('users.username')}</TableHead>
              <TableHead>{t('users.role')}</TableHead>
              <TableHead>{t('users.status')}</TableHead>
              <TableHead>{t('users.createdAt')}</TableHead>
              <TableHead className="text-right">{t('users.actions')}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users?.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium">
                  <div className="flex items-center space-x-2">
                    <UserIcon className="h-4 w-4 text-muted-foreground" />
                    <span>{user.username}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={getRoleBadgeVariant(user.role)}>
                    {getRoleLabel(user.role)}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center space-x-2">
                    <Switch
                      checked={user.is_active}
                      onCheckedChange={() => handleToggleStatus(user)}
                    />
                    <span className={user.is_active ? "text-green-600" : "text-gray-500"}>
                      {user.is_active ? t('users.active') : t('users.inactive')}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {user.created_at ? new Date(user.created_at).toLocaleString() : '-'}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end space-x-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openEditDialog(user)}
                      title={t('users.edit')}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openResetPasswordDialog(user)}
                      title={t('users.resetPassword')}
                    >
                      <Key className="h-4 w-4" />
                    </Button>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="icon" title={t('users.delete')}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>{t('users.deleteConfirmTitle')}</AlertDialogTitle>
                          <AlertDialogDescription>
                            {t('users.deleteConfirmDesc', { username: user.username })}
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => handleDeleteUser(user.id)}
                            className="bg-destructive hover:bg-destructive/90"
                          >
                            {t('common.delete')}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {(!users || users.length === 0) && (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                  {t('users.noUsers')}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* 编辑用户对话框 */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('users.editUser')}</DialogTitle>
            <DialogDescription>{t('users.editUserDesc')}</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleEditUser}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit-username">{t('users.username')}</Label>
                <Input
                  id="edit-username"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-role">{t('users.role')}</Label>
                <select
                  id="edit-role"
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md bg-background"
                  required
                >
                  <option value="admin">{t('users.roles.admin')}</option>
                  <option value="operator">{t('users.roles.operator')}</option>
                  <option value="viewer">{t('users.roles.viewer')}</option>
                </select>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button type="submit">{t('users.save')}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* 重置密码对话框 */}
      <Dialog open={isResetPasswordDialogOpen} onOpenChange={setIsResetPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('users.resetPassword')}</DialogTitle>
            <DialogDescription>
              {t('users.resetPasswordDesc', { username: selectedUser?.username })}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleResetPassword}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="new-password">{t('users.newPassword')}</Label>
                <Input
                  id="new-password"
                  type="password"
                  value={resetPasswordData.new_password}
                  onChange={(e) => setResetPasswordData({ ...resetPasswordData, new_password: e.target.value })}
                  placeholder={t('users.newPasswordPlaceholder')}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm-password">{t('users.confirmPassword')}</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  value={resetPasswordData.confirm_password}
                  onChange={(e) => setResetPasswordData({ ...resetPasswordData, confirm_password: e.target.value })}
                  placeholder={t('users.confirmPasswordPlaceholder')}
                  required
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsResetPasswordDialogOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button type="submit">{t('users.resetPassword')}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
