import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

interface AuthGuardProps {
  children: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const token = useAuthStore((state) => state.token);

  if (!token) {
    // Redirect unauthenticated users back to the landing page
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};
