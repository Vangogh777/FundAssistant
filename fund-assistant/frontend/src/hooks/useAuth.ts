import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { authApi } from '@/api/client';

interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  api_keys: Record<string, string>;
  notify_configs: Record<string, unknown>;
  preferences: Record<string, unknown>;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  updateUser: (data: Record<string, unknown>) => Promise<void>;
}

export const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  isAuthenticated: false,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  updateUser: async () => {},
});

export function useAuthProvider(): AuthContextType {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      authApi
        .getMe()
        .then(res => setUser(res.data))
        .catch(() => localStorage.clear())
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await authApi.login({ username, password });
    localStorage.setItem('access_token', res.data.access_token);
    localStorage.setItem('refresh_token', res.data.refresh_token);
    const me = await authApi.getMe();
    setUser(me.data);
  }, []);

  const register = useCallback(async (username: string, email: string, password: string) => {
    const res = await authApi.register({ username, email, password });
    localStorage.setItem('access_token', res.data.access_token);
    localStorage.setItem('refresh_token', res.data.refresh_token);
    const me = await authApi.getMe();
    setUser(me.data);
  }, []);

  const logout = useCallback(() => {
    localStorage.clear();
    setUser(null);
  }, []);

  const updateUser = useCallback(async (data: Record<string, unknown>) => {
    const res = await authApi.updateMe(data);
    setUser(res.data);
  }, []);

  return { user, loading, isAuthenticated: !!user, login, register, logout, updateUser };
}

export function useAuth() {
  return useContext(AuthContext);
}
