import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE = '/api';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// 请求拦截：自动附加 Token
client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截：Token 过期自动刷新
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function onRefreshed(token: string) {
  refreshSubscribers.forEach(cb => cb(token));
  refreshSubscribers = [];
}

client.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        // 无刷新 Token，跳转登录
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise(resolve => {
          refreshSubscribers.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(client(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const res = await axios.post(`${API_BASE}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        const { access_token, refresh_token: newRefresh } = res.data;
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', newRefresh);

        onRefreshed(access_token);
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return client(originalRequest);
      } catch {
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default client;

// ====== Auth API ======
export const authApi = {
  register: (data: { username: string; email: string; password: string }) =>
    client.post('/auth/register', data),
  login: (data: { username: string; password: string }) =>
    client.post('/auth/login', data),
  refresh: (refresh_token: string) =>
    client.post('/auth/refresh', { refresh_token }),
  getMe: () => client.get('/auth/me'),
  updateMe: (data: Record<string, unknown>) => client.put('/auth/me', data),
};
