# Universal Interaction Checklist

Use this as a coverage prompt, not as a mandatory all-items checklist for every control. Mark `Y / N / N/A / OPEN` and attach evidence for high-risk findings.

## A. Page / view
- Entry point is discoverable and destination is correct.
- Page title, current location, object identity and context are understandable.
- Initial state, loading, empty, partial, error, offline, permission-denied and expired states are handled where applicable.
- Content hierarchy, grouping, labels, units, truncation, overflow, scrolling and sticky regions remain understandable.
- Primary and secondary actions are visually and behaviorally distinguishable.
- Overlay, modal, drawer, tooltip and menu stacking/closing behavior is coherent.
- Direct URL/deep link, refresh, back/forward, share/reopen and session expiry behave as specified.
- Leaving with unsaved work warns or preserves draft according to product rules.

## B. Interactive controls
For each control, record: role/semantic name, trigger modality, supported states, action, feedback, side effect, cancel/retry path.
- Default/initial state is correct.
- Enabled/disabled/read-only state is correct and understandable.
- Focus/hover/pressed/selected/expanded/checked state is correct where applicable.
- Keyboard/touch/pointer/voice/physical control can activate it using supported platform conventions.
- Single, repeated, rapid, long-press and concurrent activation are handled as intended.
- Loading is visible and does not invite duplicate action when action is not repeatable.
- Success/failure feedback reflects the actual result.
- Failure preserves or resets previous state according to the defined rule.
- Cancel, undo, close, retry and recovery work where applicable.
- Result persists after refresh/reopen/re-entry when the business rule requires it.

## C. Forms and input
- Required/optional fields, formats, min/max, length, precision, range and cross-field rules.
- Empty, whitespace-only, leading/trailing spaces, Unicode, emoji, combining marks, RTL text, punctuation, very long strings.
- IME composition, paste, autofill, password manager, autocomplete, scan input and voice input where applicable.
- Validation timing (input/blur/submit) and exact error anchor/message.
- Soft keyboard does not cover the active field or primary action; focus and scroll move correctly.
- Repeated submission, slow response, timeout, network loss, retry and double-tap.
- Error correction retains valid input and does not silently discard data.

## D. Lists, tables and cards
- Empty/single/multiple/large datasets; long text; missing values; deleted/disabled records.
- Search, clear, filters, combined filters, sort, pagination, page-size changes and refresh.
- Selection across pages and selection invalidation after filters/data changes.
- Row click vs inline action click; context menu; batch action count/confirmation.
- Partial success/failure is transparent; retries do not duplicate changes.
- Concurrent changes, stale rows and deleted selected objects are handled coherently.

## E. Navigation and overlays
- Back/close/escape/system-back gesture returns to the correct prior context.
- Breadcrumb/tab/menu/deep-link destinations and active states match.
- Modal focus, initial focus, focus trap (when appropriate), focus return and screen-reader announcement.
- Backdrop click and ESC behavior match the design rule; destructive dialog cannot close accidentally if the action is in progress.
- Nested overlays and scroll locking do not cause inaccessible or unreachable content.

## F. Timing / lifecycle / resilience
- Slow network, offline, reconnect, timeout, server error, stale response, request cancellation.
- Background/foreground, page hide/show, app suspend/resume, process termination, desktop sleep/wake, device reboot.
- Time-zone and clock changes, expiration boundaries, daylight-saving changes where relevant.
- Debounce/throttle, delayed feedback, queued actions and out-of-order responses.
- Idempotency and compensation for retrying state-changing operations.

## G. Trust, security and access
- Role-appropriate visibility and availability of actions.
- Direct route/API cannot bypass denied permissions.
- Data scope cannot be widened by modifying IDs or filters.
- Destructive action clearly identifies target and consequences.
- External URL schemes/domains and download targets are safe and expected.
- Sensitive input is masked and not echoed in logs/screenshots.
- Permission prompts explain purpose and support deny/retry/settings recovery.

## H. Visual / responsive / accessibility
- Layout does not clip, overlap, hide, or misplace critical content across supported viewport/device settings.
- Text scaling, browser zoom, OS display scale, orientation and window resize do not break core tasks.
- Color is not the only state indicator; contrast and focus visibility meet chosen standard/profile.
- Keyboard order follows logical reading/task order; focus is not lost or obscured.
- Screen reader announces control name, role, value, state and error where applicable.
- Motion, sound, haptics and flashing can be understood or reduced as required by profile.
- Dynamic content and visual regression comparisons use tolerances and exclude nondeterministic regions.

## I. Admin → consumer linkage
- The admin action changes the intended object, version, placement, audience and schedule.
- Preview is clearly distinguished from production publishing.
- Approval and publish permissions are independently checked.
- Consumer API returns the intended version and fields.
- Resource URL resolves to the expected asset variant.
- C-end sees the correct state for guest/member/region/device/time where applicable.
- User action (click/download/play/submit) reaches the expected destination and produces the expected business event.
- Update, withdrawal, expiration and rollback propagate according to cache and consistency SLA.
