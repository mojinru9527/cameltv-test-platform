---
title: "Batch 59 遗留问题修复 QA 报告"
owner: "qa-team"
created: "2026-07-30"
last_reviewed: "2026-07-30"
status: "local-pass-with-external-conditions"
expires: "2027-01-30"
tags: ["batch-59", "qa", "legacy-debt", "agent-team"]
related:
  - "batch-59-legacy-debt-issue-register.md"
  - "../../C-CONDITIONS.md"
---

# Batch 59 遗留问题修复 QA 报告

## 1. 判决

**LOCAL PASS WITH EXTERNAL CONDITIONS**

Batch 59 本地代码、CI 契约、构建、单元/集成测试、一次性 PostgreSQL 16
并发回归和 fixture a11y 全部通过。真实业务环境、真实 E2E 账号、VPN、
AI/OCR、ELK、真机和旧库快照不在本次本地成功结论内。

## 2. 固定基线

| 项 | 值 |
| --- | --- |
| workflow / executor | Agent Team / Codex |
| 分支 | `feature/batch-59-legacy-debt-closure` |
| 基线 | `origin/main@5830622` |
| worktree | `F:\CamelTv-worktrees\codex-batch-59-legacy-debt-closure` |
| frontend / backend port | 5179 / 8006 |
| 子模块 | `lanhu-mcp@c9f4a43124c1e10c442a487c54c456b1ad32d65e` |

## 3. 自检结果

| 门禁 | 命令摘要 | 结果 |
| --- | --- | --- |
| CI/Jenkins 契约 | Batch59 contracts + change classifier | 17 passed；27 subtests passed |
| 后端 F821 | `ruff check app/ --select F821` | PASS，0 项 |
| Batch59 后端定向 | management + lifecycle | 8 passed |
| Alembic | heads + migration runbook | 单一 head；4 passed |
| PostgreSQL 16 并发 | 空库 migrate head 后执行 Batch48 concurrency | 3 passed，0 skipped |
| 后端全量 | `pytest -q` | 900 collected；897 passed；3 skipped；0 failed |
| 前端 lint | `npm run lint` | PASS，0 个未抑制 error/warning；135 条既有 unused 债务显式登记在 suppressions |
| TypeScript | `npm run typecheck` | PASS |
| 前端定向 | AddCasesModal + CaseDrawer | 6 passed |
| 前端全量 | `npm test` | 56 files；222 passed；0 failed |
| 覆盖率硬门禁 | `npm run test:coverage` | 56 files；222 passed；四项阈值均通过 |
| 生产构建 | `npm run build` | 3412 modules transformed；PASS |
| fixture a11y | `npm run test:a11y:ci` | 36 passed；0 failed |
| 真实后端响应式 E2E | Playwright `--list` | 13 tests collected；新增 tablet/mobile 2 项；未实跑 |
| 差异格式 | `git diff --check` | PASS |

覆盖率实测：

| Statements | Branches | Functions | Lines |
| ---: | ---: | ---: | ---: |
| 28.33% | 22.66% | 23.83% | 29.74% |

阈值分别为 27%、22%、23%、28%，作用是对 Batch 58 实际基线 fail-closed，
不是把低覆盖率描述成理想状态。

## 4. skip / warning 精确集合

后端全量 3 个 skip 全部来自：

`tests/test_batch48_postgresql_concurrency.py`

它们只在未显式提供 PostgreSQL 集成变量时 skip。本批随后在一次性
PostgreSQL 16 容器中执行 `alembic upgrade head`，同 3 项 3/3 通过；
required CI 已按相同步骤配置。

唯一 warning：

`tests/test_v27_smoke.py` 导入 ORM `TestReport` 时触发 PytestCollectionWarning。
该 warning 已存在于 Batch 58 基线，不由本分支新增；本批未把它隐藏。

## 5. 失败发现与关闭记录

