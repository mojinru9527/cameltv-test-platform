# Batch 115 — QA 报告（Part 2 全部解决）

> **QA (🔍)** | Date: 2026-08-07 | Verdict: 有条件通过（部署后验证 C115-1/2/4）

## 1. 交付与证据

| 资产 | 结果 | 证据 |
|------|------|------|
| C107-1 知识导入 | capture **code=0 source#31**（接口测试考虑点）；sources 31 + 检索 5 命中 | `evidence/batch-115/knowledge-c1071-summary.json` |
| B114-2 Runner 加固 | playwright.config chromium launch args（--disable-dev-shm-usage/--no-sandbox/--disable-gpu）；本地 10/10 无回归 | config diff + 运行日志 |
| B112-3 UI job 定时 | TestSchedule job_type=ui + UiTestJob cron/schedule_enabled + 迁移 + 调度分发 + 前端定时设置；**单测 7/7** | `tests/test_batch115_ui_schedule.py` + alembic revision |
| C107-2 接口依赖链 | TestCase depends_on_ids + $prev 变量注入 + 环检测；**单测 4/4**；场景串联用例落库（id 1833） | `tests/test_api_dependency_chain.py` |
| B10 XHR 采集 | capture-page-xhr.py 采集 **981 条样本**（9 页，含请求头，解决 batch-112 缺口） | `evidence/batch-115/xhr-capture-sample.json` |
| 生成链路消费关联基座 | ai_service functional 提示注入关联基座；**单测 4/4** | `tests/test_association_baseline_injection.py` |
| B112-1 重探 | news/get 仍业务 400，get_visible 200 → 口径待用户确认 | 2026-08-07 重探 |

## 2. 可执行门禁

| 门禁 | 结果 |
|------|------|
| 新单测（B112-3 7 + C107-2 4 + 注入 4） | ✅ 15 passed |
| 回归（apitest_generation/tasks/response_structure/dependency） | ✅ 37 passed |
| ruff F821（7 个改动文件） | ✅ All checks passed |
| Alembic 单头（20260807_batch115_ui_schedule） | ✅ |
| 前端 typecheck + build | ✅（npm ci 后，deep-eql 为本地依赖漂移已修复） |
| uitest 页面 vitest | ✅ 19 passed |
| scan-common-bugs | 🔄 Leader 阶段 |

## 3. 缺陷/障碍

| # | 级别 | 问题 | 处理 |
|---|:----:|------|------|
| B115-1 | P3 | 本地 npm ci 前 typecheck 报 deep-eql 缺失（依赖漂移） | npm ci 修复，登记提示 |
| B115-2 | P3 | 平台 XHR 采集为脚本工具，平台 API/UI 集成待迭代（C115-3） | 登记 |

## 4. 诚实性说明

- 平台级验证（UI 定时任务触发 10/10、场景依赖链实跑、交互 job 连续 2 次 10/10）依赖本批迁移+代码合入部署，
  按 Batch 112 模式登记 C115-1/2/4；单测已覆盖逻辑正确性。
- B112-1 为体育平台服务端问题，本批重探仍 400，需用户口径确认（内部端点 or 缺陷）。

## 5. 发布建议

状态: **有条件通过**（部署后验证 C115-1/2/4 + B112-1 口径）

## 6. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 2d / 实际 1d | 0/0/0/2 | 2 | 工具链 | 大功能批次先拆后端单测再合前端；DB 列依赖迁移先确认部署窗口 |

**技能使用**：`cameltv-agent-team`、`cameltv-bug-guard`、`playwright-cli`、`test-case-design`。