import React from 'react';
import { IssueList } from '../features/issues/IssueList';
import { Search, Filter, SlidersHorizontal } from 'lucide-react';

export const Issues: React.FC = () => {
    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex flex-col gap-1">
                    <h1 className="text-3xl font-serif font-bold text-gradient">Issues Catalog</h1>
                    <p className="text-slate-400">Total 24 operational risks detected across 5 systems.</p>
                </div>

                <div className="flex items-center gap-3">
                    <button className="flex items-center gap-2 px-3 py-2 rounded-lg glass-hover border border-white/10 text-sm font-medium">
                        <Filter className="w-4 h-4" />
                        <span>Filter</span>
                    </button>
                    <button className="flex items-center gap-2 px-3 py-2 rounded-lg glass-hover border border-white/10 text-sm font-medium">
                        <SlidersHorizontal className="w-4 h-4" />
                        <span>Sort</span>
                    </button>
                </div>
            </div>

            <div className="glass p-3 rounded-2xl border-white/5 bg-white/5 flex items-center gap-4">
                <div className="flex-1 flex items-center gap-3 px-3">
                    <Search className="w-5 h-5 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Search by issue title, description, or system..."
                        className="flex-1 bg-transparent border-none outline-hidden text-sm text-white placeholder:text-slate-600 font-medium"
                    />
                </div>
                <div className="h-6 w-px bg-white/10" />
                <div className="flex items-center gap-2 px-3">
                    {['All', 'Critical', 'High', 'Medium'].map(tab => (
                        <button key={tab} className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all hover:bg-white/5 active:scale-95">
                            {tab}
                        </button>
                    ))}
                </div>
            </div>

            <div className="space-y-8">
                <section>
                    <div className="flex items-center gap-2 mb-4">
                        <div className="w-2 h-2 rounded-full bg-critical glow-critical" />
                        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400">Active Issues</h3>
                    </div>
                    <IssueList />
                </section>

                <section>
                    <div className="flex items-center gap-2 mb-4 pt-4 border-t border-white/5">
                        <div className="w-2 h-2 rounded-full bg-slate-500" />
                        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400">Recently Resolved</h3>
                    </div>
                    <div className="glass p-12 rounded-2xl border-white/5 flex flex-col items-center justify-center text-slate-600 gap-2 italic">
                        No resolved issues in the last 24 hours.
                    </div>
                </section>
            </div>
        </div>
    );
};
