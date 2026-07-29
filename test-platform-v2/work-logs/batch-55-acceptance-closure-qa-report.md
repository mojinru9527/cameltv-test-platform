---
title: "Batch 55 验收收尾 QA 报告"
owner: "qa-team"
last_reviewed: "2026-07-29"
status: "executed"
tags: ["batch-55", "qa", "acceptance-closure", "production-readiness"]
related:
  - "../../tests/test-cases/functional/BATCH55-测试平台验收收尾.md"
  - "batch-55-acceptance-closure-issue-register.md"
  - "evidence/batch-55-acceptance-closure/README.md"
---

# Batch 55 验收收尾 QA 报告

## 结论

| 结论对象 | 判定 | 说明 |
|---|---|---|
| 本分支的安全收尾与缺陷修复 | PASS | 旧分支未进入历史；代理、种子账号、迁移漂移、计划详情、登录壳和后台线程均有行为测试 |
| C55-1 `/apitest` 代理问题 | PASS / CLOSED | Vitest 代理边界 + 真实 Vite/FastAPI Playwright 均通过 |
| C55-2 迁移降级文档 | PASS / CLOSED | 运行手册、显式修订降级、再升级、唯一 head 和零漂移通过 |
| C55-3～C55-5 | NOT RUN / OPEN | 旧 `qa_slice` 证据作废；进入 Batch 56 全平台验收 |
| 测试平台全功能生产交付 | NEEDS WORK | A03～A09 未完成全模块矩阵，A10 真实旧库阻塞，外部环境未执行 |

本报告不使用“HTTP 200”“可接受 422”“无数据视为通过”或“源码存在”替代业务验收。

## 版本与环境

| 项 | 值 |
|---|---|
| 基线 | `origin/main@ad62aaecc1cc26ee8a54a8211a9b6336a5942eb3` |
| 当前代码提交 | `b48e3aceed42454582b6abebf26b39d49963e86b` |
| 分支 | `fix/batch-55-acceptance-closure` |
| 工作流 / 执行器 | Agent Team / Codex |
| 本地浏览器链路 | `http://127.0.0.1:5193 → http://127.0.0.1:8023` |
| 数据 | 一次性 SQLite + 动态测试凭据 |
| 浏览器 | Playwright Chromium |

## 已修复问题

1. Vite 不再以宽泛 `/api` 前缀吞掉 `/apitest`；代理边界为 `^/api/v1(?:/|$)`。
2. 默认代理端口与 README 统一为 `8000`，独立工作树继续用 `.env.local` 覆盖。
3. Axios 与审计 CSV 下载共用 API 基址，消除 `undefined/system/...`。
4. admin/tester 凭据只在缺少种子用户时生成和散列，二次启动不再打印无效替代密码。
5. production 同时要求 `ADMIN_PASSWORD` 与 `TESTER_PASSWORD`。
6. Alembic 演练发现 `test_case.source_req_id` 已存在于迁移但丢失于 ORM；已恢复模型、Schema 和计划详情行为。
7. Agent queue processor 新增显式停止与线程 join，修复全量 Pytest 汇总后仍访问已销毁数据库的噪声。
8. API task worker 接入 FastAPI 生命周期，并仅在线程真实退出后清除句柄，修复跨测试数据库访问。
9. 登录页改为 `100dvh`、响应式最大宽度和主题令牌背景，并补充一级标题语义。
10. 青橙文字边经对照确认是 Windows Chromium ClearType，不做破坏性 CSS 伪修复。

## 自动化结果

### 后端

| 命令 | 状态 | 结果 |
|---|---|---|
| `ruff check app/ --select F821` | PASS | 退出码 0 |
| seed/security/runbook 聚焦 Pytest | PASS | 46/46 |
| testplan/migration 聚焦 Pytest | PASS | 15/15；迁移唯一 warning 已记录 |
| Agent queue/permission/locking 聚焦 Pytest | PASS | 57/57 |
| `python -m pytest -q`（修复后台线程前） | OBSERVATION | 831 collected；828 passed；3 skipped；退出码 0；汇总后有一次后台线程 DB 噪声 |
| API task worker + seed 聚焦 Pytest | PASS | 20/20；退出码 0 |
| `python -m pytest -q`（线程修复后） | PASS | 833 collected；830 passed；3 skipped；0 failed；退出码 0；汇总后无后台线程或 `no such table` 噪声 |

三个 skip 均为未显式启用 Batch 48 PostgreSQL 集成环境：

- `test_parallel_import_is_idempotent_and_counts_do_not_drift`
- `test_parallel_admin_link_requests_return_one_success_and_conflicts`
- `test_parallel_module_extraction_converges_on_one_tree`

