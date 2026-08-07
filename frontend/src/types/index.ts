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
  local_port: number;
  remote_port: number;
  server_addr: string;
  server_port?: number; // 可选的 FRP 服务器端口
  token?: string; // 可选的认证令牌
  user?: string; // 可选的用户名
  status: ClientStatus;
  error_msg?: string; // 异常时的最近错误信息
  enabled: boolean;
  frp_version?: string; // frp 版本（留空表示自动取最新）
  image?: string; // 自定义镜像
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
  proxy_name?: string; // 代理名称（表单生成模式）
  local_port?: number;
  remote_port?: number;
  frp_version?: string; // 可选，留空自动取最新
  image?: string; // 可选，自定义镜像
  config_content?: string; // 粘贴配置模式
}

// 更新客户端表单数据
export interface UpdateClientFormData {
  name?: string;
  enabled?: boolean;
  frp_version?: string;
  image?: string;
}

// API 响应
export interface ApiResponse<T = unknown> {
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