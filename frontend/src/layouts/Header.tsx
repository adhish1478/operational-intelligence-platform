import React from 'react';
import { Bell, ChevronDown, Plus } from 'lucide-react';

export const Header: React.FC = () => {
    return (
        <header className="h-16 border-b border-white/5 glass px-8 flex items-center justify-between sticky top-0 z-50">
            <div className="flex items-center gap-4 text-sm text-slate-400">
                <span>Workspaces</span>
                <ChevronDown className="w-4 h-4" />
                <span className="text-white/20">/</span>
                <span className="text-white font-medium">Acme Corp</span>
            </div>

            <div className="flex items-center gap-6">
                <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-white text-sm font-medium transition-colors shadow-lg shadow-primary/20">
                    <Plus className="w-4 h-4" />
                    <span>New Issue</span>
                </button>

                <button className="relative text-slate-400 hover:text-white transition-colors">
                    <Bell className="w-5 h-5" />
                    <span className="absolute -top-1 -right-1 w-2 h-2 bg-critical rounded-full glow-critical" />
                </button>

                <div className="w-px h-6 bg-white/10" />

                <button className="flex items-center gap-3 p-1 pl-3 rounded-full border border-white/10 glass-hover ring-primary/20 hover:ring-2 transition-all">
                    <div className="flex flex-col items-end mr-1">
                        <span className="text-xs font-semibold text-white leading-none">Alex Rivera</span>
                        <span className="text-[10px] text-slate-500 leading-none mt-1">Founder / CEO</span>
                    </div>
                    <div className="w-8 h-8 rounded-full bg-linear-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-[10px] font-bold text-white uppercase ring-2 ring-background">
                        AR
                    </div>
                </button>
            </div>
        </header>
    );
};
