# Operational Intelligence Design System

This design system is extracted from the Stitch project **"Operational Command Center"** and serves as the style guide for the frontend implementation. It adopts a **Modern Corporate** aesthetic—influenced by high-density, engineering-grade software like Linear and Palantir.

---

## 1. Brand & Design Philosophy
*   **Precision & Authority**: Prioritize data density and functional hierarchy over decorative elements.
*   **Tonal Layering**: Communicate depth using varying surface tones and low-contrast borders rather than heavy shadows.
*   **Color as Signifier**: Limit the use of color to status, priority, and actions to minimize semantic noise.

---

## 2. Color Palette
The design system operates primarily in a light-mode scheme using Slate and Neutral tones:

### Foundation Colors
*   **Background (Neutral-50)**: `#F7F9FB`
    *   *Usage*: Main application background. A clean, professional "off-white" that reduces screen glare.
*   **Primary Text (Slate-900 / on-background)**: `#191C1E` (Custom primary color `#0F172A` overrides text colors for maximum legibility).
    *   *Usage*: Primary headings, text, and critical elements.
*   **Borders & Boundaries (Slate-200 / outline-variant)**: `#C6C6CD` (and secondary `#E2E8F0` / `#76777D` for high-contrast outlines).
    *   *Usage*: Outer boundaries of cards, tables, search inputs, and sidebar borders.

### Surfaces (Tonal Layering)
*   **Surface Bright / Lowest Container**: `#FFFFFF`
    *   *Usage*: Card backgrounds, modal windows, table rows.
*   **Surface Container Low**: `#F2F4F6`
    *   *Usage*: Input fields, inactive states, sidebar background.
*   **Surface Container**: `#ECEEF0`
    *   *Usage*: Inner wells, panel containers.
*   **Surface Container High**: `#E6E8EA`
    *   *Usage*: Hover states, active tabs.
*   **Surface Container Highest / Surface Dim**: `#E0E3E5` / `#D8DADC`
    *   *Usage*: Headers, active indicator boundaries.

### Semantic Tones (Inviolable Status Signifiers)
*   **Primary Action (Slate-900 / Indigo)**: `#0F172A` (Hover: `#1E293B`, Container: `#131B2E`)
*   **Secondary Actions**: `#515F74` (Container: `#D5E3FD`)
*   **Success (Emerald)**: `#10B981` (On-Success: `#FFFFFF`)
*   **Warning (Amber)**: `#F59E0B` (On-Warning: `#FFFFFF`)
*   **Error / Critical (Hyper Red)**: `#BA1A1A` (Container: `#FFDAD6`, On-Error: `#FFFFFF`, On-Error-Container: `#93000A`)

---

## 3. Typography
Legibility in data-heavy layouts is driven by the **Inter** font family, with **JetBrains Mono** reserved for technical data.

| Type Scale | Font Family | Font Size | Font Weight | Line Height | Letter Spacing | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Headline Large** | Inter | `24px` | 600 (Semi-bold) | `32px` | `-0.02em` | Main page titles |
| **Headline Medium** | Inter | `18px` | 600 (Semi-bold) | `24px` | `-0.01em` | Card & drawer headers |
| **Headline Small** | Inter | `14px` | 600 (Semi-bold) | `20px` | Normal | Table & list section headers |
| **Body Medium** | Inter | `14px` | 400 (Regular) | `20px` | Normal | Body text, descriptions |
| **Body Small** | Inter | `13px` | 400 (Regular) | `18px` | Normal | Data cells, secondary labels |
| **Label Caps** | Inter | `11px` | 600 (Semi-bold) | `16px` | `0.05em` | Table column titles (uppercase) |
| **Mono Label** | JetBrains Mono | `12px` | 400 (Regular) | `16px` | Normal | IDs, timestamps, log details |

---

## 4. Spacing & Grid (The 4px Rule)
All paddings, margins, gaps, and sizes must align to a strict 4px grid.

*   **Base Unit**: `4px`
*   **Density Compact**: `4px` (e.g., cell padding in high-density tables)
*   **Density Comfortable**: `12px` (e.g., standard button/input horizontal padding)
*   **Gutter**: `16px` (e.g., spacing between grid items)
*   **Container Padding**: `24px` (e.g., main content area outer margin)
*   **Sidebar Width**: `240px` (fixed-width sidebar navigation)

---

## 5. Shape & Corner Radii
*   **sm (`0.125rem` / `2px`)**: Very small components (checkboxes, status dots).
*   **DEFAULT (`0.25rem` / `4px`)**: Buttons, input fields, tags, mini cards.
*   **md (`0.375rem` / `6px`)**: Dropdowns, context menus.
*   **lg (`0.5rem` / `8px`)**: Large dashboard containers, main card blocks.
*   **xl (`0.75rem` / `12px`)**: Modals, large dialogue boxes.
*   **full (`9999px`)**: User avatars, pill-shaped status dots.

---

## 6. Depth & Elevation
*   **Level 0 (Background)**: `#F7F9FB` (Neutral-50) flat background.
*   **Level 1 (Default Card/Sidebar)**: Pure `#FFFFFF` card background + 1px `#C6C6CD` (outline-variant) or `#E2E8F0` border.
*   **Level 2 (Popovers/Modals/Command Palette)**: Pure `#FFFFFF` background + 1px `#C6C6CD` border + 4px blur shadow (`rgba(15, 23, 42, 0.05)`).
*   **Dimming Overlay**: `#0F172A` with `20%` opacity behind modals.
