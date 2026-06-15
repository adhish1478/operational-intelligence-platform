import React, { useState } from 'react';
import { RefreshCw } from 'lucide-react';

interface IntegrationConnector {
  id: string;
  name: string;
  category: string;
  status: 'connected' | 'error' | 'disconnected';
  desc: string;
  connectedAt?: string;
}

export const Integrations: React.FC = () => {
  const [connectors, setConnectors] = useState<IntegrationConnector[]>([
    { id: 'slack', name: 'Slack Workspace', category: 'Communication', status: 'connected', desc: 'Syncs channel alerts, incident notifications, and triage chat feeds.', connectedAt: '2026-06-14T11:00:00Z' },
    { id: 'jira', name: 'Jira Software', category: 'Project Tracking', status: 'connected', desc: 'Creates tickets, pulls assignee data, and connects sprint blockers.', connectedAt: '2026-06-14T11:10:00Z' },
    { id: 'github', name: 'GitHub Integration', category: 'Code Repositories', status: 'connected', desc: 'Tracks pull requests, commits, and branch code audit checkups.', connectedAt: '2026-06-14T11:20:00Z' },
    { id: 'gmail', name: 'Gmail Workspace', category: 'Email Communication', status: 'disconnected', desc: 'Parses executive complaints, SLA notification chains, and feedback.' },
    { id: 'notion', name: 'Notion Workspace', category: 'Documentation', status: 'disconnected', desc: 'Indexes readiness checklists, sprint plans, and team reports.' }
  ]);

  const toggleConnection = (id: string) => {
    setConnectors(prev => prev.map(c => {
      if (c.id === id) {
        return {
          ...c,
          status: c.status === 'connected' ? 'disconnected' : 'connected',
          connectedAt: c.status === 'disconnected' ? new Date().toISOString() : undefined
        };
      }
      return c;
    }));
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant pb-4">
        <div>
          <h1 className="text-headline-lg text-on-surface">System Integrations</h1>
          <p className="text-body-md text-on-surface-variant">
            Connect and synchronize third-party systems to aggregate operational evidence feeds.
          </p>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {connectors.map(c => (
          <div key={c.id} className="bg-surface border border-outline-variant rounded-lg p-5 flex flex-col justify-between gap-4 hover:border-outline transition-colors">
            
            {/* Top row */}
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] uppercase font-bold text-outline-variant bg-surface-low border border-outline-variant px-1.5 py-0.5 rounded font-mono">
                    {c.category}
                  </span>
                  <h3 className="text-headline-sm font-semibold text-on-surface mt-2">{c.name}</h3>
                </div>

                {/* Status Indicator */}
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                  c.status === 'connected' 
                    ? 'bg-success/10 text-success' 
                    : 'bg-slate-100 text-slate-500'
                }`}>
                  {c.status}
                </span>
              </div>

              <p className="text-body-sm text-on-surface-variant">
                {c.desc}
              </p>
            </div>

            {/* Actions */}
            <div className="border-t border-outline-variant/60 pt-4 flex items-center justify-between">
              {c.status === 'connected' ? (
                <div className="flex items-center gap-1.5 text-[11px] font-mono text-outline">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin-slow" />
                  <span>Synced 5m ago</span>
                </div>
              ) : (
                <span className="text-[11px] text-outline italic">Not synchronized</span>
              )}

              <button
                onClick={() => toggleConnection(c.id)}
                className={`px-3 py-1.5 rounded text-body-sm font-semibold transition-colors ${
                  c.status === 'connected'
                    ? 'bg-surface-low hover:bg-surface-high text-error border border-outline-variant/80'
                    : 'bg-primary hover:bg-slate-800 text-white'
                }`}
              >
                {c.status === 'connected' ? 'Disconnect' : 'Connect'}
              </button>
            </div>

          </div>
        ))}
      </div>

    </div>
  );
};
