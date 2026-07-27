# Batch E (Sprint 0.6) — Design Spec

> **Design Department (🎨)** | Date: 2026-07-02 | Status: Done

---

## Overview

Batch E is the P1 security final regression. Design impact is minimal — C5 and C6 are code/process, C7 is audit verification, C8 is backend testing.

## Design Touchpoints

### C7: Accessibility Audit Fixes

If axe-core finds violations, potential fixes:

| Violation | Likely Fix | Priority |
|-----------|-----------|----------|
| Form inputs missing labels | Add `aria-label` or `<label htmlFor>` | Critical |
| Color contrast insufficient | Use `text-muted-hc` / `border-hc` tokens from S8a | Serious |
| Missing landmark roles | Add `role="navigation"`, `role="main"` etc. | Moderate |
| Link text not descriptive | Add `aria-label` to icon-only links | Serious |

**Design tokens already available** (from batch D S8a):
- `--text-muted-high-contrast: hsl(215 16% 35%)` → Tailwind `text-muted-hc`
- `--border-high-contrast: hsl(215 16% 55%)` → Tailwind `border-border-hc`

**Focus visible** (from batch D S8b):
- Global `*:focus-visible` ring in `globals.css`

No new design tokens or components needed for this batch.

## No New UI Components

Batch E does NOT introduce any new UI components. All work is:
- C5: Hook fix (no visual change)
- C6: Documentation (no visual change)
- C7: Audit + minor markup fixes (no visual change)
- C8: Backend test suite (no visual change)

## Design Sign-off

✅ **Approved** — No design review needed. Proceed to Dev.
