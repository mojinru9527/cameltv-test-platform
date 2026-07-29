---
title: "Batch 55 测试平台验收收尾用例"
owner: "qa-team"
created: "2026-07-29"
status: "executed"
tags: ["batch-55", "test-platform-v2", "acceptance-closure", "production-readiness"]
related:
  - "../../test-case-standards/生产级模块验收规则.md"
  - "BATCH47-测试平台需求服务-生产级验收.md"
  - "BATCH48-测试平台需求服务-生产级复测.md"
  - "../../../docs/superpowers/plans/2026-07-29-batch-55-acceptance-closure.md"
  - "../../../test-platform-v2/work-logs/batch-55-acceptance-closure-issue-register.md"
---

# Batch 55 测试平台验收收尾用例

> 基线：`origin/main@ad62aaecc1cc26ee8a54a8211a9b6336a5942eb3`。
> 分支：`fix/batch-55-acceptance-closure`；Agent Team / Codex；独立端口 `5193 → 8023`。
> 目标：证明 Batch 55 可合入的安全修复，并纠正旧分支的假阳性结论；本文件不替代 Batch 56 全平台生产验收。
> 状态：`PASS` / `FAIL` / `BLOCKED` / `NOT RUN`；阻塞和未执行不进入通过分母。

## 1. 放行边界

- 旧 `feature/batch-55-production-acceptance-and-fixes` 不合并、不 cherry-pick。
- C55-1、C55-2 只有在确定性测试和运行时证据都通过后才关闭。
- C55-3、C55-4、C55-5 保持 Open，直到 Batch 56 完成真实数据、真实浏览器、六主题全路由验收。
- 明文凭据、Token、Cookie、数据库和本地 `.ai-worktree.json` 不得进入提交。
- 一次性空库演练不能替代 A10 的真实旧 PostgreSQL 快照升级。
- 本轮全平台结论只要存在关键 `BLOCKED` 或 `NOT RUN`，即保持 `NEEDS WORK`。

## 2. 执行用例

| 用例 ID | A 规则 | 功能点 | 类型 / 优先级 | 操作与输入 | 可观察预期 | 实际结果 | 状态 |
|---|---|---|---|---|---|---|---|
| B55-CLEAN-001 | A01/A12 | 干净基线 | 安全/P0 | 从 `origin/main` 新建 Codex Agent Team 工作树并验证元数据 | 独立分支、端口、数据库；无旧提交历史 | verifier 退出码 0；基线与元数据已记录 | PASS |
| B55-CLEAN-002 | A11/A12 | 旧脚本处置 | 安全/P0 | 检查提交差异和 Pytest 收集范围 | 不包含 `qa_slice`、明文凭据、Token 片段或 tracked `.ai-worktree.json` | 旧分支判废；本分支独立重做 | PASS |
| B55-SEED-001 | A02/A04 | 首次种子账号 | Pytest/P0 | 临时 SQLite；动态配置 admin/tester 凭据；执行 seed | 两用户创建；存储哈希可验证；明文不落库 | 聚焦测试通过 | PASS |
| B55-SEED-002 | A02/A07 | 二次启动幂等 | Pytest/P0 | 对同一库再次执行 seed | 不再次哈希、不生成/输出替代凭据；原哈希不变 | 聚焦测试通过 | PASS |
| B55-SEED-003 | A04/A11 | 生产安全校验 | Pytest/负面/P0 | production 下留空 admin/tester 密码 | 启动配置校验同时报告两项并拒绝不安全配置 | 聚焦测试通过 | PASS |
| B55-PROXY-001 | A03/A11 | 代理边界 | Vitest/正负面/P0 | 表驱动匹配 `/api/v1`、`/api/v10`、`/api`、`/apitest`、`/api-keys` | 仅 `/api/v1` 及其子路径进入代理 | 6 组契约通过 | PASS |
| B55-PROXY-002 | A03/A11 | API 基址 | Vitest/边界/P1 | 未设置、空白、相对/绝对地址、尾斜杠 | 默认 `/api/v1`；直连地址保留 `/api/v1` 且无重复斜杠 | 7 组契约通过 | PASS |
| B55-PROXY-003 | A09 | `/apitest` 真实路由 | Playwright/回归/P0 | 真实 Vite 打开 `/apitest`，不注入登录态 | 文档为 SPA HTML 200；React 跳转 `/login`；出现真实表单 | Chromium 通过 | PASS |
| B55-PROXY-004 | A04/A09 | 真实后端代理 | Playwright/集成/P0 | 浏览器同源请求 `/api/v1/open/health` | JSON、HTTP 200、业务 code 0、status=ok | 5193 → 8023 通过 | PASS |
| B55-LOGIN-001 | A09 | 登录壳响应式 | Playwright/兼容/P0 | 1440×900、768×1024、390×844、320×568 打开登录页 | 标题/输入/按钮可见；横向溢出≤1px | 四视口通过并采集脱敏截图 | PASS |
| B55-LOGIN-002 | A09 | 登录壳无障碍/运行时 | Playwright/a11y/P1 | 四视口执行 Axe；监听 console/pageerror/requestfailed | serious/critical=0；三类运行时错误集合为空 | Chromium 通过 | PASS |
| B55-LOGIN-003 | A09/A12 | 字体色边归因 | 对照实验/P2 | 检查 computed style、无 CSS 控制页、`--disable-lcd-text` 控制页 | 若为 ClearType，项目 CSS 无阴影/滤镜，关闭 LCD 文字后色边消失 | 三项均符合；归类非缺陷 | PASS |
| B55-DB-001 | A10/A12 | 迁移恢复手册 | Pytest/文档/P1 | 检查备份/恢复、唯一 head、显式降级、行数、冒烟、staging、A10 声明 | 所有安全操作均可检索；禁止相对 `-1` 和生产 `downgrade base` | 文档契约通过 | PASS |
| B55-DB-002 | A10/A11 | 空库升级 | Alembic/P0 | 一次性 SQLite 执行 heads/current/upgrade head | 唯一 head；升级退出码 0；current 到 head | 通过 | PASS |
| B55-DB-003 | A10/A11 | 显式降级再升级 | Alembic/恢复/P1 | head → `20260727_batch48_pg_parity` → head | 指定目标成功；合并父 revision 可见；再升级成功 | 通过 | PASS |
| B55-DB-004 | A10/A11 | ORM/迁移漂移 | Alembic+Pytest/P0 | 空库升级后运行 `alembic check`；读取计划用例详情 | 零漂移；`source_req_id` 存在且不会触发 AttributeError | 红灯复现后修复；check 退出码 0 | PASS |
| B55-DB-005 | A10 | 真实旧库升级 | PostgreSQL/P0 | 脱敏旧 PostgreSQL 快照升级、行数/索引/应用冒烟 | 历史数据完整；零漂移；应用可用 | 未提供脱敏旧库快照与验收连接 | BLOCKED |
| B55-DEEP-001 | A03-A08 | Knowledge/Wiki/Trace 深层功能 | API+DB/P0 | 真实数据正面/负面、事务、审计、跨项目、幂等与分页 | 每个功能点有唯一预期及 DB/审计副作用证据 | 旧脚本证据作废；安排 Batch 56 | NOT RUN |
| B55-FLOW-001 | A03-A09 | 五条关键用户旅程 | Playwright/P0 | 用例→计划→执行→报告；定时任务；缺陷状态机 | 真实浏览器、真实后端、状态回读、清理和网络证据 | 旧 API-only 证据作废；安排 Batch 56 | NOT RUN |
| B55-THEME-001 | A09 | 六主题全平台 | Playwright+视觉/P0 | 六主题、支持的明暗模式、静态/动态路由、三视口 | 页面语义、截图、Axe、键盘、溢出、网络和控制台全部通过 | 旧源码扫描证据作废；安排 Batch 56 | NOT RUN |
| B55-EXT-001 | A01/A03/A09/A12 | 外部环境与客户输入对照 | 只读验收/P0 | 按环境账号汇总文档及其索引的 PRD、蓝湖证据、基线/后台用例、追溯矩阵和 OpenAPI 执行 | 生产只读；测试写操作使用贴近客户输入的专用可清理数据；Mock 不计生产通过；阻塞不计通过 | 本轮未执行；安排 Batch 56 | NOT RUN |
| B55-GATE-001 | A11/A12 | 双端全量门禁 | 自动化/P0 | 后端 F821+全量 Pytest；前端 typecheck+Vitest+build+依赖审计 | 无新增失败；精确记录既有失败/漏洞 | 后端 830 passed/3 skip；前端 203 passed；构建通过；2 moderate observation | PASS |

