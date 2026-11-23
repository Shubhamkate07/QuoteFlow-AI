import { useQuery } from '@tanstack/react-query';
import { dashboardService } from '../services/dashboardService';
import type { DashboardOverviewData } from '../services/dashboardService';

export const DASHBOARD_QUERY_KEY = ['dashboard', 'overview'];

export const useDashboardOverview = () => {
  return useQuery<DashboardOverviewData, Error>({
    queryKey: DASHBOARD_QUERY_KEY,
    queryFn: () => dashboardService.getOverview(),
    staleTime: 15000,
    refetchOnWindowFocus: true,
  });
};
