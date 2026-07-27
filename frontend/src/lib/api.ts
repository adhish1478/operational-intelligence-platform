import { useAuthStore } from '../store/authStore';

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: any) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(true);
    }
  });
  failedQueue = [];
};

async function request(path: string, options: RequestInit = {}): Promise<any> {
  const { activeOrgId, setAuth, logout } = useAuthStore.getState();
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  const token = useAuthStore.getState().token;
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (activeOrgId) {
    headers['X-Organization-ID'] = activeOrgId;
  }

  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const apiPath = cleanPath.startsWith('/api/v1/') ? cleanPath : `/api/v1${cleanPath}`;

  const response = await fetch(`${BASE_URL}${apiPath}`, {
    ...options,
    credentials: 'include', // Send and receive HttpOnly refresh_token cookies
    headers,
  });

  // Handle 401 Unauthorized with silent token refresh
  if (response.status === 401) {
    const isAuthRoute = cleanPath.includes('/auth/login') || cleanPath.includes('/auth/register') || cleanPath.includes('/auth/refresh');

    if (isAuthRoute) {
      if (cleanPath.includes('/auth/refresh')) {
        logout();
        window.location.href = '/';
      }
      throw new Error('Unauthorized');
    }

    if (!isRefreshing) {
      isRefreshing = true;
      try {
        // Call refresh endpoint to obtain a new access token via HttpOnly refresh cookie
        const refreshRes = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' }
        });

        if (refreshRes.ok) {
          const data = await refreshRes.json();
          const newAccessToken = data.access_token;
          const currentUser = useAuthStore.getState().user;
          const currentOrgId = useAuthStore.getState().activeOrgId || '';

          if (newAccessToken && currentUser) {
            // Update auth store with new access token
            setAuth(newAccessToken, currentUser, currentOrgId);
            processQueue(null);

            // Retry original request with new access token
            headers['Authorization'] = `Bearer ${newAccessToken}`;
            const retryResponse = await fetch(`${BASE_URL}${apiPath}`, {
              ...options,
              credentials: 'include',
              headers,
            });

            if (!retryResponse.ok) {
              const errData = await retryResponse.json().catch(() => ({}));
              throw new Error(errData.detail || 'Retry failed after token refresh');
            }

            if (retryResponse.status === 204) {
              return null;
            }

            return retryResponse.json();
          }
        }

        // Refresh failed (e.g. refresh token expired or missing)
        processQueue(new Error('Session expired'));
        logout();
        window.location.href = '/';
        throw new Error('Session expired. Please log in again.');
      } catch (err) {
        processQueue(err);
        logout();
        window.location.href = '/';
        throw err;
      } finally {
        isRefreshing = false;
      }
    } else {
      // Queue concurrent requests while token refresh is in progress
      return new Promise((resolve, reject) => {
        failedQueue.push({
          resolve: () => {
            resolve(request(path, options));
          },
          reject: (err) => reject(err),
        });
      });
    }
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

  patch: (path: string, body?: any, options?: RequestInit) => 
    request(path, { 
      ...options, 
      method: 'PATCH', 
      body: body ? JSON.stringify(body) : undefined 
    }),
    
  delete: (path: string, options?: RequestInit) => 
    request(path, { ...options, method: 'DELETE' }),

  stream: async (path: string, onEvent: (eventType: string, payload: any) => void) => {
    const { activeOrgId, token } = useAuthStore.getState();
    const headers: Record<string, string> = {
      'Accept': 'text/event-stream'
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (activeOrgId) headers['X-Organization-ID'] = activeOrgId;

    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    const apiPath = cleanPath.startsWith('/api/v1/') ? cleanPath : `/api/v1${cleanPath}`;

    const response = await fetch(`${BASE_URL}${apiPath}`, {
      method: 'GET',
      headers,
      credentials: 'include'
    });

    if (!response.ok || !response.body) {
      throw new Error(`SSE stream failed with status ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        if (!part.trim()) continue;
        const eventMatch = part.match(/^event:\s*(.+)$/m);
        const dataMatch = part.match(/^data:\s*([\s\S]+)$/m);

        if (eventMatch && dataMatch) {
          const eventType = eventMatch[1].trim();
          try {
            const payload = JSON.parse(dataMatch[1].trim());
            onEvent(eventType, payload);
          } catch (e) {
            console.error('Failed to parse SSE JSON payload', e);
          }
        }
      }
    }
  }
};