## 3. A01–A12 状态

| 规则 | 状态 | 证据 / 缺口 |
|---|---|---|
| A01 基线追溯 | PASS | Batch 47/48、`origin/main` SHA、旧分支问题和本分支提交可追溯 |
| A02 隔离环境 | PASS | 独立工作树、5193/8023、一次性 SQLite、动态测试凭据 |
| A03 正负面全功能 | NOT RUN | 本轮只覆盖 seed/proxy/login/迁移；全模块安排 Batch 56 |
| A04 API 三类校验 | NOT RUN | health 与 seed 已覆盖；全 API 输入/业务/返回未完成 |
| A05 RBAC/项目隔离 | NOT RUN | 依赖已有领域测试，尚未做 Batch 56 全模块矩阵 |
| A06 UI/API/DB/审计事务 | NOT RUN | 跨模块业务旅程未执行 |
| A07 幂等/并发/重试 | NOT RUN | seed 幂等已通过；全模块矩阵未执行 |
| A08 分页/搜索/count | NOT RUN | 全模块大数据矩阵未执行 |
| A09 浏览器/a11y/network | NOT RUN | 登录壳局部通过；全路由、全旅程、六主题未执行 |
| A10 真实旧库迁移 | BLOCKED | 空库双向契约通过；缺脱敏旧 PostgreSQL 快照 |
| A11 自动化/供应链 | PASS | 双端全量、F821、typecheck、build、Playwright 通过；2 moderate、0 high/critical 已记录 |
| A12 文档/证据一致性 | PASS | 旧假阳性已纠正；用例、问题、QA、Leader 与脱敏证据索引一致 |

## 4. 当前判定

- C55-1：证据满足，可关闭。
- C55-2：运行手册、显式降级、再升级和零漂移满足，可关闭；A10 真实旧库部分仍单独 `BLOCKED`。
- C55-3、C55-4、C55-5：证据不满足，保持 Open。
- Batch 55 收尾分支的局部修复结论：`PASS`，等待用户逐次 push 授权和 PR checks。
- 测试平台全功能生产交付结论：`NEEDS WORK`，必须进入 Batch 56。
