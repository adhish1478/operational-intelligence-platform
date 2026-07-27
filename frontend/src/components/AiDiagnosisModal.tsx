import React, { useState } from 'react';
import { 
  X, 
  Cpu, 
  Copy, 
  Check, 
  MessageSquare, 
  ExternalLink, 
  CheckCircle2, 
  Layers,
  GitCommit,
  DollarSign,
  Terminal,
  UserCheck
} from 'lucide-react';
import type { Evidence } from '../types';
import { MarkdownRenderer } from './MarkdownRenderer';

interface AiDiagnosisModalProps {
  isOpen: boolean;
  onClose: () => void;
  investigationTitle: string;
  severity: string;
  suggestedAction?: string;
  technicalRca?: any;
  businessImpact?: any;
  remediationPlan?: any;
  orchestrationMetadata?: any;
  evidenceList: Evidence[];
  currentStepIndex?: number;
  activeStepText?: string;
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
  technicalRca,
  businessImpact,
  remediationPlan,
  evidenceList,
  currentStepIndex = 0,
  activeStepText = '',
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
  const [copiedCommand, setCopiedCommand] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'technical' | 'business' | 'remediation'>('overview');

  if (!isOpen) return null;

  const handleCopy = () => {
    if (!suggestedAction) return;
    navigator.clipboard.writeText(suggestedAction);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyCommand = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedCommand(true);
    setTimeout(() => setCopiedCommand(false), 2000);
  };

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical': return 'bg-red-500/10 text-red-700 border-red-200';
      case 'high': return 'bg-amber-500/10 text-amber-700 border-amber-200';
      case 'medium': return 'bg-blue-500/10 text-blue-700 border-blue-200';
      default: return 'bg-slate-500/10 text-slate-700 border-slate-200';
    }
  };

  const getSlaBadgeClass = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'BREACHED': return 'bg-red-600 text-white';
      case 'IMMINENT_RISK': return 'bg-amber-600 text-white';
      case 'AT_RISK': return 'bg-yellow-600 text-white';
      default: return 'bg-emerald-600 text-white';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white border border-slate-200 rounded-xl shadow-2xl w-full max-w-4xl flex flex-col max-h-[90vh] overflow-hidden">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-900 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-slate-800 text-slate-200 border border-slate-700">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-[10px] font-mono tracking-wider text-slate-400 uppercase font-bold">
                  AI Forensics Analysis
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${getSeverityBadgeClass(severity)}`}>
                  {severity}
                </span>
              </div>
              <h2 className="text-base font-semibold text-slate-100 truncate max-w-xl">
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

        {/* Evidence Overview & Navigation Bar */}
        <div className="px-6 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs text-slate-600 font-mono">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-slate-400" />
            <span>Correlated Streams: <strong>{evidenceList.length} evidence logs</strong></span>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-1 bg-slate-200/70 p-1 rounded-lg">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-3 py-1 rounded text-xs font-sans font-medium transition-all ${activeTab === 'overview' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
            >
              Unified Overview
            </button>
            {technicalRca && (
              <button
                onClick={() => setActiveTab('technical')}
                className={`px-3 py-1 rounded text-xs font-sans font-medium transition-all ${activeTab === 'technical' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
              >
                Technical RCA
              </button>
            )}
            {businessImpact && (
              <button
                onClick={() => setActiveTab('business')}
                className={`px-3 py-1 rounded text-xs font-sans font-medium transition-all ${activeTab === 'business' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
              >
                Business Impact
              </button>
            )}
            {remediationPlan && (
              <button
                onClick={() => setActiveTab('remediation')}
                className={`px-3 py-1 rounded text-xs font-sans font-medium transition-all ${activeTab === 'remediation' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
              >
                Hotfix & Action
              </button>
            )}
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {isDiagnosing ? (
            <div className="py-8 px-4 flex flex-col items-center justify-center text-center max-w-xl mx-auto space-y-6">
              {/* Header */}
              <div className="flex flex-col items-center space-y-2.5">
                <div className="relative flex items-center justify-center">
                  <div className="w-14 h-14 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
                  <Cpu className="w-5 h-5 text-slate-800 absolute" />
                </div>
                <div>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-slate-800 text-xs font-semibold mb-1.5">
                    <Cpu className="w-3.5 h-3.5 text-slate-700" />
                    <span>Forensics Analysis Active</span>
                  </div>
                  <h4 className="text-base font-bold text-slate-900">Analyzing Incident Telemetry</h4>
                  <p className="text-xs text-slate-500 max-w-md">
                    Cross-correlating code commits, error logs, and business impact...
                  </p>
                </div>
              </div>

              {/* Progress Stepper Card */}
              <div className="w-full bg-slate-50/80 border border-slate-200/90 rounded-xl p-4 shadow-sm space-y-3.5 text-left">
                {/* Smooth Progress Bar */}
                <div className="w-full bg-slate-200/70 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-slate-800 h-full transition-all duration-700 ease-out rounded-full"
                    style={{ width: `${Math.min(100, Math.max(15, ((currentStepIndex + 1) / 4) * 100))}%` }}
                  />
                </div>

                {/* 4 Steps Timeline */}
                <div className="space-y-2.5 pt-1">
                  {[
                    { title: 'Correlating Telemetry', desc: 'Gathering GitHub, Jira & alert evidence streams' },
                    { title: 'Root Cause & Code Analysis', desc: 'Pinpointing offending commits and error stack traces' },
                    { title: 'Business Risk Assessment', desc: 'Calculating downtime cost ($/hr) and SLA impact' },
                    { title: 'Synthesizing Hotfix Plan', desc: 'Generating automated rollback commands and mitigation steps' }
                  ].map((step, idx) => {
                    const isDone = currentStepIndex > idx;
                    const isCurrent = currentStepIndex === idx;

                    return (
                      <div 
                        key={idx} 
                        className={`flex items-center gap-3 p-2.5 rounded-lg transition-all duration-500 ${
                          isCurrent ? 'bg-white border border-slate-300 shadow-sm' : 
                          isDone ? 'bg-slate-100/50 opacity-90' : 'opacity-40'
                        }`}
                      >
                        <div className="shrink-0">
                          {isDone ? (
                            <div className="w-5.5 h-5.5 rounded-full bg-emerald-600 text-white flex items-center justify-center shadow-sm">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                            </div>
                          ) : isCurrent ? (
                            <div className="w-5.5 h-5.5 rounded-full bg-slate-900 text-white flex items-center justify-center shadow-md animate-pulse">
                              <span className="text-[11px] font-bold">{idx + 1}</span>
                            </div>
                          ) : (
                            <div className="w-5.5 h-5.5 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center text-[11px] font-medium">
                              {idx + 1}
                            </div>
                          )}
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <h5 className={`text-xs font-bold ${isCurrent ? 'text-slate-900' : 'text-slate-800'}`}>
                              {step.title}
                            </h5>
                            {isCurrent && (
                              <span className="text-[10px] font-semibold text-slate-700 animate-pulse bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-full">
                                In Progress...
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-500 truncate mt-0.5">
                            {isCurrent && activeStepText ? activeStepText : step.desc}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (suggestedAction || technicalRca) ? (
            <div>
              {/* Tab 1: Unified Overview (Markdown) */}
              {activeTab === 'overview' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4.5 h-4.5 text-emerald-600" />
                      <span className="text-xs font-bold font-mono text-slate-700 uppercase tracking-wider">
                        Consolidated Analysis Report
                      </span>
                    </div>

                    <button
                      onClick={handleCopy}
                      className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 rounded border border-slate-200 hover:bg-slate-50 transition-colors"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copied ? 'Copied' : 'Copy Report Markdown'}</span>
                    </button>
                  </div>

                  <MarkdownRenderer content={suggestedAction || technicalRca?.root_cause_summary || ''} className="bg-slate-50/50 p-5 rounded-lg border border-slate-200/80" />
                </div>
              )}

              {/* Tab 2: Technical RCA Agent View */}
              {activeTab === 'technical' && technicalRca && (
                <div className="space-y-5">
                  <div className="p-4 bg-slate-900 text-slate-100 rounded-xl space-y-3">
                    <div className="flex items-center gap-2 text-indigo-400 text-xs font-mono font-bold uppercase">
                      <Cpu className="w-4 h-4" />
                      <span>Technical Root Cause Summary</span>
                    </div>
                    <p className="text-sm text-slate-200 leading-relaxed font-sans">
                      {technicalRca.root_cause_summary}
                    </p>
                  </div>

                  {technicalRca.offending_commit && (
                    <div className="p-4 bg-amber-500/5 border border-amber-500/20 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-amber-700 uppercase font-mono flex items-center gap-1.5">
                          <GitCommit className="w-4 h-4" /> Offending Commit Details
                        </span>
                        <code className="text-xs font-mono font-bold bg-amber-100 text-amber-900 px-2 py-0.5 rounded">
                          {technicalRca.offending_commit.hash || 'HEAD~1'}
                        </code>
                      </div>
                      <p className="text-xs text-slate-700"><strong>Author:</strong> {technicalRca.offending_commit.author || 'Unknown'}</p>
                      <p className="text-xs text-slate-700"><strong>Message:</strong> {technicalRca.offending_commit.message}</p>
                      {technicalRca.offending_commit.diff_summary && (
                        <p className="text-xs font-mono bg-white p-2 rounded border border-amber-200 text-slate-800">
                          {technicalRca.offending_commit.diff_summary}
                        </p>
                      )}
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                      <h5 className="text-xs font-bold text-slate-700 font-mono uppercase">Impacted Services</h5>
                      <div className="flex flex-wrap gap-1.5">
                        {technicalRca.impacted_services?.map((srv: string) => (
                          <span key={srv} className="px-2 py-1 rounded bg-slate-200 text-slate-800 border border-slate-300 text-xs font-mono font-bold">
                            {srv}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                      <h5 className="text-xs font-bold text-slate-700 font-mono uppercase">Error Signatures</h5>
                      <div className="flex flex-wrap gap-1.5">
                        {technicalRca.error_fingerprints?.map((fp: string) => (
                          <span key={fp} className="px-2 py-1 rounded bg-red-50 text-red-700 border border-red-200 text-xs font-mono font-bold">
                            {fp}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: Business Impact & SLA Assessment Panel */}
              {activeTab === 'business' && businessImpact && (
                <div className="space-y-5">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 bg-red-50/70 border border-red-200 rounded-xl space-y-1">
                      <span className="text-[10px] font-mono text-red-600 font-bold uppercase">Financial Exposure</span>
                      <div className="text-2xl font-black text-red-900 font-mono flex items-center">
                        <DollarSign className="w-5 h-5 text-red-600" />
                        {businessImpact.estimated_downtime_cost_per_hour?.toLocaleString()}/hr
                      </div>
                    </div>

                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                      <span className="text-[10px] font-mono text-slate-500 font-bold uppercase">SLA Compliance Status</span>
                      <div>
                        <span className={`inline-block px-2.5 py-1 rounded text-xs font-mono font-bold uppercase ${getSlaBadgeClass(businessImpact.sla_breach_status)}`}>
                          {businessImpact.sla_breach_status}
                        </span>
                      </div>
                    </div>

                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                      <span className="text-[10px] font-mono text-slate-500 font-bold uppercase">Financial Risk Level</span>
                      <div className="text-lg font-bold text-slate-800 font-mono">
                        {businessImpact.financial_risk_level}
                      </div>
                    </div>
                  </div>

                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                    <h5 className="text-xs font-bold text-slate-700 font-mono uppercase flex items-center gap-1.5">
                      <UserCheck className="w-4 h-4 text-slate-700" /> Affected Customer Tiers
                    </h5>
                    <div className="space-y-2">
                      {businessImpact.affected_customer_tiers?.map((ct: any, idx: number) => (
                        <div key={idx} className="p-3 bg-white border border-slate-200 rounded-lg flex items-center justify-between text-xs">
                          <div>
                            <span className="font-bold text-slate-900">{ct.tier}</span>
                            <p className="text-slate-500 mt-0.5">{ct.impact_summary}</p>
                          </div>
                          <span className="px-2 py-1 bg-slate-100 text-slate-800 border border-slate-200 font-mono font-bold rounded">
                            {ct.account_count} Tenant Accounts
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 4: Remediation Plan Panel */}
              {activeTab === 'remediation' && remediationPlan && (
                <div className="space-y-5">
                  <div className="p-4 bg-slate-900 text-slate-100 rounded-xl space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-emerald-400 uppercase flex items-center gap-1.5">
                        <Terminal className="w-4 h-4" /> Git Rollback Command
                      </span>
                      <button
                        onClick={() => handleCopyCommand(remediationPlan.git_rollback_command)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-mono transition-colors flex items-center gap-1"
                      >
                        {copiedCommand ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedCommand ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                    <pre className="p-3 bg-black rounded-lg text-emerald-400 font-mono text-xs overflow-x-auto border border-slate-800">
                      {remediationPlan.git_rollback_command}
                    </pre>
                  </div>

                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                    <h5 className="text-xs font-bold text-slate-700 font-mono uppercase">Immediate Mitigation Steps</h5>
                    <ol className="space-y-2 text-xs text-slate-700 font-sans">
                      {remediationPlan.immediate_mitigation_steps?.map((step: string, idx: number) => (
                        <li key={idx} className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-start gap-2">
                          <span className="px-1.5 py-0.5 rounded bg-slate-200 text-slate-900 font-mono font-bold shrink-0">{idx + 1}</span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>

                  {remediationPlan.verification_script && (
                    <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                      <h5 className="text-xs font-bold text-slate-700 font-mono uppercase">Verification Command Check</h5>
                      <pre className="p-3 bg-slate-900 text-slate-200 rounded-lg font-mono text-xs overflow-x-auto">
                        {remediationPlan.verification_script}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-4 bg-slate-50 rounded-xl border border-dashed border-slate-200">
              <div className="p-3 rounded-full bg-slate-100 text-slate-800 border border-slate-200">
                <Cpu className="w-8 h-8" />
              </div>
              <div className="max-w-md">
                <h4 className="text-sm font-bold text-slate-900">Run AI Forensics Analysis</h4>
                <p className="text-xs text-slate-500 mt-1">
                  Correlates evidence logs, code commits, and calculates business SLA impact.
                </p>
              </div>
              <button
                onClick={onRunDiagnosis}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs rounded-lg transition-colors shadow flex items-center gap-2"
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
            <Cpu className={`w-4 h-4 text-slate-700 ${isDiagnosing ? 'animate-spin' : ''}`} />
            <span>{isDiagnosing ? 'Re-running...' : 'Re-Run Diagnostics'}</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={onShareSlack}
              disabled={isSharingSlack || !!slackPostedChannel || !(suggestedAction || technicalRca)}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold text-white rounded-lg bg-[#4A154B] hover:bg-[#3b113c] transition-colors disabled:opacity-50 shadow-sm"
            >
              <MessageSquare className="w-4 h-4" />
              <span>
                {isSharingSlack ? 'Sharing...' : slackPostedChannel ? `Shared to ${slackPostedChannel}` : 'Share to Slack'}
              </span>
            </button>

            <button
              onClick={onEscalateJira}
              disabled={isEscalatingJira || !!jiraTicket || !(suggestedAction || technicalRca)}
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
