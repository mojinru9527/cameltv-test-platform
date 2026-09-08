# Execution entry ownership audit

Date: 2026-09-08. Scope: application code at this branch. This records reachable
call paths, not an assumption that every subprocess definition is an API.

| Entry | Owner / admission | Verification |
| --- | --- | --- |
| Playground compile/run and synchronous plan execution | Registered ExecutionRoute forwards to runner; browser execution takes heavy lease | Route registry tests; real authenticated/project-scoped HTTP browser smoke |
| Asynchronous plan execution | API persists PlanExecutionJob; runner claims it | Fresh-process tests; accept while runner down, complete after restart |
| UI jobs, Lanhu polling, API/DSH queued jobs, schedules | Shared task consumer lifecycle starts only in worker role | Ownership/queue/scheduler regressions |
| Direct XHR capture, native browser, Lanhu OCR | Heavy admission before subprocess; supervised process groups | Resource suite and actual Linux termination checks |
| DSH parent orchestration | Separate orchestration lane, retained until child lifecycle ends | DSH admission/timeout tests; real mixed-memory sizing still pending |
| Knowledge search/reembed | Registered HTTP forwarding, runner-only model load, heavy lease | RAG tests; real model container smoke |
| Scheduled knowledge catch-up | Runner only, optional 03:31 Asia/Shanghai, existing bounded batch | Filtering/idempotence/busy-deferral tests |
| Temporal browser work | Dedicated gateway, runner image, shared heavy-budget volume | Compose contracts; full live topology rehearsal still pending |

## Exempt definitions and why they are not newly routed

Application-wide symbol/import search finds `case_compiler_service` imported by
`test_plan_service._compile_ui_case`, which explicitly passes `validate=False`.
Its `_validate_spec` subprocess path is therefore not reached from that production
caller. The other importer, `LegacyPlaywrightCompilerAdapter.compile_legacy`, has
no application caller. Compiler validation remains a development/legacy adapter
path; wiring a future endpoint must add execution ownership first.

`BrowserRuntimeDriver` is a standalone definition with no application instantiation.
`ffmpeg_service`, `openvpn_service` and the duplicate application-side
`services/tencent_executor.py` have no application import/call sites in this scan.
They are not evidence of active production browser work, and deleting them would
not establish RAM savings. The live release executor is the separate
`deploy/release-console/tencent_executor.py` implementation.

The audit used application-wide symbol search and subprocess/launch/model-load
inventory (`execution-entry-inventory.log`, local). Route registry tests validate
actual aggregated FastAPI registration. No production data, permissions or
historical URLs were deleted. Full DSH/Temporal workload sizing remains a distinct
release prerequisite rather than being inferred from this static inventory.
