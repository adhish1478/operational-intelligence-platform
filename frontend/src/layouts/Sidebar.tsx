import React from 'react';
import {
    LayoutDashboard,
    AlertCircle,
    Layers,
    FileBarChart,
    Settings,
    ChevronDown,
    Zap
} from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

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
    return (
        <aside className="w-[240px] bg-surface-low border-r border-outline-variant flex flex-col h-screen sticky top-0">
            {/* Workspace / Org Switcher */}
            <div className="p-4 border-b border-outline-variant">
                <button className="w-full flex items-center gap-2 p-2 rounded bg-surface border border-outline-variant hover:bg-surface-high transition-colors text-left group">
                    <div className="w-6 h-6 rounded bg-primary flex items-center justify-center shrink-0">
                        <Zap className="text-white w-4.5 h-4.5 fill-current" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <h4 className="text-body-sm font-semibold truncate text-on-surface">Global Workspace</h4>
                        <p className="text-[10px] text-on-surface-variant truncate">Global Ops / Dev</p>
                    </div>
                    <ChevronDown className="w-4 h-4 text-on-surface-variant group-hover:text-on-surface shrink-0" />
                </button>
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
                        {item.label === 'Investigations' && (
                            <span className="bg-error-container text-error text-[10px] px-1.5 py-0.5 rounded font-bold">
                                3
                            </span>
                        )}
                    </NavLink>
                ))}
            </nav>

            {/* Settings & User Profile Footer */}
            <div className="p-3 border-t border-outline-variant space-y-2">
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

                {/* User avatar and profile card */}
                <div className="flex items-center gap-2.5 p-2 rounded hover:bg-surface-high transition-colors">
                    <div className="w-8 h-8 rounded-full bg-secondary-container text-on-secondary-container font-bold flex items-center justify-center text-xs">
                        AA
                    </div>
                    <div className="flex-1 min-w-0">
                        <h5 className="text-[12px] font-semibold text-on-surface truncate">Adhish Aravind</h5>
                        <p className="text-[10px] text-on-surface-variant truncate">Lead SecOps / Admin</p>
                    </div>
                </div>
            </div>
        </aside>
    );
};
