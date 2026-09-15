import client from './client';
import type { ApiResponse, Internship } from '../types';

export interface CreateInternshipData {
  company_name: string;
  start_date: string;
  end_date: string;
  total_expected_days: number;
}

export const internshipsApi = {
  getActive: async (): Promise<ApiResponse<Internship>> => {
    const { data } = await client.get('/api/v1/internships/active');
    return data;
  },
  getById: async (id: string): Promise<ApiResponse<Internship>> => {
    const { data } = await client.get(`/api/v1/internships/${id}`);
    return data;
  },
  create: async (payload: CreateInternshipData): Promise<ApiResponse<Internship>> => {
    const { data } = await client.post('/api/v1/internships', payload);
    return data;
  }
};
