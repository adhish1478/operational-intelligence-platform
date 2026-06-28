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

### 4.1. Design Philosophy & Evolution (Audit Decided)
This platform adopts a **Modern Corporate** aesthetic—influenced by high-density, engineering-grade software like Linear and Palantir. It represents a pivot from the initial "Titanium & Glass" dark mode theme to a light-themed **"Operational Command Center"**:
*   **Theme Shift:** Flat, high-legibility light mode surfaces with strict outlines and borders (`#C6C6CD` or `#E2E8F0`) instead of dark shadows or glowing translucent elements.
*   **Precision & Authority:** Prioritize data density and functional hierarchy over decorative elements.
*   **Tonal Layering:** Communicate depth using varying surface tones and low-contrast borders rather than heavy shadows.
*   **Color as Signifier:** Limit the use of color to status, priority, and actions to minimize semantic noise. Avoid neon glows.

### 4.2. Color Palette
The design system operates primarily in a light-mode scheme using Slate and Neutral tones:

#### Foundation Colors
*   **Background (Neutral-50):** `#F7F9FB`
    *   *Usage:* Main application background. A clean, professional "off-white" that reduces screen glare.
*   **Primary Text (Slate-900 / on-background):** `#191C1E` (Custom primary color `#0F172A` overrides text colors for maximum legibility).
    *   *Usage:* Primary headings, text, and critical elements.
*   **Borders & Boundaries (Slate-200 / outline-variant):** `#C6C6CD` (and secondary `#E2E8F0` / `#76777D` for high-contrast outlines).
    *   *Usage:* Outer boundaries of cards, tables, search inputs, and sidebar borders.

#### Surfaces (Tonal Layering)
*   **Surface Bright / Lowest Container:** `#FFFFFF`
    *   *Usage:* Card backgrounds, modal windows, table rows.
*   **Surface Container Low:** `#F2F4F6`
    *   *Usage:* Input fields, inactive states, sidebar background.
*   **Surface Container:** `#ECEEF0`
    *   *Usage:* Inner wells, panel containers.
*   **Surface Container High:** `#E6E8EA`
    *   *Usage:* Hover states, active tabs.
*   **Surface Container Highest / Surface Dim:** `#E0E3E5` / `#D8DADC`
    *   *Usage:* Headers, active indicator boundaries.

#### Semantic Tones (Inviolable Status Signifiers)
*   **Primary Action (Slate-900 / Indigo):** `#0F172A` (Hover: `#1E293B`, Container: `#131B2E`)
*   **Secondary Actions:** `#515F74` (Container: `#D5E3FD`)
*   **Success (Emerald):** `#10B981` (On-Success: `#FFFFFF`)
*   **Warning (Amber):** `#F59E0B` (On-Warning: `#FFFFFF`)
*   **Error / Critical (Hyper Red):** `#BA1A1A` (Container: `#FFDAD6`, On-Error: `#FFFFFF`, On-Error-Container: `#93000A`)

### 4.3. Typography
Legibility in data-heavy layouts is driven by the **Inter** font family, with **JetBrains Mono** reserved for technical data (timestamps, logs, IDs).

| Type Scale | Font Family | Font Size | Font Weight | Line Height | Letter Spacing | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Headline Large** | Inter | `24px` | 600 (Semi-bold) | `32px` | `-0.02em` | Main page titles |
| **Headline Medium** | Inter | `18px` | 600 (Semi-bold) | `24px` | `-0.01em` | Card & drawer headers |
| **Headline Small** | Inter | `14px` | 600 (Semi-bold) | `20px` | Normal | Table & list section headers |
| **Body Medium** | Inter | `14px` | 400 (Regular) | `20px` | Normal | Body text, descriptions |
| **Body Small** | Inter | `13px` | 400 (Regular) | `18px` | Normal | Data cells, secondary labels |
| **Label Caps** | Inter | `11px` | 600 (Semi-bold) | `16px` | `0.05em` | Table column titles (uppercase) |
| **Mono Label** | JetBrains Mono | `12px` | 400 (Regular) | `16px` | Normal | IDs, timestamps, log details |

### 4.4. Spacing & Grid (The 4px Rule)
All paddings, margins, gaps, and sizes must align to a strict 4px grid to enforce high data density.
*   **Base Unit:** `4px`
*   **Density Compact:** `4px` (e.g., cell padding in high-density tables)
*   **Density Comfortable:** `12px` (e.g., standard button/input horizontal padding)
*   **Gutter:** `16px` (e.g., spacing between grid items)
*   **Container Padding:** `24px` (e.g., main content area outer margin)
*   **Sidebar Width:** `240px` (fixed-width sidebar navigation)

### 4.5. Shape & Corner Radii
*   **sm (`0.125rem` / `2px`):** Very small components (checkboxes, status dots).
*   **DEFAULT (`0.25rem` / `4px`):** Buttons, input fields, tags, mini cards.
*   **md (`0.375rem` / `6px`):** Dropdowns, context menus.
*   **lg (`0.5rem` / `8px`):** Large dashboard containers, main card blocks.
*   **xl (`0.75rem` / `12px`):** Modals, large dialogue boxes.
*   **full (`9999px`):** User avatars, pill-shaped status dots.

