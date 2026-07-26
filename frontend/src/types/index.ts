export type Severity = 'low' | 'medium' | 'high' | 'critical';
export type InvestigationStatus = 'open' | 'investigating' | 'resolved' | 'closed';
export type InvestigationCategory = 'launch_delay' | 'customer_escalation' | 'revenue_risk' | 'team_blocker' | 'security';
export type SourceSystem = 'slack' | 'jira' | 'gmail' | 'github' | 'notion';

export interface Evidence {
  id: string;
  type: 'gmail' | 'slack' | 'jira' | 'github' | 'email' | 'notion';
  timestamp: string;
  sourceUrl: string;
  summary: string;
  author: { name: string; avatar?: string };
  metadata: Record<string, string | number | boolean>;
}

export interface EntityReference {
  type: 'customer' | 'project' | 'team' | 'service';
  id: string;
  name: string;
}

export interface OperationalInvestigation {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  status: InvestigationStatus;
  category: InvestigationCategory;
  sourceSystems: SourceSystem[];
  assignedTo?: {
    name: string;
    avatar: string;
  };
  detectedAt: string;
  suggestedAction: string;
  evidence: Evidence[];
  entities: EntityReference[];
}

export interface User {
  id: string;
  name: string;
  email: string;
  avatar: string;
  role: 'admin' | 'viewer';
}
