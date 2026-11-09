# Batch 277b-1 — P0-4 `/uitest` 节点化：QA Report

> **部门**：🔍 QA
> **日期**：2026-11-09
> **立场**：默认"需要改进"。本批是**契约 + 执行器**切片，默认行为不变；P0-4 未闭环，只对"新增路径正确性"负责。
> **基线**：`origin/main @ 0fbd420fb`

---

## 1. 交付验收

| # | 交付项 | 验收 | 证据 |
|---|--------|:----:|------|
| 1 | `ui_test_run.execution_job_id` + 可逆迁移 | ✅ | up/down/up 全 0；downgrade 后列消失、再 upgrade 恢复 |
| 2 | `uitest_execution_mode` 开关（默认 local） | ✅ | 默认值 `local`；node 分支仅在显式设置时生效 |
| 3 | node 模式 trigger → `ExecutionJob(kind="ui")` | ✅ | `test_trigger_job_node_mode_dispatches` |
| 4 | 载荷构建：spec 读取 + guard + env | ✅ | 3 条 build_payload 单测（正常/危险 API/路径穿越） |
| 5 | 状态投影 + 用例回写 | ✅ | 3 条 sync/report 单测（映射/幂等/report 钩子） |
| 6 | 节点 spec 执行器 | ✅ | 4 条单测（报告解析/非法名/超时/无报告） |
| 7 | 本地路径不受影响 | ✅ | 默认 local；90 条相关回归通过 |

---

## 2. 硬门禁

| 检查 | 结果 |
|------|:----:|
| 全量后端 `pytest -q` | ✅ **1332 passed / 43 skipped / 0 failed**（174s） |
| 新增单测 | ✅ 12/12 |
| 相关回归（ui/job 协议） | ✅ 90/90 |
| 迁移可逆 | ✅ upgrade → downgrade -1 → upgrade |
| 质量 ratchet | ✅ increased_keys=0（ruff 400 / mypy 89） |
| 路由基线 | ✅ 无新增/删除端点 |
| P0-4 守卫 | ⚠️ 仍红（Dockerfile 含 Chromium），**符合预期**：277b-2 才闭环 |

---

## 3. 安全审查

| 项 | 结论 |
|----|------|
| spec 安全拦截位置 | ✅ 控制面派发前 `spec_guard.assert_spec_safe`，不通过即拒绝（不进节点） |
| 路径穿越 | ✅ 节点侧 `_safe_rel_path` 拒绝绝对路径/`..`/非法字符；单测覆盖 |
| 凭据外泄 | ✅ 节点子进程 env 剔除 `SECRET/TOKEN/PASSWORD` 前缀；仅注入环境 slot + `BASE_URL` |
| 伪造通过 | ✅ 无报告/超时/0 用例 → `all_pass=false` + error，不伪造 |
| 重复执行 | ✅ 本地恢复线程排除 `execution_job_id != NULL` 的节点任务 |

---

## 4. 残留与风险

| 项 | 说明 | 承接 |
|----|------|------|
| 默认仍 local | 生产行为不变，P0-4 未闭环 | 277b-2 |
| 节点无真实 E2E | 本环境无 Playwright/节点；报告解析只按稳定字段假设 | 277b-2 真机验收 |
| `xhr_capture` / playground 本地 Chromium | Dockerfile 去浏览器前必须一并处理 | 277b-2 |
| 节点 `npx` 依赖 | 节点机器需能解析 `npx playwright` | 277b-2 前置检查 + README |

---

## 5. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 1.5-2 人日 / 实际 ≈ 1h |
| 缺陷 | 新增 0 P0；ratchet 发现 4 处新 lint（RUF100/UP017/F401），已修 |
| 返工次数 | 2（ruff 规则按 ratchet 口径修正；分支承接：先在已合并 worktree 改，后迁移到新 worktree） |
| 根因分类 | 工具链（ratchet 规则集比单独 ruff 更严） |
| 下次避免 | 提交前直接跑 `quality_ratchet.py`，不要只跑 `ruff check app` |

---

## 6. QA 判定

- 277b-1 的契约、执行器、投影、单测全部通过；默认行为零变化；
- **建议 Leader APPROVED（277b-1）**；
- **P0-4 仍未闭环**：必须等 277b-2 真实节点验收 + Dockerfile 去 Chromium + evidence。
