import axios from 'axios';

const client = axios.create({
  baseURL: '', // proxy handles /api
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('stajos_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('stajos_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default client;
