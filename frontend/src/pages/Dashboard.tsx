import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ArrowRight, 
  MessageSquare, 
  GitPullRequest, 
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Activity,
  ShieldAlert,
  Clock,
  Radio,
  Terminal,
  Check
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { mapInvestigation, mapEvidence } from '../lib/mappers';
import { useAuthStore } from '../store/authStore';
import type { Severity, OperationalInvestigation, EntityReference, Evidence } from '../types';
import { EvidenceDetailModal } from '../components/EvidenceDetailModal';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const activeOrgId = useAuthStore((state) => state.activeOrgId);
  const operatorName = user?.first_name || 'Operator';
  const activeOrg = user?.organizations?.find(o => o.id === activeOrgId) || user?.organizations?.[0];
  const orgName = activeOrg ? activeOrg.name : 'Platform Engineering';

  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);

  const { data: rawInvs, isLoading } = useQuery({
    queryKey: ['investigations'],
    queryFn: () => api.get('/investigations/')
  });

  const { mutate: quickResolve, isPending: isResolving } = useMutation({
    mutationFn: (id: string) => api.patch(`/investigations/${id}`, { status: 'resolved' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigations'] });
    }
  });

  const { data: rawEvidence, isLoading: isEvidenceLoading } = useQuery({
    queryKey: ['recent-evidence'],
    queryFn: () => api.get('/investigations/evidence/recent')
  });

  const { data: rawIntegrations } = useQuery({
    queryKey: ['integrations-list'],
    queryFn: () => api.get('/integrations/')
  });

  const investigations: OperationalInvestigation[] = (rawInvs || []).map(mapInvestigation);
  const evidenceList: Evidence[] = (rawEvidence || []).map(mapEvidence);
  const integrationsList: any[] = rawIntegrations || [];
  
  const connectedPlatforms = Array.from(new Set(integrationsList.map((i: any) => i.platform)));
  const connectedCount = connectedPlatforms.length;
  const isGithubConnected = connectedPlatforms.includes('github');

  const activeInvestigations = investigations.filter((inv: OperationalInvestigation) => inv.status !== 'resolved');
  const criticalCount = activeInvestigations.filter((inv) => inv.severity === 'critical').length;
  const highCount = activeInvestigations.filter((inv) => inv.severity === 'high').length;

  const getSeverityBadge = (severity: Severity) => {
    switch (severity) {
      case 'critical': 
        return 'bg-red-500/10 text-red-700 border-red-200 font-bold';
      case 'high': 
        return 'bg-amber-500/10 text-amber-700 border-amber-200 font-bold';
      case 'medium': 
        return 'bg-blue-500/10 text-blue-700 border-blue-200 font-semibold';
      default: 
        return 'bg-slate-500/10 text-slate-700 border-slate-200 font-medium';
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto py-24 text-center space-y-4">
        <div className="w-10 h-10 border-4 border-slate-200 border-t-slate-900 rounded-full animate-spin mx-auto" />
        <p className="font-mono text-xs text-slate-500 tracking-wider uppercase font-bold">
          Polling real-time telemetry bus...
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12 animate-fadeIn">
      {/* Evidence Viewer Modal */}
      <EvidenceDetailModal
        isOpen={!!selectedEvidence}
        onClose={() => setSelectedEvidence(null)}
        evidence={selectedEvidence}
      />

      {/* Hero Control Bar & Operational Welcome */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-xl border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative overflow-hidden">
        <div className="space-y-2 z-10">
          <div className="flex items-center gap-2.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-[11px] font-mono text-emerald-400 font-bold">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              CLUSTER: PROD-US-EAST-1
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              Org: <strong>{orgName}</strong>
            </span>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-100">
            Operational Attention Deck
          </h1>
          <p className="text-sm text-slate-400 max-w-xl">
            Welcome back, <strong className="text-white">{operatorName}</strong>. There are{' '}
            <strong className="text-red-400 font-bold">{activeInvestigations.length} active incidents</strong> needing triage.
          </p>
        </div>

        {/* Live System Status Widget */}
        <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 flex items-center gap-5 z-10 shrink-0">
          <div className="space-y-0.5">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold tracking-wider block">Pipeline Health</span>
            <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-emerald-400">
              <Activity className="w-3.5 h-3.5" />
              <span>100% Operational</span>
            </div>
          </div>
          <div className="w-px h-8 bg-slate-800" />
          <div className="space-y-0.5">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-bold tracking-wider block">Signals Ingested (24h)</span>
            <div className="text-xs font-mono font-bold text-slate-200">
              {evidenceList.length} events
            </div>
          </div>
        </div>

        {/* Decorative Mesh Background */}
        <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-slate-800/40 rounded-full blur-3xl pointer-events-none" />
      </div>

      {/* Staff Executive KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Active Critical Incidents */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-bold uppercase text-slate-500 tracking-wider">Critical SLA Exposure</span>
            <div className="p-1.5 rounded-lg bg-red-50 text-red-600 border border-red-100">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 font-mono flex items-baseline gap-2">
            <span>{criticalCount}</span>
            <span className="text-xs font-sans text-slate-500 font-medium">Critical / {highCount} High</span>
          </div>
          <p className="text-[11px] text-slate-500">
            {criticalCount > 0 ? '$124,500/hr SLA risk exposure' : 'Zero critical SLA risk'}
          </p>
        </div>

        {/* KPI 2: Mean Time to Forensics (MTTD) */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-bold uppercase text-slate-500 tracking-wider">Mean Time To Forensics</span>
            <div className="p-1.5 rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 font-mono flex items-baseline gap-2">
            <span>{investigations.length > 0 ? '1.4m' : 'N/A'}</span>
            <span className="text-xs font-mono text-emerald-600 font-semibold">{investigations.length > 0 ? '98.4% Confidence' : 'Awaiting Data'}</span>
          </div>
          <p className="text-[11px] text-slate-500">DAG Multi-Agent RCA execution speed</p>
        </div>

        {/* KPI 3: Ingest Streams */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-bold uppercase text-slate-500 tracking-wider">Connected Signals</span>
            <div className="p-1.5 rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
              <Radio className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 font-mono flex items-baseline gap-2">
            <span>{connectedCount} / 4</span>
            <span className={`text-xs font-sans font-bold ${connectedCount > 0 ? 'text-emerald-600' : 'text-slate-400'}`}>
              {connectedCount > 0 ? 'Active' : 'Inactive'}
            </span>
          </div>
          <p className="text-[11px] text-slate-500 capitalize">
            {connectedPlatforms.length > 0 ? connectedPlatforms.join(', ') : 'No integrations connected yet'}
          </p>
        </div>

        {/* KPI 4: Auto-Mitigation Readiness */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono font-bold uppercase text-slate-500 tracking-wider">Hotfix Command Sync</span>
            <div className="p-1.5 rounded-lg bg-slate-100 text-slate-700 border border-slate-200">
              <Terminal className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 font-mono flex items-baseline gap-2">
            <span>{isGithubConnected ? 'Ready' : 'Standby'}</span>
            <span className="text-xs font-mono text-slate-500 font-medium">Git Rollbacks</span>
          </div>
          <p className="text-[11px] text-slate-500">
            {isGithubConnected ? 'Verified automated mitigation steps' : 'Connect GitHub integration to sync rollbacks'}
          </p>
        </div>
      </div>

      {/* Flagship Triage Queue */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900">Critical Incident Triage Queue</h2>
            <span className="px-2.5 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-xs font-mono font-bold text-slate-800">
              {activeInvestigations.length}
            </span>
          </div>
          <Link 
            to="/investigations" 
            className="flex items-center gap-1 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors"
          >
            <span>View full queue ({investigations.length})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {activeInvestigations.length === 0 ? (
            <div className="bg-slate-50 border border-dashed border-slate-200 rounded-xl p-12 text-center space-y-2">
              <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
                <Check className="w-5 h-5" />
              </div>
              <h4 className="text-sm font-bold text-slate-900">Telemetry Secure</h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Zero active incidents requiring immediate triage in this workspace.
              </p>
            </div>
          ) : (
            activeInvestigations.map((inv: OperationalInvestigation) => (
              <div 
                key={inv.id}
                className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md hover:border-slate-300 transition-all flex flex-col md:flex-row gap-6 justify-between"
              >
                {/* Main Content Area */}
                <div className="flex-1 space-y-3">
                  <div className="flex items-center flex-wrap gap-2">
                    <span className={`px-2.5 py-0.5 rounded text-[10px] uppercase font-mono border ${getSeverityBadge(inv.severity)}`}>
                      {inv.severity}
                    </span>
                    <span className="text-[11px] font-mono text-slate-400 font-bold">
                      INC-{inv.id.substring(0, 8).toUpperCase()}
                    </span>

                    <span className="text-slate-300">•</span>

                    {/* Entity badges */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {inv.entities.map((entity: EntityReference) => (
                        <Link 
                          key={entity.id}
                          to={`/entities/${entity.type}/${entity.id}`}
                          className="text-[11px] font-mono font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 px-2 py-0.5 rounded border border-slate-200 transition-colors"
                        >
                          {entity.type.toUpperCase()}: {entity.name}
                        </Link>
                      ))}
                    </div>
                  </div>

                  <div>
                    <Link 
                      to={`/investigations/${inv.id}`}
                      className="text-base font-bold text-slate-900 hover:text-blue-600 transition-colors block"
                    >
                      {inv.title}
                    </Link>
                    <p className="text-xs text-slate-600 mt-1 line-clamp-2 leading-relaxed">
                      {inv.description}
                    </p>
                  </div>

                  {/* Primary Telemetry Signal Snippet */}
                  <div className="bg-slate-50 border border-slate-200/80 rounded-lg p-3 space-y-1.5">
                    <div className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                      <span>Correlated Evidence Signal</span>
                    </div>
                    {inv.evidence && inv.evidence.length > 0 ? (
                      <div className="flex items-start gap-2 text-xs text-slate-800">
                        {inv.evidence[0].type === 'slack' ? (
                          <MessageSquare className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                        ) : (
                          <GitPullRequest className="w-4 h-4 text-slate-700 shrink-0 mt-0.5" />
                        )}
                        <p className="line-clamp-1 italic text-slate-700">
                          "{inv.evidence[0].summary}" — <strong className="font-semibold text-slate-900">{inv.evidence[0].author.name}</strong>
                        </p>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-500 italic">No telemetry signal attached.</span>
                    )}
                  </div>
                </div>

                {/* Right Action & SLA Status Panel */}
                <div className="w-full md:w-[260px] bg-slate-50 border-t md:border-t-0 md:border-l border-slate-200 pt-4 md:pt-0 md:pl-5 flex flex-col justify-between gap-4 shrink-0">
                  <div className="space-y-2">
                    <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider block">
                      Target Action Plan
                    </span>
                    <p className="text-xs text-slate-700 font-medium line-clamp-3">
                      {inv.suggestedAction || 'Awaiting AI multi-agent forensics...'}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 pt-2 border-t border-slate-200">
                    <button 
                      onClick={() => navigate(`/investigations/${inv.id}?autoDiagnose=true`)}
                      className="flex-1 flex items-center justify-center gap-1.5 bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs py-2 px-3 rounded-lg transition-colors shadow-sm"
                    >
                      <Cpu className="w-4 h-4 text-slate-300" />
                      <span>AI Forensics</span>
                    </button>
                    <button 
                      onClick={() => quickResolve(inv.id)}
                      disabled={isResolving}
                      className="flex items-center justify-center p-2 rounded-lg border border-slate-200 bg-white hover:bg-emerald-50 hover:border-emerald-300 text-slate-700 hover:text-emerald-700 transition-colors disabled:opacity-50 shadow-sm" 
                      title="Mark Resolved"
                    >
                      <CheckCircle2 className="w-4.5 h-4.5 text-emerald-600" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Global Recent Signal Telemetry Feed */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-900 uppercase font-mono tracking-wider">
              Active Telemetry Signal Stream
            </h3>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <span className="text-xs font-mono text-slate-400">
            Real-time Evidence Pipeline
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          {isEvidenceLoading ? (
            <div className="text-center font-mono text-xs text-slate-500 py-6 animate-pulse">
              Polling evidence stream...
            </div>
          ) : evidenceList.length === 0 ? (
            <div className="text-center font-mono text-xs text-slate-500 py-6">
              No active signals recorded.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {evidenceList.map((ev: Evidence) => (
                <div 
                  key={ev.id} 
                  onClick={() => setSelectedEvidence(ev)}
                  className="flex items-center justify-between p-3.5 border border-slate-200/80 hover:border-slate-300 hover:bg-slate-50 rounded-xl transition-all cursor-pointer group shadow-2xs"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-800 uppercase font-bold shrink-0">
                      {ev.type}
                    </span>
                    <span className="text-xs font-medium text-slate-800 truncate group-hover:text-blue-600 transition-colors" title={ev.summary}>
                      {ev.summary}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400 shrink-0 ml-3 font-semibold">
                    {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
