import client from './client';
import type { ApiResponse, DashboardStats } from '../types';

export const dashboardApi = {
  getStats: async (internship_id?: string): Promise<ApiResponse<DashboardStats>> => {
    const { data } = await client.get('/api/v1/dashboard/stats', { params: { internship_id } });
    return data;
  }
};
