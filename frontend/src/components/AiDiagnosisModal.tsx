import React, { useState } from 'react';
import { 
  X, 
  Cpu, 
  Sparkles, 
  Copy, 
  Check, 
  MessageSquare, 
  ExternalLink, 
  CheckCircle2, 
  Layers
} from 'lucide-react';
import type { Evidence } from '../types';
import { MarkdownRenderer } from './MarkdownRenderer';

interface AiDiagnosisModalProps {
  isOpen: boolean;
  onClose: () => void;
  investigationTitle: string;
  severity: string;
  suggestedAction?: string;
  evidenceList: Evidence[];
  onRunDiagnosis: () => Promise<void>;
  isDiagnosing: boolean;
  onShareSlack: () => Promise<void>;
  isSharingSlack: boolean;
  slackPostedChannel: string | null;
  onEscalateJira: () => Promise<void>;
  isEscalatingJira: boolean;
  jiraTicket: { key: string; url: string } | null;
}

export const AiDiagnosisModal: React.FC<AiDiagnosisModalProps> = ({
  isOpen,
  onClose,
  investigationTitle,
  severity,
  suggestedAction,
  evidenceList,
  onRunDiagnosis,
  isDiagnosing,
  onShareSlack,
  isSharingSlack,
  slackPostedChannel,
  onEscalateJira,
  isEscalatingJira,
  jiraTicket
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = () => {
    if (!suggestedAction) return;
    navigator.clipboard.writeText(suggestedAction);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical': return 'bg-red-500/10 text-red-700 border-red-200';
      case 'high': return 'bg-amber-500/10 text-amber-700 border-amber-200';
      case 'medium': return 'bg-blue-500/10 text-blue-700 border-blue-200';
      default: return 'bg-slate-500/10 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white border border-slate-200 rounded-xl shadow-2xl w-full max-w-3xl flex flex-col max-h-[85vh] overflow-hidden">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-900 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              <Sparkles className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono tracking-wider text-indigo-400 uppercase font-bold">
                  AI Forensic Engine
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getSeverityBadgeClass(severity)}`}>
                  {severity}
                </span>
              </div>
              <h2 className="text-base font-semibold text-slate-100 truncate max-w-lg">
                {investigationTitle}
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Evidence Overview Bar */}
        <div className="px-6 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs text-slate-600 font-mono">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-slate-400" />
            <span>Correlated Telemetry: <strong>{evidenceList.length} evidence logs</strong></span>
          </div>
          <div className="flex items-center gap-3">
            {Array.from(new Set(evidenceList.map(e => e.type))).map(type => (
              <span key={type} className="px-2 py-0.5 rounded bg-slate-200/60 text-slate-700 text-[10px] uppercase font-bold">
                {type}
              </span>
            ))}
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {isDiagnosing ? (
            <div className="py-16 flex flex-col items-center justify-center text-center space-y-4">
              <div className="relative">
                <div className="w-14 h-14 rounded-full border-4 border-indigo-100 border-t-indigo-600 animate-spin" />
                <Cpu className="w-6 h-6 text-indigo-600 absolute inset-0 m-auto" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-900">Synthesizing Incident Evidence</h4>
                <p className="text-xs text-slate-500 font-mono mt-1">
                  Correlating {evidenceList.length} telemetry logs across Slack, Jira, GitHub, and Gmail via GPT-4o...
                </p>
              </div>
            </div>
          ) : suggestedAction ? (
            <div className="space-y-4">
              {/* Report Header Bar */}
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4.5 h-4.5 text-emerald-600" />
                  <span className="text-xs font-bold font-mono text-slate-700 uppercase tracking-wider">
                    Root Cause Diagnosis Report
                  </span>
                </div>

                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 rounded border border-slate-200 hover:bg-slate-50 transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
                </button>
              </div>

              {/* Formatted Report Payload */}
              <MarkdownRenderer content={suggestedAction} className="bg-slate-50/50 p-5 rounded-lg border border-slate-200/80" />
            </div>
          ) : (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-4 bg-slate-50 rounded-xl border border-dashed border-slate-200">
              <div className="p-3 rounded-full bg-indigo-50 text-indigo-600">
                <Sparkles className="w-8 h-8" />
              </div>
              <div className="max-w-md">
                <h4 className="text-sm font-bold text-slate-900">Generate Incident Root Cause Analysis</h4>
                <p className="text-xs text-slate-500 mt-1">
                  Click below to trigger automated LLM forensic synthesis across all {evidenceList.length} correlated telemetry logs.
                </p>
              </div>
              <button
                onClick={onRunDiagnosis}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg transition-colors shadow flex items-center gap-2"
              >
                <Cpu className="w-4 h-4" />
                <span>Run AI Forensics</span>
              </button>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex flex-wrap items-center justify-between gap-3 shrink-0">
          <button
            onClick={onRunDiagnosis}
            disabled={isDiagnosing}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 hover:text-slate-900 border border-slate-200 hover:bg-white rounded-lg transition-colors disabled:opacity-50"
          >
            <Sparkles className={`w-4 h-4 text-indigo-600 ${isDiagnosing ? 'animate-spin' : ''}`} />
            <span>{isDiagnosing ? 'Re-running...' : 'Re-Run Diagnostics'}</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={onShareSlack}
              disabled={isSharingSlack || !!slackPostedChannel || !suggestedAction}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold text-white rounded-lg bg-[#4A154B] hover:bg-[#3b113c] transition-colors disabled:opacity-50 shadow-sm"
            >
              <MessageSquare className="w-4 h-4" />
              <span>
                {isSharingSlack ? 'Sharing...' : slackPostedChannel ? `Shared to ${slackPostedChannel}` : 'Share to Slack'}
              </span>
            </button>

            <button
              onClick={onEscalateJira}
              disabled={isEscalatingJira || !!jiraTicket || !suggestedAction}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold text-white rounded-lg bg-[#0052CC] hover:bg-[#0041a3] transition-colors disabled:opacity-50 shadow-sm"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>
                {isEscalatingJira ? 'Escalating...' : jiraTicket ? `Jira Ticket: ${jiraTicket.key}` : 'Escalate to Jira'}
              </span>
            </button>

            {jiraTicket && (
              <a
                href={jiraTicket.url}
                target="_blank"
                rel="noreferrer"
                className="p-2 text-slate-600 hover:text-indigo-600 transition-colors"
                title="View Jira Ticket"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
