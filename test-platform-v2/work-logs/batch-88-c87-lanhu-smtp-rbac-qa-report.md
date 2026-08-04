# Batch 88 — QA 报告（C87-1 蓝湖设计源 / C87-2 SMTP / C87-3 RBAC）

> **QA (🔍)** | Date: 2026-08-05 | Verdict: PASS（C87-1 证据包运行中，待收尾复测）

## 测试总览

| 条件 | 通过 | 失败 | 阻塞 |
|:-----|:----:|:----:|:----:|
| C87-1 蓝湖项目级设计源证据包（Web/APP） | 1（代码+链路） | 0 | 1（job 运行中） |
| C87-2 SMTP 真实收发（plan_done + defect_assigned） | 2/2 | 0 | 0 |
| C87-3 项目级 RBAC 全项目核验/修复 | 4/4 | 0 | 0 |
| 门禁（ruff/pytest/vitest/build/scan/audit） | 全绿 | 0 | 0 |

## 可执行门禁（命令 + 退出码）

| # | 门禁 | 命令 | 退出码 | 结果 |
|---|------|------|:------:|------|
| G1 | 后端全量 pytest | `.venv python -m pytest -q` | 0 | **1050 passed, 3 skipped, 0 failed**（4m04s） |
| G2 | 后端 F821 | `ruff check app --select F821` | 0 | All checks passed |
| G3 | Alembic 单头 | `alembic heads` | 0 | `20260728_merge_batch37_main (head)` 单头 |
| G4 | 前端 typecheck | `npm run typecheck` | 0 | tsc -b 通过 |
| G5 | 前端 build | `npm run build` | 0 | built in 10.78s |
| G6 | 前端 vitest | `npm test` | 0 | **334 passed (87 files)**；首轮 1 次 worker 意外退出（环境抖动），重跑 334/334 |
| G7 | 扫描 | `scan-common-bugs.ps1` | 0 | **HARD 0，WARN 209**（与基线一致，无新增类别） |
| G8 | C 条件审计 | `audit-cconditions.ps1 -RequireLatestBatch` | 0 | 硬错 0、警告 0 |
| G9 | 受影响模块 pytest | lanhu/smtp/rbac/evidence 相关 | 0 | test_lanhu_* 40 + test_smtp_* 24 + test_rbac_project_roles 5 全绿 |

## 逐条件验证

### C87-1：蓝湖项目级设计源证据包 → OCR → RAG/Wiki（运行中）

**代码能力（已交付）**：
- `lanhu_provider._resolve_project_doc`：项目级链接（仅 tid+pid）自动发现文档；需求提取与证据包两条链路共享（`_extract_lanhu_content` 重构复用）
- `lanhu_provider._get_design_board_pages`：设计图板项目 → 下载全部设计原图（type=image，224 张）+ 批注卡（type=card，17 张）为证据页；原图直接作为证据段
- `job_runner._local_image_capture`：本地图片直采（免浏览器往返），OCR 直接跑原图
- `job_runner._dom_text_for`：仅解析 HTML，图片二进制不再混入 merged_text
- 测试：`test_lanhu_provider.py` + `test_lanhu_screenshot_service.py` + `test_lanhu_evidence_worker.py` 全绿（40+7）

**真实执行证据（job #1 Web 项目，运行中）**：
- 发现页面：**241**（224 设计图 + 17 批注卡），captured/OCR 持续推进，failed=0
- 抽查前 10 页：`capture=success ocr=success segs=1`，OCR 文本为真实设计内容（赛事回放入口 / 赛事回放详情 / 转账 / 骆驼币账户 / 充值结果 等）
- 已知质量点：1 页 `bg切图` OCR unavailable（纯背景图）→ 收尾按设计走 `lanhu_evidence:review` 人工审核豁免；4 页 merged_text 含 PNG 二进制（修复已合入，运行中任务不回改，证据以 OCR 文本为准）
- job #2（APP 项目）排队等待 #1 完成后执行

**待收尾**：job #1/#2 完成后：质量门禁（import_ready）→ 审核豁免无 OCR 页 → 导入需求/RAG/Wiki → 核对 Raw Source/知识源/追溯。

### C87-2：SMTP 真实收发（✅ 闭环）

- 配置落地：`backend/.env` SMTP 五件套（qq 587 STARTTLS，`SMTP_FROM=2602997810@qq.com` 修正 `pop.qq.com` 误填）；`.env.example` 模板已存在无需改动
- `POST /notify/test`（plan_done）→ `{"sent":1}`；`POST /defects` 指派（defect_assigned）→ 200
- `notification_log` 实查：2 条 `status=sent`
- **IMAP 收件验证**：`imap.qq.com:993` 登录成功，收件箱最后两封来自 `2602997810@qq.com`：`测试计划执行完成 — 测试计划(通知测试)` 与 `[P2] 缺陷指派 — C87-2 缺陷指派 SMTP 验证`
- 证据：[smtp-verification.md](evidence/batch-88/smtp-verification.md)

### C87-3：项目级 RBAC 全项目核验/修复（✅ 闭环）

- 根因：`seed.py::_TESTER_ACTIONS` 缺失 tester 业务权限 → 补齐 51 项（testcase/testplan/report/schedule/defect/requirement/dataset/review/mission/notify/uitest/avcheck），管理域不授予
- 存量库幂等：重启 `run_seed()` 自动补齐，RolePermission 无重复；重启前 403 → 重启后 200
- 全项目矩阵：项目 1（admin+tester）/ 项目 2（tester）无权限空洞
- 行为：项目内建用例 200/200（项目1、项目2）；非成员项目 403；建系统用户 403
- 测试：`test_rbac_project_roles.py` 5/5（含矩阵契约锁定）
- 证据：[rbac-matrix.md](evidence/batch-88/rbac-matrix.md)

## 缺陷与遗留

| # | 级别 | 内容 | 处理 |
|---|:----:|------|------|
| B88-Q1 | P3 | 设计图板 1 页纯背景图 OCR 为空（bg切图） | 收尾按设计人工审核豁免（lanhu_evidence:review） |
| B88-Q2 | P3 | 用户链接 1/2 在蓝湖侧实际项目名分别为 APP_UI / WEB_UI（与用户标注相反） | 不影响采集；QA/Leader 向用户如实说明 |
| B88-Q3 | P3 | 运行中证据任务 merged_text 含 PNG 二进制（4 页） | `_dom_text_for` 已修复（commit d3def0d），运行中任务不回改，OCR 文本为准 |

## CI 分层核对

本批变更域：`test-platform-v2/backend/**`（seed/lanhu_provider/job_runner/screenshot_service/tests）+ `test-platform-v2/work-logs/**`（docs）→ CI 按 backend 域运行后端 required + 扩展；本地已执行后端全量 + 前端全量（双端全量兜底）。

## 发布建议

状态：**NEEDS WORK →（证据包任务完成后转 READY）**

- 必修复：0
- 建议修复：B88-Q1 审核豁免、B88-Q2 链接命名说明、B88-Q3 已修复
- 阻断项：C87-1 job #1/#2 完成后质量门禁 + 导入证据（预计 1–3h 后台执行）

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3d / 实际 2d | 0/0/0/3 | 1（测试文件混入函数体已拆） | 外部依赖 + 工具链 | 证据包 OCR 先小样测速再全量跑；测试补丁用独立 hunk 避免函数体混入 |

**技能使用**：`cameltv-agent-team`（流水线）、`cameltv-bug-guard`（编码避坑）、`cameltv-api-test`（API 验证）、`test-case-design`（RBAC 矩阵用例）
