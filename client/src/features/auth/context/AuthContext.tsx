import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import { authService } from '../services/authService';
import { tokenStorage } from '../../../lib/api';
import type {
  User,
  UserOrganization,
  LoginCredentials,
  RegisterPayload,
  AuthContextType,
} from '../types';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [activeOrganization, setActiveOrganization] = useState<UserOrganization | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const resolveActiveOrg = (currentUser: User) => {
    if (!currentUser.organizations || currentUser.organizations.length === 0) {
      setActiveOrganization(null);
      return;
    }

    const savedOrgId = tokenStorage.getActiveOrgId();
    const matched = currentUser.organizations.find((org) => org.id === savedOrgId);
    if (matched) {
      setActiveOrganization(matched);
    } else {
      const firstOrg = currentUser.organizations[0];
      setActiveOrganization(firstOrg);
      tokenStorage.setActiveOrgId(firstOrg.id);
    }
  };

  const refreshUser = useCallback(async () => {
    try {
      const userData = await authService.getCurrentUser();
      setUser(userData);
      resolveActiveOrg(userData);
    } catch {
      setUser(null);
      setActiveOrganization(null);
      tokenStorage.clearTokens();
    }
  }, []);

  // Initial authentication check on application boot
  useEffect(() => {
    const initializeAuth = async () => {
      const token = tokenStorage.getAccessToken();
      if (token) {
        await refreshUser();
      }
      setIsLoading(false);
    };

    initializeAuth();

    // Listen for session expiry from axios interceptor
    const handleSessionExpired = () => {
      setUser(null);
      setActiveOrganization(null);
      tokenStorage.clearTokens();
    };

    window.addEventListener('auth:session-expired', handleSessionExpired);
    return () => window.removeEventListener('auth:session-expired', handleSessionExpired);
  }, [refreshUser]);

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await authService.login(credentials);
      setUser(res.user);
      resolveActiveOrg(res.user);
    } catch (err: any) {
      const errMsg = err?.message || 'Login failed. Please verify your credentials.';
      setError(errMsg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload: RegisterPayload) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await authService.register(payload);
      setUser(res.user);
      resolveActiveOrg(res.user);
    } catch (err: any) {
      const errMsg = err?.message || 'Registration failed. Please check form details.';
      setError(errMsg);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setActiveOrganization(null);
      setError(null);
      setIsLoading(false);
    }
  };

  const switchOrganization = (organizationId: string) => {
    if (!user) return;
    const matched = user.organizations.find((org) => org.id === organizationId);
    if (matched) {
      setActiveOrganization(matched);
      tokenStorage.setActiveOrgId(matched.id);
    }
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        activeOrganization,
        isAuthenticated: !!user,
        isLoading,
        error,
        login,
        register,
        logout,
        switchOrganization,
        refreshUser,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
