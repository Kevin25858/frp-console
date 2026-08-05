/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';

interface AuthContextType {
    isAuthenticated: boolean;
    isLoading: boolean;
    username?: string;
    checkAuth: () => Promise<void>;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [username, setUsername] = useState<string | undefined>();
    const isCheckingRef = useRef<boolean>(false);
    const abortControllerRef = useRef<AbortController | null>(null);

    const checkAuth = async () => {
        if (isCheckingRef.current) return;

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        abortControllerRef.current = new AbortController();
        isCheckingRef.current = true;
        setIsLoading(true);

        try {
            const response = await fetch('/api/me', {
                credentials: 'include',
                signal: abortControllerRef.current.signal
            });
            if (response.ok) {
                const data = await response.json();
                setIsAuthenticated(true);
                setUsername(data.username);
            } else {
                setIsAuthenticated(false);
                setUsername(undefined);
            }
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') return;
            setIsAuthenticated(false);
            setUsername(undefined);
        } finally {
            setIsLoading(false);
            isCheckingRef.current = false;
            abortControllerRef.current = null;
        }
    };

    const logout = async () => {
        try {
            await fetch('/logout', { credentials: 'include', method: 'GET' });
        } catch {
            // ignore
        }
        setIsAuthenticated(false);
        setUsername(undefined);
    };

    useEffect(() => {
        checkAuth();
        return () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    return (
        <AuthContext.Provider value={{ isAuthenticated, isLoading, username, checkAuth, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

function useAuthInternal() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

export const useAuth = useAuthInternal
