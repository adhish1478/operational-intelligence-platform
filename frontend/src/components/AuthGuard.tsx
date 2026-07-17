import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

interface AuthGuardProps {
  children: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const { token, activeOrgId } = useAuthStore();
  const location = useLocation();

  if (!token) {
    // Redirect unauthenticated users back to the landing page
    return <Navigate to="/" replace />;
  }

  // Redirect users who haven't completed onboarding to the /onboarding page
  if (!activeOrgId && location.pathname !== '/onboarding') {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
};
