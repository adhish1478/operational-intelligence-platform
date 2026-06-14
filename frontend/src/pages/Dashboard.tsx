import React from 'react';
import { IssueList } from '../features/issues/IssueList';

export const Dashboard: React.FC = () => {
    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-1">
                <h1 className="text-3xl font-serif font-bold text-gradient">Good morning, Alex.</h1>
                <p className="text-slate-400">Here's what requires your attention today.</p>
            </div>

            {/* Risk Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[
                    { label: 'Critical Risks', value: '3', color: 'text-critical', glow: 'glow-critical' },
                    { label: 'Revenue at Risk', value: '$124k', color: 'text-warning', glow: '' },
                    { label: 'Team Blockers', value: '12', color: 'text-primary', glow: 'glow-primary' },
                    { label: 'Escalations', value: '5', color: 'text-indigo-400', glow: '' },
                ].map((item) => (
                    <div key={item.label} className="glass p-6 rounded-2xl border-white/5 space-y-2 group glass-hover">
                        <span className="text-sm font-medium text-slate-500 uppercase tracking-wider">{item.label}</span>
                        <div className={`text-4xl font-bold font-serif ${item.color} ${item.glow}`}>{item.value}</div>
                    </div>
                ))}
            </div>

            {/* Main Content Area */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-4">
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="text-lg font-semibold">Active Investigations</h3>
                        <button className="text-xs text-primary hover:underline font-medium">View All</button>
                    </div>
                    <IssueList />
                </div>
                <div className="space-y-4">
                    <h3 className="text-lg font-semibold">Connected Systems</h3>
                    <div className="glass rounded-2xl border-white/5 p-6 h-[460px]">
                        <div className="space-y-4">
                            {[
                                { name: 'Slack', status: 'Active', color: 'text-success' },
                                { name: 'Jira', status: 'Active', color: 'text-success' },
                                { name: 'Gmail', status: 'Active', color: 'text-success' },
                                { name: 'GitHub', status: 'Configuring', color: 'text-warning' },
                            ].map(app => (
                                <div key={app.name} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 glass-hover cursor-pointer group">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center font-bold text-xs">
                                            {app.name[0]}
                                        </div>
                                        <span className="text-sm font-medium">{app.name}</span>
                                    </div>
                                    <span className={`text-[10px] bg-white/5 px-2 py-0.5 rounded-full font-bold ${app.color}`}>{app.status}</span>
                                </div>
                            ))}
                        </div>

                        <div className="mt-8 pt-6 border-t border-white/10">
                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">System Health</h4>
                            <div className="space-y-6">
                                {[
                                    { label: 'Data Latency', value: '1.2s', trend: 'down' },
                                    { label: 'AI Confidence', value: '94%', trend: 'up' },
                                ].map(stat => (
                                    <div key={stat.label} className="flex items-center justify-between">
                                        <span className="text-xs text-slate-400">{stat.label}</span>
                                        <span className="text-xs font-mono font-bold text-white">{stat.value}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
