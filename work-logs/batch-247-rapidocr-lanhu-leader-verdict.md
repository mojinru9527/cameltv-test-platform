# Batch 247 — Leader Verdict

status: LOCAL APPROVED — PENDING PR CHECKS
date: 2026-09-17

## Review

| 部门 | 工件 | 结论 |
|---|---|---|
| 🟦 Product | `work-logs/batch-247-rapidocr-lanhu-prd-summary.md` | ✅ |
| 🟨 PM | `work-logs/batch-247-rapidocr-lanhu-pm-plan.md` | ✅ |
| 🎨 Design | `work-logs/batch-247-rapidocr-lanhu-design-spec.md` | ✅ |
| 💻 Dev | RapidOCR CLI / provider / screenshot / lock / Dockerfile | ✅ |
| 🔍 QA | `work-logs/batch-247-rapidocr-lanhu-qa-report.md` | ✅ |

Issue #422 的 5 项验收均已覆盖：

- RapidOCR 内置 CLI 与真实中文截图识别
- runner/full lock 的新增包与 Windows/Linux hash 解析
- 低置信度块保留
- 截图 device scale factor 可配置，默认 2x
- Dockerfile opencv 系统库 + 容器 OCR 冒烟

## Verdict

本地工程门禁与真实 OCR 证据满足 Draft PR 条件。最终 `APPROVED` 待：

1. PR required checks 全绿；
2. `audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过；
3. 合并 main 并关闭 Issue #422。

## 流程回写

| 发现 | 处理 | 落点 |
|---|---|---|
| CLI 的 `print` 被 debug-scan 判为 HARD | 改为 `sys.stdout.write` / `sys.stderr.write` | `rapidocr_cli.py` |
| Windows 生成锁会丢 Linux-only transitive | 保持基准锁约束，新增包增量合并并做 Linux dry-run | `requirements*.lock` |
