import { useState, useEffect, useCallback, useRef } from 'react';
import { apiFetch, ApiError } from '@/lib/api.ts';

interface UseApiReturn<T> {
  data: T | null;
  isLoading: boolean;
  error: ApiError | null;
  fetchData: (signal?: AbortSignal) => Promise<void>;
}

/**
 * 比较两个对象是否相等（浅比较）
 */
function shallowEqual(objA: Record<string, unknown>, objB: Record<string, unknown>): boolean {
  if (objA === objB) return true;
  const keysA = Object.keys(objA);
  const keysB = Object.keys(objB);
  if (keysA.length !== keysB.length) return false;
  for (const key of keysA) {
    if (objA[key] !== objB[key]) return false;
  }
  return true;
}

export function useApi<T>(url: string, options: RequestInit = {}, autoFetch = true): UseApiReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(autoFetch);
  const [error, setError] = useState<ApiError | null>(null);

  // 使用 ref 存储 abortController
  const abortControllerRef = useRef<AbortController | null>(null);

  // 使用 ref 存储上一次的 options，用于比较
  const prevOptionsRef = useRef(options);
  const optionsRef = useRef(options);

  // 只在 options 真正变化时更新 ref
  if (!shallowEqual(prevOptionsRef.current as Record<string, unknown>, options as Record<string, unknown>)) {
    optionsRef.current = options;
    prevOptionsRef.current = options;
  }

  const fetchData = useCallback(async (signal?: AbortSignal) => {
    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // 创建新的 AbortController，但如果外部提供了 signal，则使用外部的
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // 如果外部提供了 signal，监听它的 abort 事件
    if (signal) {
      signal.addEventListener('abort', () => {
        abortController.abort();
      });
    }

    setIsLoading(true);
    setError(null);
    try {
      const result = await apiFetch<T>(url, {
        ...optionsRef.current,
        signal: abortController.signal,
      });
      setData(result);
    } catch (err) {
      // 忽略被取消的请求
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      if (err instanceof ApiError) {
        setError(err);
      } else {
        const message = err instanceof Error ? err.message : 'An unexpected error occurred';
        setError(new ApiError(500, { message }, message));
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [url]); // 依赖 url，options 通过 ref 管理

  useEffect(() => {
    if (autoFetch) {
      fetchData();
    }

    // 清理函数：取消挂载时的请求
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchData, autoFetch]);

  return { data, isLoading, error, fetchData };
}
