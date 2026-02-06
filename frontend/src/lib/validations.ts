/**
 * Zod 验证模式
 * 使用 Zod 进行表单和数据验证
 */
import { z } from 'zod';

// 密码验证
export const passwordSchema = z
  .string()
  .min(8, '密码至少需要 8 个字符')
  .regex(/[A-Z]/, '密码必须包含至少一个大写字母')
  .regex(/[a-z]/, '密码必须包含至少一个小写字母')
  .regex(/[0-9]/, '密码必须包含至少一个数字')
  .regex(/[^A-Za-z0-9]/, '密码必须包含至少一个特殊字符');

// 简化版密码验证（用于设置页面）
export const simplePasswordSchema = z
  .string()
  .min(8, '密码至少需要 8 个字符');

// 客户端名称验证
export const clientNameSchema = z
  .string()
  .min(1, '客户端名称不能为空')
  .max(100, '客户端名称不能超过 100 个字符')
  .regex(/^[a-zA-Z0-9_\-\u4e00-\u9fa5]+$/, '客户端名称只能包含字母、数字、下划线、连字符和中文');

// 端口验证
export const portSchema = z
  .number()
  .int('端口号必须是整数')
  .min(1, '端口号必须在 1-65535 范围内')
  .max(65535, '端口号必须在 1-65535 范围内');

// 服务器地址验证
export const serverAddrSchema = z
  .string()
  .min(1, '服务器地址不能为空')
  .regex(
    /^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/,
    '服务器地址格式不正确'
  );

// 创建客户端表单验证
export const createClientSchema = z.object({
  name: clientNameSchema,
  server_addr: serverAddrSchema.optional(),
  server_port: z.number().int().min(1).max(65535).optional(),
  token: z.string().optional(),
  user: z.string().optional(),
  local_port: portSchema.optional(),
  remote_port: portSchema.optional(),
  always_on: z.boolean().optional(),
  config_content: z.string().optional(),
});

// 更新客户端表单验证
export const updateClientSchema = z.object({
  name: clientNameSchema.optional(),
  enabled: z.boolean().optional(),
  always_on: z.boolean().optional(),
});

// 登录表单验证
export const loginSchema = z.object({
  username: z.string().min(1, '用户名不能为空'),
  password: z.string().min(1, '密码不能为空'),
});

// 修改密码表单验证
export const changePasswordSchema = z.object({
  old_password: z.string().min(1, '请输入旧密码'),
  new_password: simplePasswordSchema,
  confirm_password: z.string().min(1, '请确认新密码'),
}).refine((data) => data.new_password === data.confirm_password, {
  message: '两次输入的密码不一致',
  path: ['confirm_password'],
});

// TOML 配置验证（简单版）
export const tomlConfigSchema = z
  .string()
  .min(1, '配置不能为空')
  .refine((value) => {
    // 基本的 TOML 语法检查
    const lines = value.split('\n');
    let valid = true;

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;

      // 检查表头
      if (trimmed.startsWith('[') && trimmed.endsWith(']')) continue;

      // 检查键值对
      if (trimmed.includes('=')) {
        const parts = trimmed.split('=');
        if (parts.length !== 2) {
          valid = false;
          break;
        }
        if (!parts[0].trim()) {
          valid = false;
          break;
        }
      }
    }

    return valid;
  }, 'TOML 配置格式不正确');

// 导出类型
export type CreateClientFormData = z.infer<typeof createClientSchema>;
export type UpdateClientFormData = z.infer<typeof updateClientSchema>;
export type LoginFormData = z.infer<typeof loginSchema>;
export type ChangePasswordFormData = z.infer<typeof changePasswordSchema>;
