import React, { useState } from 'react';
import { FileBarChart, Download, Plus } from 'lucide-react';

interface ReportItem {
  id: string;
  title: string;
  type: 'Weekly Digest' | 'Incident Summary' | 'Security Audit';
  date: string;
  impactSummary: string;
}

export const Reports: React.FC = () => {
  const [reports] = useState<ReportItem[]>([
    { id: '1', title: 'Q2 Authentication Services SLA Audit', type: 'Security Audit', date: '2026-06-12', impactSummary: 'Assesses Auth Gateway Redis connection spikes. Outlines 4 recommendations for branch configuration policies.' },
    { id: '2', title: 'Weekly Operational Intelligence Digest - W24', type: 'Weekly Digest', date: '2026-06-08', impactSummary: 'Summarizes TechCorp customer escalation details, developer blockers velocity impact, and connected workspace sync metrics.' },
    { id: '3', title: 'Major Incident Post-Mortem: Auth Spikes', type: 'Incident Summary', date: '2026-06-02', impactSummary: 'Full timeline breakdown of Redis handshake timeout outages affecting customer logins. Identifies pool size gaps.' }
  ]);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant pb-4">
        <div>
          <h1 className="text-headline-lg text-on-surface">Operational Reports</h1>
          <p className="text-body-md text-on-surface-variant">
            Automated intelligence reports, SLA audits, and cross-platform post-mortems.
          </p>
        </div>
      </div>

      {/* Reports Grid List */}
      <div className="space-y-4">
        {reports.map(rep => (
          <div key={rep.id} className="bg-surface border border-outline-variant rounded-lg p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-5 hover:border-outline transition-colors">
            
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded bg-surface-low border border-outline-variant flex items-center justify-center text-secondary shrink-0">
                <FileBarChart className="w-5.5 h-5.5" />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] uppercase font-bold text-outline-variant bg-surface-container border border-outline-variant px-1.5 py-0.2 rounded font-mono">
                    {rep.type}
                  </span>
                  <span className="text-mono-label text-[11px] text-outline">
                    Generated: {rep.date}
                  </span>
                </div>
                <h3 className="text-headline-sm font-semibold text-on-surface hover:text-primary transition-colors cursor-pointer">
                  {rep.title}
                </h3>
                <p className="text-body-sm text-on-surface-variant mt-1.5 max-w-2xl">
                  {rep.impactSummary}
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 shrink-0 w-full md:w-auto border-t md:border-t-0 border-outline-variant/40 pt-3 md:pt-0">
              <button className="flex-1 md:flex-initial flex items-center justify-center gap-1.5 px-3 py-1.5 rounded border border-outline-variant hover:bg-surface-high text-body-sm font-semibold text-on-surface transition-colors">
                <Download className="w-4 h-4" />
                <span>Export PDF</span>
              </button>
              <button className="flex-1 md:flex-initial flex items-center justify-center gap-1.5 px-3 py-1.5 rounded bg-primary hover:bg-slate-800 text-white text-body-sm font-semibold transition-colors">
                <Plus className="w-4 h-4" />
                <span>Triage Items</span>
              </button>
            </div>

          </div>
        ))}
      </div>

    </div>
  );
};
