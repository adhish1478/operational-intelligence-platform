import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, ArrowUpRight } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { mapInvestigation } from '../lib/mappers';
import type { Severity, InvestigationStatus, OperationalInvestigation } from '../types';

export const InvestigationsQueue: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const { data: rawInvs, isLoading } = useQuery({
    queryKey: ['investigations'],
    queryFn: () => api.get('/investigations/')
  });

  const investigations: OperationalInvestigation[] = (rawInvs || []).map(mapInvestigation);

  const getSeverityBadgeClass = (severity: Severity) => {
    switch (severity) {
      case 'critical': return 'badge-critical';
      case 'high': return 'badge-warning';
      case 'medium': return 'badge-info';
      default: return 'badge-info';
    }
  };

  const getStatusBadgeClass = (status: InvestigationStatus) => {
    switch (status) {
      case 'open': return 'bg-error/10 text-error';
      case 'investigating': return 'bg-warning/10 text-warning';
      case 'resolved': return 'bg-success/10 text-success';
      case 'closed': return 'bg-slate-200 text-slate-700 font-semibold';
      default: return 'bg-slate-100 text-slate-600';
    }
  };

  // Filter investigations
  const filteredInvestigations = investigations.filter((inv: OperationalInvestigation) => {
    const matchesSearch = inv.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          inv.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          inv.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSeverity = severityFilter === 'all' || inv.severity === severityFilter;
    const matchesStatus = statusFilter === 'all' || inv.status === statusFilter;
    return matchesSearch && matchesSeverity && matchesStatus;
  });

  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto py-24 text-center font-mono text-xs text-on-surface-variant animate-pulse">
        Loading investigations...
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant pb-4">
        <div>
          <h1 className="text-headline-lg text-on-surface">Investigations Queue</h1>
          <p className="text-body-md text-on-surface-variant">
            Analyze and triage critical security, performance, and process risks.
          </p>
        </div>
        
        {/* Count Stats summary */}
        <div className="flex items-center gap-4 text-body-sm">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-error animate-pulse" />
            <span className="text-on-surface font-semibold">
              {investigations.filter((i: OperationalInvestigation) => i.status === 'open').length} Open
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-warning" />
            <span className="text-on-surface font-semibold">
              {investigations.filter((i: OperationalInvestigation) => i.status === 'investigating').length} Triaging
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-success" />
            <span className="text-on-surface font-semibold">
              {investigations.filter((i: OperationalInvestigation) => i.status === 'resolved').length} Resolved
            </span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-surface border border-outline-variant rounded-lg p-3 flex flex-col md:flex-row gap-3">
        {/* Search */}
        <div className="flex-1 flex items-center gap-2 px-2.5 py-1.5 rounded bg-surface-low border border-outline-variant/60 text-body-sm">
          <Search className="w-4 h-4 text-outline" />
          <input
            type="text"
            placeholder="Search queue by title, summary details, or id..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 bg-transparent border-0 outline-none text-on-surface placeholder-outline focus:ring-0"
          />
        </div>

        {/* Severity filter tabs */}
        <div className="flex items-center gap-1">
          {['all', 'critical', 'high', 'medium'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-2.5 py-1.5 rounded text-[11px] font-semibold uppercase tracking-wider transition-colors ${
                severityFilter === sev
                  ? 'bg-primary text-white'
                  : 'text-on-surface-variant hover:bg-surface-low hover:text-on-surface'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>

        {/* Status filter tabs */}
        <div className="flex items-center gap-1 border-l border-outline-variant pl-3">
          {['all', 'open', 'investigating', 'resolved', 'closed'].map((stat) => (
            <button
              key={stat}
              onClick={() => setStatusFilter(stat)}
              className={`px-2.5 py-1.5 rounded text-[11px] font-semibold uppercase tracking-wider transition-colors ${
                statusFilter === stat
                  ? 'bg-secondary text-white'
                  : 'text-on-surface-variant hover:bg-surface-low hover:text-on-surface'
              }`}
            >
              {stat}
            </button>
          ))}
        </div>
      </div>

      {/* Investigations Table (High Density) */}
      <div className="bg-surface border border-outline-variant rounded-lg overflow-hidden">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-outline-variant bg-surface-low text-label-caps text-on-surface-variant uppercase font-semibold">
              <th className="px-4 py-3 font-bold">id</th>
              <th className="px-4 py-3 font-bold">investigation</th>
              <th className="px-4 py-3 font-bold">owner</th>
              <th className="px-4 py-3 font-bold">created</th>
              <th className="px-4 py-3 font-bold">exposure</th>
              <th className="px-4 py-3 font-bold">severity</th>
              <th className="px-4 py-3 font-bold">status</th>
              <th className="px-4 py-3 font-bold text-right">actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredInvestigations.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-body-sm text-on-surface-variant italic">
                  No active investigations found matching current filter rules.
                </td>
              </tr>
            ) : (
              filteredInvestigations.map((inv: OperationalInvestigation) => (
                <tr 
                  key={inv.id} 
                  className="border-b border-outline-variant/60 hover:bg-surface-low transition-colors align-middle text-body-sm text-on-surface group"
                >
                  {/* ID */}
                  <td className="px-4 py-3 font-mono text-mono-label text-on-surface-variant">
                    {inv.id.substring(0, 8)}
                  </td>
                  
                  {/* Title and details */}
                  <td className="px-4 py-3">
                    <div className="font-semibold group-hover:text-primary transition-colors">
                      <Link to={`/investigations/${inv.id}`} className="hover:underline">
                        {inv.title}
                      </Link>
                    </div>
                    <div className="text-[11px] text-on-surface-variant line-clamp-1 mt-0.5 max-w-sm">
                      {inv.description}
                    </div>
                  </td>

                  {/* Owner */}
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700">
                      <span>Unassigned</span>
                    </span>
                  </td>

                  {/* Created Time */}
                  <td className="px-4 py-3 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                    {inv.detectedAt ? new Date(inv.detectedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '14m ago'}
                  </td>

                  {/* Financial Exposure */}
                  <td className="px-4 py-3 font-mono text-[11px] font-bold text-slate-800 whitespace-nowrap">
                    {inv.severity === 'critical' ? '$124.5k/hr' : inv.severity === 'high' ? '$15.0k/hr' : 'Nominal'}
                  </td>
                  
                  {/* Severity */}
                  <td className="px-4 py-3">
                    <span className={getSeverityBadgeClass(inv.severity)}>
                      {inv.severity.toUpperCase()}
                    </span>
                  </td>
                  
                  {/* Status */}
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${getStatusBadgeClass(inv.status)}`}>
                      {inv.status}
                    </span>
                  </td>
                  
                  {/* Action */}
                  <td className="px-4 py-3 text-right">
                    <Link 
                      to={`/investigations/${inv.id}?autoDiagnose=true`}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-primary hover:underline"
                    >
                      <span>Diagnose</span>
                      <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
