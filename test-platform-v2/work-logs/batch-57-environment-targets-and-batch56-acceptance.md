---
title: "Batch 57 固定运行环境与 Batch 56 验收遗留"
owner: "qa-team"
last_reviewed: "2026-07-29"
status: "active"
expires: "2027-01-29"
tags: ["batch-57", "runtime-profile", "production-acceptance", "agent-team"]
related:
  - "../../docs/work-logs/batch-56-production-acceptance-execution-matrix.md"
  - "batch-56-production-acceptance-qa-report.md"
  - "../../docs/superpowers/plans/2026-07-29-batch-57-environment-targets-and-acceptance.md"
---

# Batch 57 固定运行环境与 Batch 56 验收遗留

## 1. 本批目标

测试平台自身只采用 local、production 两套固定实例。每套实例拥有固定
访问地址、独立后端和独立数据库；用户通过书签选择环境，不在页面运行中切库。

`/environment` 页面继续管理被测系统的目标地址与变量，不承担测试平台自身
运行数据库的切换。

## 2. Batch 57 基线

| 项 | 结果 |
| --- | --- |
| 执行器 / workflow | Codex / Agent Team |
| 分支 | `feature/batch-57-environment-targets-and-acceptance` |
| 基线 | `origin/main@eb4437c826bc896ba78822e4b705c533db29c0cc` |
| Batch 56 合入 | PR #83 已 squash 合入 `main` |
| 本地入口 | `http://localhost:5173/` |
| 本地后端 | `http://127.0.0.1:8000` |
| 初始健康检查 | 前端、后端和前端代理 API 均为 HTTP 200 |

旧 Batch 56 worktree 已停止，并可恢复地归档为
`F:\CamelTv-worktrees\retired-codex-batch-56-full-platform-production-acceptance`；
分支与已合入主干的历史未删除。

## 3. Batch 56 权威结论

Batch 56 的最终 Verdict 是 `NEEDS WORK`，不得宣称全功能生产 `READY`。
本地全路由、RBAC、构建、回归、容器与供应链门禁已经通过，但外部真实环境
仍有 7 个 P0、3 个 P1 阻断。

### P0

| ID | 遗留 | 解除条件 |
| --- | --- | --- |
| B56-B01 | 测试节点 6 返回 503 | 服务恢复后按同一浏览器矩阵复测 |
| B56-B02 | 六服务实时 OpenAPI 不完整 | 提供六份实时契约或可追溯快照 |
| B56-B03 | 无效 Bearer 仍返回成功 | 对齐公开/受保护边界、实现与 OpenAPI |
| B56-B04 | 运营后台登录未形成浏览器会话 | 修复 Cookie/storage 与重定向后复测 |
| B56-B05 | 真实 AI/OCR 未配置 | 提供授权服务与无 fallback 证据 |
| B56-B08 | 缺真实旧 PostgreSQL 脱敏快照 | 提供基线、SHA 与隔离恢复副本 |
| B56-B09 | 设计源证据包不可复核 | 提供当前导出、来源、时间与 SHA |

### P1

| ID | 遗留 | 解除条件 |
| --- | --- | --- |
| B56-B06 | 无设备代理/SoloX | 部署认证代理并完成真机采样 |
| B56-B07 | 缺 ELK 只读 trace 证据 | 提供索引权限并完成脱敏关联 |
| B56-B10 | 生产节点浏览器超时/内容不足 | 在批准窗口和正确 VPN 边界复测 |

另有 React Router 2 个 moderate advisory；high/critical 为 0。修复需要破坏性
大版本迁移，应作为独立依赖升级任务处理。

## 4. 证据闭环复核

Batch 56 计划要求的独立 issue register、evidence README、Leader Verdict 和
`C-CONDITIONS.md` 更新未随 PR #83 完整落库，B56-B01～B10 只登记在 QA 报告。
执行矩阵声明 `G56-016` 已关闭，与实际交付物存在不一致。

知识模块仍存在未完成实现：

- `SourceListTab.tsx` 的同步覆盖率仍为固定“未同步”。
- `version_differ.py` 的 AI diff 仍回退为规则结果。
- `attachment_extractor.py` 的附件 AI 分析仍为 stub。
- `navigates_to_extractor.py` 的多模态/DOM 提取仍为 stub 或简化正则。

