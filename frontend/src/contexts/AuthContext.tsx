import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { User } from '../types';
import { authApi } from '../api/auth';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => {
    const t = localStorage.getItem('stajos_token');
    return t && t !== 'undefined' && t !== 'null' ? t : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(false);
  }, [token]);

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    if (res.success && res.data?.access_token) {
      const newToken = res.data.access_token;
      setToken(newToken);
      localStorage.setItem('stajos_token', newToken);
      if (res.data.user) {
        setUser(res.data.user);
      }
    }
  };

  const register = async (email: string, password: string, full_name: string) => {
    const res = await authApi.register(email, password, full_name);
    if (res.success && res.data) {
      if (res.data.access_token) {
        const newToken = res.data.access_token;
        setToken(newToken);
        localStorage.setItem('stajos_token', newToken);
      }
      if (res.data.user) {
        setUser(res.data.user);
      }
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('stajos_token');
  };

  const value = {
    user,
    token,
    isAuthenticated: !!token,
    loading,
    login,
    register,
    logout
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
