# Batch Design Spec — Legacy execution readonly endpoints

## Interaction design

The historical API task tab is an audit/history surface. It must not offer destructive or retry actions.

- Add a visible read-only notice: `历史执行记录只读；新执行与失败重跑请使用执行中心。`
- Add a secondary link/button to `/executions` labeled `前往执行中心`.
- Keep filtering, refresh, task detail, item curl and failure analysis.
- Remove cancel, retry and delete controls from task rows.

## API contract

For an owned legacy object, mutation routes return `410 Gone` with a message naming the canonical replacement. No database write occurs before the error.

- `POST /apitest/tasks/{id}/cancel`
- `POST /apitest/tasks/{id}/retry-failed`
- `DELETE /apitest/tasks/{id}`
- `POST /apitest/runner/tasks`
- `POST /apitest/runner/claim`
- `POST /apitest/runner/report`

Project isolation is checked first: foreign objects retain `404`; owned historical objects return `410`.

## UX copy

- Notice: `历史执行记录只读，仅用于审计与排障。`
- Replacement hint: `请前往执行中心查看 canonical ExecutionRun 或发起新执行。`
- No destructive confirmation dialog remains for historical tasks.

## Accessibility and consistency

- Use existing `Card`/`Button` primitives and semantic link navigation.
- No new visual tokens or dependency.
- The notice must be readable without relying on color alone.
