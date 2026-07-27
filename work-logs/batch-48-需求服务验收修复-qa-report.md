---
title: "Batch 48 需求服务验收修复 QA 报告"
owner: "qa-team"
created: "2026-07-27"
status: "final"
verdict: "ready"
tags: ["batch-48", "requirement-service", "acceptance", "agent-team", "codex"]
related:
  - "../tests/test-cases/functional/BATCH48-测试平台需求服务-生产级复测.md"
  - "../tests/test-case-standards/生产级模块验收规则.md"
  - "kanbans/DEV-batch-48-acceptance-fixes.md"
---

# Batch 48 需求服务验收修复 QA 报告

> 执行日期：2026-07-27
>
> 执行方式：Codex Agent Team
>
> 分支：`feature/batch-48-acceptance-fixes`
>
> 基线：`origin/main@a68e492e1b50a6adc112bbf457b456606b373ddf`
>
> Batch 47 验收资产：`defef886f8c31d797fc3e25e4a2dc9fc0b4aca84`
>
> Batch 48 初始实现：`d1f7e52be70757c14d4acc153dee17571773b931`；真实外部复测兼容与 PostgreSQL 修复：`4dc307ed481fdb9ba01f5b8f949aeed7aef24503`；蓝湖三条行为修复：`b9a2066d273a097cccbd2456bae062ad45aa297c`；子模块 fork 配置：`060fdc0`

## 1. 结论

**结论：`READY`，满足生产可交付门禁。**

Batch 47 的 21 个缺陷均已有实现修复和行为级回归；本地后端、前端、迁移、三视口浏览器契约与 high/critical 供应链门禁通过。真实 AI、真实旧版 PostgreSQL 升级、真实 PostgreSQL 多连接并发以及真实蓝湖三条关键链路也已完成复测。48 条行为复测中：

| 状态 | P0 | P1 | 合计 |
| --- | ---: | ---: | ---: |
| 通过 | 28 | 20 | 48 |
| 失败 | 0 | 0 | 0 |
| 阻塞 | 0 | 0 | 0 |
| 未执行 | 0 | 0 | 0 |
| **总计** | **28** | **20** | **48** |

三条原蓝湖阻塞用例 B47-MOD-004、B47-MOD-006、B47-MOD-010 均已通过，行为验收达到 48/48。根仓 gitlink 指向的 `lanhu-mcp@74bfa7b463ef505008ea25466bc950ad9ed67324` 已发布到 `mojinru9527/lanhu-mcp` 的 `feature/batch-48-bounded-download` 分支，`.gitmodules` 已指向该可访问 fork；全新临时目录独立克隆得到相同 SHA 且工作区干净。A12 交付可追溯通过，最终结论为 `READY`。

## 2. 环境与证据边界

| 项目 | 实际环境 |
| --- | --- |
| 工作区 | `F:\CamelTv-worktrees\codex-batch-48-acceptance-fixes`，Agent Team/Codex 元数据已核对 |
| 前端 | 本机隔离端口 5183，headed Chromium |
| 浏览器视口 | `1440×900`、`768×1024`、`390×844` |
| 后端 | 同分支 FastAPI TestClient、临时 SQLite、真实 AI 服务与隔离 PostgreSQL 克隆 |
| 后端网络限制 | Windows 对 8013/8014 绑定返回 10013；未使用共享 8000 服务替代 |
| 浏览器 API | 确定性契约 fixture；真实后端行为由同批次 Pytest/迁移测试独立证明 |
| 外部环境 | AI 配置、蓝湖认证与旧 PG 卷均通过本地忽略配置使用；蓝湖附件异常采用受控不可读项验证人工处理分支；本文不记录 URL、Cookie、Key、OCR 正文或数据库口令 |

浏览器 fixture 证明页面行为、路由、响应式、键盘、a11y、控制台和请求次数；它不冒充真实外部服务或真实后端网络闭环。

## 3. 修复结果

### 3.1 后端与数据一致性

- 上传限制按实际流字节执行；20 MB 边界、伪造长度、空/损坏文件均有无副作用断言。
- 列表使用服务端分页/搜索，返回真实创建人且 Brief 不携带正文；详情按项目隔离读取。
- 拆分确认/驳回保留评估与继承字段；审查、编辑、导入状态持久化。
- 导入业务、计数和审计同事务；重复导入幂等，数据库唯一约束提供并发最后防线。
- 模块树 full/lazy 三层一致；parent、bundle、service、endpoint 均校验项目归属。
- API 匹配确认去重持久化；审计记录实际持久化数量，coverage 可追溯。
- Batch 48 迁移补齐历史字段、表、约束和索引；模型注册与 Alembic metadata 对齐。
- 旧卷 `codex-cameltv-pg-staging-20260714-data` 仅通过隔离克隆复测；从 `20260714_lanhu_pg_reconcile` 升至 `20260727_batch48_pg_parity`，重复升级通过且业务数据计数不变。
- 真实 PostgreSQL 多连接并发中，导入 4 路得到 1 导入、3 跳过；模块关联 6 路得到 1×200、5×409，最终各 1 条且计数无漂移。

