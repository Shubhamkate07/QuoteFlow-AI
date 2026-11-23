/**
 * Centralized, validated environment configuration
 */

export const env = Object.freeze({
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? '/api' : 'http://localhost:8000/api'),
  appName: import.meta.env.VITE_APP_NAME || 'QuoteFlow AI',
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
});
