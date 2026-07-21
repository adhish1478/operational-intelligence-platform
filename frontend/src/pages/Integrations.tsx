import React, { useState, useEffect } from 'react';
import { RefreshCw, ShieldAlert, ChevronDown, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

interface PotentialConnector {
  platform: 'slack' | 'github' | 'jira' | 'gmail';
  name: string;
  category: string;
  desc: string;
}

const POTENTIAL_CONNECTORS: PotentialConnector[] = [
  { platform: 'slack', name: 'Slack Workspace', category: 'Communication', desc: 'Syncs channel alerts, incident notifications, and triage chat feeds.' },
  { platform: 'jira', name: 'Jira Software', category: 'Project Tracking', desc: 'Creates tickets, pulls assignee data, and connects sprint blockers.' },
  { platform: 'github', name: 'GitHub Integration', category: 'Code Repositories', desc: 'Tracks pull requests, commits, and branch code audit checkups.' },
  { platform: 'gmail', name: 'Gmail Workspace', category: 'Email Communication', desc: 'Parses executive complaints, SLA notification chains, and feedback.' }
];

export const Integrations: React.FC = () => {
  const [mutatingId, setMutatingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // UI Expand state for select drawer
  const [expandedPlatform, setExpandedPlatform] = useState<string | null>(null);
  const [selectedRepos, setSelectedRepos] = useState<string[]>([]);
  const [savingRepos, setSavingRepos] = useState(false);

  // 1. Fetch configured integrations
  const { data: rawConfigs, isLoading, refetch } = useQuery({
    queryKey: ['integrations'],
    queryFn: () => api.get('/integrations/')
  });

  const configuredList = rawConfigs || [];
  
  // Retrieve active GitHub configuration ID if connected
  const githubConfig = configuredList.find((c: any) => c.platform === 'github');
  const githubConnectedId = githubConfig?.id;

  // Fetch repositories from backend using active GitHub integration credentials
  const { data: repoList, isLoading: isLoadingRepos } = useQuery({
    queryKey: ['github-repos', githubConnectedId],
    queryFn: () => api.get(`/integrations/github/${githubConnectedId}/repos`),
    enabled: !!githubConnectedId && expandedPlatform === 'github'
  });

  // Sync selected checkboxes with loaded database preferences
  useEffect(() => {
    if (githubConfig?.tracked_repos) {
      setSelectedRepos(githubConfig.tracked_repos);
    } else {
      setSelectedRepos([]);
    }
  }, [githubConfig?.tracked_repos]);

  // Listen for OAuth completion messages from popup windows
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'OIP_INTEGRATION_CONNECTED' && event.data?.platform === 'github') {
        refetch();
      }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [refetch]);

  const handleToggle = async (platform: string, connectedId?: string) => {
    setMutatingId(platform);
    setError(null);
    try {
      if (connectedId) {
        // Disconnect integration
        await api.delete(`/integrations/${connectedId}`);
        await refetch();
      } else if (platform === 'github') {
        // Open the authorization endpoint inside a centered popup window
        const token = localStorage.getItem('token') || '';
        const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
        const authUrl = `${BASE_URL}/api/v1/integrations/github/authorize?token=${token}`;
        
        const width = 600;
        const height = 650;
        const left = window.screenX + (window.outerWidth - width) / 2;
        const top = window.screenY + (window.outerHeight - height) / 2;
        
        window.open(
          authUrl,
          'Connect GitHub',
          `width=${width},height=${height},left=${left},top=${top},status=no,menubar=no,toolbar=no`
        );
        return; // Popup opened
      } else {
        // Connect other platforms with dummy credential placeholders for now
        await api.post('/integrations/', {
          platform,
          status: 'active',
          credentials: { api_key: 'dummy-ops-token' }
        });
        await refetch();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to update integration connection.');
    } finally {
      setMutatingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto py-24 text-center font-mono text-xs text-on-surface-variant animate-pulse">
        Syncing system integrations...
      </div>
    );
  }

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

      {error && (
        <div className="p-3 bg-red-50 text-red-700 text-xs rounded flex items-start gap-2 border border-red-100 max-w-lg">
          <ShieldAlert className="w-4.5 h-4.5 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {POTENTIAL_CONNECTORS.map(connector => {
          // Check if active in database list
          const activeConfig = configuredList.find((c: any) => c.platform === connector.platform);
          const isConnected = !!activeConfig;
          const statusLabel = isConnected ? 'connected' : 'disconnected';
          const connectedId = activeConfig?.id;
          const isPending = mutatingId === connector.platform;

          return (
            <div key={connector.platform} className="bg-surface border border-outline-variant rounded-lg p-5 flex flex-col justify-between gap-4 hover:border-outline transition-colors">
              
              {/* Top row */}
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-outline-variant bg-surface-low border border-outline-variant px-1.5 py-0.5 rounded font-mono">
                      {connector.category}
                    </span>
                    <h3 className="text-headline-sm font-semibold text-on-surface mt-2">{connector.name}</h3>
                  </div>

                  {/* Status Indicator */}
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    isConnected 
                      ? 'bg-success/10 text-success' 
                      : 'bg-slate-100 text-slate-500'
                  }`}>
                    {statusLabel}
                  </span>
                </div>

                <p className="text-body-sm text-on-surface-variant leading-relaxed">
                  {connector.desc}
                </p>
              </div>

              {/* Actions */}
              <div className="border-t border-outline-variant/60 pt-4 flex items-center justify-between">
                {isConnected ? (
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-outline">
                    <RefreshCw className={`w-3.5 h-3.5 ${isPending ? 'animate-spin' : 'animate-spin-slow'}`} />
                    <span>Active Telemetry</span>
                    {connector.platform === 'github' && (
                      <button
                        onClick={() => setExpandedPlatform(expandedPlatform === 'github' ? null : 'github')}
                        className="ml-1 p-0.5 rounded hover:bg-surface-low text-on-surface-variant hover:text-on-surface transition-colors"
                        title="Configure tracked repositories"
                      >
                        <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${expandedPlatform === 'github' ? 'rotate-180' : ''}`} />
                      </button>
                    )}
                  </div>
                ) : (
                  <span className="text-[11px] text-outline italic">Not synchronized</span>
                )}

                <button
                  onClick={() => handleToggle(connector.platform, connectedId)}
                  disabled={isPending}
                  className={`px-3 py-1.5 rounded text-body-sm font-semibold transition-colors disabled:opacity-50 ${
                    isConnected
                      ? 'bg-surface-low hover:bg-surface-high text-error border border-outline-variant/80'
                      : 'bg-primary hover:bg-slate-800 text-white'
                  }`}
                >
                  {isPending ? 'Saving...' : isConnected ? 'Disconnect' : 'Connect'}
                </button>
              </div>

              {/* Expanded Repo Selection Drawer */}
              {connector.platform === 'github' && isConnected && expandedPlatform === 'github' && (
                <div className="mt-2 border-t border-outline-variant/60 pt-4 space-y-3">
                  <div className="flex flex-col gap-1">
                    <h4 className="text-[12px] font-bold text-on-surface uppercase tracking-wider">Tracked Repositories</h4>
                    <p className="text-[11px] text-on-surface-variant leading-relaxed">
                      Select repositories to scan for pull requests and code modifications.
                    </p>
                  </div>

                  {isLoadingRepos ? (
                    <div className="flex items-center gap-1.5 justify-center py-6 text-[11px] text-outline font-mono">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                      <span>Fetching repositories...</span>
                    </div>
                  ) : (
                    <div className="max-h-48 overflow-y-auto border border-outline-variant/80 rounded bg-surface-low p-2 space-y-1.5">
                      {(!repoList || repoList.length === 0) ? (
                        <p className="text-[11px] text-on-surface-variant text-center py-4 italic">No repositories found.</p>
                      ) : (
                        repoList.map((repo: any) => {
                          const isChecked = selectedRepos.includes(repo.full_name);
                          return (
                            <label 
                              key={repo.id} 
                              className="flex items-start gap-2 p-1.5 hover:bg-surface-high rounded cursor-pointer transition-colors text-[11px] text-on-surface"
                            >
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedRepos([...selectedRepos, repo.full_name]);
                                  } else {
                                    setSelectedRepos(selectedRepos.filter(name => name !== repo.full_name));
                                  }
                                }}
                                className="mt-0.5 rounded border-outline-variant text-primary focus:ring-primary h-3.5 w-3.5"
                              />
                              <div className="flex-1 min-w-0">
                                <p className="font-semibold truncate" title={repo.full_name}>
                                  {repo.full_name}
                                </p>
                                {repo.private && (
                                  <span className="text-[9px] font-bold text-error uppercase tracking-wider block mt-0.5">Private</span>
                                )}
                              </div>
                            </label>
                          );
                        })
                      )}
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2 border-t border-outline-variant/40">
                    <span className="text-[11px] text-outline font-mono">
                      {selectedRepos.length} selected
                    </span>
                    <button
                      onClick={async () => {
                        setSavingRepos(true);
                        try {
                          await api.post(`/integrations/github/${connectedId}/track`, {
                            repos: selectedRepos
                          });
                          await refetch();
                          setExpandedPlatform(null);
                        } catch (err: any) {
                          setError(err.message || 'Failed to save tracking settings.');
                        } finally {
                          setSavingRepos(false);
                        }
                      }}
                      disabled={savingRepos || isLoadingRepos}
                      className="px-2.5 py-1 bg-primary hover:bg-slate-800 text-white rounded text-[11px] font-bold transition-colors disabled:opacity-50"
                    >
                      {savingRepos ? 'Saving...' : 'Save Settings'}
                    </button>
                  </div>
                </div>
              )}

            </div>
          );
        })}
      </div>

    </div>
  );
};

