# Component Inventory

This component inventory defines the UI building blocks of the **Operational Intelligence Platform**, aligned with the light-themed "Operational Command Center" design system and focused on an investigation-first architecture.

---

## 1. Navigation & Layout Components

### Persistent Sidebar Navigation (`Sidebar`)
*   **Width**: Fixed `240px`.
*   **Background**: `Surface Container Low` (`#F2F4F6`) with a 1px right border (`#C6C6CD`).
*   **Sections**:
    *   *Workspace Switcher*: Dropdown to change org/workspace scopes.
    *   *Main Navigation*: Attention Deck (Dashboard), Investigations Queue, Integrations, Reports, Settings.
    *   *Interactive State*: Active items highlighted in `Surface Container` (`#ECEEF0`) with `Slate-900` text.

### Global Header (`Header`)
*   **Background**: Pure `#FFFFFF` with a 1px bottom border.
*   **Breadcrumbs**: Modern hierarchy links (e.g., `Investigations / TechCorp Escalation`) in `body-sm`.
*   **Command Palette Quick-Launch**: Clicking the search icon or trigger button shows `⌘K` shortcut hint.

### Global Command Palette (`CommandPalette`)
*   **Trigger**: Shortcut `⌘K` or header search click.
*   **Aesthetic**: Centered modal popover, pure white background, 1px border, 4px blur shadow.
*   **Features**:
    *   Grouped list: *Actions*, *Investigations*, *Entities (Customers, Teams)*, *Integrations*.
    *   Keyboard navigation supports `Enter` to open and `Esc` to exit.

---

## 2. Dashboard Components (Attention Deck)

### Active Investigation Cards (`InvestigationAlertCard`)
*   **Aesthetic**: White background container with 1px left accent border (Critical = Red, Warning = Amber, Info = Blue).
*   **Layout**:
    *   *Header*: Entity markers (e.g., Customer: TechCorp, Service: Auth Gateway) + Severity Badge.
    *   *Body*: Investigation Title, business impact description, and detected duration.
    *   *Action Zone*: Action buttons ("Start Triage", "Assign Owner", "Resolve") + source system icons.

### Business Impact Panel (`BusinessImpactAlerts`)
*   **Aesthetic**: Bordered Slate-200 card containing high-contrast risk alerts (revenue risk, SLA breaches, customer churn threat indicators).
*   **Layout**: Summarizes which key business metrics are actively threatened by unresolved investigations.

---

## 3. Queue Components (`InvestigationsQueue`)

### High-Density Investigations Table (`InvestigationsTable`)
*   **Aesthetic**: Bordered rows, no vertical grid lines, 4px vertical cell padding.
*   **Rows**: Hover state highlights row with background `Neutral-100` (`#ECEEF0`).
*   **Columns**:
    *   *ID*: Text in `mono-label` (`JetBrains Mono`).
    *   *Investigation*: Title and quick description.
    *   *Impact*: Associated entity references (Customer, Project, Service).
    *   *Severity*: "Light Fill" background status chip.
    *   *Detected*: `mono-label` timestamp.
    *   *Assignee*: User avatar.

---

## 4. Investigation View Components (`InvestigationDetails`)

### Evidence Feed (`EvidenceFeed`)
*   **Aesthetic**: Chronological list of incoming cross-platform evidence items.
*   **Evidence Item Card**:
    *   *Slack discussion*: Shows chat thread snippet, author name, avatar, and channel name.
    *   *Jira tickets*: Shows ticket key (`mono-label`), assignee, status, and description.
    *   *GitHub events*: Shows commit hash (`mono-label`), author, PR title, and repository name.
    *   *Emails*: Shows sender, subject, and excerpt of the discussion.
    *   *Notion docs*: Links to related workspace docs with snippet text.
    *   *Metadata*: Action button to "Attach to Timeline" or "Mark as Key Evidence".

### Interactive Timeline (`Timeline`)
*   **Aesthetic**: Vertical track connecting timeline nodes.
*   **Nodes**: Interactive dots colored by event type (Integration event, human log comment, status transition).

---

## 5. Entity Details Components (`EntityDashboard`)

### Entity Overview Header (`EntityHeader`)
*   **Layout**: Title in `headline-lg`, entity type badge (e.g., Customer, Service), owner assignment, current risk level status card.

### Entity Risk Summary (`EntityRiskCard`)
*   **Layout**: Breakdown of the active risks affecting this entity (e.g. 2 active Critical investigations, 5 linked Slack escalation logs).

---

## 6. Integrations & Administration (`IntegrationsGrid`)

### Connector Cards
*   **Aesthetic**: Grid layout with 16px gap.
*   **Card**: Icon logo, status badge ("Connected", "Not Synced"), toggle switch, and configure button.
