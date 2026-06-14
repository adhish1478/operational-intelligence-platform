export type Severity = 'low' | 'medium' | 'high' | 'critical';
export type IssueStatus = 'open' | 'investigating' | 'resolved';
export type IssueCategory = 'launch_delay' | 'customer_escalation' | 'revenue_risk' | 'team_blocker' | 'security';
export type SourceSystem = 'slack' | 'jira' | 'gmail' | 'github';

export interface OperationalIssue {
    id: string;
    title: string;
    description: string;
    severity: Severity;
    status: IssueStatus;
    category: IssueCategory;
    sourceSystems: SourceSystem[];
    assignedTo?: {
        name: string;
        avatar: string;
    };
    detectedAt: string;
    suggestedAction: string;
}

export interface User {
    id: string;
    name: string;
    email: string;
    avatar: string;
    role: 'admin' | 'viewer';
}
