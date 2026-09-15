# PM Plan — Plan/CI cutover

1. Add `create_plan_campaign()` to Campaign service.
2. Route execute-all through environment precheck + production guard + canonical adapter.
3. Remove PlanExecutionJob enqueue from execute-all, including async_mode.
4. Update legacy tests that asserted old job/TestExecution behavior.
5. Add architecture guards for execute-all and CI direct executor usage.
6. Run targeted/full regression, migration sanity, PR and merge.
