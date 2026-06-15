import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  MessageSquare, 
  GitCommit, 
  CheckCircle,
  FileText,
  Mail,
  ExternalLink,
  ChevronRight,
  Send
} from 'lucide-react';
import { mockInvestigations } from '../services/mockData';
import type { Severity } from '../types';

export const InvestigationDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const investigation = mockInvestigations.find(inv => inv.id === id) || mockInvestigations[0];
  
  const [commentText, setCommentText] = useState('');
  const [timelineEvents, setTimelineEvents] = useState([
    { id: '1', type: 'system', text: 'Investigation opened automatically via SysAlert', time: '10:14 AM' },
    { id: '2', type: 'system', text: 'Severity set to Critical based on TechCorp SLA agreement', time: '10:15 AM' },
    { id: '3', type: 'integration', text: 'Slack thread #techcorp-incident pulled as active evidence', time: '10:16 AM' }
  ]);

  const handleAddComment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    
    const newEvent = {
      id: Date.now().toString(),
      type: 'user',
      text: `Adhish Aravind: ${commentText}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    
    setTimelineEvents(prev => [...prev, newEvent]);
    setCommentText('');
  };

  const getSeverityBadgeClass = (severity: Severity) => {
    switch (severity) {
      case 'critical': return 'badge-critical';
      case 'high': return 'badge-warning';
      case 'medium': return 'badge-info';
      default: return 'badge-info';
    }
  };

  // Render icons for each evidence type
  const getEvidenceIcon = (type: string) => {
    switch (type) {
      case 'slack': return <MessageSquare className="w-4.5 h-4.5 text-secondary shrink-0" />;
      case 'github': return <GitCommit className="w-4.5 h-4.5 text-secondary shrink-0" />;
      case 'jira': return <CheckCircle className="w-4.5 h-4.5 text-secondary shrink-0" />;
      case 'email': return <Mail className="w-4.5 h-4.5 text-secondary shrink-0" />;
      case 'notion': return <FileText className="w-4.5 h-4.5 text-secondary shrink-0" />;
      default: return <FileText className="w-4.5 h-4.5 text-secondary shrink-0" />;
    }
  };

  // Mock Logs matching the category
  const mockSystemLogs = [
    { timestamp: '10:14:02.129', service: 'auth-gateway', level: 'WARN', msg: 'Redis timeout on handshake key: auth_session_techcorp' },
    { timestamp: '10:14:05.402', service: 'auth-gateway', level: 'ERR', msg: 'Token validation response latency exceeded threshold: 3500ms' },
    { timestamp: '10:14:08.922', service: 'auth-gateway', level: 'WARN', msg: 'Re-establishing auth pool sockets due to buffer exhaustion' },
    { timestamp: '10:14:12.301', service: 'auth-gateway', level: 'ERR', msg: 'Redis timeout on handshake key: auth_session_techcorp (retries exhausted)' },
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
          <button className="px-3 py-1.5 border border-outline-variant hover:bg-surface-high text-body-sm font-semibold rounded transition-colors text-on-surface">
            Mark Resolved
          </button>
          <button className="px-3 py-1.5 bg-primary hover:bg-slate-800 text-white text-body-sm font-semibold rounded transition-colors">
            Share Context
          </button>
        </div>
      </div>

      {/* Flagship Multi-Pane Board Grid Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-0 overflow-hidden pb-4">
        
        {/* Pane 1 (Left / 4 Columns): Diagnostic Summary & System Log Feed */}
        <div className="lg:col-span-4 flex flex-col gap-4 min-h-0">
          <div className="bg-surface border border-outline-variant rounded-lg p-4 space-y-4 shrink-0">
            <div>
              <h3 className="text-headline-sm text-outline uppercase tracking-wider font-bold mb-1.5">Root Cause Summary</h3>
              <p className="text-body-sm text-on-surface">{investigation.description}</p>
            </div>

            <div className="bg-error-container/40 border border-error/20 rounded p-3">
              <h4 className="text-body-sm font-semibold text-error flex items-center gap-1.5 mb-1">
                <span>Suggested Remediation</span>
              </h4>
              <p className="text-body-sm text-on-surface">{investigation.suggestedAction}</p>
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
                <div key={index} className="leading-relaxed">
                  <span className="text-slate-400">[{log.timestamp}]</span>{' '}
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
              {investigation.evidence.length} items
            </span>
          </div>

          {/* List of Evidence cards */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {investigation.evidence.map((ev) => (
              <div 
                key={ev.id} 
                className="p-3 border border-outline-variant rounded bg-surface hover:border-outline transition-colors space-y-2 group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {getEvidenceIcon(ev.type)}
                    <span className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">
                      {ev.type}
                    </span>
                    {ev.author.name && (
                      <>
                        <span className="text-outline text-xs">•</span>
                        <span className="text-body-sm font-semibold text-on-surface">
                          {ev.author.name}
                        </span>
                      </>
                    )}
                  </div>
                  <a 
                    href={ev.sourceUrl} 
                    target="_blank" 
                    rel="noreferrer"
                    className="text-outline hover:text-primary transition-colors flex items-center gap-1 text-[10px]"
                  >
                    <span>Source</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                <p className="text-body-sm text-on-surface leading-relaxed">
                  {ev.summary}
                </p>

                {/* Integration specific metadata pills */}
                {Object.keys(ev.metadata).length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1.5 border-t border-outline-variant/40">
                    {Object.entries(ev.metadata).map(([key, val]) => (
                      <span 
                        key={key}
                        className="text-[10px] bg-surface-low border border-outline-variant/60 text-on-surface-variant px-1.5 py-0.2 rounded font-mono"
                      >
                        {key}: {val}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Pane 3 (Right / 3 Columns): Timeline Log & Entity Relationships */}
        <div className="lg:col-span-3 flex flex-col gap-4 min-h-0 overflow-y-auto">
          {/* Associated Entities */}
          <div className="bg-surface border border-outline-variant rounded-lg p-4 space-y-3 shrink-0">
            <h3 className="text-headline-sm text-outline uppercase tracking-wider font-bold">Linked Entities</h3>
            <div className="space-y-2">
              {investigation.entities.map(entity => (
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
    </div>
  );
};
