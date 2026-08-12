import { create } from 'zustand';

export interface OrganizationRef {
  id: string;
  name: string;
  slug: string;
  role?: string;
}

export interface UserProfile {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  organizations?: OrganizationRef[];
}

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  activeOrgId: string | null;
  setAuth: (token: string, user: UserProfile, activeOrgId: string) => void;
  setActiveOrgId: (orgId: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: (() => {
    try {
      const savedUser = localStorage.getItem('user');
      return savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  })(),
  activeOrgId: localStorage.getItem('activeOrgId'),
  setAuth: (token, user, activeOrgId) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('activeOrgId', activeOrgId);
    set({ token, user, activeOrgId });
  },
  setActiveOrgId: (activeOrgId) => {
    localStorage.setItem('activeOrgId', activeOrgId);
    set({ activeOrgId });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('activeOrgId');
    set({ token: null, user: null, activeOrgId: null });
  },
}));
