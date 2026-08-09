# Batch 126 — QA 报告（测试平台生产对抗性审查 + 修复）

> **QA (🔍)** | Date: 2026-08-09 | Verdict: PASS（C126-1~4 为非阻塞后续）

## 1. 交付与证据

| # | 交付 | 证据 |
|---|------|------|
| 1 | **对抗性审查报告**：24 导航模块生产走查 + API 数据核对 + 前端源码路由核对 | `batch-126-production-adversarial-review.md`：P1×5 / P2×5 / P3×2 + 修正早期误报记录 |
| 2 | **图谱完整性修复（B126-1）**：GraphTab fetch limit 200→1000，全量 970 实体/968 关系呈现 + 大数据量渲染提示 | GraphTab.tsx |
| 3 | **差异对比引导（B126-8）**：发起对比 disabled 时显示「请先输入需求关键词」+ tooltip | WikiDiffTab.tsx |

## 2. 关键发现（生产）

- **P1**：图谱视图仅 195 节点/161 边（970 实体被 limit 截断）；实体全部「来源待补」；项目知识无需求/设计稿；需求覆盖率 0%；AI 审核台 85 条待审置信度 0%。
- **P2**：图谱渲染性能差（CDP 超时）；Wiki 原始 markdown 未渲染；差异对比按钮无引导（已修）；用例口径不一致（工作台 vs 用例服务）；项目球 SphereTab 死代码。
- **P3**：交互覆盖缺口 517；报告中心 0 报告。
- **修正**：差异对比/AI 审核台/用例脑图/需求文档/用例服务早期误报「建设中」→ 复核均可用（路由猜错）。

## 3. 可执行门禁

| 门禁 | 结果 / 退出码 | 日志摘要 |
|------|---------------|----------|
| `npm ci` | ✅ 0 | 安装 559 个包；`npm audit` 报告 4 个 high 基线漏洞，本分支未修改依赖 |
| `npm run typecheck` | ✅ 0 | `tsc -b` |
| `npm run build` | ✅ 0 | Vite 7.3.6；3431 modules；8.97s |
| 相关 Vitest | ✅ 0 | `batch54-production-governance.test.ts` + `GraphTab.test.tsx`：2 files / 9 tests |
| 前端全量 `npm test` | ✅ 0 | 94 files / 362 tests；无 worker 异常 |
| `git diff --check origin/main` | ✅ 0 | 无空白错误 |
| 调试/凭据扫描 | ✅ 0 | 本批 6 个原始文件无 `console.log`/`debugger`/密钥模式命中 |

后端、Alembic 与 OpenAPI：本分支无后端、迁移或 API schema 变更，按 CI 分类不适用。

### QA 修复闭环

- 首轮全量 Vitest 捕获 `GraphTab.tsx:496` 的固定色板类 `text-amber-600`，触发主题治理测试失败。
- 按 UI 规范替换为 `text-status-warning`；定向测试 9/9、随后全量 362/362 通过。
- `scan-common-bugs.ps1` 仍报告 2 个 HARD 与 247 个 WARN 基线项；2 个 HARD 位于未改动的后端脚本 `build_lanhu_hierarchy.py`、`run_all_base_cases.py`，不属于本分支新增失败。
- `audit-cconditions.ps1` 仍报告 4 个历史孤儿条件（C120-3、C122-1、C122-3、C123-1），均不由本批新增；C126-1~4 已同步到 `C-CONDITIONS.md`。

## 4. 发布建议

状态: **READY** ｜ 必修复: 0 ｜ 非阻塞后续: C126-1~4（实体来源/覆盖率口径/置信度/图谱性能）

## 5. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 审查 1d / 实际 0.5d | 0/5/6/2 | 2 | 需求不清 + 工具链 | 走查前先读路由/tab 定义；提交前先跑主题治理测试与全量 Vitest |

**技能使用**：`cameltv-agent-team`、`cameltv-ui-conventions`、`cameltv-bug-guard`（技能结论不替代上述执行证据）。