### 前端

| 命令 | 状态 | 结果 |
|---|---|---|
| `npm run typecheck` | PASS | 初次发现 TS6305；共享配置移出 app compilation 后退出码 0 |
| `npm test` | PASS | 48/48 文件；203/203 测试 |
| `npm run build` | PASS | Vite 3349 modules transformed；退出码 0 |
| 聚焦代理/API 基址 Vitest | PASS | 13/13 |
| `batch55-proxy-login.spec.ts` | PASS | Chromium 1/1；四视口、Axe、运行时错误与真实 health 代理 |
| `npm audit --omit=dev` | OBSERVATION | 2 moderate；0 high/critical；退出码 1 |
| `npm audit` | OBSERVATION | 同上；没有新增依赖或 lockfile 变更 |

两个 moderate 均来自现有 `react-router`。npm 只提供强制升级 `react-router-dom@7.18.2` 的破坏性修复；本收尾分支不在无迁移方案时跨 major 升级。该风险进入 Batch 56 依赖升级验证，不影响当前“无 high/critical、无新增依赖”的范围判定。

## 真实浏览器结果

| 检查 | 结果 |
|---|---|
| `/apitest` 文档响应 | SPA HTML，HTTP 200 |
| 未登录 React 路由 | 跳转 `/login` |
| `/api/v1/open/health` | 经 Vite 到后端；JSON、HTTP 200、code 0、status ok |
| 1440×900 | 无横向溢出；关键控件可见 |
| 768×1024 | 无横向溢出；关键控件可见 |
| 390×844 | 无横向溢出；关键控件可见 |
| 320×568 | 无横向溢出；关键控件可见 |
| Axe | serious/critical 0 |
| console.error | 0 |
| pageerror | 0 |
| requestfailed | 0 |

截图保存在本机临时脱敏证据目录 `C:\Users\26029\AppData\Local\Temp\batch55-acceptance-closure-evidence`，不含凭据或用户数据，不进入 Git。

## 迁移演练结果

| 步骤 | 结果 |
|---|---|
| `alembic heads` | 唯一 head：`20260728_merge_batch37_main` |
| 空库 `upgrade head` | PASS |
| 显式 `downgrade 20260727_batch48_pg_parity` | PASS；合并点的两个父 revision 可见 |
| 再次 `upgrade head` | PASS |
| 初次 `alembic check` | FAIL：ORM 丢失 `test_case.source_req_id` |
| 恢复 ORM/Schema 后 `alembic check` | PASS：No new upgrade operations detected |
| 计划详情读取关联用例 | PASS：不再 AttributeError，`source_req_id` 可返回 |
| 真实旧 PostgreSQL 快照 | BLOCKED：未提供脱敏快照和验收连接 |

## A01–A12 判定

| 规则 | 状态 |
|---|---|
| A01 | PASS |
| A02 | PASS |
| A03 | NOT RUN（全模块安排 Batch 56） |
| A04 | NOT RUN（局部通过，全 API 未覆盖） |
| A05 | NOT RUN |
| A06 | NOT RUN |
| A07 | NOT RUN（seed 幂等局部通过） |
| A08 | NOT RUN |
| A09 | NOT RUN（登录壳局部通过，全路由/旅程/主题未覆盖） |
| A10 | BLOCKED |
| A11 | PASS（双端全量、构建、真实浏览器通过；依赖审计为 2 moderate observation） |
| A12 | PASS（用例、问题登记、QA、Leader Verdict 与脱敏证据索引一致） |

## 未解决问题与 Batch 56 输入

- C55-3：Knowledge/Wiki/Trace 深层功能。
- C55-4：用例→计划→执行→报告、定时任务、缺陷状态机真实浏览器闭环。
- C55-5：六主题、支持的明暗模式、全部静态/动态路由和三视口矩阵。
- 真实旧 PostgreSQL 快照升级和 PostgreSQL 并发。
- 体育平台生产只读、测试环境可恢复写链路、用户端/运营后台需求对照。
- 全平台输入必须从客户验收文档索引的 PRD、蓝湖需求证据、基线/后台用例、追溯矩阵和 OpenAPI 派生；真实前端、后端和数据库结果才可计入生产验收通过。
- Mock 仅允许覆盖不可控第三方失败分支，必须单独标记，不能替代真实客户输入、真实业务副作用或生产验收结论。
- 缺失 VPN、外部凭据、蓝湖链接/凭据、AI Key、ELK 或生产后台只读访问时，保持 `BLOCKED`。
