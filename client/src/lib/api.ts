import axios, {
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios';
import { env } from '../config/env';

const ACCESS_TOKEN_KEY = 'quoteflow_access_token';
const REFRESH_TOKEN_KEY = 'quoteflow_refresh_token';
const ACTIVE_ORG_KEY = 'quoteflow_active_org_id';

export const tokenStorage = {
  getAccessToken: (): string | null => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: (): string | null => localStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens: (access: string, refresh: string): void => {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  },
  clearTokens: (): void => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(ACTIVE_ORG_KEY);
  },
  getActiveOrgId: (): string | null => localStorage.getItem(ACTIVE_ORG_KEY),
  setActiveOrgId: (orgId: string): void => {
    localStorage.setItem(ACTIVE_ORG_KEY, orgId);
  },
};

/**
 * Standardized API client for QuoteFlow AI backend
 */
const api = axios.create({
  baseURL: env.apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Flag and queue to handle concurrent 401s during token refresh
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: AxiosError | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Request interceptor: attach Bearer token and Active Organization ID
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const accessToken = tokenStorage.getAccessToken();
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }

    const activeOrgId = tokenStorage.getActiveOrgId();
    if (activeOrgId && config.headers) {
      config.headers['X-Organization-Id'] = activeOrgId;
    }

    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// Response interceptor: silent token refresh and error normalization
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };
    const status = error.response?.status;

    // Handle 401 Unauthorized with token refresh (avoid infinite loop on auth endpoints)
    const isAuthEndpoint =
      originalRequest.url?.includes('/auth/login') ||
      originalRequest.url?.includes('/auth/register') ||
      originalRequest.url?.includes('/auth/token/refresh');

    if (status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = tokenStorage.getRefreshToken();
      if (!refreshToken) {
        isRefreshing = false;
        tokenStorage.clearTokens();
        return Promise.reject(normalizeError(error));
      }

      try {
        // Direct call using unintercepted axios instance to prevent loop
        const { data } = await axios.post(`${env.apiBaseUrl}/auth/token/refresh/`, {
          refresh: refreshToken,
        });

        const newAccess = data.access;
        const newRefresh = data.refresh || refreshToken;

        tokenStorage.setTokens(newAccess, newRefresh);
        processQueue(null, newAccess);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        }
        return api(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr as AxiosError, null);
        tokenStorage.clearTokens();
        // Custom event so UI can react and redirect to login
        window.dispatchEvent(new CustomEvent('auth:session-expired'));
        return Promise.reject(normalizeError(error));
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(normalizeError(error));
  }
);

function normalizeError(error: AxiosError) {
  const status = error.response?.status;
  const data = error.response?.data as any;

  let message = 'An unexpected server error occurred.';
  if (data?.detail) {
    message = data.detail;
  } else if (data?.message) {
    message = data.message;
  } else if (typeof data === 'string') {
    message = data;
  } else if (error.message) {
    message = error.message;
  }

  return {
    status,
    message,
    errors: data?.errors || (typeof data === 'object' ? data : null),
    isNetworkError: !error.response,
  };
}

export default api;
