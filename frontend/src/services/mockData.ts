import type { OperationalInvestigation } from '../types';

export const mockInvestigations: OperationalInvestigation[] = [
  {
    id: '1e084d237ac94e8ab3b6b900ea4afa8f',
    title: 'TechCorp Escalation: Customer Churn Risk',
    description: 'High-tier customer TechCorp experienced repeated authentication latencies (>3.5s) on their production workspace. CS Lead flagged threat of churn due to integration blockage.',
    severity: 'critical',
    status: 'investigating',
    category: 'customer_escalation',
    sourceSystems: ['slack', 'jira', 'github', 'gmail'],
    assignedTo: { name: 'Adhish Aravind', avatar: 'AA' },
    detectedAt: '2026-06-15T10:14:00Z',
    suggestedAction: 'Scale the primary Auth Gateway container replica set and merge hotfix #482.',
    entities: [
      { type: 'customer', id: 'techcorp', name: 'TechCorp' },
      { type: 'service', id: 'auth-gateway', name: 'Auth Gateway' },
      { type: 'team', id: 'core-platform', name: 'Core Platform' }
    ],
    evidence: [
      {
        id: 'ev-1',
        type: 'slack',
        timestamp: '2026-06-15T10:16:00Z',
        sourceUrl: 'https://slack.com/archives/C012345/p162391',
        summary: 'CS Lead: TechCorp CTO mentioned on Slack that registration failures are causing a blocker for their onboarding batch. They are talking to Account Execs about churn risk.',
        author: { name: 'Alex Rivera', avatar: 'AR' },
        metadata: { channel: '#customer-escalations', replies: 8 }
      },
      {
        id: 'ev-2',
        type: 'jira',
        timestamp: '2026-06-15T10:20:00Z',
        sourceUrl: 'https://jira.atlassian.com/browse/OIP-842',
        summary: 'OIP-842: Investigate high Redis connection queue in auth validation middleware.',
        author: { name: 'Jira Automator' },
        metadata: { status: 'In Progress', priority: 'Highest', reporter: 'SysAlert' }
      },
      {
        id: 'ev-3',
        type: 'github',
        timestamp: '2026-06-15T10:35:00Z',
        sourceUrl: 'https://github.com/oip/auth-gateway/pull/482',
        summary: 'GitHub PR #482: fix(auth): switch to Redis pool connections to prevent handshake timeouts.',
        author: { name: 'Dev Engineer', avatar: 'DE' },
        metadata: { branch: 'hotfix/redis-timeouts', reviews: '1 Approved', filesChanged: 4 }
      },
      {
        id: 'ev-4',
        type: 'email',
        timestamp: '2026-06-15T10:45:00Z',
        sourceUrl: 'https://mail.google.com',
        summary: 'CTO Escalation Thread: Customer TechCorp demands SLA penalty reports for last 12 hours of unstable authentications.',
        author: { name: 'CS Operations' },
        metadata: { importance: 'High', subject: 'Urgent SLA Report - TechCorp' }
      }
    ]
  },
  {
    id: 'launch_delay',
    title: 'Auth Gateway v2 Release Blocked',
    description: 'The scheduled release of the Auth Gateway V2 service is behind schedule by 4 days due to unreviewed pull requests containing security updates and missing audit logs.',
    severity: 'high',
    status: 'open',
    category: 'launch_delay',
    sourceSystems: ['github', 'notion', 'jira'],
    assignedTo: { name: 'Sarah Connor', avatar: 'SC' },
    detectedAt: '2026-06-15T08:30:00Z',
    suggestedAction: 'Review and merge GitHub PR #149 and sign off the compliance checklist.',
    entities: [
      { type: 'project', id: 'auth-v2', name: 'Authentication v2' },
      { type: 'service', id: 'auth-gateway', name: 'Auth Gateway' },
      { type: 'team', id: 'core-platform', name: 'Core Platform' }
    ],
    evidence: [
      {
        id: 'ev-5',
        type: 'github',
        timestamp: '2026-06-15T08:32:00Z',
        sourceUrl: 'https://github.com/oip/auth-gateway/pull/149',
        summary: 'GitHub PR #149: security(compliance): integrate strict JWT token audit tracking logs.',
        author: { name: 'Security Architect', avatar: 'SA' },
        metadata: { status: 'Pending Review', testsPassed: true }
      },
      {
        id: 'ev-6',
        type: 'notion',
        timestamp: '2026-06-14T15:00:00Z',
        sourceUrl: 'https://notion.so/oip/release-readiness-checklist',
        summary: 'Notion Document: Auth v2 Launch Checklist (2/5 compliance audits remaining). Needs SecOps approval.',
        author: { name: 'Release Lead' },
        metadata: { docStatus: 'Drafting', lastModifiedBy: 'Sarah Connor' }
      }
    ]
  },
  {
    id: 'security_alert',
    title: 'CORS Configuration Bypass in Production',
    description: 'A direct merge to main bypassed security checkpoints and allowed open CORS settings (*), leaving backend validation endpoints vulnerable.',
    severity: 'medium',
    status: 'resolved',
    category: 'security',
    sourceSystems: ['github', 'slack'],
    assignedTo: { name: 'DevSec Ops', avatar: 'DS' },
    detectedAt: '2026-06-14T20:10:00Z',
    suggestedAction: 'Revert commit a8b9c1d and enable branch protection for production config.',
    entities: [
      { type: 'service', id: 'auth-gateway', name: 'Auth Gateway' },
      { type: 'team', id: 'secops', name: 'SecOps' }
    ],
    evidence: [
      {
        id: 'ev-7',
        type: 'github',
        timestamp: '2026-06-14T20:12:00Z',
        sourceUrl: 'https://github.com/oip/auth-gateway/commit/a8b9c1d',
        summary: 'Direct commit a8b9c1d: bypass(config): configure open access endpoints for troubleshooting staging bypass.',
        author: { name: 'Junior Dev', avatar: 'JD' },
        metadata: { branch: 'main', forcePushed: false }
      }
    ]
  }
];
