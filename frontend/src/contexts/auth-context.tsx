import { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import type { UserRole } from '@/types';

interface AuthContextType {
    isAuthenticated: boolean;
    isLoading: boolean;
    username?: string;
    userRole?: UserRole;
    checkAuth: () => Promise<void>;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [username, setUsername] = useState<string | undefined>();
    const [userRole, setUserRole] = useState<UserRole | undefined>();
    const isCheckingRef = useRef<boolean>(false);
    const abortControllerRef = useRef<AbortController | null>(null);

    const checkAuth = async () => {
        // 使用 useRef 来防止重复检查，因为它的更新是同步的
        if (isCheckingRef.current) {
            console.log('[Auth] Already checking auth, skipping...');
            return;
        }

        // 取消之前的请求
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        // 创建新的 AbortController
        abortControllerRef.current = new AbortController();

        isCheckingRef.current = true;
        setIsLoading(true);
        try {
            const response = await fetch('/api/me', {
                credentials: 'include',
                signal: abortControllerRef.current.signal
            });
            console.log('[Auth] /api/me response status:', response.status);
            if (response.ok) {
                const data = await response.json();
                console.log('[Auth] User is authenticated:', data);
                setIsAuthenticated(true);
                setUsername(data.username);
                setUserRole(data.role);
            } else {
                console.log('[Auth] User is not authenticated');
                setIsAuthenticated(false);
                setUsername(undefined);
                setUserRole(undefined);
            }
        } catch (error) {
            // 忽略被取消的请求
            if (error instanceof Error && error.name === 'AbortError') {
                console.log('[Auth] Request was aborted');
                return;
            }
            console.error('[Auth] Check auth error:', error);
            setIsAuthenticated(false);
            setUsername(undefined);
            setUserRole(undefined);
        } finally {
            setIsLoading(false);
            isCheckingRef.current = false;
            abortControllerRef.current = null;
        }
    };

    const logout = async () => {
        try {
            const response = await fetch('/logout', {
                credentials: 'include',
                method: 'GET'
            });
            if (response.ok) {
                setIsAuthenticated(false);
                setUsername(undefined);
                setUserRole(undefined);
                console.log('[Auth] User logged out successfully');
            }
        } catch (error) {
            console.error('[Auth] Logout error:', error);
            // 即使失败也清除本地状态
            setIsAuthenticated(false);
            setUsername(undefined);
            setUserRole(undefined);
        }
    };

    useEffect(() => {
        console.log('[Auth] Initializing auth check');
        checkAuth();

        // 清理函数：取消挂载时的请求
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    return (
        <AuthContext.Provider value={{ isAuthenticated, isLoading, username, userRole, checkAuth, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