### 4.6. Depth & Elevation
*   **Level 0 (Background):** `#F7F9FB` (Neutral-50) flat background.
*   **Level 1 (Default Card/Sidebar):** Pure `#FFFFFF` card background + 1px `#C6C6CD` or `#E2E8F0` border.
*   **Level 2 (Popovers/Modals/Command Palette):** Pure `#FFFFFF` background + 1px `#C6C6CD` border + 4px blur shadow (`rgba(15, 23, 42, 0.05)`).
*   **Dimming Overlay:** `#0F172A` with `20%` opacity behind modals.

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
*Note: This roadmap corresponds to the frontend application execution.*

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

---

## 9. Component Inventory

### 9.1. Navigation & Layout Components

#### Persistent Sidebar Navigation (`Sidebar`)
*   **Width:** Fixed `240px`.
*   **Background:** `Surface Container Low` (`#F2F4F6`) with a 1px right border (`#C6C6CD`).
*   **Sections:**
    *   *Workspace Switcher*: Dropdown to change org/workspace scopes.
    *   *Main Navigation*: Attention Deck (Dashboard), Investigations Queue, Integrations, Reports, Settings.
    *   *Interactive State*: Active items highlighted in `Surface Container` (`#ECEEF0`) with `Slate-900` text.

#### Global Header (`Header`)
*   **Background:** Pure `#FFFFFF` with a 1px bottom border.
*   **Breadcrumbs:** Modern hierarchy links (e.g., `Investigations / TechCorp Escalation`) in `body-sm`.
*   **Command Palette Quick-Launch:** Clicking the search icon or trigger button shows `⌘K` shortcut hint.

#### Global Command Palette (`CommandPalette`)
*   **Trigger:** Shortcut `⌘K` or header search click.
*   **Aesthetic:** Centered modal popover, pure white background, 1px border, 4px blur shadow.
*   **Features:**
    *   Grouped list: *Actions*, *Investigations*, *Entities (Customers, Teams)*, *Integrations*.
    *   Keyboard navigation supports `Enter` to open and `Esc` to exit.

### 9.2. Dashboard Components (Attention Deck)

#### Active Investigation Cards (`InvestigationAlertCard`)
*   **Aesthetic:** White background container with 1px left accent border (Critical = Red, Warning = Amber, Info = Blue).
*   **Layout:**
    *   *Header*: Entity markers (e.g., Customer: TechCorp, Service: Auth Gateway) + Severity Badge.
    *   *Body*: Investigation Title, business impact description, and detected duration.
    *   *Action Zone*: Action buttons ("Start Triage", "Assign Owner", "Resolve") + source system icons.

#### Business Impact Panel (`BusinessImpactAlerts`)
*   **Aesthetic:** Bordered Slate-200 card containing high-contrast risk alerts (revenue risk, SLA breaches, customer churn threat indicators).
*   **Layout:** Summarizes which key business metrics are actively threatened by unresolved investigations.

### 9.3. Queue Components (`InvestigationsQueue`)

#### High-Density Investigations Table (`InvestigationsTable`)
*   **Aesthetic:** Bordered rows, no vertical grid lines, 4px vertical cell padding.
*   **Rows:** Hover state highlights row with background `Neutral-100` (`#ECEEF0`).
*   **Columns:**
    *   *ID*: Text in `mono-label` (`JetBrains Mono`).
    *   *Investigation*: Title and quick description.
    *   *Impact*: Associated entity references (Customer, Project, Service).
    *   *Severity*: "Light Fill" background status chip.
    *   *Detected*: `mono-label` timestamp.
    *   *Assignee*: User avatar.

### 9.4. Investigation View Components (`InvestigationDetails`)

#### Evidence Feed (`EvidenceFeed`)
*   **Aesthetic:** Chronological list of incoming cross-platform evidence items.
*   **Evidence Item Card:**
    *   *Slack discussion*: Shows chat thread snippet, author name, avatar, and channel name.
    *   *Jira tickets*: Shows ticket key (`mono-label`), assignee, status, and description.
    *   *GitHub events*: Shows commit hash (`mono-label`), author, PR title, and repository name.
    *   *Emails*: Shows sender, subject, and excerpt of the discussion.
    *   *Notion docs*: Links to related workspace docs with snippet text.
    *   *Metadata*: Action button to "Attach to Timeline" or "Mark as Key Evidence".

#### Interactive Timeline (`Timeline`)
*   **Aesthetic:** Vertical track connecting timeline nodes.
*   **Nodes:** Interactive dots colored by event type (Integration event, human log comment, status transition).

### 9.5. Entity Details Components (`EntityDashboard`)

#### Entity Overview Header (`EntityHeader`)
*   **Layout:** Title in `headline-lg`, entity type badge (e.g., Customer, Service), owner assignment, current risk level status card.

#### Entity Risk Summary (`EntityRiskCard`)
*   **Layout:** Breakdown of the active risks affecting this entity (e.g., 2 active Critical investigations, 5 linked Slack escalation logs).

### 9.6. Integrations & Administration (`IntegrationsGrid`)

#### Connector Cards
*   **Aesthetic:** Grid layout with 16px gap.
*   **Card:** Icon logo, status badge ("Connected", "Not Synced"), toggle switch, and configure button.