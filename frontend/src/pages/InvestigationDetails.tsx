import React, { useState, useEffect } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { 
  MessageSquare, 
  GitCommit, 
  CheckCircle,
  FileText,
  Mail,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  Send,
  ShieldAlert,
  Sparkles,
  Cpu
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { mapInvestigation, mapEvidence } from '../lib/mappers';
import type { Severity, Evidence, EntityReference, InvestigationStatus } from '../types';
import { EvidenceDetailModal } from '../components/EvidenceDetailModal';
import { AiDiagnosisModal } from '../components/AiDiagnosisModal';
import { MarkdownRenderer } from '../components/MarkdownRenderer';

export const InvestigationDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();

  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);
  const [isRcaModalOpen, setIsRcaModalOpen] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [diagnosing, setDiagnosing] = useState(false);
  const [diagnoseError, setDiagnoseError] = useState<string | null>(null);

  // Closed loop action states
  const [sharingSlack, setSharingSlack] = useState(false);
  const [slackPostedChannel, setSlackPostedChannel] = useState<string | null>(null);
  const [slackError, setSlackError] = useState<string | null>(null);

  const [isStatusMenuOpen, setIsStatusMenuOpen] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [escalatingJira, setEscalatingJira] = useState(false);
  const [jiraTicket, setJiraTicket] = useState<{ key: string; url: string } | null>(null);
  const [jiraError, setJiraError] = useState<string | null>(null);

  useEffect(() => {
    if (searchParams.get('autoDiagnose') === 'true' && id) {
      setIsRcaModalOpen(true);
      if (!activeDiagnosis && !diagnosing) {
        handleRunDiagnosis();
      }
    }
  }, [searchParams, id]);
  
  const handleSetStatus = async (newStatus: InvestigationStatus) => {
    if (!id || !investigation) return;
    setIsStatusMenuOpen(false);
    setResolving(true);
    try {
      await api.patch(`/investigations/${id}`, { status: newStatus });
      const statusEvt = {
        id: Date.now().toString(),
        type: 'system',
        text: `Investigation status changed to ${newStatus.toUpperCase()}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setTimelineEvents(prev => [...prev, statusEvt]);
      await refetchInv();
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Failed to update status.');
    } finally {
      setResolving(false);
    }
  };
  
  const [diagnosisData, setDiagnosisData] = useState<any>(null);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [activeStepText, setActiveStepText] = useState<string>('');

  const [timelineEvents, setTimelineEvents] = useState([
    { id: '1', type: 'system', text: 'Investigation opened automatically via SysAlert', time: '10:14 AM' },
    { id: '2', type: 'system', text: 'Severity set to Critical based on SLA agreement', time: '10:15 AM' }
  ]);

  // 1. Fetch Investigation Details
  const { data: rawInv, isLoading: isInvLoading, refetch: refetchInv } = useQuery({
    queryKey: ['investigation', id],
    queryFn: () => api.get(`/investigations/${id}`),
    enabled: !!id
  });

  // 2. Fetch Evidence Timeline from MongoDB
  const { data: rawEv, isLoading: isEvidenceLoading } = useQuery({
    queryKey: ['evidence', id],
    queryFn: () => api.get(`/investigations/${id}/evidence`),
    enabled: !!id
  });

  // 3. Fetch Diagnoses History (Structured Multi-Agent Reports)
  const { data: rawDiagnoses, refetch: refetchDiagnoses } = useQuery({
    queryKey: ['diagnoses', id],
    queryFn: () => api.get(`/investigations/${id}/diagnoses`),
    enabled: !!id
  });

  const latestDiagnosis = rawDiagnoses && rawDiagnoses.length > 0 ? rawDiagnoses[rawDiagnoses.length - 1] : null;
  const activeDiagnosis = diagnosisData || latestDiagnosis;

  const investigation = rawInv ? mapInvestigation(rawInv) : null;
  const evidenceList = (rawEv || []).map(mapEvidence);

  const handleRunDiagnosis = async () => {
    if (!id) return;
    setIsRcaModalOpen(true);
    setDiagnosing(true);
    setDiagnoseError(null);
    setCurrentStepIndex(0);
    setActiveStepText('Gathering correlated telemetry from GitHub, Jira, and alerts...');

    try {
      await api.stream(`/investigations/${id}/diagnose/stream`, (eventType, payload) => {
        if (eventType === 'triage') {
          setCurrentStepIndex(0);
          setActiveStepText(`Correlating ${payload.evidence_count} evidence streams across GitHub, Jira, and Slack...`);
        } else if (eventType === 'rca_complete') {
          setCurrentStepIndex(1);
          setActiveStepText(`Root cause located: ${payload.offending_commit?.hash ? `Commit #${payload.offending_commit.hash.slice(0, 7)} by ${payload.offending_commit.author}` : payload.root_cause_summary?.slice(0, 60)}`);
        } else if (eventType === 'business_impact_complete') {
          setCurrentStepIndex(2);
          setActiveStepText(`Financial risk assessed: $${payload.estimated_downtime_cost_per_hour?.toLocaleString() || '18,500'}/hr exposure calculated.`);
        } else if (eventType === 'remediation_complete') {
          setCurrentStepIndex(3);
          setActiveStepText(`Automated hotfix plan generated: ${payload.git_rollback_command || 'Git rollback ready'}.`);
        } else if (eventType === 'finished') {
          setCurrentStepIndex(4);
          setActiveStepText('Analysis complete.');
          setDiagnosisData({
            report_summary: payload.report_summary,
            technical_rca: payload.technical_rca,
            business_impact: payload.business_impact,
            remediation_plan: payload.remediation_plan,
            orchestration_metadata: { triage_mode: 'DAG_MULTI_AGENT' }
          });
        }
      });

      const aiEvent = {
        id: Date.now().toString(),
        type: 'ai-forensics',
        text: `AI Forensic Analysis completed`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setTimelineEvents(prev => [...prev, aiEvent]);

      await refetchInv();
      await refetchDiagnoses();
    } catch (err: any) {
      try {
        const resp = await api.post(`/investigations/${id}/diagnose`);
        setDiagnosisData(resp);
      } catch (fallbackErr: any) {
        setDiagnoseError(fallbackErr.message || 'AI Diagnosis request failed.');
      }
    } finally {
      setDiagnosing(false);
    }
  };

  const handleAddComment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    
    const newEvent = {
      id: Date.now().toString(),
      type: 'user',
      text: `SecOps: ${commentText}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    
    setTimelineEvents(prev => [...prev, newEvent]);
    setCommentText('');
  };

  const handleShareSlack = async () => {
    if (!id) return;
    setSharingSlack(true);
    setSlackPostedChannel(null);
    setSlackError(null);
    try {
      const resp = await api.post(`/investigations/${id}/share-slack`);
      setSlackPostedChannel(resp.channel || '#alerts');
      const slackEvt = {
        id: Date.now().toString(),
        type: 'escalation',
        text: `Shared AI Diagnosis report to Slack channel ${resp.channel || '#alerts'}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setTimelineEvents(prev => [...prev, slackEvt]);
    } catch (err: any) {
      setSlackError(err.response?.data?.detail || err.message || 'Failed to share to Slack.');
    } finally {
      setSharingSlack(false);
    }
  };

  const handleEscalateJira = async () => {
    if (!id) return;
    setEscalatingJira(true);
    setJiraTicket(null);
    setJiraError(null);
    try {
      const resp = await api.post(`/investigations/${id}/escalate-jira`);
      setJiraTicket({ key: resp.key, url: resp.url });
      const jiraEvt = {
        id: Date.now().toString(),
        type: 'escalation',
        text: `Escalated incident to Jira ticket ${resp.key}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setTimelineEvents(prev => [...prev, jiraEvt]);
      await refetchInv();
    } catch (err: any) {
      setJiraError(err.response?.data?.detail || err.message || 'Failed to escalate to Jira.');
    } finally {
      setEscalatingJira(false);
    }
  };

  const getSeverityBadgeClass = (severity: Severity) => {
    switch (severity) {
      case 'critical': return 'badge-critical';
      case 'high': return 'badge-warning';
      case 'medium': return 'badge-info';
      default: return 'badge-info';
    }
  };

  // Render distinct branded icons for each evidence type
  const getEvidenceIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'slack': 
        return (
          <span className="p-1 rounded bg-[#4A154B]/10 text-[#4A154B] border border-[#4A154B]/20 shrink-0" title="Slack Signal">
            <MessageSquare className="w-3.5 h-3.5" />
          </span>
        );
      case 'github': 
      case 'push':
      case 'pull_request':
        return (
          <span className="p-1 rounded bg-slate-900 text-slate-100 border border-slate-700 shrink-0" title="GitHub Signal">
            <GitCommit className="w-3.5 h-3.5" />
          </span>
        );
      case 'jira': 
        return (
          <span className="p-1 rounded bg-[#0052CC]/10 text-[#0052CC] border border-[#0052CC]/20 shrink-0" title="Jira Ticket Signal">
            <CheckCircle className="w-3.5 h-3.5" />
          </span>
        );
      case 'email': 
      case 'gmail': 
        return (
          <span className="p-1 rounded bg-red-500/10 text-red-600 border border-red-200 shrink-0" title="Gmail Alert Signal">
            <Mail className="w-3.5 h-3.5" />
          </span>
        );
      case 'alert': 
        return (
          <span className="p-1 rounded bg-amber-500/10 text-amber-600 border border-amber-200 shrink-0" title="System Alert">
            <ShieldAlert className="w-3.5 h-3.5" />
          </span>
        );
      default: 
        return (
          <span className="p-1 rounded bg-slate-100 text-slate-700 border border-slate-200 shrink-0">
            <FileText className="w-3.5 h-3.5" />
          </span>
        );
    }
  };

  if (isInvLoading) {
    return (
      <div className="max-w-6xl mx-auto py-24 text-center font-mono text-xs text-on-surface-variant animate-pulse">
        Fetching incident forensics database metadata...
      </div>
    );
  }

  if (!investigation) {
    return (
      <div className="max-w-6xl mx-auto py-24 text-center font-mono text-xs text-error">
        Incident Record Not Found.
      </div>
    );
  }

  // Mock Logs matching the category
  const mockSystemLogs = [
    { timestamp: '10:14:02.129', service: 'auth-gateway', level: 'WARN', msg: 'Redis timeout on handshake key: auth_session_cache' },
    { timestamp: '10:14:05.402', service: 'auth-gateway', level: 'ERR', msg: 'Token validation response latency exceeded threshold: 3500ms' },
    { timestamp: '10:14:08.922', service: 'auth-gateway', level: 'WARN', msg: 'Re-establishing auth pool sockets due to buffer exhaustion' },
  ];


  return (
    <div className="max-w-7xl mx-auto flex flex-col gap-5 h-[calc(100vh-80px)] overflow-hidden">
      
      {/* Page Title & Breadcrumbs header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-outline-variant pb-3 shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className={getSeverityBadgeClass(investigation.severity)}>
              {investigation.severity.toUpperCase()}
            </span>
            <span className="text-mono-label text-outline">INVESTIGATION ID: {investigation.id}</span>
          </div>
          <h1 className="text-headline-md font-semibold text-on-surface">{investigation.title}</h1>
        </div>

        <div className="flex items-center gap-2">
          {/* AI Forensics Modal Trigger */}
          <button 
            onClick={() => {
              setIsRcaModalOpen(true);
              if (!activeDiagnosis && !diagnosing) {
                handleRunDiagnosis();
              }
            }}
            className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white text-body-sm font-semibold rounded-lg transition-all shadow-sm flex items-center gap-2 border border-slate-800"
          >
            <Cpu className="w-4 h-4 text-slate-300" />
            <span>AI Forensics & RCA</span>
          </button>

          {/* Status Dropdown Selector */}
          <div className="relative">
            <button 
              onClick={() => setIsStatusMenuOpen(!isStatusMenuOpen)}
              disabled={resolving}
              className={`px-3.5 py-1.5 border font-semibold text-body-sm rounded-lg transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50 ${
                investigation.status === 'resolved'
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-700 hover:bg-emerald-100'
                  : investigation.status === 'closed'
                  ? 'bg-slate-100 border-slate-300 text-slate-700 hover:bg-slate-200'
                  : investigation.status === 'investigating'
                  ? 'bg-amber-50 border-amber-300 text-amber-700 hover:bg-amber-100'
                  : 'border-outline-variant hover:bg-surface-high text-on-surface'
              }`}
            >
              <CheckCircle className={`w-4 h-4 ${
                investigation.status === 'resolved' ? 'text-emerald-600' :
                investigation.status === 'closed' ? 'text-slate-500' :
                investigation.status === 'investigating' ? 'text-amber-500' : 'text-slate-400'
              }`} />
              <span className="capitalize">
                {resolving ? 'Updating...' : `Status: ${investigation.status}`}
              </span>
              <ChevronDown className="w-3.5 h-3.5 opacity-60 ml-0.5" />
            </button>

            {isStatusMenuOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white border border-slate-200 rounded-lg shadow-xl py-1 z-30 font-sans">
                <div className="px-3 py-1 text-[10px] uppercase font-bold text-slate-400 border-b border-slate-100">
                  Update Incident Status
                </div>
                <button
                  onClick={() => handleSetStatus('open')}
                  className="w-full px-3 py-2 text-left text-xs font-semibold hover:bg-slate-50 flex items-center gap-2 text-slate-800"
                >
                  <span className="w-2 h-2 rounded-full bg-red-500" />
                  <span>Open</span>
                </button>
                <button
                  onClick={() => handleSetStatus('investigating')}
                  className="w-full px-3 py-2 text-left text-xs font-semibold hover:bg-slate-50 flex items-center gap-2 text-slate-800"
                >
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  <span>Investigating</span>
                </button>
                <button
                  onClick={() => handleSetStatus('resolved')}
                  className="w-full px-3 py-2 text-left text-xs font-semibold hover:bg-slate-50 flex items-center gap-2 text-slate-800"
                >
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span>Resolved</span>
                </button>
                <button
                  onClick={() => handleSetStatus('closed')}
                  className="w-full px-3 py-2 text-left text-xs font-semibold hover:bg-slate-50 flex items-center gap-2 border-t border-slate-100 text-slate-700"
                >
                  <span className="w-2 h-2 rounded-full bg-slate-400" />
                  <span>Closed (Archive)</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {diagnoseError && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded flex items-start gap-2 shrink-0">
          <ShieldAlert className="w-4.5 h-4.5 shrink-0 mt-0.5" />
          <span>{diagnoseError}</span>
        </div>
      )}

      {/* Flagship Multi-Pane Board Grid Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-0 overflow-hidden pb-4">
        
        {/* Pane 1 (Left / 4 Columns): Diagnostic Summary & System Log Feed */}
        <div className="lg:col-span-4 flex flex-col gap-4 min-h-0 overflow-y-auto pr-1">
          <div className="bg-surface border border-outline-variant rounded-lg p-4 space-y-4 shrink-0">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <h3 className="text-headline-sm text-outline uppercase tracking-wider font-bold">Root Cause Summary</h3>
                <button
                  onClick={() => setIsRcaModalOpen(true)}
                  className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors"
                >
                  <Sparkles className="w-3 h-3" />
                  <span>Full AI Report</span>
                </button>
              </div>
              <p className="text-body-sm text-on-surface font-sans">{activeDiagnosis?.technical_rca?.root_cause_summary || investigation.description || 'Awaiting description analysis.'}</p>
            </div>

            <div className="bg-error-container/40 border border-error/20 rounded p-3 space-y-3">
              <div>
                <h4 className="text-body-sm font-semibold text-error flex items-center gap-1.5 mb-1">
                  <span>Suggested Remediation</span>
                </h4>
                {(investigation.suggestedAction || activeDiagnosis?.report_summary) ? (
                  <MarkdownRenderer content={investigation.suggestedAction || activeDiagnosis?.report_summary} />
                ) : (
                  <p className="text-body-sm text-on-surface">No remediation suggested yet. Run AI Diagnostics above.</p>
                )}
              </div>

              <div className="pt-2.5 border-t border-outline-variant/40 space-y-2">
                <span className="text-[10px] font-mono text-slate-500 font-bold uppercase tracking-wider block">
                  Integration Actions
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  {/* Open / Share Slack Thread */}
                  <button
                    onClick={handleShareSlack}
                    disabled={sharingSlack || !!slackPostedChannel}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-[#4A154B] hover:bg-[#3b113c] text-white transition-all shadow-xs disabled:opacity-75"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    <span>
                      {sharingSlack ? 'Sharing...' : slackPostedChannel ? `Open Slack Thread (${slackPostedChannel})` : 'Open Slack Thread'}
                    </span>
                  </button>

                  {/* Open / Escalate Jira Ticket */}
                  {jiraTicket ? (
                    <a
                      href={jiraTicket.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-[#0052CC] hover:bg-[#0041a3] text-white transition-all shadow-xs"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>Open Jira Ticket ({jiraTicket.key})</span>
                      <ExternalLink className="w-3 h-3 ml-0.5" />
                    </a>
                  ) : (
                    <button
                      onClick={handleEscalateJira}
                      disabled={escalatingJira}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-[#0052CC] hover:bg-[#0041a3] text-white transition-all shadow-xs disabled:opacity-75"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>{escalatingJira ? 'Creating Ticket...' : 'Open Jira Ticket'}</span>
                    </button>
                  )}

                  {/* Open GitHub PR / Code Commit if GitHub evidence exists */}
                  {evidenceList.find((e: Evidence) => e.type === 'github' && e.sourceUrl) && (
                    <a
                      href={evidenceList.find((e: Evidence) => e.type === 'github' && e.sourceUrl)?.sourceUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-slate-900 hover:bg-slate-800 text-white transition-all shadow-xs border border-slate-700"
                    >
                      <GitCommit className="w-3.5 h-3.5 text-slate-300" />
                      <span>Open GitHub PR</span>
                      <ExternalLink className="w-3 h-3 ml-0.5" />
                    </a>
                  )}
                </div>
              </div>

              {(slackError || jiraError) && (
                <p className="text-[10px] text-error font-mono leading-tight">
                  Error: {slackError || jiraError}
                </p>
              )}
            </div>
          </div>

          {/* High-density Live Terminal Logs */}
          <div className="bg-primary text-white rounded-lg p-4 font-mono text-[12px] flex-1 flex flex-col min-h-0 overflow-hidden shadow-inner">
            <div className="flex items-center justify-between border-b border-white/10 pb-2 mb-2 shrink-0">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Live Diagnostic Logs</span>
              <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
            </div>
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-2">
              {mockSystemLogs.map((log, index) => (
                <div key={index} className="leading-relaxed text-[11px]">
                  <span className="text-slate-450">[{log.timestamp}]</span>{' '}
                  <span className="text-secondary-container font-semibold">{log.service}:</span>{' '}
                  <span className={log.level === 'ERR' ? 'text-error' : 'text-warning font-semibold'}>
                    [{log.level}]
                  </span>{' '}
                  <span className="text-slate-100">{log.msg}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Pane 2 (Center / 5 Columns): Multi-Platform Evidence Feed */}
        <div className="lg:col-span-5 flex flex-col bg-surface border border-outline-variant rounded-lg min-h-0 overflow-hidden">
          <div className="p-4 border-b border-outline-variant bg-surface-low flex items-center justify-between shrink-0">
            <h3 className="text-headline-sm text-on-surface">Evidence Feed</h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface border border-outline-variant text-on-surface-variant font-bold">
              {evidenceList.length} items
            </span>
          </div>

          {/* List of Evidence cards */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {isEvidenceLoading ? (
              <div className="text-center font-mono text-xs text-on-surface-variant py-12 animate-pulse">
                Querying MongoDB timeline...
              </div>
            ) : evidenceList.length === 0 ? (
              <div className="text-center font-mono text-xs text-on-surface-variant py-12 border border-dashed border-outline-variant rounded">
                No telemetry logs attached to this incident.
              </div>
            ) : (
              evidenceList.map((ev: Evidence) => (
                <div 
                  key={ev.id} 
                  onClick={() => setSelectedEvidence(ev)}
                  className="p-3.5 border border-outline-variant rounded-lg bg-surface hover:border-primary/50 transition-all space-y-2 group cursor-pointer shadow-xs"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getEvidenceIcon(ev.type)}
                      <span className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider font-mono">
                        {ev.type}
                      </span>
                      {ev.author && ev.author.name && (
                        <>
                          <span className="text-outline text-xs">•</span>
                          <span className="text-body-sm font-semibold text-on-surface">
                            {ev.author.name}
                          </span>
                        </>
                      )}
                    </div>
                    {ev.sourceUrl && (
                      <a 
                        href={ev.sourceUrl} 
                        target="_blank" 
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-outline hover:text-primary transition-colors flex items-center gap-1 text-[10px]"
                      >
                        <span>Source</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>

                  <p className="text-body-sm font-medium text-on-surface leading-relaxed group-hover:text-primary transition-colors">
                    {ev.summary}
                  </p>

                  {/* Integration specific metadata pills (filtering out long body strings) */}
                  {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1.5 border-t border-outline-variant/40">
                      {Object.entries(ev.metadata).map(([key, val]) => {
                        if (key === 'body' || key === 'snippet') return null;
                        return (
                          <span 
                            key={key}
                            className="text-[10px] bg-surface-low border border-outline-variant/60 text-on-surface-variant px-2 py-0.5 rounded font-mono"
                          >
                            {key}: {String(val)}
                          </span>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Modal Viewer */}
        <EvidenceDetailModal
          isOpen={!!selectedEvidence}
          onClose={() => setSelectedEvidence(null)}
          evidence={selectedEvidence}
        />

        {/* Pane 3 (Right / 3 Columns): Timeline Log & Entity Relationships */}
        <div className="lg:col-span-3 flex flex-col gap-4 min-h-0 overflow-y-auto">
          {/* Associated Entities */}
          <div className="bg-surface border border-outline-variant rounded-lg p-4 space-y-3 shrink-0">
            <h3 className="text-headline-sm text-outline uppercase tracking-wider font-bold">Linked Entities</h3>
            <div className="space-y-2">
              {investigation.entities.map((entity: EntityReference) => (
                <Link 
                  key={entity.id}
                  to={`/entities/${entity.type}/${entity.id}`}
                  className="flex items-center justify-between p-2 rounded bg-surface-low border border-outline-variant/60 hover:bg-surface-container transition-colors group"
                >
                  <div>
                    <div className="text-[10px] text-on-surface-variant uppercase font-bold tracking-wider">{entity.type}</div>
                    <div className="text-body-sm font-semibold text-on-surface group-hover:text-primary transition-colors">{entity.name}</div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-outline group-hover:text-on-surface transition-colors" />
                </Link>
              ))}
            </div>
          </div>

          {/* Interactive Timeline */}
          <div className="bg-surface border border-outline-variant rounded-lg p-4 flex-1 flex flex-col min-h-0 overflow-hidden">
            <h3 className="text-headline-sm text-outline uppercase tracking-wider font-bold mb-3 shrink-0">Audit Timeline</h3>
            
            {/* Timeline Stream */}
            <div className="flex-1 overflow-y-auto relative pl-4 border-l border-outline-variant space-y-4 mb-3 pr-2">
              {timelineEvents.map((evt) => (
                <div key={evt.id} className="relative text-body-sm">
                  {/* Timeline Dot */}
                  <span className="absolute -left-[20.5px] top-1 w-2.5 h-2.5 rounded-full border-2 border-surface bg-outline" />
                  <div className="flex items-center justify-between gap-2 text-outline text-[11px] mb-0.5">
                    <span className="font-semibold uppercase text-[9px] tracking-wider">
                      {evt.type}
                    </span>
                    <span className="font-mono">{evt.time}</span>
                  </div>
                  <p className="text-on-surface leading-tight text-[12px]">{evt.text}</p>
                </div>
              ))}
            </div>

            {/* Input Comment Box */}
            <form onSubmit={handleAddComment} className="flex gap-1.5 shrink-0 border-t border-outline-variant/60 pt-3">
              <input
                type="text"
                placeholder="Log activity note..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                className="flex-1 bg-surface-low border border-outline-variant rounded px-2.5 py-1.5 text-body-sm text-on-surface focus:outline-none focus:border-outline"
              />
              <button 
                type="submit"
                className="bg-primary hover:bg-slate-800 text-white p-2 rounded transition-colors shrink-0"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>
        </div>

      </div>

      {/* AI Diagnosis Forensic Modal */}
      <AiDiagnosisModal
        isOpen={isRcaModalOpen}
        onClose={() => setIsRcaModalOpen(false)}
        investigationTitle={investigation.title}
        severity={investigation.severity}
        suggestedAction={investigation.suggestedAction || activeDiagnosis?.report_summary}
        technicalRca={activeDiagnosis?.technical_rca}
        businessImpact={activeDiagnosis?.business_impact}
        remediationPlan={activeDiagnosis?.remediation_plan}
        orchestrationMetadata={activeDiagnosis?.orchestration_metadata}
        evidenceList={evidenceList}
        currentStepIndex={currentStepIndex}
        activeStepText={activeStepText}
        onRunDiagnosis={handleRunDiagnosis}
        isDiagnosing={diagnosing}
        onShareSlack={handleShareSlack}
        isSharingSlack={sharingSlack}
        slackPostedChannel={slackPostedChannel}
        onEscalateJira={handleEscalateJira}
        isEscalatingJira={escalatingJira}
        jiraTicket={jiraTicket}
      />
    </div>
  );
};
