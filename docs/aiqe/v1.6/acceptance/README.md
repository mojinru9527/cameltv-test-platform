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
- `WAIVED` 额外需要 `waiver_reason`、`waived_by`、`approved_by`、`waiver_expires_at`。

### V1.6.2 起：GA 模式必须绑定真实 GitHub Reviewer（FIX-014）

角色别名（`qa`/`security`）只是职责标签，**不再作为身份认证依据**。
`release_verdict.py` 在 GA 模式下使用 `require_github_identity=True`，记录还必须包含：

```json
{
  "reviewer": "security",
  "reviewer_login": "MoojinR",
  "reviewer_user_id": 12345678,
  "pr_number": 641,
  "review_id": 3456789012,
  "review_state": "APPROVED",
  "reviewed_commit_sha": "<40-hex current head>",
  "review_submitted_at": "2026-11-26T01:20:00Z"
}
```

- `reviewer_user_id` 必须是 GitHub numeric user id；与作者/实现者相同则拒绝；
- `reviewed_commit_sha` 必须等于被验收的精确 commit，push 后 stale review 必须重新审批；
- `review_id` 必须能通过 GitHub API 在线回查 `state/commit_id/user.id/user.login`；
- 缺 `review_id`、无法在线回查、`review_state != APPROVED` 时记录不得 `ACCEPTED`；
- 存量仅含 `reviewer: <角色>` 的记录保留为历史，但 GA 模式下为 `PENDING`，不得当作已完成。

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
