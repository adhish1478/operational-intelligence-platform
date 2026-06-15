# Operational Intelligence Platform: Implementation Plan

This document serves as the comprehensive source of truth for the development of the **Operational Intelligence Platform (OIP)**. It details the product vision, architectural decisions, design system, and technical roadmap required to build a premium, enterprise-grade SaaS interface.

---

## 1. Product Vision & Goals

### Vision
To provide an "AI Chief of Staff" that transforms fragmented noise from Slack, Jira, Gmail, Notion, and GitHub into high-fidelity, actionable operational intelligence.

### Business Goals
*   **Consolidated Visibility:** Reduce the need to context-switch between 5+ tools.
*   **Action-Oriented:** Move beyond "dashboards" (static charts) to "workstreams" (active investigations).
*   **Risk Mitigation:** Proactively surface launch delays, customer churn, and security gaps.

### User Goals
*   Understand the "Why" and "Who" behind every business anomaly.
*   Execute immediate corrective actions directly from the platform.
*   Collaborate with stakeholders with shared context.

---

## 2. User Personas & Workflows

| Persona | Key Pain Point | Primary Workflow in OIP |
| :--- | :--- | :--- |
| **Founder / CEO** | Information siloed in technical tools they don't use daily. | High-level "Risk Radar" overview and "Executive Summaries" of major projects. |
| **Engineering Manager** | Unseen blockers delaying sprints and team burnout. | Monitoring "Team Blockers" and "Developer Velocity Risks" across Jira/GitHub. |
| **Ops Manager** | Manual tracking of cross-departmental initiatives. | Managing "Operational Investigations" and verifying "Source System" alignment. |
| **CS Lead** | Customer complaints lost in Slack threads or email chains. | Tracking "Customer Escalations" and linking them to engineering root causes. |

---

## 3. Information Architecture (Navigation & Routes)

### Navigation Strategy
*   **Primary Sidebar:** Persistent navigation with workspace switching and top-level modules.
*   **Command Palette (CMD+K):** Deep search across investigations, entities, integrations, and documentation.
*   **Contextual Breadcrumbs:** High-level path tracking for deep investigation pages.

### Route Definitions
*   `/login` - Enterprise SSO / Auth.
*   `/onboarding` - First-time integration setup flow.
*   `/dashboard` - **Attention Deck (Dashboard)**: Investigation-first view displaying active investigations, business impact, recommended actions, and escalation signals. *Avoids metric-heavy templates and chart-first layouts.*
*   `/investigations` - Global search/filter list of all active and historical investigations.
*   `/investigations/:id` - **Investigation Details (Flagship View)**: Multi-pane diagnostic interface featuring the Evidence Feed, system logs, root cause analysis, and collaboration tools.
*   `/entities/:type/:id` - **Entity Details View**: Aggregated hub for specific Customers, Projects, Teams, or Services summarizing active investigations, evidence history, ownership, and risk levels.
*   `/integrations` - Marketplace for connecting Slack, Jira, Gmail, Notion, GitHub, etc.
*   `/reports` - Automated weekly/monthly executive summaries.
*   `/settings` - User preferences, team management, and billing.

---

## 4. Design System & Aesthetics

**Theme:** Light Mode "Engineering-Grade" (Strict Slate & Neutral palette) aligned with the Stitch "Operational Command Center" project design.

### Color Strategy
*   **Background:** Neutral-50 (`#F7F9FB`) flat clean surface.
*   **Surface:** Pure White (`#FFFFFF`) with 1px Slate border (`#C6C6CD`). Tonal layering surfaces: Low (`#F2F4F6`), Medium (`#ECEEF0`), High (`#E6E8EA`).
*   **Accent (Primary):** Slate-900 (`#0F172A`) for buttons and primary focus states.
*   **Status Tones (No Glows, Light Fill background strategy):**
    *   *Critical:* Hyper Red (`#BA1A1A`) with light container background (`#FFDAD6`).
    *   *Warning:* Amber Gold (`#F59E0B`).
    *   *Success:* Neon Emerald (`#10B981`).

### Typography
*   **Scale:** Compact hierarchy driven by *Inter* font family (13px/14px body standard) to maximize data density.
*   **Mono:** *JetBrains Mono* (`mono-label` at 12px) for ID tags, timestamps, and log data.

### Spacing & Shapes
*   **Grid:** Strict 4px grid rules (Compact 4px, Comfortable 12px, Gutter 16px, Container Padding 24px).
*   **Shapes:** Crisp 4px corner radius for buttons, inputs, and minor cards; 8px for large dashboard containers.

---

## 5. Technical Architecture

