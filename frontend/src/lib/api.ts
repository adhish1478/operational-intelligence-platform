import { useAuthStore } from '../store/authStore';

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

async function request(path: string, options: RequestInit = {}) {
  const { token, activeOrgId, logout } = useAuthStore.getState();
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (activeOrgId) {
    headers['X-Organization-ID'] = activeOrgId;
  }

  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  // Automatically prepend versioned API prefix to match FastAPI mounts
  const apiPath = cleanPath.startsWith('/api/v1/') ? cleanPath : `/api/v1${cleanPath}`;
  const response = await fetch(`${BASE_URL}${apiPath}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Session token expired or invalidated by blocklist
    logout();
    // Safely redirect to landing page
    window.location.href = '/';
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'API request failed');
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const api = {
  get: (path: string, options?: RequestInit) => 
    request(path, { ...options, method: 'GET' }),
    
  post: (path: string, body?: any, options?: RequestInit) => 
    request(path, { 
      ...options, 
      method: 'POST', 
      body: body ? JSON.stringify(body) : undefined 
    }),
    
  put: (path: string, body?: any, options?: RequestInit) => 
    request(path, { 
      ...options, 
      method: 'PUT', 
      body: body ? JSON.stringify(body) : undefined 
    }),
    
  delete: (path: string, options?: RequestInit) => 
    request(path, { ...options, method: 'DELETE' }),
};
