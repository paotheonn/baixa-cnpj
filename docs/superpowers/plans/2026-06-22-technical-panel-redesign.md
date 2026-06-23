# Technical Panel Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the local RF CNPJ web UI into a modern technical panel with clean typography, compact cards, and a professional light theme.

**Architecture:** Keep the existing single React client component and shadcn/ui primitives. Change only presentation, typography wiring, and layout hierarchy; preserve API calls, state shape, and form behavior.

**Tech Stack:** Next.js 16, React 19, Tailwind CSS 4, shadcn/ui, lucide-react.

---

## File Structure

- Modify `web/src/app/layout.tsx`: wire active Next font variables to the CSS token names used by Tailwind.
- Modify `web/src/app/globals.css`: update theme tokens and add utilities for the technical panel background/surfaces.
- Modify `web/src/components/pipeline-console.tsx`: reorganize the page into compact header, configuration cards, and execution sidebar without changing behavior.

### Task 1: Typography And Theme Tokens

**Files:**
- Modify: `web/src/app/layout.tsx`
- Modify: `web/src/app/globals.css`

- [ ] **Step 1: Wire font variables**

Change `layout.tsx` so the loaded fonts expose `--font-sans` and `--font-mono`, matching `globals.css`.

- [ ] **Step 2: Replace neutral default tokens**

Update `globals.css` root variables to use a light slate/blue technical palette, compact radius, and correct `--font-sans`/`--font-mono` references.

- [ ] **Step 3: Add technical background utility**

Replace the heavy grid with a subtle layered background utility and add optional utility classes for technical cards and code chips.

- [ ] **Step 4: Verify theme compiles**

Run `npm.cmd --prefix "web" run build`. Expected: Next build exits 0.

### Task 2: Pipeline Console Layout

**Files:**
- Modify: `web/src/components/pipeline-console.tsx`

- [ ] **Step 1: Keep state and API logic unchanged**

Leave `useState`, `useEffect`, `toggleTable`, `refreshOutputName`, and `submit` behavior intact.

- [ ] **Step 2: Replace hero with compact technical header**

Use a top bar with product label and badges for `Local`, `FastAPI`, and `CSV + Parquet`. Use a smaller title and concise description.

- [ ] **Step 3: Rebuild configuration cards**

Use dense sections for base/scope and auxiliary tables, with clearer labels and less whitespace.

- [ ] **Step 4: Rebuild execution sidebar**

Move output settings, cleanup, submit button, progress, command hints, errors, and result summary into a professional right-side execution panel.

- [ ] **Step 5: Preserve responsive behavior**

Use a single-column mobile layout and a two-column desktop workbench with a sticky sidebar.

### Task 3: Verification

**Files:**
- Verify: full project

- [ ] **Step 1: Run Python tests**

Run `python -m pytest -q`. Expected: all tests pass.

- [ ] **Step 2: Run web build**

Run `npm.cmd --prefix "web" run build`. Expected: Next build exits 0.

- [ ] **Step 3: Inspect changed files**

Run `git status --short` and review the modified UI files. Do not commit unless the user explicitly requests it.