### Tech Stack
*   **Framework:** Vite + React 18 + TypeScript (Strict).
*   **Styling:** Tailwind CSS + Framer Motion (for micro-animations).
*   **Components:** shadcn/ui custom-themed.
*   **State:** TanStack Query (Server State), Zustand (Local UI State).
*   **Routing:** React Router v6.

### Folder Structure (Feature-Based)
```text
src/
├── assets/             # Global images, icons
├── components/         # Shared UI (atoms/molecules)
├── features/           # Domain-specific logic
│   ├── dashboard/      # Attention Deck cards, active queue alerts
│   ├── investigations/ # List, Evidence Feed, timeline, log view
│   ├── entities/       # Entity summary pages (Customer, Team, etc.)
│   ├── integrations/   # Connectors, status cards
│   └── reports/        # PDF generators, summary views
├── hooks/              # Global custom hooks
├── lib/                # Configs (api, utils, providers)
├── store/              # Global UI state (Zustand)
└── types/              # Centralized TS definitions
```

---

## 6. Type Definitions & Mock Data

### Central Investigation Interfaces
```typescript
export interface Evidence {
  id: string;
  type: 'slack' | 'jira' | 'github' | 'email' | 'notion';
  timestamp: string;
  sourceUrl: string;
  summary: string;
  author: { name: string; avatar?: string };
  metadata: Record<string, any>;
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
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'investigating' | 'resolved';
  category: 'launch_delay' | 'customer_escalation' | 'revenue_risk' | 'team_blocker' | 'security';
  sourceSystems: ('slack' | 'jira' | 'gmail' | 'github' | 'notion')[];
  assignedTo?: { name: string; avatar: string };
  detectedAt: string;
  suggestedAction: string;
  evidence: Evidence[];
  entities: EntityReference[];
}
```

### Mock Scenarios
1.  **Launch Delay:** "Feature 'User Auth' behind schedule by 4 days based on Jira velocity."
    *   *Evidence*: Jira tickets, Slack discussion in #dev-auth, GitHub commit events.
    *   *Entities*: Project "Authentication", Team "Core Infra", Service "Auth Gateway".
2.  **Customer Escalation:** "High-tier client TechCorp mentioning 'churn' in Slack #general."
    *   *Evidence*: Slack chat transcripts, emails, Zendesk ticket metadata.
    *   *Entities*: Customer "TechCorp", Account Team, Service "Main API".
3.  **Security Risk:** "New unreviewed PR in GitHub modifying `/auth` endpoint."
    *   *Evidence*: GitHub PR diff summary, Notion authorization doc.
    *   *Entities*: Service "Auth Gateway", Team "SecOps".

---

## 7. Scalability & Future SaaS Requirements

### Reliability & Scalability
*   **Virtualization:** Use `react-window` for the global list of investigations to handle 10k+ items.
*   **Skeleton States:** Complex investigation details views must use progressive loading/skeletons.
*   **Offline Indicator:** Basic presence detection for collaborative sessions.

### Future SaaS Capabilities
*   **Multi-tenancy:** Workspace/Org switcher in the sidebar.
*   **Role-Based Access (RBAC):** Admin vs. Viewer permissions for sensitive investigations.
*   **Billing/Quotas:** Integrated usage tracking for connected data volume.
*   **Audit Logging:** Tracking who viewed/modified high-severity investigations.

---

## 8. Implementation Roadmap

### Phase 1: Foundation
*   [ ] Configure design system tokens in Tailwind and `index.css`.
*   [ ] Create basic outer layout: Sidebar (with org switcher) and Header (with command palette link).
*   [ ] Initialize routing schema (`/dashboard`, `/investigations`, `/entities`).

### Phase 2: Flagship Investigation Details & Evidence Feed
*   [ ] Implement the multi-pane Investigation Details view (`/investigations/:id`).
*   [ ] Build the **Evidence Feed** component grouping Slack threads, GitHub commits, Jira issues, emails, and Notion pages.
*   [ ] Build the high-density JetBrains Mono log viewer pane.
*   [ ] Set up the interactive collaborative timeline.

### Phase 3: Dashboard & Queue
*   [ ] Build the investigation-first **Attention Deck Dashboard** focused on active investigations, risk impact, and escalation items (avoiding chart-first grids).
*   [ ] Implement the high-density **Investigations Queue** list with filtering and search.

### Phase 4: Entity Details & Integrations
*   [ ] Build the **Entity Details** view aggregating investigations and risk history per Customer, Team, Project, or Service.
*   [ ] Build the integrations setup grid dashboard.

### Phase 5: Polish & Assembly
*   [ ] Global Command Palette integration (`⌘K`).
*   [ ] Complete verification with mock data sets.
*   [ ] Run `npm run lint` and `npm run build` validation checks.