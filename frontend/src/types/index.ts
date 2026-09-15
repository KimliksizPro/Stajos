export interface User {
  id: string;
  email: string;
  full_name: string;
}

export interface Internship {
  id: string;
  user_id: string;
  company_name: string;
  start_date: string;
  end_date: string;
  total_expected_days: number;
  status: string;
}

export interface DailyLog {
  id: string;
  internship_id: string;
  date: string;
  day_number: number;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  title: string;
  raw_content: string;
  ai_refined_content?: string;
  ai_status: 'pending' | 'accepted' | 'rejected';
  technologies: string[];
  tags: string[];
  topics: string[];
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_logs: number;
  total_duration_minutes: number;
  unique_technologies_count: number;
  ai_refined_percentage: number;
}

export interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: PaginationMeta;
  errors?: any[];
}