| 发现 | 初始结果 | 处置 | 最终结果 |
| --- | --- | --- | --- |
| Dataset 跨项目更新 | foreign update `code=0` | service/API 联合 `project_id` | foreign detail/update/delete/rows 均拒绝 |
| CSV/Excel 报告导出 | CSV 崩溃、公式注入、执行人/备注快照缺失 | 文本缓冲 + UTF-8 BOM；危险公式前缀转义；批量快照最新执行信息 | CSV/XLSX 内容与恶意标题回归通过 |
| Excel 报告导出 | 读取不存在的 `case_results/pass_` | 映射真实 `cases/stats/plan_info` | 标题、fail 统计、状态通过 |
| AddCasesModal | 同一事件请求旧筛选 state | 显式 filter snapshot + AbortController | 2 项回归通过 |
| hooks lint | 12 errors + 1 stale disable | 最小依赖/生命周期修复 | hooks lint 0 |
| 全仓前端 lint | 原命令只覆盖 `src` hooks，两条规则以外可能假绿 | 覆盖 src/e2e/config 的 TypeScript 推荐规则、unused、console、debugger；135 条既有 unused 形成显式非回退基线 | 0 个未抑制问题 |
| WikiDiff 请求 | 选择历史任务会重复 GET，旧响应可能覆盖新选择 | 单一 selected-task effect、真实 AbortSignal、受控轮询 | lint/typecheck/full suite 通过 |
| CaseDrawer 编辑 | 域列表延迟返回时可能清空原模块 | 只在所选域已加载后校验模块 | 新增回归通过 |
| PG required gate | 启动空 PG 后 3/3 缺表失败 | workflow 增加 migrate head | 一次性 PG 16：3/3 |
| WebSocket 测试 | 独立端口下 4403 | origin 读取当前 CORS 配置 | 38/38 |
| a11y hard gate | 32 pass / 4 fail | tablet 隐藏溢出的非关键 coverage 摘要 | 36/36 |
| Jenkins runtime/deploy | Node 只声明未升级；持久化 PG 卷与每次随机密码冲突；`/health` 可被 SPA 假 200 | Jenkins 镜像升级 Node 22；首次生成并复用 secrets；容器内请求后端 8000/health | 契约测试覆盖 |

## 6. 未执行与剩余风险

- C55-5-P2 的真实后端 tablet/mobile 用例已就绪，但未提供
  `E2E_USERNAME/E2E_PASSWORD`，因此不写 PASS。
- Jenkinsfile 与 Jenkins Node 22 镜像无可用 controller 做 declarative linter、镜像构建和真实流水线执行；
  本批以静态契约、Compose/后端现有测试和构建命令覆盖。
- ESLint 的 135 条既有 `no-unused-vars` 债务没有伪装成已修复，已逐文件计数写入
  `eslint-suppressions.json`；新增或计数增加会重新使 lint 失败。
- GitHub Actions 只有 push 后才能获得 hosted runner 结果；本地已验证其实际
  PostgreSQL/a11y 命令链。
- B56-B01～B10、G56-011 和 C58 云条件按 issue register 继续保留。
- G56-014 仍 `OPEN`；J03/J08/J09/J15/J16 及各旅程剩余真实 UI 主链未关闭。

## 7. 首轮异常说明

为避免把环境问题写成“历史失败”，保留首轮事实：

- 初次后端全量为 891 passed / 6 failed / 3 skipped；其中 3 项因新 worktree
  未初始化 `lanhu-mcp`，初始化强制子模块后相关 30 项通过；另 3 项为测试
  硬编码 5173，与本 worktree 5179 冲突，修复后 38 项通过。
- 初次并行前端全量/coverage 各有同一 5 秒 timeout；目标文件单独 10/10，
  随后顺序全量和 coverage 均 221/221；审查修复补 1 项回归后最终 222/222，
  判定首轮为并行资源争用，不提高超时掩盖。
- 初次 PG 专项 3/3 缺表失败，促使 workflow 增加迁移前置；迁移后 3/3 通过。
- 初次 a11y 为 32/36，修复 4 个 tablet Theme Lab 失败后全量 36/36。
