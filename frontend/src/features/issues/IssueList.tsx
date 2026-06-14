import React from 'react';
import { IssueCard } from './IssueCard';
import type { OperationalIssue } from '../../types';

const MOCK_ISSUES: OperationalIssue[] = [
    {
        id: '1',
        title: 'Launch Delay: User Auth Feature',
        description: 'Sprint velocity has dropped by 40% in the last 48 hours. Three key Jira tickets are currently stuck in "Code Review" for more than 24 hours.',
        severity: 'critical',
        status: 'open',
        category: 'launch_delay',
        sourceSystems: ['jira', 'slack'],
        detectedAt: '2h ago',
        suggestedAction: 'Escalate to Engineering Lead to unblock code reviews.'
    },
    {
        id: '2',
        title: 'Customer Escalation: Acme Corp',
        description: 'High-priority message in #customer-success-acme mentioning potential churn due to unresolved API latency issues.',
        severity: 'high',
        status: 'investigating',
        category: 'customer_escalation',
        sourceSystems: ['slack', 'gmail'],
        detectedAt: '4h ago',
        suggestedAction: 'Link Slack thread to Jira issue #LAT-452 and assign to API team.'
    },
    {
        id: '3',
        title: 'Security Risk: Unreviewed PR',
        description: 'New PR #245 in "service-gateway" modifies the authentication middleware without a required security review from Sr. Security Engineer.',
        severity: 'medium',
        status: 'open',
        category: 'security',
        sourceSystems: ['github'],
        detectedAt: '6h ago',
        suggestedAction: 'Trigger automated security scan and ping @security-ops.'
    },
    {
        id: '4',
        title: 'Revenue Risk: Stripe Webhook Failures',
        description: 'Detected a 15% increase in failed payment webhooks. Discrepancy found between Stripe logs and Gmail support tickets.',
        severity: 'high',
        status: 'open',
        category: 'revenue_risk',
        sourceSystems: ['gmail', 'slack'],
        detectedAt: '1h ago',
        suggestedAction: 'Check CloudWatch logs for recent deployment errors in the billing service.'
    }
];

export const IssueList: React.FC = () => {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {MOCK_ISSUES.map((issue) => (
                <IssueCard
                    key={issue.id}
                    id={issue.id}
                    title={issue.title}
                    description={issue.description}
                    severity={issue.severity}
                    sources={issue.sourceSystems}
                    detectedAt={issue.detectedAt}
                    suggestedAction={issue.suggestedAction}
                />
            ))}
        </div>
    );
};
