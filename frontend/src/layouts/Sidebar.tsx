import React from 'react';
import {
    LayoutDashboard,
    AlertCircle,
    Layers,
    FileBarChart,
    Settings,
    Zap,
    LogOut
} from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useAuthStore } from '../store/authStore';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

const navItems = [
    { icon: LayoutDashboard, label: 'Attention Deck', path: '/dashboard' },
    { icon: AlertCircle, label: 'Investigations', path: '/investigations' },
    { icon: Layers, label: 'Integrations', path: '/integrations' },
    { icon: FileBarChart, label: 'Reports', path: '/reports' },
];

export const Sidebar: React.FC = () => {
    const navigate = useNavigate();
    const { user, activeOrgId, logout } = useAuthStore();

    // Find active organization details
    const activeOrg = user?.organizations?.find(o => o.id === activeOrgId) || user?.organizations?.[0];
    const orgName = activeOrg ? activeOrg.name : (user?.first_name ? `${user.first_name}'s Organization` : 'My Organization');
    const orgSlug = activeOrg ? activeOrg.slug : 'workspace';

    // Calculate avatar initials
    const initials = user?.first_name 
        ? `${user.first_name.charAt(0)}${user.last_name?.charAt(0) || ''}`.toUpperCase()
        : user?.email ? user.email.slice(0, 2).toUpperCase() : 'US';

    const fullName = user?.first_name
        ? `${user.first_name} ${user.last_name || ''}`.trim()
        : user?.email || 'User Session';

    const handleLogout = async () => {
        try {
            const token = localStorage.getItem('token');
            const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            
            // Attempt to blocklist token on backend
            if (token) {
                await fetch(`${BASE_URL}/api/v1/auth/logout`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'Authorization': `Bearer ${token}` }
                }).catch(() => {});
            }
        } finally {
            // Guarantee store cleanup and redirect
            logout();
            navigate('/');
        }
    };

    return (
        <aside className="w-[240px] bg-surface-low border-r border-outline-variant flex flex-col h-screen sticky top-0">
            {/* User Organization Header */}
            <div className="p-4 border-b border-outline-variant">
                <div className="flex items-center gap-2.5 p-2 rounded bg-surface border border-outline-variant text-left">
                    <div className="w-7 h-7 rounded bg-slate-900 flex items-center justify-center shrink-0">
                        <Zap className="text-white w-4 h-4 fill-current" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <h4 className="text-body-sm font-bold truncate text-on-surface">{orgName}</h4>
                        <p className="text-[10px] font-mono text-on-surface-variant truncate">{orgSlug}</p>
                    </div>
                </div>
            </div>

            {/* Navigation links */}
            <nav className="flex-1 px-3 py-4 space-y-1">
                {navItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) => cn(
                            "flex items-center gap-2.5 px-3 py-2 rounded text-body-sm transition-all duration-150 group",
                            isActive
                                ? "bg-surface-container text-on-surface font-semibold border border-outline-variant/60"
                                : "text-on-surface-variant hover:bg-surface-high hover:text-on-surface border border-transparent"
                        )}
                    >
                        <item.icon className="w-4.5 h-4.5" />
                        <span className="flex-1">{item.label}</span>
                    </NavLink>
                ))}
            </nav>

            {/* Settings & User Profile Footer */}
            <div className="p-3 border-t border-outline-variant space-y-1">
                <NavLink
                    to="/settings"
                    className={({ isActive }) => cn(
                        "flex items-center gap-2.5 px-3 py-2 rounded text-body-sm transition-all duration-150",
                        isActive
                            ? "bg-surface-container text-on-surface font-semibold border border-outline-variant/60"
                            : "text-on-surface-variant hover:bg-surface-high hover:text-on-surface border border-transparent"
                    )}
                >
                    <Settings className="w-4.5 h-4.5" />
                    <span>Settings</span>
                </NavLink>

                {/* Logout Button */}
                <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded text-body-sm text-red-600 hover:bg-red-50 hover:text-red-700 border border-transparent transition-all duration-150 text-left font-medium"
                >
                    <LogOut className="w-4.5 h-4.5" />
                    <span>Log Out</span>
                </button>

                {/* User avatar and profile card */}
                <div className="flex items-center gap-2.5 p-2 rounded hover:bg-surface-high transition-colors mt-2">
                    <div className="w-8 h-8 rounded-full bg-secondary-container text-on-secondary-container font-bold flex items-center justify-center text-xs shrink-0">
                        {initials}
                    </div>
                    <div className="flex-1 min-w-0">
                        <h5 className="text-[12px] font-semibold text-on-surface truncate">{fullName}</h5>
                        <p className="text-[10px] text-on-surface-variant truncate">{user?.email || 'SecOps / Admin'}</p>
                    </div>
                </div>
            </div>
        </aside>
    );
};

