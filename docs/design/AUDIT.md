# OpsSaathi AI: UI/UX Design Audit (Before Redesign)

**Phase:** U6 Frontend Redesign  
**Task:** U6-A1 Design Audit  
**Auditor:** Antigravity  
**Date:** 15 November 2026  
**Screenshots Inspected:** `docs/design/before/` (`merchant_workspace_1440px.png`, `merchant_chat_390px.png`, `ops_console_1440px.png`, `evidence_breakdown_390px.png`, `case_timeline_1440px.png`, `approval_modal.png`, `integration_health_modal.png`)

---

## 1. Executive Summary

The initial OpsSaathi AI interface was engineered with high technical competence, but heavily favored a **dark-mode "cyberpunk / AI developer dashboard" aesthetic** over an authentic, calm Indian fintech product. 

For an MSME Kirana merchant in Pune or Jaipur, the dark `slate-950` backgrounds, neon cyan/purple glowing borders, and pervasive developer jargon (`LangGraph`, `SSE Stream`, `Trace Node`, `Cryptographic SHA-256`) create intimidation and cognitive friction rather than confidence and trust.

This audit evaluates the current UI against the **AI Slop Checklist** (UPSCALE_PLAN §7.2) and sets the baseline for the Paytm-inspired clean design system.

---

## 2. Evaluation Against the "AI Slop" Checklist

| Checklist Item | Current Status | Specific Violations Found | Severity |
| :--- | :---: | :--- | :---: |
| **1. Neon / Purple Gradients & Glowing Borders** | ❌ **High Violation** | `bg-slate-950/80 backdrop-blur-sm`, `border-purple-500/20`, cyan glowing badges (`bg-cyan-500/10 text-cyan-400 animate-pulse`), `border-slate-800`. Felt like a Web3/crypto dapp rather than Paytm. | **Critical** |
| **2. Icon-in-Circle Cards Repeated Everywhere** | ❌ **High Violation** | Every metric, card header, and button embeds a circular tinted icon box (`w-10 h-10 rounded-2xl bg-cyan-500/10 border border-cyan-500/20`). Creates visual noise without adding informational hierarchy. | **High** |
| **3. Tech Jargon on Merchant Screens** | ❌ **High Violation** | Merchant workspace exposes "LangGraph Run ID", "SSE Event Stream", "Discrepancy Engine", "Zero-Knowledge Verifier Role". Kirana merchants need plain Hindi/Marathi/English: "Settlement Status", "Expected", "Received", "Pending". | **Critical** |
| **4. Decorative Badges & Animated Pulses** | ❌ **Moderate Violation** | `animate-pulse` dots on "OPERATIONAL", "ONLINE", and "LIVE" status chips; over 6 simultaneous badges on a single case view (`OVERDUE`, `SYNTHETIC_DEMO`, `P1`, `AWAITING_APPROVAL`, `v1`). | **High** |
| **5. Walls of Text in Chat** | ⚠️ **Moderate Violation** | Multi-paragraph agent responses explaining internal node execution rather than answering the core question: *"Where is my ₹6,000?"* | **Medium** |
| **6. Inconsistent Spacing & Radii** | ⚠️ **Moderate Violation** | Mix of `rounded-2xl`, `rounded-3xl`, and `rounded-xl` across modals, cards, and buttons. Inconsistent padding (`p-4` vs `p-6` vs `p-3.5`). | **Medium** |
| **7. Lack of Paytm Brand Identity** | ❌ **High Violation** | Almost no Paytm Navy (`#002E6E`) or Paytm Cyan (`#00BAF2`). Dominated by generic Tailwind `slate-900` dark theme. | **High** |

---

## 3. Screen-by-Screen Usability & Layout Audit

### Screen 1: Merchant Home & Dashboard (`merchant_workspace_1440px.png` & `merchant_chat_390px.png`)
- **Viewport Issues at 390px:**
  - Layout was squeezed into two side-by-side columns on mobile or overflowed horizontally.
  - Chat input bar with mic and action chips crowded the small screen, making typing difficult with one thumb.
- **Cognitive Friction:**
  - The live trace panel ("Node Transitions: Intake -> Investigate -> Reconcile") was placed above the actual conversation, distracting the merchant from the actual settlement answer.
- **Dead Ends:**
  - No bottom navigation bar (`Home`, `Payments`, `Settlements`, `Help`) standard in financial apps like Paytm for Business.

### Screen 2: Operations Console (`ops_console_1440px.png`)
- **Strengths:**
  - Comprehensive queue view, filterable statuses, clear case timeline.
- **Usability Shortfalls:**
  - The split screen had too much vertical scrolling to reach the "Verify Resolution" button.
  - Cryptographic action hash (`44efa879046...`) was shown raw in full 64 characters without a human-readable summary ("Re-sync batch BATCH_01 for ₹6,000.00").
  - The "Simulate Bank Settlement" button looked like a primary production button rather than an explicit testing tool.

### Screen 3: Modals (Approval, Health, Case Creation) (`approval_modal.png`, `integration_health_modal.png`)
- **Usability Shortfalls:**
  - Full-screen dark overlays (`bg-slate-950/80`) caused dark-on-dark contrast fatigue.
  - Health modal contained deep technical infrastructure details (SQLAlchemy engine status, read-only pragma) that belong strictly in admin views, not general operations.

---

## 4. Required Design System Overhaul (Plan for U6-A2 to U6-A8)

1. **Brand Palette Shift:**
   - Migrate from `slate-950` dark mode to a **crisp, clean white and neutral light-grey foundation** (`#F5F7FA`, `#FFFFFF`).
   - Establish **Paytm Navy (`#002E6E`)** as primary brand color for navigation, headers, and primary buttons.
   - Establish **Paytm Cyan (`#00BAF2`)** as vibrant secondary accent for interactive highlights, active tabs, and primary action links.
   - Distinct, calm status colors:
     - Success / Resolved: Emerald (`#0A8754` / `#E8F8F0`)
     - In Progress / Verifying: Amber / Cyan (`#007EA7` / `#E5F6FD`)
     - Awaiting Approval / Overdue: Coral / Ruby (`#D9381E` / `#FDF0ED`)
     - Neutral / Secondary: Slate Neutral (`#5A6E85` / `#EDF2F7`)
2. **Typography & Script Support:**
   - Load **Noto Sans Devanagari** and clean geometric sans-serif to render Hindi (हिंदी) and Marathi (मराठी) without clipped ascenders or awkward glyph kerning.
3. **Information Architecture & Layout:**
   - **Merchant View (Mobile-First 390px):**
     - Native bottom navigation: `Home`, `Payments`, `Settlements`, `Help`.
     - Prominent Settlement Summary Card: Expected, Received, Pending.
     - Single primary action: *"Ask OpsSaathi"* or category chips (*"Settlement Delay"*, *"Refund Issue"*).
     - Move technical trace behind a collapsed *"Technical Evidence"* expander.
   - **Operations Console (Desktop-First 1440px):**
     - Professional, light-themed payments dashboard layout (left navigation sidebar, clean data table, split drawer for evidence).
