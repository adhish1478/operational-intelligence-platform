import React from 'react';
import { 
  X, 
  Mail, 
  MessageSquare, 
  GitCommit, 
  CheckCircle, 
  FileText, 
  ExternalLink,
  Clock,
  Tag
} from 'lucide-react';
import type { Evidence } from '../types';

interface EvidenceDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  evidence: Evidence | null;
}

export const EvidenceDetailModal: React.FC<EvidenceDetailModalProps> = ({
  isOpen,
  onClose,
  evidence
}) => {
  if (!isOpen || !evidence) return null;

  const isGmail = evidence.type === 'gmail' || evidence.type === 'email';
  const authorName = evidence.author?.name || (evidence.metadata?.from as string) || 'System Sender';
  const subject = (evidence.metadata?.subject as string) || evidence.summary;
  const bodyText = (evidence.metadata?.body as string) || (evidence.metadata?.snippet as string) || evidence.summary;

  const getPlatformIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'slack': return <MessageSquare className="w-4 h-4 text-[#E01E5A]" />;
      case 'github': return <GitCommit className="w-4 h-4 text-secondary" />;
      case 'jira': return <CheckCircle className="w-4 h-4 text-[#0052CC]" />;
      case 'gmail':
      case 'email': return <Mail className="w-4 h-4 text-[#EA4335]" />;
      default: return <FileText className="w-4 h-4 text-secondary" />;
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((part) => part.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2) || 'EV';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-surface border border-outline-variant rounded-xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Modal Header Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-outline-variant bg-surface-low">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-surface border border-outline-variant/60 shadow-sm">
              {getPlatformIcon(evidence.type)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-surface border border-outline-variant text-on-surface-variant">
                  {evidence.type}
                </span>
                <span className="text-outline text-xs">•</span>
                <span className="text-body-xs font-mono text-outline flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(evidence.timestamp).toLocaleString()}
                </span>
              </div>
              <h3 className="text-title-md font-semibold text-on-surface mt-0.5 line-clamp-1">
                {subject}
              </h3>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg border border-outline-variant hover:bg-surface-high text-on-surface-variant hover:text-on-surface transition-colors"
            title="Close viewer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Sender Info Bar */}
        <div className="px-6 py-3 border-b border-outline-variant/60 bg-surface flex items-center justify-between text-body-sm">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 text-primary font-mono font-bold text-xs flex items-center justify-center shrink-0">
              {getInitials(authorName)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-on-surface text-body-sm">{authorName}</span>
              </div>
              {evidence.metadata?.from && (
                <p className="text-[11px] text-on-surface-variant font-mono">
                  {String(evidence.metadata.from)}
                </p>
              )}
            </div>
          </div>

          {evidence.sourceUrl && (
            <a
              href={evidence.sourceUrl}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline px-3 py-1.5 rounded bg-surface-low border border-outline-variant/60 transition-colors"
            >
              <span>View Source</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>

        {/* Main Body Reader Container */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <div className="bg-surface-low border border-outline-variant/60 rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-outline-variant/40 pb-2">
              <span className="text-[10px] font-mono uppercase font-bold text-outline tracking-wider">
                {isGmail ? 'Full Email Body Payload' : 'Telemetry Event Content'}
              </span>
              {evidence.metadata?.email_id && (
                <span className="text-[10px] font-mono text-outline">
                  ID: {String(evidence.metadata.email_id)}
                </span>
              )}
            </div>

            <div className="text-body-sm text-on-surface leading-relaxed whitespace-pre-wrap font-sans">
              {bodyText}
            </div>
          </div>

          {/* Structured Metadata Collapsible / Badges */}
          {evidence.metadata && Object.keys(evidence.metadata).length > 0 && (
            <div className="space-y-2 pt-2">
              <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase font-semibold text-outline">
                <Tag className="w-3.5 h-3.5" />
                <span>Extracted Event Metadata</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(evidence.metadata).map(([key, val]) => {
                  if (key === 'body' || key === 'snippet') return null; // Already rendered in main container
                  return (
                    <div
                      key={key}
                      className="flex items-center gap-1.5 text-[11px] font-mono bg-surface-low border border-outline-variant/60 px-2 py-1 rounded text-on-surface-variant"
                    >
                      <span className="text-outline font-semibold">{key}:</span>
                      <span className="text-on-surface truncate max-w-[300px]">{String(val)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions Bar */}
        <div className="px-6 py-3 border-t border-outline-variant bg-surface-low flex items-center justify-between">
          <span className="text-[11px] font-mono text-outline">
            Evidence ID: {evidence.id}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-primary hover:bg-slate-800 text-white text-xs font-semibold rounded transition-colors"
          >
            Close Viewer
          </button>
        </div>

      </div>
    </div>
  );
};
