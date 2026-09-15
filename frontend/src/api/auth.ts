import client from './client';
import type { ApiResponse, User } from '../types';

interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  user?: User;
}

export const authApi = {
  login: async (email: string, password: string): Promise<ApiResponse<AuthResponse>> => {
    const { data } = await client.post('/api/v1/auth/login', { email, password });
    return data;
  },
  register: async (email: string, password: string, full_name: string): Promise<ApiResponse<AuthResponse>> => {
    const { data } = await client.post('/api/v1/auth/register', { email, password, full_name });
    return data;
  },
};
