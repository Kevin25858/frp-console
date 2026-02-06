import { useState, useEffect, useCallback, useRef } from 'react';
import { apiFetch, ApiError } from '@/lib/api.ts';

interface UseApiReturn<T> {
  data: T | null;
  isLoading: boolean;
  error: ApiError | null;
  fetchData: (...args: any[]) => Promise<void>;
}

export function useApi<T>(url: string, options: RequestInit = {}, autoFetch = true): UseApiReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(autoFetch);
  const [error, setError] = useState<ApiError | null>(null);

  // 使用 ref 存储 options 以避免不必要的重新渲染
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiFetch(url, optionsRef.current);
      setData(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err);
      } else {
        setError(new ApiError(500, { message: 'An unexpected error occurred' }, (err as Error).message));
      }
    } finally {
      setIsLoading(false);
    }
  }, [url]);

  useEffect(() => {
    if (autoFetch) {
      fetchData();
    }
  }, [fetchData, autoFetch]);

  return { data, isLoading, error, fetchData };
}
