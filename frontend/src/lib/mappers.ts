import type { OperationalInvestigation, Evidence, Severity, InvestigationStatus } from '../types';

export const mapInvestigation = (inv: any): OperationalInvestigation => {
  return {
    id: inv.id,
    title: inv.title,
    description: inv.description || '',
    severity: (inv.severity || 'medium') as Severity,
    status: (inv.status || 'open') as InvestigationStatus,
    category: 'security',
    sourceSystems: ['slack', 'github'],
    detectedAt: inv.detected_at || new Date().toISOString(),
    suggestedAction: inv.suggestion_action || '',
    evidence: [],
    entities: []
  };
};

export const mapEvidence = (ev: any): Evidence => {
  return {
    id: ev.id,
    type: ev.type || 'alert',
    timestamp: ev.created_at || new Date().toISOString(),
    sourceUrl: ev.source_url || '',
    summary: ev.summary || '',
    author: {
      name: ev.author_name || 'System'
    },
    metadata: ev.metadata || {}
  };
};
