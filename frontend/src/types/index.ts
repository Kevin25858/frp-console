/**
 * 共享类型定义
 * 统一管理所有 TypeScript 类型
 */

// 客户端状态
export type ClientStatus = 'running' | 'stopped' | 'error';

// 客户端类型
export interface Client {
  id: number;
  name: string;
  config_path: string;
  local_port: number;
  remote_port: number;
  server_addr: string;
  server_port?: number; // 可选的 FRP 服务器端口
  token?: string; // 可选的认证令牌
  user?: string; // 可选的用户名
  status: ClientStatus;
  enabled: boolean;
  always_on: boolean;
  traffic_in_cache: number;
  traffic_out_cache: number;
  connections_active_cache: number;
  created_at: string;
  updated_at: string;
}

// 创建客户端表单数据
export interface CreateClientFormData {
  name: string;
  server_addr?: string;
  server_port?: number;
  token?: string;
  user?: string;
  local_port?: number;
  remote_port?: number;
  always_on?: boolean;
  config_content?: string; // 粘贴配置模式
}

// 更新客户端表单数据
export interface UpdateClientFormData {
  name?: string;
  enabled?: boolean;
  always_on?: boolean;
}

// 告警类型
export type AlertType = 'restart_limit' | 'always_on_failed' | 'offline';

// 告警状态
export interface Alert {
  id: number;
  client_id: number | null;
  alert_type: AlertType;
  message: string;
  sent_to: string;
  sent_at: string;
  resolved: boolean;
  client_name?: string; // 连接查询时包含
}

// 告警统计
export interface AlertStats {
  total: number;
  unresolved: number;
  resolved: number;
  by_type: Record<AlertType, number>;
}

// API 响应
export interface ApiResponse<T = any> {
  message?: string;
  error?: string;
  data?: T;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// 登录表单数据
export interface LoginFormData {
  username: string;
  password: string;
}

// 修改密码表单数据
export interface ChangePasswordFormData {
  old_password: string;
  new_password: string;
}

// 用户角色类型
export type UserRole = 'admin' | 'operator' | 'viewer';

// 用户信息
export interface User {
  id: number;
  username: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// 创建用户表单数据
export interface CreateUserFormData {
  username: string;
  password: string;
  role: UserRole;
}

// 更新用户表单数据
export interface UpdateUserFormData {
  role?: UserRole;
  is_active?: boolean;
}

// 重置密码表单数据
export interface ResetPasswordFormData {
  new_password: string;
}

// Dashboard 统计数据
export interface DashboardStats {
  total: number;
  running: number;
  stopped: number;
  error: number;
}

// Toast 消息类型
export type ToastType = 'success' | 'error' | 'warning' | 'info';

// Toast 配置
export interface ToastOptions {
  type?: ToastType;
  title?: string;
  message: string;
  description?: string; // 可选的详细描述
  duration?: number;
}

// 环境配置
export interface AppConfig {
  apiUrl: string;
  version: string;
}