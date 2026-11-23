import React, { type ReactElement, type ReactNode } from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, type MemoryRouterProps } from 'react-router-dom';

/**
 * Creates an isolated, non-retrying QueryClient for tests
 */
export const createTestQueryClient = (): QueryClient => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
        gcTime: 0,
      },
    },
  });
};

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialEntries?: MemoryRouterProps['initialEntries'];
  queryClient?: QueryClient;
}

/**
 * Standard test wrapper providing QueryClient and MemoryRouter
 */
export const renderWithProviders = (
  ui: ReactElement,
  options: CustomRenderOptions = {}
) => {
  const {
    initialEntries = ['/'],
    queryClient = createTestQueryClient(),
    ...renderOptions
  } = options;

  const Wrapper: React.FC<{ children: ReactNode }> = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
    </QueryClientProvider>
  );

  return {
    user: userEvent.setup(),
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  };
};

// Re-export common testing library utilities
export * from '@testing-library/react';
export { userEvent };
