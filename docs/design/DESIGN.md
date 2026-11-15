# OpsSaathi AI: Design System & Tokens (Paytm-Like Clean UI)

**Phase:** U6 Frontend Redesign  
**Task:** U6-A2 Design Tokens & Guidelines  
**Author:** Antigravity  
**Status:** Approved Specification  
**Brand Compliance:** Inspired by clean Paytm for Business aesthetics. **No Paytm logo marks used.**

---

## 1. Brand Color Palette & Semantic Tokens

Our color tokens move completely away from the "neon cyberpunk" dark mode toward a **light, calm, authoritative fintech interface** built on Paytm's signature brand blues on a clean neutral foundation.

### Primary Brand Palette
```css
--paytm-navy:       #002E6E;  /* Primary headers, navigation background, solid brand buttons */
--paytm-navy-hover: #002352;  /* Button hover state */
--paytm-cyan:       #00BAF2;  /* Interactive accent, active tabs, action links, focus rings */
--paytm-cyan-light: #E5F6FD;  /* Tinted background for badges, active tab pills, selected items */
--paytm-cyan-hover: #00A3D6;  /* Cyan button hover state */
```

### Neutral Surface & Text Palette (Light Theme Foundation)
```css
--surface-canvas:    #F5F7FA;  /* App canvas background */
--surface-card:      #FFFFFF;  /* Card surface */
--surface-subtle:    #F0F3F7;  /* Secondary containers, input background */
--surface-border:    #E2E8F0;  /* Standard card and container borders */
--surface-divider:   #EDF2F7;  /* List item separators */

--text-primary:      #0F1E36;  /* High-contrast body, primary headers */
--text-secondary:    #4A5568;  /* Subtitles, secondary descriptions, table labels */
--text-muted:        #718096;  /* Timestamps, metadata, small auxiliary labels */
--text-disabled:     #A0AEC0;  /* Disabled text and placeholder */
```

### Semantic Status & State Chips
Every status in the case state machine maps to a clear, calm status token:

| State / Status | Background Token | Text / Icon Token | Border Token | Usage |
| :--- | :--- | :--- | :--- | :--- |
| `NEW` | `#EFF6FF` (`blue-50`) | `#1D4ED8` (`blue-700`) | `#BFDBFE` | Newly logged ticket |
| `IN_PROGRESS` | `#F0FDF4` (`green-50`) | `#15803D` (`green-700`) | `#BBF7D0` | Actively being investigated |
| `AWAITING_APPROVAL` | `#FFF7ED` (`orange-50`) | `#C2410C` (`orange-700`) | `#FED7AA` | Held for supervisor review (> ₹5K) |
| `APPROVED` | `#ECFDF5` (`emerald-50`) | `#047857` (`emerald-700`) | `#A7F3D0` | Supervisor granted approval |
| `VERIFYING` | `#EFF6FF` (`cyan-50`) | `#0284C7` (`cyan-700`) | `#BAE6FD` | Under read-only DB verification |
| `RESOLVED` | `#F0FDF4` (`emerald-50`) | `#15803D` (`emerald-800`) | `#86EFAC` | Confirmed ₹0 discrepancy |
| `REJECTED` | `#FEF2F2` (`red-50`) | `#B91C1C` (`red-700`) | `#FECACA` | Approval denied by supervisor |
| `CANCELLED` | `#F1F5F9` (`slate-100`) | `#475569` (`slate-600`) | `#CBD5E1` | Case withdrawn |

---

## 2. Typography & Script Support

### Font Stack
```css
font-family: 'Inter', 'Noto Sans Devanagari', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```
- **Latin:** Clean geometric sans (`Inter` / system-ui).
- **Indic Scripts (Hindi / Marathi):** Loaded from Google Fonts (`Noto Sans Devanagari`: weights 400, 500, 600, 700). Guarantees that conjuncts, matras, and currency characters (`₹`, `६`, `०`) render crisp without layout shift.

### Type Scale
- **Display / Balance:** `text-2xl` (24px) / `font-bold` / `tracking-tight` (for large settlement totals like ₹15,000.00).
- **Page Heading:** `text-lg` (18px) / `font-semibold` (for section headers, modal titles).
- **Section Heading:** `text-base` (16px) / `font-medium` (for card titles, list headers).
- **Body / Primary Text:** `text-sm` (14px) / `font-normal` (line-height 1.5).
- **Small / Metadata:** `text-xs` (12px) / `font-medium` (for status chips, dates, queue names).
- **Micro / Badge:** `text-[11px]` (11px) / `font-semibold` / `uppercase` (provenance badges: `PAYTM_STAGING`, `SYNTHETIC_DEMO`).

---

## 3. Spacing & Elevation Scale

### Spacing
- Micro: `gap-1.5` (6px) for badges and icon-text pairings.
- Compact: `p-2.5` / `gap-2` (8-10px) for list rows and chip groups.
- Standard: `p-4` / `gap-4` (16px) for card body padding and mobile screen gutters.
- Spacious: `p-6` / `gap-6` (24px) for desktop container layouts and modal bodies.

### Border Radius
- `rounded-lg` (8px): Inputs, buttons, status chips, dropdown items.
- `rounded-xl` (12px): Cards, alert banners, list container blocks.
- `rounded-2xl` (16px): Modals, bottom navigation sheets, prominent summary tiles.
- `rounded-full`: Avatar circles, pills, radio selectors.

### Elevation (Shadows)
- **Zero heavy drop-shadows.**
- Card resting: `shadow-sm` (`box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05)`).
- Card interactive hover: `shadow-md` (`box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08)`).
- Modal overlay: `shadow-xl` (`box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1)`).

---

## 4. Iconography Standards

- **Single Icon Family:** `lucide-react` only. No mix-and-match with FontAwesome or custom SVG blobs.
- **Sizes:**
  - Inline with small text: `w-3.5 h-3.5` (14px)
  - Standard button/menu icon: `w-4 h-4` (16px)
  - Card header / prominent icon: `w-5 h-5` (20px)

---

## 5. UI Do's and Don'ts

| Do | Don't |
| :--- | :--- |
| ✅ Show real numbers first: **Expected ₹15,000**, **Received ₹9,000**, **Pending ₹6,000**. | ❌ Don't show animated glowing blobs, purple glassmorphism, or developer traces on the home screen. |
| ✅ Use plain language: *"Settlement Issue"*, *"Checking with Bank"*, *"Waiting for Approval"*. | ❌ Don't use developer jargon: *"LangGraph checkpoint"*, *"Deterministic Decimal calculation"*, *"Anti-IDOR bounding"*. |
| ✅ Indian numbering format: `₹15,000.00` and `₹1,200.00`. | ❌ Don't write plain floats or western formatting like `$15000` or `15000.0`. |
| ✅ Clean white surfaces (`#FFFFFF`) with subtle `#E2E8F0` borders on `#F5F7FA` canvas. | ❌ Don't use pitch-black `bg-slate-950` dark backgrounds that look like a hacker terminal. |
| ✅ Put technical audit traces behind a clearly labeled **"Technical Details"** expander for judges. | ❌ Don't force merchants to look at SSE JSON streams before seeing their money status. |
| ✅ Mobile touch targets strictly $\ge$ 48px height. | ❌ Don't squeeze multiple small buttons horizontally on 390px screens. |
