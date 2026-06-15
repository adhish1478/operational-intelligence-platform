import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Users, 
  FolderKanban, 
  Terminal, 
  Building2, 
  ArrowUpRight, 
  GitCommit,
  MessageSquare
} from 'lucide-react';
import { mockInvestigations } from '../services/mockData';

export const EntityDetails: React.FC = () => {
  const { type, id } = useParams<{ type: string; id: string }>();

  // Find investigations associated with this entity
  const associatedInvestigations = mockInvestigations.filter(inv => 
    inv.entities.some(e => e.type === type && e.id === id)
  );

  // Static Metadata based on entity type & id
  const getEntityMetadata = () => {
    switch (type) {
      case 'customer':
        return {
          title: id === 'techcorp' ? 'TechCorp' : 'Customer Workspace',
          badge: 'Enterprise Customer',
          icon: Building2,
          owner: 'Alex Rivera (CS Lead)',
          riskLevel: 'Critical Churn Threat',
          riskColor: 'badge-critical',
          details: [
            { label: 'Contract Tier', value: 'Enterprise SLA Gold' },
            { label: 'Annual Value', value: '$240,000 ARR' },
            { label: 'Primary Contact', value: 'CTO (cto@techcorp.com)' },
            { label: 'Sync Status', value: 'Synced via Slack & Gmail' },
          ]
        };
      case 'service':
        return {
          title: id === 'auth-gateway' ? 'Auth Gateway' : 'Service Microservice',
          badge: 'Production Service',
          icon: Terminal,
          owner: 'Sarah Connor (Core Infra Lead)',
          riskLevel: 'Moderate Latency Warning',
          riskColor: 'badge-warning',
          details: [
            { label: 'Active Replica Sets', value: '3 Nodes' },
            { label: 'Current Latency', value: '1.2s avg (threshold: 300ms)' },
            { label: 'Language / Framework', value: 'Go v1.22 / Redis' },
            { label: 'Build Target', value: 'K8s Cluster - US-East' },
          ]
        };
      case 'team':
        return {
          title: id === 'core-platform' ? 'Core Platform Team' : 'Engineering Pod',
          badge: 'Core Engineering Group',
          icon: Users,
          owner: 'Sarah Connor (EM)',
          riskLevel: 'High Sprint Blockage',
          riskColor: 'badge-warning',
          details: [
            { label: 'Member Count', value: '8 engineers' },
            { label: 'Active Sprints', value: 'Sprint 14B - Core Auth' },
            { label: 'Primary Slack Channel', value: '#dev-core-platform' },
            { label: 'Weekly Velocity', value: '42 story points' },
          ]
        };
      case 'project':
        return {
          title: id === 'auth-v2' ? 'Authentication v2' : 'Active Initiative',
          badge: 'SaaS Expansion Project',
          icon: FolderKanban,
          owner: 'Sarah Connor (EM)',
          riskLevel: 'Launch Delayed (4 days)',
          riskColor: 'badge-warning',
          details: [
            { label: 'Release Schedule', value: 'June 25, 2026' },
            { label: 'Readiness Checklist', value: '3/5 Audits Completed' },
            { label: 'Repository Path', value: 'github.com/oip/auth-gateway' },
            { label: 'Main Feature Branch', value: 'release/v2-auth' },
          ]
        };
      default:
        return {
          title: 'System Entity',
          badge: 'Entity Profile',
          icon: FolderKanban,
          owner: 'Ops Administrator',
          riskLevel: 'Healthy',
          riskColor: 'badge-success',
          details: []
        };
    }
  };

  const entity = getEntityMetadata();
  const Icon = entity.icon;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      
      {/* Header Profile Section */}
      <div className="bg-surface border border-outline-variant rounded-lg p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded bg-surface-low border border-outline-variant flex items-center justify-center text-secondary">
            <Icon className="w-6.5 h-6.5" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] uppercase font-bold text-outline-variant bg-primary text-white px-2 py-0.5 rounded font-mono">
                {type}
              </span>
              <span className="text-body-sm text-on-surface-variant font-medium">
                {entity.badge}
              </span>
            </div>
            <h1 className="text-headline-md font-semibold text-on-surface leading-tight">{entity.title}</h1>
          </div>
        </div>

        {/* Risk Level Callout */}
        <div className="bg-surface-low border border-outline-variant rounded p-3 text-right">
          <div className="text-[10px] font-bold text-outline uppercase tracking-wider mb-1">Risk Assessment</div>
          <span className={entity.riskColor}>
            {entity.riskLevel.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Main Grid: Entity parameters & associated items */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Panel (4 Columns): Metadata Parameters */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-surface border border-outline-variant rounded-lg p-4 space-y-3">
            <h3 className="text-headline-sm text-outline uppercase tracking-wider font-bold">Ownership & Contact</h3>
            <div className="text-body-sm text-on-surface">
              <span className="text-on-surface-variant text-[11px] block">Responsible Owner</span>
              <strong className="font-semibold">{entity.owner}</strong>
            </div>
          </div>

          <div className="bg-surface border border-outline-variant rounded-lg p-4 space-y-3">
            <h3 className="text-headline-sm text-outline uppercase tracking-wider font-bold">Profile Details</h3>
            <div className="space-y-3">
              {entity.details.map((item, idx) => (
                <div key={idx} className="text-body-sm py-1.5 border-b border-outline-variant/40 last:border-0 last:pb-0">
                  <span className="text-on-surface-variant text-[11px] block">{item.label}</span>
                  <span className="font-medium text-on-surface">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel (8 Columns): Associated Investigations & Evidence */}
        <div className="lg:col-span-8 space-y-6">
          
          {/* Active Investigations */}
          <div className="space-y-3">
            <h2 className="text-headline-sm text-outline uppercase tracking-wider font-bold">Linked Active Investigations</h2>
            <div className="bg-surface border border-outline-variant rounded-lg overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-low border-b border-outline-variant text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">
                    <th className="px-4 py-2">ID</th>
                    <th className="px-4 py-2">Investigation</th>
                    <th className="px-4 py-2">Severity</th>
                    <th className="px-4 py-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {associatedInvestigations.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-8 text-center text-body-sm text-on-surface-variant italic">
                        No active investigations currently mapped to this entity.
                      </td>
                    </tr>
                  ) : (
                    associatedInvestigations.map((inv) => (
                      <tr key={inv.id} className="border-b border-outline-variant/60 hover:bg-surface-low transition-colors align-middle text-body-sm text-on-surface">
                        <td className="px-4 py-2.5 font-mono text-mono-label text-on-surface-variant">
                          {inv.id.substring(0, 8)}
                        </td>
                        <td className="px-4 py-2.5 font-semibold">
                          <Link to={`/investigations/${inv.id}`} className="hover:underline">
                            {inv.title}
                          </Link>
                        </td>
                        <td className="px-4 py-2.5">
                          <span className={inv.severity === 'critical' ? 'badge-critical' : 'badge-warning'}>
                            {inv.severity.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <Link 
                            to={`/investigations/${inv.id}`} 
                            className="inline-flex items-center gap-1 text-[11px] font-bold text-primary hover:underline"
                          >
                            <span>Open Details</span>
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

          {/* Evidence highlights from associated investigations */}
          {associatedInvestigations.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-headline-sm text-outline uppercase tracking-wider font-bold">Associated Evidence Feed</h2>
              <div className="space-y-2">
                {associatedInvestigations.flatMap(inv => inv.evidence).slice(0, 3).map((ev) => (
                  <div key={ev.id} className="bg-surface border border-outline-variant rounded p-3 space-y-1">
                    <div className="flex items-center justify-between text-[11px] text-on-surface-variant">
                      <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider">
                        {ev.type === 'slack' ? <MessageSquare className="w-3.5 h-3.5 text-secondary" /> : <GitCommit className="w-3.5 h-3.5 text-secondary" />}
                        <span>{ev.type}</span>
                        {ev.author.name && (
                          <>
                            <span>•</span>
                            <span className="font-semibold text-on-surface">{ev.author.name}</span>
                          </>
                        )}
                      </div>
                      <span className="font-mono text-mono-label">{ev.timestamp.split('T')[0]}</span>
                    </div>
                    <p className="text-body-sm text-on-surface">{ev.summary}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
};
