# Operational Intelligence Platform: Implementation Plan

This document serves as the comprehensive source of truth for the development of the **Operational Intelligence Platform (OIP)**. It details the product vision, architectural decisions, design system, and technical roadmap required to build a premium, enterprise-grade SaaS interface.

---

## 1. Product Vision & Goals

### Vision
To provide an "AI Chief of Staff" that transforms fragmented noise from Slack, Jira, Gmail, and GitHub into high-fidelity, actionable business intelligence.

### Business Goals
*   **Consolidated Visibility:** Reduce the need to context-switch between 5+ tools.
*   **Action-Oriented:** Move beyond "dashboards" (static charts) to "workstreams" (active issues).
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
| **Ops Manager** | Manual tracking of cross-departmental initiatives. | Managing "Operational Issues" and verifying "Source System" alignment. |
| **CS Lead** | Customer complaints lost in Slack threads or email chains. | Tracking "Customer Escalations" and linking them to engineering root causes. |

---

## 3. Information Architecture (Navigation & Routes)

### Navigation Strategy
*   **Primary Sidebar:** Persistent navigation with workspace switching and top-level modules.
*   **Command Palette (CMD+K):** Deep search across issues, integrations, and documentation.
*   **Contextual Breadcrumbs:** High-level path tracking for deep investigation pages.

### Route Definitions
*   `/login` - Enterprise SSO / Auth.
*   `/onboarding` - First-time integration setup flow.
*   `/dashboard` - The "Pulse" view: High-level risk categories and activity heatmaps.
*   `/issues` - Global search/filter list of all identified operational risks.
*   `/issues/:id` - **Investigation View:** Root cause analysis, system logs, and collaboration.
*   `/integrations` - Marketplace for connecting Slack, Jira, Gmail, Notion, etc.
*   `/reports` - Automated weekly/monthly executive summaries.
*   `/settings` - User preferences, team management, and billing.

---

## 4. Design System & Aesthetics

**Theme:** "Titanium & Glass" (High-contrast Dark Mode with Glassmorphism)

### Color Strategy
*   **Background:** Deep Obsidian (`#020617`) with subtle mesh gradients.
*   **Surface:** Translucent Glass (`rgba(15, 23, 42, 0.6)`) with 12px blur.
*   **Accent (Primary):** Electric Indigo (`#6366f1`) for main actions.
*   **Status Tones:**
    *   *Critical:* Hyper Red (`#ef4444`) with outer glow.
    *   *Warning:* Amber Gold (`#f59e0b`).
    *   *Success:* Neon Emerald (`#10b981`).

### Typography
*   **Headings:** *Outfit* or *Inter* (Semi-bold, tight tracking).
*   **Body:** *Inter* (Variable, high legibility).
*   **Mono:** *JetBrains Mono* for system IDs and technical logs.

### UI Components (Atomic Design)
*   **Atoms:** Buttons (variants: glass, solid, ghost), Badges (status/priority), Tooltips, Avatars.
*   **Molecules:** Issue Cards (hover-active), Search Inputs (CMD+K style), Stat Widgets.
*   **Organisms:** Issue Feed, Global Sidebar, Root Cause Timeline.
*   **Templates:** Dashboard Layout, Split-pane Investigation View.

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
│   ├── dashboard/      # Cards, stats, mini-feed
│   ├── issues/         # List, filter, investigation view
│   ├── integrations/   # Connectors, status cards
│   └── reports/        # PDF generators, summary views
├── hooks/              # Global custom hooks
├── lib/                # Configs (api, utils, providers)
├── store/              # Global UI state (Zustand)
└── types/              # Centralized TS definitions
```

---

## 6. Type Definitions & Mock Data

### Core Issue Interface
```typescript
interface OperationalIssue {
  id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'investigating' | 'resolved';
  category: 'launch_delay' | 'customer_escalation' | 'revenue_risk' | 'team_blocker' | 'security';
  sourceSystems: ('slack' | 'jira' | 'gmail' | 'github')[];
  assignedTo?: { name: string; avatar: string };
  detectedAt: string;
  suggestedAction: string;
}
```

### Mock Scenarios
1.  **Launch Delay:** "Feature 'User Auth' behind schedule by 4 days based on Jira velocity."
2.  **Customer Escalation:** "High-tier client mentioning 'churn' in Slack #general."
3.  **Security Risk:** "New unreviewed PR in GitHub modifying `/auth` endpoint."

---

## 7. Scalability & Future SaaS Requirements

### Reliability & Scalability
*   **Virtualization:** Use `react-window` for the global issues list to handle 10k+ items.
*   **Skeleton States:** Complex investigation views must use progressive loading/skeletons.
*   **Offline Indicator:** Basic presence detection for collaborative sessions.

### Future SaaS Capabilities
*   **Multi-tenancy:** Workspace/Org switcher in the sidebar.
*   **Role-Based Access (RBAC):** Admin vs. Viewer permissions for sensitive issues.
*   **Billing/Quotas:** Integrated usage tracking for connected data volume.
*   **Audit Logging:** Tracking who viewed/modified high-severity issues.

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Current)
*   [ ] Initialize Vite/TS project.
*   [ ] Configure Tailwind & Design Tokens.
*   [ ] Setup basic Layout (Sidebar + Header).

### Phase 2: Core UX
*   [ ] Implement Dashboard (Risk Widgets).
*   [ ] Build Global Issues List with filtering.
*   [ ] Create the "Investigation View" (Root Cause Analysis).

### Phase 3: Enrichment
*   [ ] Integrations Management UI.
*   [ ] Command Palette (CMD+K) implementation.
*   [ ] Framer Motion animations for transitions.

### Phase 4: Polish
*   [ ] Mock data stress test.
*   [ ] Responsive optimization (Mobile/Large Screens).
*   [ ] Accessibility (ARIA labels, keyboard nav).