### 3.2 前端与浏览器

- 详情按需加载；服务端分页、搜索、覆盖率和审查路由接通。
- “基于拆分生成”与“重新拆分”语义分离，并有直接动作断言。
- 编辑值参与导入；API 匹配可确认并刷新恢复。
- 证据轮询不重叠、可取消，故障按 3/6/12/30 秒退避且连续失败只提示一次。
- Axios 取消请求不再弹出错误 toast。
- 390 px 可完成上传、分页、搜索、Space 选择、预览和审查入口；Axe 无违规。

### 3.3 供应链

- 移除未使用的运行/测试依赖，升级 Vite、Vitest、PostCSS、OpenAPI 工具链并固定 lockfile。
- 生产和全依赖审计均为 high=0、critical=0。
- 剩余 2 个 moderate 来自 React Router；升级到 7.18.1 是 major 变更，本批次未在缺少完整路由迁移回归的情况下强升。当前系统不使用 React Router SSR hydration，且内部导航不接收不可信反斜杠 URL；风险继续登记，不影响本批次 high/critical 门禁。

### 3.4 真实外部链路

- 真实 AI 完成上传→拆分→刷新恢复→确认→基于拆分生成闭环：拆分结果为 2 个模块、15 个功能点，生成 13 条功能用例；状态、数据库和上传/拆分/确认/生成审计一致，专项 27/27 通过。
- 真实蓝湖认证返回 HTTP 200，页面枚举在 4.75 秒内得到 106 页，页 ID、文件名和层级均完整；证据不包含 URL、查询参数、Cookie、页面名称或响应正文。
- 蓝湖目标页有界下载在 34.154 秒内完成，仅下载 URL 指定的 1 页，共 295 个文件、2,547,710 字节，无临时分片残留；下载器已限制资源数、总字节、整体时限并支持取消清理。
- B47-MOD-004 在真实 PostgreSQL 中完成 4 路并发，全部返回相同模块 ID，最终仅 1 个 module + 1 个 page，无重复或半棵树。
- B47-MOD-006 复用既有真实 URL；正常附件继续处理，受控不可读附件计入失败并返回人工处理提示，失败项无业务副作用，重试不产生重复知识实体。
- B47-MOD-010 生成 7 段未截断截图和 637 个中文 OCR 文本块，`merged_text` 非空；可见浏览器复核中控制台错误和失败请求均为 0。原始截图、OCR 正文和模型文件未提交。

## 4. 自动化与命令证据

| 门禁 | 结果 | 统计/备注 |
| --- | --- | --- |
| `ruff check app/ --select F821` | 通过 | exit 0 |
| 初始实现需求服务专项 Pytest | 通过 | 56/56，2 warnings |
| 最终后端全量 Pytest | 通过 | 812 passed、2 skipped、5 warnings，277.32 秒；2 条默认跳过用例在显式真实 PG 环境中 2/2 通过 |
| `alembic upgrade head` | 通过 | 旧 PG 隔离克隆从 `20260714_lanhu_pg_reconcile` 升至唯一 head `20260727_batch48_pg_parity`；重复升级安全且数据计数不变 |
| `alembic check` | 通过 | `No new upgrade operations detected`，metadata 零漂移 |
| 真实 AI 专项 | 通过 | 27/27；2 模块、15 功能点、13 条功能用例 |
| 真实 PostgreSQL 导入并发 | 通过 | 4 路：1 导入、3 跳过；最终 1 条，计数无漂移 |
| 真实 PostgreSQL 关联并发 | 通过 | 6 路：1×200、5×409；最终 1 条关联 |
| 真实蓝湖三条专项 | 通过 | 有界下载；MOD-004 真实 PG 并发；MOD-006 失败转人工；MOD-010 截图/OCR；见 `lanhu-three-regression-audit.md` |
| `lanhu-mcp` 全量 | 通过 | 17 passed |
| 后端蓝湖/模块专项 | 通过 | 106 passed |
| 真实 PostgreSQL MOD-004 并发 | 通过 | 1 passed |
| `npm ci` | 通过 | lockfile 可重建 |
| `npm run typecheck` | 通过 | exit 0 |
| `npm test` | 通过 | 29 文件、124 测试 |
| `npm run build` | 通过 | Vite 7.3.6；仅已有 wiki 动静态导入 chunk 提示 |
| 需求页 headed Playwright | 通过 | Chromium 1/1，4.5 秒 |
| 登录 a11y Playwright | 通过 | Chromium 1/1 |
| `npm audit --omit=dev --json` | 门禁通过 | 命令因 moderate 返回 exit 1；moderate=2、high=0、critical=0 |
| `npm audit --json` | 门禁通过 | 命令因 moderate 返回 exit 1；moderate=2、high=0、critical=0 |
| `git diff --check` | 通过 | 无空白错误 |

