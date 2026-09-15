# Design Spec — Plan Campaign adapter

```
TestPlan + TestPlanCase + TestCase(api)
  -> create_plan_campaign()
  -> TestCampaign + CampaignItem
  -> start_campaign()
  -> existing ExecutionRun
```

- `environment_id` is required for API cases and validated by `ensure_plan_execution_ready`.
- Production environments require `confirm_prod=true` through `require_allowed_operation`.
- `async_mode` is response metadata only; no background PlanExecutionJob is persisted.
- Non-API cases are counted as skipped in this slice and remain on their existing path.