因此 `G56-011` 的“Knowledge/Wiki/Trace 深层功能已关闭”证据不足，应在真实
AI/OCR、设计源证据和跨项目隔离条件具备后重新验收。

## 5. Batch 57 仓库内修复

| ID | 结果 | 证据 |
| --- | --- | --- |
| B57-SEC-01 | 环境/变量跨项目 IDOR 已修复 | 项目、环境、变量联合归属；跨项目 list/create/update/delete/resolve 4 组回归通过，秘密不回显 |
| B57-WIKI-01 | Wiki 同步 Badge 不再固定“未同步” | 最新 active 发布包真实 coverage；loading/synced/partial/failed/error；两条数据仍各 1 次 bundle/coverage 请求 |
| B57-DEP-01 | React Router 风险已修复 | React 19.2.8、React Router 8.3.0、Node 22.22；`npm audit` 0 vulnerability，216 项 Vitest、typecheck、build 通过 |
| B57-DOC-01 | Batch 56 交付物对账已补齐 | issue register、evidence README、Leader Verdict、C tracker 和 execution matrix 一致；G56-016 仅按文档对账关闭 |

`G56-011` 仍保持 `OPEN`：Wiki coverage 展示已修复，但真实 AI diff、附件 AI
分析、多模态/DOM 提取仍需要真实 AI/OCR 与设计源输入，不能用规则结果或 stub
冒充闭环。

## 6. Batch 57 新增审计发现

环境 API 的若干读取、更新、删除和变量解析路径需要重新验证
`project_id + environment_id + variable_id` 的联合隔离。当前服务层按裸 ID
操作的路径可能形成跨项目越权，尤其变量 resolve 可能返回解密值。该问题不在
Batch 56 的十项正式阻断中，必须补隔离测试后再确定缺陷等级；本批不以环境
profile 改造掩盖该风险。

## 7. Batch 57 自检

| 门禁 | 结果 | 状态 |
| --- | --- | --- |
| Runtime profile + Compose + 隔离定向测试 | 20 passed | PASS |
| 后端 F821 | 0 项 | PASS |
| 后端全量 Pytest | 869 collected；866 passed、3 skipped、0 failed | PASS |
| 前端 TypeScript | `npm run typecheck` 退出码 0 | PASS |
| 前端生产构建 | Vite 7.3.6；3350 modules transformed | PASS |
| 前端全量 Vitest | 54 files、216 tests、0 failed | PASS |
| 前端供应链 | `npm audit`：0 vulnerability | PASS |
| Compose 解析 | production profile `docker compose config --quiet` 退出码 0 | PASS |
| PowerShell 启动器 | 语法通过；首次安全初始化、启动、status 和幂等复用通过 | PASS |
| 浏览器登录页 | 标题、2 个输入框、提交按钮、代理健康 200 | PASS |
| 浏览器真实登录 | admin 登录后进入 `/workbench`；工作台加载完成 | PASS |
| 浏览器控制台/网络 | console error 0；failed request 0 | PASS |
| worktree 元数据 | agent-team / codex / start confirmed | PASS |
| 凭据与运行产物 | local profile、SQLite、manifest 均受 Git 忽略且未跟踪 | PASS |

3 个 skip 均来自 `test_batch48_postgresql_concurrency.py`，需要显式 Batch 48
PostgreSQL 集成环境；Batch 56 已单独记录对应 PG 专项 3/3 通过，不是隐藏失败。
全量测试另有 3 个既有 warning：一个模型收集 warning、两个 Alembic
`path_separator` 弃用 warning。

Batch 56 的 React Router 6 moderate 风险已按官方迁移路径升级到
React Router 8.3.0；同时升级 React 19.2.8 和 Node 22.22 运行基线。当前
`npm audit` 为 0 vulnerability。

## 8. 交付状态

- 本地实例当前运行在 `http://localhost:5173/`。
- 后端固定为 `http://127.0.0.1:8000`。
- 本地数据库固定为 `platform-local.db`。
- 重复执行启动命令会复用相同进程；数据库、端口或 manifest 不匹配时
  fail closed，不会把旧进程误报为当前 profile。
- production profile 示例中的 `change-me` 和 `example.com` 值在启动前
  强制阻断，并且必须显式提供 `-ConfirmProduction`。
