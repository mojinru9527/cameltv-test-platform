# Batch 231 - Design Spec

> Design | Date: 2026-09-06 | Status: Approved for implementation

## Truthful State Model

- `PASS` means verified evidence exists and satisfies the check.
- `FAIL` means evidence exists and violates the check.
- `NOT_EVALUATED` means required evidence or selection is absent.
- `BLOCKED` means execution was requested but an external/configuration prerequisite prevents it.
- UI labels, badges, counts, buttons, and toasts must reflect the same state. Zero denominators never render as PASS.

## Interaction Decisions

- Gate: Build and Campaign selects use non-empty sentinel values. Evaluate remains disabled until both real IDs are selected; a short inline reason names missing prerequisites.
- Version task: the existing three-step creation/review wizard remains the canonical way to adopt or modify plan items. Detail uses the latest run state; blocked or terminal tasks do not show an enabled run action.
- DSH/AI: readiness separates configuration, runtime availability, and verified provider health. Quota failure is visible before submission when known. Deterministic output carries a visible fallback label.
- Schedule: an already-running trigger uses warning/info feedback and links the message to the existing run ID.
- Environment: detail is a scannable definition list containing Base URL, access type, execution mode, and runner key. Missing values display `未配置`.
- API assets mobile toolbar: controls wrap into stable full-width rows below 640px; no absolute widths can overlap. Icon-only actions retain tooltips and accessible names.

## API And Data Decisions

- Route-owned identifiers are not duplicated as required request-body fields.
- Version-task lookup APIs accept `project_id` and scope at query time. Nested resource association is checked before every mutation.
- Scenario review actions map to canonical enum values; historical lowercase values are normalized on read and repaired by migration where persisted.
- Source refs are structured objects with positive persisted IDs. Rendering uses labeled fields, never Python repr strings.
- Coverage Guard mutates the selection into the effective FULL result in one transaction.
- Lineage names contract-version nodes as `CONTRACT_VERSION`; no fake embedded rule identity is invented.

## Responsive And Accessibility Baseline

- Validate 1440x900, 768x1024, and 390x844.
- No root horizontal overflow, overlapping filters, clipped status labels, inaccessible icon buttons, unhandled console errors, or hidden HTTP 404s.

