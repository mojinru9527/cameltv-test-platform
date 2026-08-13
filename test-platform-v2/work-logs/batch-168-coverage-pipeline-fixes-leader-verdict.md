# Batch 168 — Leader Verdict
> **Leader (🎯)** | Date: 2026-08-13 | Decision: APPROVED（待用户一次总确认 + CI required checks 全绿后合入）

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 良好 | 后端 1427 pass；前端 458 pass；真实数据复测 77.8% 达标 |
| 风险 | 低 | 新行为均有阈值/幂等守卫；外部凭据 fail closed |
| 覆盖 | 达标 | D1–D8 均有单测 + 真实 16.0.0 证据 |

## 关键决策（已批准）
1. 覆盖口径修正：有模块树时只统计版本内用例（requirement_module_id 或 bundle 绑定文档），避免跨版本污染。
2. 模块级端点匹配：只绑定已导入真实端点，GET 优先、confidence>=0.4、按置信度排序、允许同一端点服务相关模块（module 维度区分行）。
3. UI 变体回填覆盖历史已导入用例；executed 覆盖如实统计（执行过即算，含 fail）。

## 抽检通过
- ✅ `app/services/version_coverage_service.py` — 键/版本圈定/P0P1 口径。
- ✅ `app/services/requirement_service.py` — is_deleted 过滤、变体独立行、FP→父模块映射、模块级匹配。
- ✅ `app/services/test_plan_service.py` — ui_environment_id 与 `_ui_error_summary`。
- ✅ `frontend/.../BundleDetail.tsx` 与 `PlanDetail.tsx` — Tab 独立、UI 环境选择。
- ✅ 硬门禁：ruff/import/alembic/pytest 1427/typecheck/lint/build/vitest 458 全绿。
- ✅ 真实数据：`retest-168.json` 14/18=77.8%，gate_passed=true，UI 截图两张。

## 判决
APPROVED。仅待：用户一次总确认（推送 + Draft PR + required checks 全绿后合入）。

## 下一批次 Leader 条件
- **C167-1**（保持 Open）：真实账号登录态与写操作数据准备补齐后，UI 执行覆盖复测；未补齐前如实展示「执行未覆盖」。
- **C167-2**（本批关闭，见 C-CONDITIONS.md）：真实版本端到端基线已完成，60% 门禁 77.8% 达标。
- **C167-3**（保持 Open）：`release_bundle.api_spec_url` 接入 `POST /release-bundles/{id}/import-api-spec`，本批非目标。
- **C168-1**（新增）：test 部署后在生产站点（www.camel1.tv）用真实登录态跑 UI 执行覆盖，观察 D7 分环境与 LLM 编译在生产可用性。

## 流程回写
| 发现 | 处理 | 落点 |
|------|------|------|
| 覆盖矩阵 fallback 用 None id 聚合导致全局污染 | 已修；总结为「聚合键必须含非空语义维度」 | cameltv-bug-guard（建议补 PATTERNS） |
| 生成模块字段是 FP 别名而非父模块，导致对齐失败 | 已修；经验写入本批 QA | work-logs/batch-168-qa-report.md |
| AI 未配置时 rules 编译产生 TODO 占位 | 如实 fail + 可读摘要（不改编译器） | 无需处理 |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 6h / 实际约 5h | 0/3/3/0 | 2 | 老数据兼容与聚合键 | 真实数据样例先行 |

**技能使用**: cameltv-agent-team（六部门）、cameltv-bug-guard、cameltv-ui-conventions、test-case-design。
