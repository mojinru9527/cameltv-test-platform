# Leader Verdict — Legacy readonly production evidence

> Batch: `legacy-readonly-evidence` | Mode: light | Decision: **APPROVED**

## Review

| Area | Verdict | Evidence |
|---|---|---|
| Scope | ✅ | Evidence/gate-only change |
| Readonly URL gate | ✅ | Four authenticated production probes returned 410 |
| Historical mapping | ✅ | API 1999/1999, UI 203/203 |
| Restore drill | ✅ | Production dump restored and verified in isolation |
| Zero-write observation | ✅ current | No Legacy new/update, fingerprints unchanged |
| Deletion safety | ✅ | Deletion remains blocked by zero-cycle and signoff flags |

No C condition is added. PR-09 deletion remains deferred until the observation and signoff gates are satisfied.

## 流程回写

| 发现 | 处理 | 落点 |
|---|---|---|
| Production readonly verification was not reflected in the machine gate | Set `legacy_urls_readonly_or_redirect=true` with evidence | `legacy_delete_gate.json`, production evidence work-log |
