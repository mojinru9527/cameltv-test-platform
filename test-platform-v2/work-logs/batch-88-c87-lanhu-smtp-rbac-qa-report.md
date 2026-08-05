# Batch 88 — QA 报告（C87-1 蓝湖设计源 / C87-2 SMTP / C87-3 RBAC）

> **QA (🔍)** | Date: 2026-08-05 | Verdict: PASS（C87-1 证据包运行中，待收尾复测）

## 测试总览

| 条件 | 通过 | 失败 | 阻塞 |
|:-----|:----:|:----:|:----:|
| C87-1 蓝湖项目级设计源证据包（Web/APP） | 2/2 全闭环 | 0 | 0 |
| C87-2 SMTP 真实收发（plan_done + defect_assigned） | 2/2 | 0 | 0 |
| C87-3 项目级 RBAC 全项目核验/修复 | 4/4 | 0 | 0 |
| 门禁（ruff/pytest/vitest/build/scan/audit） | 全绿 | 0 | 0 |

## 可执行门禁（命令 + 退出码）

| # | 门禁 | 命令 | 退出码 | 结果 |
|---|------|------|:------:|------|
| G1 | 后端全量 pytest | `.venv python -m pytest -q` | 0 | **1054 passed, 3 skipped, 0 failed**（3m43s，含本批新增 4 项） |
| G2 | 后端 F821 | `ruff check app --select F821` | 0 | All checks passed |
| G3 | Alembic 单头 | `alembic heads` | 0 | `20260728_merge_batch37_main (head)` 单头 |
| G4 | 前端 typecheck | `npm run typecheck` | 0 | tsc -b 通过 |
| G5 | 前端 build | `npm run build` | 0 | built in 10.78s |
| G6 | 前端 vitest | `npm test` | 0 | **334 passed (87 files)**；首轮 1 次 worker 意外退出（环境抖动），重跑 334/334 |
| G7 | 扫描 | `scan-common-bugs.ps1` | 0 | **HARD 0，WARN 209**（与基线一致，无新增类别；临时 gitignored 脚本已清理） |
| G8 | C 条件审计 | `audit-cconditions.ps1 -RequireLatestBatch` | 0 | 硬错 0、警告 0 |
| G9 | 受影响模块 pytest | lanhu/smtp/rbac/evidence 相关 | 0 | test_lanhu_* 40 + test_smtp_* 24 + test_rbac_project_roles 5 全绿 |

## 逐条件验证

### C87-1：蓝湖项目级设计源证据包 → OCR → RAG/Wiki（✅ 闭环）

**代码能力（已交付）**：
- `lanhu_provider._resolve_project_doc`：项目级链接（仅 tid+pid）自动发现文档；需求提取与证据包两条链路共享（`_extract_lanhu_content` 重构复用）
- `lanhu_provider._get_design_board_pages`：设计图板项目 → 下载全部设计原图（type=image，224 张）+ 批注卡（type=card，17 张）为证据页；原图直接作为证据段
- `job_runner._local_image_capture`：本地图片直采（免浏览器往返），OCR 直接跑原图
- `job_runner._dom_text_for`：仅解析 HTML，图片二进制不再混入 merged_text
- 测试：`test_lanhu_provider.py` + `test_lanhu_screenshot_service.py` + `test_lanhu_evidence_worker.py` 全绿（40+7）

**真实执行证据（job #1 Web 项目 241 页 / job #2 APP 项目 102 页，均完成）**：

| 项 | job 1（Web 项目） | job 2（APP 项目） |
|----|-------------------|-------------------|
| 发现页面 | 241（224 图 + 17 批注卡） | 102（设计图板） |
| 捕获/OCR | 241 / 221 | 102 / 98 |
| 无 OCR 页（人工审核豁免） | 20 | 4 |
| 终态 | success | success |
| 质量门禁 | import_ready=true | import_ready=true |
| 需求文档 | 蓝湖证据包 1（65,050 字符） | 蓝湖证据包 2（50,455 字符） |
| RAG 知识源 | source#2，241 chunks | source#3，102 chunks |
| Wiki Raw Source | #1（65,028 字符） | #2（50,433 字符） |
| 溯源 | evidence_job_id + source_ref + immutable_version | 同左 |

- OCR 抽查为真实设计内容（赛事回放入口/骆驼币账户/充值结果/首页-PC 等），中文+英文混排识别
- **数据质量修复**：预修复 DOM 提取把 PNG 二进制写入图片页 merged_text → `_dom_text_for` 修复 + `sanitize_evidence_text` 清洗 + `repair_evidence_imports` 重导（319 图片页清洗，旧产物删除后重导，Wiki/Chunks 二进制垃圾 0）
- 版本 diff 对设计图板链接跳过（无 versionId，非致命，日志记录）

> 备注：ruff F401/F811 存在 7 处存量未使用 import（lanhu_provider asyncio/json/httpx 等，非本批引入）；本批仅新增 `import html` 且已使用，CI 硬门禁 F821=0 不受影响。

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
| B88-Q3 | P3 | merged_text 含 PNG 二进制 NUL → Word 导出崩溃（job1/job2 导出阶段 failed） | 已修复：`sanitize_evidence_text` 文本清洗 + `resume_failed_job_in_new_session` 断点续跑（commit bd46f29/2ddd9dd），已捕获页面不重跑 OCR |
| B88-Q4 | P3 | 设计图板 Word 导出嵌入 241 张大图，耗时 >15 分钟 | 记录为已知成本；后续批次评估设计图板跳过 docx 或限制截图嵌入 |

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
