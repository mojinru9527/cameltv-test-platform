# Design Spec
ExecutionRun now owns runner lock state. Claim only selects QUEUED runs matching project and required capabilities.
Heartbeat/report require the same runner_id. Report accepts FINISHED/CANCELLED. Cancel is valid only while QUEUED/RUNNING.
