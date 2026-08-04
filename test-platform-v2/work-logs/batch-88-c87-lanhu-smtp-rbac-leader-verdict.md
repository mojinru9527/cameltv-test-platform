# Batch 88 — Leader Verdict（C87-1/2/3）

> **Leader (🎯)** | Date: 2026-08-05 | Decision: 有条件通过（C87-1 证据包运行中，收尾复测后 APPROVED）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | 完整批次（mode: full），三条件严格按 C-CONDITIONS 纳入，无范围蔓延 |
| 实现质量 | PASS | RBAC seed 矩阵补齐 + 51 项测试锁定；蓝湖项目级链接共享 helper + 设计图板分支，测试 40/40 |
| 证据 | PASS | C87-2 IMAP 真实收件、C87-3 全项目矩阵 + 行为验证、门禁全绿；C87-1 真实 OCR 页抽查通过 |
| 诚实性 | PASS | 链接实际项目名（APP_UI/WEB_UI）如实记录；OCR 空页/PNG 二进制瑕疵不掩盖 |
| 门禁 | PASS | ruff F821=0、pytest 1050、vitest 334、build OK、scan HARD=0、audit-cconditions 0 硬错 |
| 风险 | 低 | C87-1 证据包耗时（模型加载 ~20s/页）；外部项无新增 |

## 关键决策（已批准）

1. **tester 权限矩阵**按 Design §1.2 补齐（不含 system/project/manage/生产操作）；`lanhu_evidence:import` 仍留管理员（防止未审证据直入知识库）。
2. **蓝湖项目级链接**：设计图板优先（原图直采 OCR），无图板退回文档发现；docId 直链行为不变。
3. **SMTP**：`SMTP_FROM` 修正为发件邮箱（QQ 要求 From=登录邮箱），证书校验保持开启。
4. **证据包质量门禁不变**：每页需截图/文本/OCR 或人工审核；无 OCR 页走 `lanhu_evidence:review` 豁免。

## 抽检通过

- ✅ `seed.py` tester 矩阵 + `test_rbac_project_roles.py` 5/5（矩阵含 51 项必需、0 项越权）
- ✅ `lanhu_provider._resolve_project_doc` / `_get_design_board_pages` / `job_runner._local_image_capture` — 测试 40/40 + 真实 OCR 文本抽查（赛事回放/骆驼币账户等）
- ✅ `notify_service` SMTP 链路 — NotificationLog 2 条 sent + IMAP 真实收件两封
- ✅ 全项目 RBAC 矩阵 — 项目1/2 成员角色无空洞；项目内 200、跨项目 403、越权 403
- ✅ CI 分层：backend 域变更，本地双端全量兜底

## 判决

**有条件通过**：代码、测试、门禁与 C87-2/C87-3 证据齐备。C87-1 两个真实证据包任务后台运行中（预计 2–3h）；
完成后 QA 需补齐：质量门禁核对 → 无 OCR 页人工审核豁免 → 导入需求/RAG/Wiki → 溯源核对，再转 APPROVED 并进入一次总确认。

## 下一批次 Leader 条件

- 无新增阻断条件；C87-1 完成后关闭，剩余外部项（真机 CP-C1/C2、Test5）维持 Deferred。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 蓝湖项目级链接常为设计图板（241 张图+批注卡），非 Axure 文档 | 证据包新增图板分支（原图直采 OCR），避免「缺少 docId」死路 | `lanhu_provider._get_design_board_pages` + `job_runner._local_image_capture` |
| PaddleOCR 每页子进程加载模型 ~20s，241 页/项目耗时数小时 | 记录为已知成本；后续批次可评估常驻 OCR 服务 | QA 复盘卡 B88 |
| 用户链接 1/2 蓝湖侧实际项目名 APP_UI/WEB_UI（标注相反） | 如实记录，采集不受影响 | QA B88-Q2 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3d / 实际 2d（待证据包完成） | 0/0/0/3 | 1 | 外部依赖 + 工具链 | 证据包先小样测速再排期；OCR 成本计入批次工时 |

**技能使用**：`cameltv-agent-team`、`cameltv-bug-guard`、`cameltv-api-test`、`test-case-design`
