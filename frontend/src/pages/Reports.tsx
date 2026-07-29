import React, { useState } from 'react';
import { FileBarChart, Download, AlertCircle, ShieldAlert, Award, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { mapInvestigation } from '../lib/mappers';
import type { OperationalInvestigation } from '../types';

export const Reports: React.FC = () => {
  const [selectedReport, setSelectedReport] = useState<any | null>(null);
  // Fetch Live SLA Metrics from API
  const { data: digest, isLoading: isDigestLoading } = useQuery({
    queryKey: ['reports-digest'],
    queryFn: () => api.get('/reports/digest')
  });

  // Fetch Live Investigations to construct actual operational report items
  const { data: rawInvs, isLoading: isInvsLoading } = useQuery({
    queryKey: ['reports-investigations'],
    queryFn: () => api.get('/investigations/')
  });

  const investigations: OperationalInvestigation[] = (rawInvs || []).map(mapInvestigation);

  const reports = investigations.length > 0
    ? investigations.map((inv) => ({
        id: inv.id,
        title: `Post-Mortem: ${inv.title}`,
        type: (inv.severity === 'critical' ? 'Incident Post-Mortem' : inv.severity === 'high' ? 'Security Audit' : 'Weekly Digest') as any,
        date: inv.detectedAt ? new Date(inv.detectedAt).toISOString().split('T')[0] : '2026-07-27',
        impactSummary: inv.suggestedAction || inv.description || 'Assesses system root causes, telemetry logs, and remediation policies.'
      }))
    : [
        { 
          id: '1', 
          title: 'Q2 Authentication Services SLA Audit', 
          type: 'Security Audit' as const, 
          date: '2026-06-12', 
          impactSummary: 'Assesses Auth Gateway Redis connection spikes. Outlines 4 recommendations for branch configuration policies.' 
        },
        { 
          id: '2', 
          title: 'Weekly Operational Intelligence Digest - W24', 
          type: 'Weekly Digest' as const, 
          date: '2026-06-08', 
          impactSummary: 'Summarizes TechCorp customer escalation details, developer blockers velocity impact, and connected workspace sync status.' 
        }
      ];

  const handleExportPdf = (rep: { title: string; type: string; date: string; impactSummary: string }) => {
    const reportText = `==================================================
OPERATIONAL INTELLIGENCE REPORT
==================================================
Title: ${rep.title}
Report Type: ${rep.type}
Generated Date: ${rep.date}

EXECUTIVE SUMMARY & IMPACT:
--------------------------------------------------
${rep.impactSummary}

RECOMMENDED ACTIONS & SLA POLICY:
--------------------------------------------------
1. Conduct root cause verification across telemetry streams.
2. Ensure automated rollback scripts are verified against staging environment.
3. Review SLA response thresholds and update team escalation routing.

==================================================
Service Assistant Operational Intelligence Platform
`;

    const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${rep.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_report.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (isDigestLoading || isInvsLoading) {
    return (
      <div className="max-w-6xl mx-auto py-24 text-center font-mono text-xs text-on-surface-variant animate-pulse">
        Generating intelligence digest...
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant pb-4">
        <div>
          <h1 className="text-headline-lg text-on-surface">Operational Reports</h1>
          <p className="text-body-md text-on-surface-variant">
            Automated intelligence reports, SLA audits, and cross-platform post-mortems for your active organization.
          </p>
        </div>
      </div>

      {/* Live SLA Weekly Summary Metrics Dashboard */}
      {digest && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-white border border-[#C6C6CD] p-5 rounded-lg shadow-sm">
          {/* Card 1: Total Active */}
          <div className="space-y-1">
            <span className="text-[10px] uppercase font-bold text-outline font-mono block">Active Incidents</span>
            <div className="text-3xl font-bold text-[#0F172A]">{digest.total_active}</div>
            <p className="text-[11px] text-on-surface-variant">Currently under triage.</p>
          </div>

          {/* Card 2: SLA Breaches */}
          <div className="space-y-1 border-l-0 md:border-l border-[#C6C6CD] pl-0 md:pl-4">
            <span className="text-[10px] uppercase font-bold text-outline font-mono block flex items-center gap-1">
              <ShieldAlert className="w-3.5 h-3.5 text-error shrink-0" />
              SLA Breaches
            </span>
            <div className={`text-3xl font-bold ${digest.sla_breaches > 0 ? 'text-error' : 'text-on-surface'}`}>
              {digest.sla_breaches}
            </div>
            <p className="text-[11px] text-on-surface-variant">Critical action required.</p>
          </div>

          {/* Card 3: SLA Warnings */}
          <div className="space-y-1 border-l-0 md:border-l border-[#C6C6CD] pl-0 md:pl-4">
            <span className="text-[10px] uppercase font-bold text-outline font-mono block flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5 text-warning shrink-0" />
              SLA Warnings
            </span>
            <div className={`text-3xl font-bold ${digest.sla_warnings > 0 ? 'text-warning' : 'text-on-surface'}`}>
              {digest.sla_warnings}
            </div>
            <p className="text-[11px] text-on-surface-variant">Nearing response deadlines.</p>
          </div>

          {/* Card 4: Resolved last 7 days */}
          <div className="space-y-1 border-l-0 md:border-l border-[#C6C6CD] pl-0 md:pl-4">
            <span className="text-[10px] uppercase font-bold text-outline font-mono block flex items-center gap-1">
              <Award className="w-3.5 h-3.5 text-success shrink-0" />
              Resolved (7d)
            </span>
            <div className="text-3xl font-bold text-success">{digest.total_resolved_last_7_days}</div>
            <p className="text-[11px] text-on-surface-variant">Total closed anomalies.</p>
          </div>
        </div>
      )}

      {/* Reports Grid List */}
      <div className="space-y-4">
        {reports.map(rep => (
          <div 
            key={rep.id} 
            onClick={() => setSelectedReport(rep)}
            className="bg-surface border border-outline-variant rounded-lg p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-5 hover:border-slate-400 hover:shadow-sm transition-all cursor-pointer group"
          >
            
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-800 shrink-0 group-hover:bg-slate-900 group-hover:text-white transition-colors">
                <FileBarChart className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] uppercase font-bold text-slate-700 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded font-mono">
                    {rep.type}
                  </span>
                  <span className="text-mono-label text-[11px] text-slate-500 font-semibold">
                    Generated: {rep.date}
                  </span>
                </div>
                <h3 className="text-base font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  {rep.title}
                </h3>
                <p className="text-xs text-slate-600 mt-1.5 max-w-2xl line-clamp-2 leading-relaxed">
                  {rep.impactSummary}
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 shrink-0 w-full md:w-auto border-t md:border-t-0 border-outline-variant/40 pt-3 md:pt-0">
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedReport(rep);
                }}
                className="flex-1 md:flex-initial flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-bold text-slate-800 transition-colors shadow-2xs"
              >
                <span>Read Full Report</span>
              </button>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  handleExportPdf(rep);
                }}
                className="flex items-center justify-center p-1.5 rounded-lg border border-slate-300 bg-slate-900 hover:bg-slate-800 text-white transition-colors shadow-2xs"
                title="Export PDF / Text"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>

          </div>
        ))}
      </div>

      {/* Interactive Report Reader Modal */}
      {selectedReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs animate-fadeIn">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-200 bg-slate-900 text-white flex items-center justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-emerald-400 font-mono text-[10px] uppercase font-bold border border-slate-700">
                    {selectedReport.type}
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    {selectedReport.date}
                  </span>
                </div>
                <h3 className="text-lg font-extrabold text-slate-100">
                  {selectedReport.title}
                </h3>
              </div>
              <button 
                onClick={() => setSelectedReport(null)}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-5 text-slate-800">
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                <h4 className="text-xs font-bold font-mono text-slate-500 uppercase tracking-wider">
                  Executive Summary & Impact Breakdown
                </h4>
                <p className="text-sm leading-relaxed text-slate-800 font-sans">
                  {selectedReport.impactSummary}
                </p>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
                <h4 className="text-xs font-bold font-mono text-slate-500 uppercase tracking-wider">
                  Post-Mortem Policy & Recommendations
                </h4>
                <ol className="space-y-2 text-xs text-slate-700 font-sans">
                  <li className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-start gap-2">
                    <span className="px-1.5 py-0.5 rounded bg-slate-200 text-slate-900 font-mono font-bold shrink-0">1</span>
                    <span>Conduct automated root cause validation across telemetry streams before rolling out new deployments.</span>
                  </li>
                  <li className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-start gap-2">
                    <span className="px-1.5 py-0.5 rounded bg-slate-200 text-slate-900 font-mono font-bold shrink-0">2</span>
                    <span>Verify database connection pool thresholds and circuit breakers on upstream microservices.</span>
                  </li>
                  <li className="p-2.5 bg-white border border-slate-200 rounded-lg flex items-start gap-2">
                    <span className="px-1.5 py-0.5 rounded bg-slate-200 text-slate-900 font-mono font-bold shrink-0">3</span>
                    <span>Review escalation response SLAs with platform engineering on-call leads.</span>
                  </li>
                </ol>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between gap-3">
              <button 
                onClick={() => setSelectedReport(null)}
                className="px-4 py-2 rounded-lg border border-slate-300 text-xs font-bold text-slate-700 hover:bg-white transition-colors"
              >
                Close Reader
              </button>
              <button 
                onClick={() => handleExportPdf(selectedReport)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition-colors shadow-sm"
              >
                <Download className="w-4 h-4 text-slate-300" />
                <span>Export Report Document</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
