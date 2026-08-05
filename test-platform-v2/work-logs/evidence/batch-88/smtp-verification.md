# Batch 88 — SMTP 真实收发验证证据（C87-2 / J11）

> 日期：2026-08-05 | 环境：batch-88 worktree 后端 8044（独立 SQLite）

## 1. 配置落地

- `backend/.env`（gitignore，不入库）：`SMTP_HOST=smtp.qq.com`、`SMTP_PORT=587`、`SMTP_USER=2602997810@qq.com`、`SMTP_PASSWORD=<掩码>`、`SMTP_FROM=2602997810@qq.com`（修正 deploy/.env 中疑似误填的 `pop.qq.com`）、`SMTP_USE_TLS=true`、`SMTP_VERIFY_CERT=true`。
- `backend/.env.example` / `deploy/.env.example` 原本已含 SMTP 契约模板，无需改动（无 tracked diff）。

## 2. 发送验证（NotificationLog，SQLite 实查）

| id | channel | event | status | error | created_at |
|----|---------|-------|--------|-------|-----------|
| 1 | email（收件人 2602997810@qq.com） | `plan_done` | sent | （空） | 2026-08-04 16:40:33 |
| 2 | 同上 | `defect_assigned` | sent | （空） | 2026-08-04 16:40:51 |

- `POST /api/v1/notify/test` → `{"sent":1,"failed":0,"skipped":0}`（plan_done）
- `POST /api/v1/defects`（DEF-20260804-001，assignee_id=2）→ 200，触发 defect_assigned 后台通知

## 3. 收件验证（QQ IMAP，真实收件箱）

- `imap.qq.com:993` SSL 登录成功（使用 SMTP 授权码）
- INBOX 最后两封来自 `2602997810@qq.com`：
  - Subject：`测试计划执行完成 — 测试计划(通知测试)`（plan_done）
  - Subject：`[P2] 缺陷指派 — C87-2 缺陷指派 SMTP 验证`（defect_assigned）

## 4. 结论

C87-2（J11 邮件通知缺口）闭环：真实 SMTP 发送 + 真实收件箱收件均验证通过。
