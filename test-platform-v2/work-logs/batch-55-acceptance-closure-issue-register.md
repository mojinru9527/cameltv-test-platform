---
title: "Batch 55 验收收尾问题登记"
owner: "qa-team"
last_reviewed: "2026-07-29"
status: "active"
tags: ["batch-55", "acceptance", "security", "agent-team"]
---

# Batch 55 验收收尾问题登记

## 交付边界

| 项 | 值 |
|---|---|
| 基线 | `origin/main@ad62aaecc1cc26ee8a54a8211a9b6336a5942eb3` |
| 工作树 | `F:\CamelTv-worktrees\codex-batch-55-acceptance-closure` |
| 分支 | `fix/batch-55-acceptance-closure` |
| 工作流 | `agent-team` |
| 执行器 | `codex` |
| 前端 / 后端端口 | `5193` / `8023` |
| 首次登记时间 | `2026-07-29T14:42:30+08:00` |

旧分支 `feature/batch-55-production-acceptance-and-fixes` 被判定为不可交付。该分支不得整体合并、不得 cherry-pick，也不得从其提交历史复制凭据或本地执行器元数据。可以进入本分支的改动，必须从 `origin/main` 独立复现，并由本分支测试重新证明。

## 问题清单

| ID | 优先级 | 状态 | 问题 | 处理原则 |
|---|---:|---|---|---|
| B55-SEC-01 | P0 | CLOSED | 旧分支跟踪了本地 `.ai-worktree.json`，且执行器记录与本次用户确认不一致 | 新分支没有该文件；Codex Agent Team verifier 通过 |
| B55-SEC-02 | P0 | CLOSED / EXTERNAL ROTATION BLOCKED | 五个独立脚本复用了同一明文管理员凭据，其中一个还输出 Token 片段 | 旧历史不合并；本分支无凭据；共享环境轮换需凭据所有者确认 |
| B55-QA-01 | P0 | CLOSED AS INVALID EVIDENCE | 六个 `qa_slice` 文件位于 Pytest 收集范围之外，普通 CI 不会执行 | 本分支不含这些脚本；确定性检查进入 Pytest/Vitest/Playwright |
| B55-QA-02 | P0 | CLOSED AS INVALID EVIDENCE | 状态码集合把 `422` 当成功，无数据时构造成功结果，失败清理不影响结论 | 新用例使用唯一预期；阻塞/未执行不计通过 |
| B55-QA-03 | P0 | OPEN AS C55-4 | API 请求脚本被标记为端到端浏览器验收 | 旧证据作废；Batch 56 执行真实浏览器业务旅程 |
| B55-QA-04 | P0 | OPEN AS C55-5 | 源码正则和文件存在检查被标记为主题、响应式和无障碍验收 | 旧证据作废；Batch 56 执行六主题全路由矩阵 |
| B55-DOC-01 | P0 | CLOSED | QA 结论为 `NEEDS WORK`，Leader 仅条件通过，但 C 条件写成全部关闭 | 新 QA/Leader/C 条件保持一致：局部 PASS、全平台 NEEDS WORK |
| B55-FE-01 | P1 | CLOSED | Vite 的 `/api` 前缀代理会吞掉前端 `/apitest` 路由 | 13 个单元契约和 1 个真实浏览器用例通过 |
| B55-AUTH-01 | P1 | CLOSED | 已存在本地数据库重启时仍会生成并打印新的管理员密码，但该密码不会更新已有用户 | 只在缺用户时生成/散列；二次 seed 不调用哈希且无输出 |
| B55-DB-01 | P1 | CLOSED / A10 BLOCKED | 旧分支迁移文档没有进入主干，且未形成可复现的迁移恢复证据 | 运行手册、空库双向演练和零漂移通过；真实旧库仍阻塞 |
| B55-DB-02 | P1 | CLOSED | 迁移含 `source_req_id`，但 ORM 丢失字段，计划详情触发 AttributeError 且 Alembic 检测漂移 | 恢复模型/Schema；行为测试和 `alembic check` 通过 |
| B55-BE-01 | P1 | CLOSED | 全量 Pytest 汇总后 Agent queue 守护线程继续访问已销毁测试数据库 | 新增 shutdown event、join 和 lifespan 清理；57 个相关测试及最终全量通过 |
| B55-BE-02 | P1 | CLOSED | Agent queue 修复后，全量回归继续发现 API task worker 跨测试数据库存活 | FastAPI 生命周期关闭 worker；join 后才清除句柄；20 个聚焦测试及最终全量通过 |
| B55-FE-02 | P1 | CLOSED | 共享 Vite 代理契约同时进入 app/node TS project，干净环境触发 TS6305 | 契约移至 frontend/config；声明输出进入 ignored node_modules/.tmp |
| B55-UI-01 | P1 | CLOSED（登录壳范围） | 登录卡片固定宽度、全屏高度和强渐变/阴影未形成窄屏生产门禁 | 使用设计令牌和最大宽度；320/390/768/1440 浏览器通过 |
| B55-UI-02 | P2 | CLOSED — NON-DEFECT | Chromium 截图中文字出现青橙边 | 计算样式与无 CSS 控制页证明其为 Windows ClearType 子像素抗锯齿；不做 CSS 伪修复 |

## 安全处置

- 本登记不保存、复述或校验旧明文凭据。
- 已暴露凭据是否仍在任何共享环境有效，需要由凭据所有者在对应环境完成轮换；代码仓库无法证明外部轮换已完成。
- 本地验收使用新生成的、只存在于 ignored `.env` 的强凭据。
- 生产体育站、生产 API 和生产 ELK 仅允许只读检查。
- 未提供生产运营后台只读地址/账号、蓝湖精确需求链接/凭据、旧 PostgreSQL 脱敏快照或 VPN 时，相应结果必须为 `BLOCKED`，不得改写为 `PASS`。

## 关闭规则

1. 每项关闭必须链接到证据索引中的用例 ID、命令、退出码、环境和提交 SHA。
2. HTTP `200`、文件存在或源码关键字命中，不能单独作为功能通过证据。
3. C55-1/C55-2 可以在本收尾批次按证据关闭；C55-3/C55-4/C55-5 进入 Batch 56 全平台验收。
4. 任一 P0/P1 失败或关键外部环境阻塞时，全平台生产结论保持 `NEEDS WORK`。
