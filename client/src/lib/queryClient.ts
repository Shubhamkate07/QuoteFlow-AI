import { QueryClient } from '@tanstack/react-query';

/**
 * Global QueryClient instance with procurement-optimized defaults
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (failureCount, error: any) => {
        // Do not retry 4xx errors (client errors)
        if (error?.status >= 400 && error?.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 15,    // 15 minutes (garbage collection)
    },
    mutations: {
      retry: false,
    },
  },
});
