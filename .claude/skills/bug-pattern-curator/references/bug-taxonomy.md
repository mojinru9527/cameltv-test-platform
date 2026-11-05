# Bug Taxonomy — classification vocabulary for imported real defects

This taxonomy is only a classification vocabulary. It is not a list of CamelTV bugs and it does not itself authorize new test cases. A label becomes a project historical pattern only after real Bug evidence is imported and summarized in the primary generator's Pattern Library.

## 1. User-visible symptom
- `UI-RENDER`: missing/incorrect/duplicate visual content, clipping, overlap, incorrect state rendering.
- `NO-RESPONSE`: action appears inert or feedback absent.
- `WRONG-ACTION`: wrong target, unintended navigation/action, click region too large/small.
- `WRONG-DATA`: stale, incorrect, mixed-version, missing or duplicated data.
- `DATA-LOSS`: unsaved input/draft/selection/progress lost.
- `BLOCKED-FLOW`: user cannot continue/exit/recover.
- `MISLEADING-FEEDBACK`: UI reports success/failure/loading inconsistent with actual state.
- `ACCESS-DENIED-ERROR`: wrong visibility, authorization, data scope or entitlement.
- `ACCESSIBILITY-BLOCK`: keyboard, focus, screen reader, contrast, scaling, alternative input.
- `PERFORMANCE-LAG`: slow response, freeze, jank, timeout, high resource usage.
- `CRASH-RESET`: crash, restart, unexpected reload, device reboot, process termination.
- `RESOURCE-FAILURE`: image/document/video/file unavailable or corrupted.

## 2. Interaction failure pattern
- `DOUBLE-ACTION`: double click, repeated submit, duplicate request/record/payment.
- `RACE-CONDITION`: concurrent edits, stale response overwrites newer state, order-sensitive events.
- `STATE-DRIFT`: UI/client/server/cache/device state mismatch.
- `STUCK-LOADING`: spinner/progress never completes or wrong progress.
- `FOCUS-NAVIGATION`: focus loss, wrong tab order, ESC/back behavior, focus obscured.
- `GESTURE-CONFLICT`: scroll vs swipe, back gesture, drag/drop, long-press, touch target.
- `FORM-VALIDATION`: wrong timing, wrong field, missing boundary, incorrect normalization.
- `MODAL-LAYERING`: z-index, overlay, scroll lock, close behavior, nested dialogs.
- `ROUTE-RETURN`: deep link, refresh, browser history, page stack, redirect context.
- `UNSAVED-CHANGE`: no save warning, autosave failure, stale editor, overwrite conflict.
- `BULK-OPERATION`: selection scope, partial success, wrong count, batch retry.
- `FEEDBACK-TIMING`: feedback too early/late/transient or not tied to action.
- `CONTENT-TARGETING`: wrong audience, placement, locale, device, ordering or campaign.

## 3. Likely mechanism (only when evidence supports)
- `FRONTEND-STATE`, `EVENT-HANDLER`, `VALIDATION-RULE`, `ROUTING`, `CSS-LAYOUT`, `RESPONSIVE-BREAKPOINT`, `ACCESSIBILITY-SEMANTICS`.
- `API-CONTRACT`, `AUTHORIZATION`, `SESSION-EXPIRY`, `DATA-MAPPING`, `DATABASE-CONSISTENCY`, `CACHE-INVALIDATION`, `CDN-PROPAGATION`.
- `ASYNC-QUEUE`, `IDEMPOTENCY`, `RETRY-COMPENSATION`, `TIMEZONE-SCHEDULER`, `FILE-PROCESSING`, `MEDIA-TRANSCODE`.
- `PLATFORM-LIFECYCLE`, `OS-INTEGRATION`, `DEVICE-CAPABILITY`, `FIRMWARE-STATE`, `SENSOR-INPUT`, `ACTUATOR-FEEDBACK`.
- `THIRD-PARTY-INTEGRATION`, `NETWORK-RESILIENCE`, `PERFORMANCE-CAPACITY`, `SECURITY-INPUT-HANDLING`.

## 4. Platform context

`WEB`, `MOBILE-WEB`, `MINI-PROGRAM`, `IOS`, `ANDROID`, `WINDOWS`, `MACOS`, `LINUX`, `DESKTOP-APP`, `PC-SOFTWARE`, `HARDWARE`, `EMBEDDED`, `IOT`, `MULTI-PLATFORM`.

环境标签按证据选择：`LOW-END-DEVICE`, `SMALL-VIEWPORT`, `HIGH-DPI`, `ROTATION`, `WEAK-NETWORK`, `OFFLINE`, `BACKGROUND-RESUME`, `MULTI-WINDOW`, `IME`, `SCREEN-READER`, `TOUCH`, `KEYBOARD`, `VOICE`, `REMOTE-CONTROL`。
