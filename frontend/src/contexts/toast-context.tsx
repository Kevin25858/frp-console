/**
 * Toast 通知上下文
 * 提供全局 Toast 通知功能
 */
import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { ToastType, ToastOptions } from '../types';

interface Toast {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
}

interface ToastContextType {
  toasts: Toast[];
  toast: (options: ToastOptions) => void;
  success: (message: string, title?: string) => void;
  error: (message: string, title?: string) => void;
  warning: (message: string, title?: string) => void;
  info: (message: string, title?: string) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((options: ToastOptions) => {
    const id = Date.now().toString() + Math.random().toString(36).substr(2, 9);
    const newToast: Toast = {
      id,
      type: options.type || 'info',
      title: options.title,
      message: options.message,
    };

    setToasts((prev) => [...prev, newToast]);

    // 自动移除
    const duration = options.duration || 3000;
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, duration);
  }, []);

  const success = useCallback((message: string, title?: string) => {
    toast({ type: 'success', message, title });
  }, [toast]);

  const error = useCallback((message: string, title?: string) => {
    toast({ type: 'error', message, title, duration: 5000 });
  }, [toast]);

  const warning = useCallback((message: string, title?: string) => {
    toast({ type: 'warning', message, title });
  }, [toast]);

  const info = useCallback((message: string, title?: string) => {
    toast({ type: 'info', message, title });
  }, [toast]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider
      value={{ toasts, toast, success, error, warning, info, dismiss }}
    >
      {children}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}