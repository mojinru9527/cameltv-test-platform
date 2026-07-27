---
title: "Batch 48 需求服务验收修复 QA 报告"
owner: "qa-team"
created: "2026-07-27"
status: "final"
verdict: "needs_work"
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
> Batch 48 实现：`d1f7e52be70757c14d4acc153dee17571773b931`

## 1. 结论

**结论：`NEEDS WORK`，当前不按生产可交付放行。**

Batch 47 的 21 个缺陷均已有实现修复和行为级回归；本地后端、前端、迁移、三视口浏览器契约与 high/critical 供应链门禁通过。48 条复测中：

| 状态 | P0 | P1 | 合计 |
| --- | ---: | ---: | ---: |
| 通过 | 24 | 17 | 41 |
| 失败 | 0 | 0 | 0 |
| 阻塞 | 4 | 3 | 7 |
| 未执行 | 0 | 0 | 0 |
| **总计** | **28** | **20** | **48** |

不能放行的原因是 7 条外部关键链路仍缺真实执行条件：真实 AI 1 条、真实蓝湖 3 条、真实旧版 PostgreSQL 快照 1 条、真实 PostgreSQL 多连接并发 2 条。阻塞未被算作通过。

## 2. 环境与证据边界

| 项目 | 实际环境 |
| --- | --- |
| 工作区 | `F:\CamelTv-worktrees\codex-batch-48-acceptance-fixes`，Agent Team/Codex 元数据已核对 |
| 前端 | `http://127.0.0.1:5183`，headed Chromium |
| 浏览器视口 | `1440×900`、`768×1024`、`390×844` |
| 后端 | 同分支 FastAPI TestClient、临时 SQLite 与隔离 Alembic 数据库 |
| 后端网络限制 | Windows 对 8013/8014 绑定返回 10013；未使用共享 8000 服务替代 |
| 浏览器 API | 确定性契约 fixture；真实后端行为由同批次 Pytest/迁移测试独立证明 |
| 外部环境 | 未提供真实 AI Key、蓝湖 Provider/证据包、脱敏旧版 PostgreSQL 快照 |

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

## 4. 自动化与命令证据

| 门禁 | 结果 | 统计/备注 |
| --- | --- | --- |
| `ruff check app/ --select F821` | 通过 | exit 0 |
| 需求服务专项 Pytest | 通过 | 56/56，2 warnings |
| 后端全量 Pytest | 通过 | 806/806，6 warnings，270.51 秒 |
| `alembic upgrade head` | 通过 | 唯一 head `20260727_batch48`；重复升级安全 |
| `alembic check` | 通过 | `No new upgrade operations detected` |
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
| A02 隔离环境 | 通过 | 独立 worktree、5183 前端、TestClient/临时数据库；未复用共享后端 |
| A03 主/备选/异常流 | 阻塞 | 本地行为通过；真实 AI/蓝湖 4 条外部流程未执行 |
| A04 API 三类校验 | 通过 | 入参、业务、响应和写副作用由 56 条专项覆盖 |
| A05 RBAC/项目隔离 | 通过 | 文档、模块、bundle、service、endpoint 跨项目均拒绝 |
| A06 UI/API/DB/审计一致 | 通过 | 导入、删除、审查、匹配等同事务与回滚断言通过 |
| A07 幂等/并发/重试 | 阻塞（本地契约通过） | API 幂等 + DB 唯一约束通过；缺真实 PG 多连接并发执行输出 |
| A08 跨页查询一致 | 通过 | 101 条后端分页 + 移动端第 2 页/服务端搜索 |
| A09 浏览器/a11y/网络 | 通过（契约） | 三视口、Enter/Space、Axe、控制台、一次 GET、审查路由 |
| A10 真实旧数据库迁移 | 阻塞 | 空库与本地旧 SQLite 通过；缺脱敏真实旧 PostgreSQL 快照 |
| A11 自动化/供应链 | 通过 | 双端全量、类型、构建、high/critical=0 |
| A12 文档/证据一致 | 通过 | PRD、测试策略、规则、复测、报告和截图索引已同步 |

## 6. 外部阻塞登记

| 用例 | 缺失条件 | 解除条件 | 责任人 | 预计时间 | 条件具备后复测时限 |
| --- | --- | --- | --- | --- | --- |
| B47-REQ-013 | 真实 AI Key/服务 | 完成拆分→确认→生成并保存请求、响应、DB/审计 | 产品/项目负责人 | 待确认 | 1 个工作日 |
| B47-MOD-004 | 真实蓝湖 Provider/证据包 | 完成重复/并发提取并核对最终树与审计 | 产品/项目负责人 | 待确认 | 1 个工作日 |
| B47-MOD-006 | 含正常/损坏附件的证据包 | 完成部分失败、知识实体和审计核对 | 产品/项目负责人 | 待确认 | 1 个工作日 |
| B47-MOD-010 | 真实截图/OCR 证据 | 完成 asset URL、图片、OCR/merged_text 浏览器闭环 | 产品/项目负责人 | 待确认 | 1 个工作日 |
| B47-NFR-005 | 脱敏真实旧版 PostgreSQL 快照 | 升级前后数据核对、重复升级、唯一 head、无漂移 | 产品/项目负责人 | 待确认 | 1 个工作日 |
| B47-REQ-022 | 真实 PostgreSQL 多连接并发环境 | 并行导入同一索引，一个成功、另一个幂等或冲突，最终计数不漂移 | 产品/项目负责人 | 待确认 | 1 个工作日 |
| B47-MOD-007 | 真实 PostgreSQL 多连接并发环境 | 并行创建同一关联，一个成功、另一个冲突，最终只有一条 | 产品/项目负责人 | 待确认 | 1 个工作日 |

## 7. 其他未提交改动合并审计

已再次检查控制工作区 `F:\CamelTv`：

- 30 个暂存路径中 29 个与最新 `origin/main` 完全相同，无需重复合并。
- 唯一不同的 Batch 45 迁移是删除幂等保护的旧版本，不纳入 Batch 48。
- `lanhu-mcp` 没有已跟踪代码变动；1150 个未跟踪项为浏览器缓存、登录调试和临时脚本，可能包含会话数据，不纳入 Batch 48。
- 未发现新增且适合合并的其他人未提交业务改动；控制工作区保持原样。

## 8. 推送状态

Batch 48 已执行“每次 push 前重新确认是否还有其他变动”的仓库门禁。本报告生成时：

- 本地实现提交已完成。
- 尚未执行任何 Batch 48 `git push`，尚未创建 PR。
- 必须先向用户展示最终文件、提交和自检范围；只有用户明确回答“没有其他变动”并授权本次 push，才可执行一次 push。
