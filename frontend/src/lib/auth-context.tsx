import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from './api-client';

interface User {
  id: string;
  email: string;
  full_name: string;
}

interface Workspace {
  id: string;
  name: string;
  currency?: string;
}

interface AuthContextType {
  user: User | null;
  workspace: Workspace | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  checkAuth: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const checkAuth = async () => {
    try {
      const { data } = await api.get('/auth/me');
      setUser(data.user);
      setWorkspace(data.workspace);
    } catch (error) {
      setUser(null);
      setWorkspace(null);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      setUser(null);
      setWorkspace(null);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const isAuthenticated = !!user;

  return (
    <AuthContext.Provider value={{ user, workspace, isLoading, isAuthenticated, checkAuth, logout }}>
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
