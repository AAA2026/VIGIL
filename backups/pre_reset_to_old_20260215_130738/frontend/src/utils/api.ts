const API_URL = (import.meta as any).env.VITE_API_URL || window.location.origin;

export const getApiUrl = () => API_URL;

export const authHeaders = () => {
  const token = localStorage.getItem('authToken');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export const apiFetch = (path: string, options: RequestInit = {}) => {
  const url = path.startsWith('http') ? path : `${API_URL}${path}`;
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const defaultHeaders = isFormData ? {} : { 'Content-Type': 'application/json' };
  return fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers || {}),
      ...authHeaders(),
    },
  });
};
