# AIQE V1.6 独立验收记录（V16-025 / Gate G）

本目录存放**非原作者**的独立验收签署记录。审计（2026-11-24）指出矩阵曾把全部
条目标为 VERIFIED（70 条）、其中 60 条 reviewer=pending，且 V16-025 的
owner=reviewer=tech-lead，不能证明独立验收，因此：

- 追踪矩阵 `docs/aiqe/v1.6/traceability/requirements.yaml` 只声明需求/代码/测试/证据；
- 独立验收只能通过本目录的 `records/<REQ-ID>.json` 产生；
- `scripts/aiqe/check_traceability.py --release-gate` 要求 P0/P1 全部 REVIEWED；
- `scripts/aiqe/release_verdict.py` 的 Gate B–G `acceptance` 字段由这些记录决定。

## 记录格式（`records/<REQ-ID>.json`）

```json
{
  "requirement_id": "V16-001-R1",
  "decision": "REVIEWED",
  "reviewer": "qa-lead",
  "reviewed_at": "2026-11-24",
  "artifact": "docs/aiqe/v1.6/acceptance/reviews/V16-001-R1-qa-lead.md"
}
```

- `decision`：`REVIEWED` 或 `WAIVED`；
- `reviewer`：必须在 `governance/review-roles.yaml` 注册，且角色域 ≠ 需求 owner 角色域；
- `artifact`：人工评审记录（仓库内文件，含检查项、结论、证据链接、签名/日期）；
- `WAIVED` 额外需要 `waiver_reason` 与 `waived_by`。

## 角色矩阵

`governance/review-roles.yaml` 定义 owner/reviewer → 角色域（engineering / qa / security /
platform / ops / ai / leadership / user）。同一角色域不得互签：
例如 owner=`backend-security`(engineering) 必须由 qa/security/leadership 角色签署。

## 操作步骤

1. Reviewer 阅读需求、代码、测试与运行证据，把结论写入
   `docs/aiqe/v1.6/acceptance/reviews/<REQ-ID>-<reviewer>.md`（建议包含：
   需求与不变量复核、生产入口调用链、测试是否覆盖失败路径、证据可反查性、遗留风险）。
2. 用 CLI 生成记录：

   ```powershell
   python scripts/aiqe/record_acceptance.py `
     --requirement V16-001-R1 `
     --reviewer qa-lead `
     --reviewed-at 2026-11-24 `
     --artifact docs/aiqe/v1.6/acceptance/reviews/V16-001-R1-qa-lead.md `
     --decision REVIEWED
   ```

3. 运行门禁并提交记录 + 评审文档：

   ```powershell
   python scripts/aiqe/check_traceability.py --strict-warnings --check-baseline
   python scripts/aiqe/release_verdict.py --write
   python scripts/aiqe/check_release_audit.py
   ```

## 红线

- 不得由 Agent 或需求 owner 自行填写 `REVIEWED`；
- 不得把“用户口头确认”直接写成 REVIEWED（需落评审文档并明确 reviewer 与日期）；
- 记录一旦提交即作为发布证据，修改需 `--force` 并保留变更说明。
