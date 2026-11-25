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
  timeout: 60000,
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

// Response interceptor: silent token refresh, retry for idempotent GET on cold starts, and error normalization
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
      _retryGet?: boolean;
    };
    const status = error.response?.status;

    // Handle 401 Unauthorized with token refresh (avoid infinite loop on auth endpoints)
    const isAuthEndpoint =
      originalRequest?.url?.includes('/auth/login') ||
      originalRequest?.url?.includes('/auth/register') ||
      originalRequest?.url?.includes('/auth/token/refresh');

    if (status === 401 && !originalRequest?._retry && !isAuthEndpoint) {
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

    // Automatic single retry for idempotent GET requests on network errors, timeouts, or 502/503/504
    const isGet = originalRequest?.method?.toLowerCase() === 'get';
    const isNetworkError = !error.response;
    const isTimeout = error.code === 'ECONNABORTED' || error.message?.toLowerCase().includes('timeout');
    const isServerWaking = status === 502 || status === 503 || status === 504;

    if (isGet && !originalRequest?._retryGet && (isNetworkError || isTimeout || isServerWaking)) {
      originalRequest._retryGet = true;
      // Brief wait before retrying so cold starting server has a chance to initialize
      await new Promise((resolve) => setTimeout(resolve, 1500));
      return api(originalRequest);
    }

    return Promise.reject(normalizeError(error));
  }
);

export interface NormalizedApiError {
  status?: number;
  message: string;
  errors?: Record<string, any> | any;
  isNetworkError: boolean;
}

function normalizeError(error: AxiosError): NormalizedApiError {
  const status = error.response?.status;
  const data = error.response?.data as any;
  const isNetwork = !error.response;
  const isTimeout = error.code === 'ECONNABORTED' || error.message?.toLowerCase().includes('timeout');
  const isServerWaking = status === 502 || status === 503 || status === 504;

  let message = 'An unexpected server error occurred.';
  if (isNetwork || isTimeout || isServerWaking) {
    message = 'Server is waking up, please wait…';
  } else if (data?.detail) {
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
    isNetworkError: isNetwork,
  };
}

/**
 * Universal error message extractor for Error instances, NormalizedApiError objects, and raw strings.
 */
export function getErrorMessage(
  err: unknown,
  fallback: string = 'An unexpected error occurred.'
): string {
  if (!err) return fallback;
  if (typeof err === 'string') return err.trim() || fallback;
  if (err instanceof Error) return err.message || fallback;
  if (typeof err === 'object') {
    const errorObj = err as Record<string, any>;
    if (typeof errorObj.message === 'string' && errorObj.message.trim()) {
      return errorObj.message;
    }
    if (typeof errorObj.detail === 'string' && errorObj.detail.trim()) {
      return errorObj.detail;
    }
    if (errorObj.response?.data) {
      const data = errorObj.response.data;
      if (typeof data === 'string' && data.trim()) return data;
      if (typeof data.detail === 'string' && data.detail.trim()) return data.detail;
      if (typeof data.message === 'string' && data.message.trim()) return data.message;
    }
  }
  return fallback;
}

/**
 * Helper to convert absolute API pagination URLs returned by backend into relative paths
 * ensuring requests route through the client's configured baseURL.
 */
export function toRelativeApiPath(fullUrl: string): string {
  try {
    const parsed = new URL(fullUrl);
    let path = parsed.pathname + parsed.search;
    if (path.startsWith('/api/')) {
      path = path.slice(4); // Returns '/quotations/?page=2'
    }
    return path;
  } catch {
    return fullUrl;
  }
}

export default api;
