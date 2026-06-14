import React from 'react';
import {
    LayoutDashboard,
    AlertCircle,
    Layers,
    FileBarChart,
    Settings,
    Zap,
    Search
} from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

const navItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
    { icon: AlertCircle, label: 'Issues', path: '/issues' },
    { icon: Layers, label: 'Integrations', path: '/integrations' },
    { icon: FileBarChart, label: 'Reports', path: '/reports' },
];

export const Sidebar: React.FC = () => {
    return (
        <aside className="w-64 glass border-r border-white/10 flex flex-col h-screen sticky top-0">
            <div className="p-6 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary glow-primary flex items-center justify-center">
                    <Zap className="text-white w-5 h-5 fill-current" />
                </div>
                <span className="text-xl font-serif font-bold text-gradient">OIP</span>
            </div>

            <nav className="flex-1 px-4 py-4 space-y-2">
                <div className="mb-4">
                    <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white transition-colors group">
                        <Search className="w-4 h-4" />
                        <span className="text-sm">Search...</span>
                        <kbd className="ml-auto text-[10px] bg-white/10 px-1.5 py-0.5 rounded text-slate-500 font-mono">⌘K</kbd>
                    </button>
                </div>

                {navItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) => cn(
                            "flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 group",
                            isActive
                                ? "bg-primary/10 text-primary border border-primary/20"
                                : "text-slate-400 hover:bg-white/5 hover:text-white border border-transparent"
                        )}
                    >
                        <item.icon className="w-5 h-5" />
                        <span className="font-medium text-sm">{item.label}</span>
                        {item.label === 'Issues' && (
                            <span className="ml-auto bg-critical/20 text-critical text-[10px] px-1.5 py-0.5 rounded-full font-bold glow-critical">
                                3
                            </span>
                        )}
                    </NavLink>
                ))}
            </nav>

            <div className="p-4 border-t border-white/10">
                <NavLink
                    to="/settings"
                    className={({ isActive }) => cn(
                        "flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200",
                        isActive
                            ? "bg-primary/10 text-primary border border-primary/20"
                            : "text-slate-400 hover:bg-white/5 hover:text-white border border-transparent"
                    )}
                >
                    <Settings className="w-5 h-5" />
                    <span className="font-medium text-sm">Settings</span>
                </NavLink>
            </div>
        </aside>
    );
};
