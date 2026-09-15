import client from './client';
import type { ApiResponse, DailyLog } from '../types';

export interface CreateLogData {
  internship_id: string;
  title: string;
  raw_content: string;
  start_time: string;
  end_time: string;
  technologies?: string[];
  tags?: string[];
  topics?: string[];
}

export interface ListLogsParams {
  internship_id?: string;
  page?: number;
  per_page?: number;
  search?: string;
  start_date?: string;
  end_date?: string;
  tech?: string;
  tag?: string;
  topic?: string;
  sort?: string;
  order?: string;
}

export const logsApi = {
  create: async (payload: CreateLogData): Promise<ApiResponse<DailyLog>> => {
    const { data } = await client.post('/api/v1/logs', payload);
    return data;
  },
  list: async (params: ListLogsParams): Promise<ApiResponse<DailyLog[]>> => {
    const { data } = await client.get('/api/v1/logs', { params });
    return data;
  },
  getById: async (id: string): Promise<ApiResponse<DailyLog>> => {
    const { data } = await client.get(`/api/v1/logs/${id}`);
    return data;
  },
  acceptAi: async (id: string): Promise<ApiResponse<DailyLog>> => {
    const { data } = await client.put(`/api/v1/logs/${id}/accept-ai`);
    return data;
  },
  rejectAi: async (id: string): Promise<ApiResponse<DailyLog>> => {
    const { data } = await client.put(`/api/v1/logs/${id}/reject-ai`);
    return data;
  }
};