## 5. A01～A12 门禁

| 门禁 | 结果 | 证据/说明 |
| --- | --- | --- |
| A01 基线可追溯 | 通过 | Batch 47 48 条、21 缺陷、基线 SHA、实现 SHA 均固定 |
| A02 隔离环境 | 通过 | 独立 worktree、5183 前端、TestClient/临时数据库、旧 PG 卷隔离克隆；未复用共享后端且未修改原卷 |
| A03 主/备选/异常流 | 通过 | 48 条行为用例全部通过；真实 AI、蓝湖提取、附件失败转人工和截图/OCR 均已闭环 |
| A04 API 三类校验 | 通过 | 入参、业务、响应和写副作用由 56 条专项覆盖 |
| A05 RBAC/项目隔离 | 通过 | 文档、模块、bundle、service、endpoint 跨项目均拒绝 |
| A06 UI/API/DB/审计一致 | 通过 | 导入、删除、审查、匹配等同事务与回滚断言通过 |
| A07 幂等/并发/重试 | 通过 | API 幂等 + DB 唯一约束通过；真实 PG 4 路导入与 6 路关联并发最终均仅 1 条且无计数漂移 |
| A08 跨页查询一致 | 通过 | 101 条后端分页 + 移动端第 2 页/服务端搜索 |
| A09 浏览器/a11y/网络 | 通过（契约） | 三视口、Enter/Space、Axe、控制台、一次 GET、审查路由 |
| A10 真实旧数据库迁移 | 通过 | 旧卷隔离克隆升级、重复升级、数据计数不变、唯一 head 与 `alembic check` 零漂移 |
| A11 自动化/供应链 | 通过 | 双端全量、类型、构建、high/critical=0 |
| A12 文档/证据一致 | 通过 | 行为证据与文档已同步；子模块提交已发布到根仓配置的可访问 fork，独立克隆得到相同 SHA 且工作区干净 |

## 6. 交付阻塞解除记录

| 原阻塞项 | 解除结果 | 复核证据 |
| --- | --- | --- |
| `lanhu-mcp` 子模块提交不可交付 | 已解除 | fork 分支远端为 `74bfa7b463ef505008ea25466bc950ad9ed67324`；根仓 URL 已更新；独立克隆 SHA 一致且工作区干净 |

## 7. 其他未提交改动合并审计

已再次检查控制工作区 `F:\CamelTv`：

- 30 个暂存路径中 29 个与最新 `origin/main` 完全相同，无需重复合并。
- 唯一不同的 Batch 45 迁移是删除幂等保护的旧版本，不纳入 Batch 48。
- `lanhu-mcp` 没有已跟踪代码变动；1150 个未跟踪项为浏览器缓存、登录调试和临时脚本，可能包含会话数据，不纳入 Batch 48。
- 未发现新增且适合合并的其他人未提交业务改动；控制工作区保持原样。

Batch 48 隔离 worktree 的子模块状态与控制工作区不同：根仓提交 `b9a2066d273a097cccbd2456bae062ad45aa297c` 已记录 gitlink `74bfa7b463ef505008ea25466bc950ad9ed67324`，提交 `060fdc0` 已把 `.gitmodules` 改到可访问 fork；子模块本地工作区干净，远端独立克隆复核通过。其他人改动合并审计完成，无剩余交付阻塞。

## 8. 推送状态

Batch 48 已执行“每次 push 前重新确认是否还有其他变动”的仓库门禁。本报告生成时：

- 本地实现与 48/48 行为回归已完成。
- 用户已确认无其他变动，`lanhu-mcp` 修复分支已推送到 fork，并通过独立克隆复核。
- 用户再次确认后，Batch 48 根仓分支已推送，并创建 Draft PR #74。
- 首轮 CI 在 npm 10 的 `npm ci` 阶段发现锁文件兼容问题：缺少 4 个传递依赖锁定条目，尚未运行到前端代码检查。
- 本地已使用 npm 10 从 `package.json` 重新生成无绝对路径、无自引用的锁文件；`npm ci`、typecheck、124 项 Vitest、build 均通过，npm audit 为 high=0、critical=0。
- 首轮后端全新检出 819 项中 818 通过、1 失败；唯一失败是后端依赖清单漏装固定子模块导入所需的 `fastmcp`。该依赖已同步到 `requirements.txt`，本地蓝湖专项与运行时导入通过。
- 该 CI 修复和本段证据形成新的根仓变更；再次 push 前必须重新展示范围，并取得用户新的“无其他变动”确认。
