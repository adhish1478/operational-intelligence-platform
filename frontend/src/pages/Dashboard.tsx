import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  ArrowRight, 
  MessageSquare, 
  GitPullRequest, 
  AlertTriangle,
  Play,
  UserPlus,
  CheckCircle2
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { mapInvestigation, mapEvidence } from '../lib/mappers';
import { useAuthStore } from '../store/authStore';
import type { Severity, OperationalInvestigation, EntityReference, Evidence } from '../types';
import { EvidenceDetailModal } from '../components/EvidenceDetailModal';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const operatorName = user?.first_name || 'Operator';
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);

  const { data: rawInvs, isLoading } = useQuery({
    queryKey: ['investigations'],
    queryFn: () => api.get('/investigations/')
  });

  const { data: recentEvidence, isLoading: isEvidenceLoading } = useQuery({
    queryKey: ['recent-evidence'],
    queryFn: () => api.get('/investigations/evidence/recent')
  });

  const investigations: OperationalInvestigation[] = (rawInvs || []).map(mapInvestigation);
  const evidenceList: Evidence[] = (recentEvidence || []).map(mapEvidence);
  const activeInvestigations = investigations.filter((inv: OperationalInvestigation) => inv.status !== 'resolved');

  const getSeverityBadgeClass = (severity: Severity) => {
    switch (severity) {
      case 'critical': return 'badge-critical';
      case 'high': return 'badge-warning';
      case 'medium': return 'badge-info';
      default: return 'badge-info';
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto py-24 text-center font-mono text-xs text-on-surface-variant animate-pulse">
        Polling telemetry feed...
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Evidence Viewer Modal */}
      <EvidenceDetailModal
        isOpen={!!selectedEvidence}
        onClose={() => setSelectedEvidence(null)}
        evidence={selectedEvidence}
      />

      {/* Header and Welcome */}
      <div className="flex flex-col gap-1 border-b border-outline-variant pb-4">
        <h1 className="text-headline-lg text-on-surface">Attention Deck</h1>
        <p className="text-body-md text-on-surface-variant">
          Hello {operatorName}. There are <strong className="text-error font-semibold">{activeInvestigations.length} active investigations</strong> requiring immediate triage.
        </p>
      </div>

      {/* Flagship Section: Attention Deck - Active Investigations */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-headline-md text-on-surface">Critical Triage Queue</h2>
          <Link 
            to="/investigations" 
            className="flex items-center gap-1.5 text-body-sm font-semibold text-primary hover:underline"
          >
            <span>View full queue</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {activeInvestigations.length === 0 ? (
            <div className="bg-surface border border-outline-variant border-dashed rounded-lg p-10 text-center text-xs font-mono text-on-surface-variant">
              Telemetry secure. Zero active incidents requiring triage.
            </div>
          ) : (
            activeInvestigations.map((inv: OperationalInvestigation) => (
              <div 
                key={inv.id}
                className="bg-surface border border-outline-variant rounded-lg p-5 flex flex-col md:flex-row gap-5 hover:border-outline transition-colors"
              >
                {/* Severity and Basic info */}
                <div className="flex-1 space-y-3">
                  <div className="flex items-center flex-wrap gap-2">
                    <span className={getSeverityBadgeClass(inv.severity)}>
                      {inv.severity.toUpperCase()}
                    </span>
                    <span className="text-mono-label text-outline">ID: {inv.id.substring(0, 8)}</span>
                    <div className="w-1.5 h-1.5 rounded-full bg-outline-variant" />
                    {/* Entity links */}
                    <div className="flex items-center gap-1.5">
                      {inv.entities.map((entity: EntityReference) => (
                        <Link 
                          key={entity.id}
                          to={`/entities/${entity.type}/${entity.id}`}
                          className="text-[11px] font-semibold text-secondary bg-surface-low border border-outline-variant/60 hover:bg-surface-container hover:text-on-surface px-1.5 py-0.5 rounded transition-colors"
                        >
                          {entity.type.toUpperCase()}: {entity.name}
                        </Link>
                      ))}
                    </div>
                  </div>

                  <div>
                    <Link 
                      to={`/investigations/${inv.id}`}
                      className="text-headline-sm font-semibold text-on-surface hover:underline hover:text-primary transition-colors block"
                    >
                      {inv.title}
                    </Link>
                    <p className="text-body-sm text-on-surface-variant mt-1.5 line-clamp-2">
                      {inv.description}
                    </p>
                  </div>

                  {/* Primary Escalation Signals */}
                  <div className="bg-surface-low rounded p-3 border border-outline-variant/40 space-y-2">
                    <div className="text-[10px] font-bold text-outline uppercase tracking-wider flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" /> Escalation Signal
                    </div>
                    {inv.evidence && inv.evidence.length > 0 ? (
                      <div className="flex items-start gap-2 text-body-sm text-on-surface">
                        {inv.evidence[0].type === 'slack' ? (
                          <MessageSquare className="w-4 h-4 text-secondary shrink-0 mt-0.5" />
                        ) : (
                          <GitPullRequest className="w-4 h-4 text-secondary shrink-0 mt-0.5" />
                        )}
                        <p className="line-clamp-1 italic">
                          "{inv.evidence[0].summary}" — <strong className="font-semibold text-on-surface">{inv.evidence[0].author.name}</strong>
                        </p>
                      </div>
                    ) : (
                      <span className="text-body-sm text-on-surface-variant">No signal recorded.</span>
                    )}
                  </div>
                </div>

                {/* Business Impact & Quick Action Panel */}
                <div className="w-full md:w-[280px] bg-surface-low border-l border-outline-variant/60 pl-0 md:pl-5 pt-4 md:pt-0 flex flex-col justify-between gap-4">
                  <div className="space-y-2">
                    <span className="text-[10px] font-bold text-outline uppercase tracking-wider block">Business Impact</span>
                    <div className="text-body-sm font-semibold text-on-surface flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-error animate-pulse" />
                      {inv.severity === 'critical' ? 'TechCorp Contract Renewal Blocked' : 'Operational SLAs Threatened'}
                    </div>
                    <p className="text-[11px] text-on-surface-variant">
                      Suggested action: <span className="text-on-surface font-medium">{inv.suggestedAction || 'Awaiting AI diagnostics'}</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button 
                      onClick={() => navigate(`/investigations/${inv.id}`)}
                      className="flex-1 flex items-center justify-center gap-1.5 bg-primary hover:bg-slate-800 text-white font-semibold text-[12px] py-1.5 px-2.5 rounded transition-colors"
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>Diagnose</span>
                    </button>
                    <button className="flex items-center justify-center p-1.5 rounded border border-outline-variant hover:bg-surface-high text-on-surface-variant hover:text-on-surface transition-colors" title="Assign Owner">
                      <UserPlus className="w-4 h-4" />
                    </button>
                    <button className="flex items-center justify-center p-1.5 rounded border border-outline-variant hover:bg-surface-high text-on-surface-variant hover:text-on-surface transition-colors" title="Mark Resolved">
                      <CheckCircle2 className="w-4 h-4 text-success" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Side-by-Side: Business Impact Targets & Latest Evidence Highlights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Business Impact Section */}
        <div className="space-y-3">
          <h3 className="text-headline-sm text-on-surface uppercase tracking-wider text-outline font-bold">Threatened Business Targets</h3>
          <div className="bg-surface border border-outline-variant rounded-lg p-4 space-y-4">
            <div className="flex items-start gap-3 border-b border-outline-variant pb-3">
              <div className="w-8 h-8 rounded bg-error/10 text-error flex items-center justify-center font-bold text-sm shrink-0">
                $
              </div>
              <div>
                <h4 className="text-body-sm font-semibold text-on-surface">$124k Revenue SLA at Risk</h4>
                <p className="text-[11px] text-on-surface-variant">TechCorp enterprise workspace authentication timeouts approaching SLA tier-1 boundaries.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded bg-warning/10 text-warning flex items-center justify-center font-bold text-sm shrink-0">
                T
              </div>
              <div>
                <h4 className="text-body-sm font-semibold text-on-surface">Team Blockers: Core Platform</h4>
                <p className="text-[11px] text-on-surface-variant">2 critical bottlenecks on Auth Gateway holding up 12 developer workflows across 3 downstream pods.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Global Recent Evidence Feed Highlights */}
        <div className="space-y-3">
          <h3 className="text-headline-sm text-on-surface uppercase tracking-wider text-outline font-bold">Active Signal Stream</h3>
          <div className="bg-surface border border-outline-variant rounded-lg p-4 space-y-3">
            {isEvidenceLoading ? (
              <div className="text-center font-mono text-xs text-on-surface-variant py-4 animate-pulse">
                Loading telemetry stream...
              </div>
            ) : evidenceList.length === 0 ? (
              <div className="text-center font-mono text-xs text-on-surface-variant py-4">
                No active signals recorded.
              </div>
            ) : (
              evidenceList.map((ev: Evidence) => (
                <div 
                  key={ev.id} 
                  onClick={() => setSelectedEvidence(ev)}
                  className="flex items-center justify-between text-body-sm py-1.5 px-2 border-b border-outline-variant/40 last:border-0 cursor-pointer hover:bg-surface-low rounded transition-colors group"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-low group-hover:bg-surface border border-outline-variant/60 text-on-surface-variant uppercase font-semibold shrink-0">
                      {ev.type}
                    </span>
                    <span className="text-on-surface text-[12px] truncate group-hover:text-primary transition-colors" title={ev.summary}>
                      {ev.summary}
                    </span>
                  </div>
                  <span className="text-mono-label text-outline text-[10px] font-mono shrink-0 ml-2">
                    {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
