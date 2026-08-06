# Batch 103 — QA Report（用例质量与接口可视优化）

> **QA (🔍)** | Date: 2026-08-06 | Verdict: 需改进（覆盖度/可视已落地，平台障碍待迭代）

## 1. 交付与生产证据

| 资产 | 结果 | 证据 |
|------|------|------|
| 功能用例覆盖度 | 用户端 90 FP → 227 条（2.52/FP）；运营后台 108 FP → 249 条（2.31/FP）；替换旧 77/133 并重导入 | local-ai-doc1/3-refreshed.json + import-refresh-summary.json |
| 用例规范对齐 | ai_service 生成提示词注入等价类/边界值/场景法/错误推测 + 正负向成对 + ≥2 条/FP；新增 case_design_method/positive_negative/test_data_note 字段（476 行回填） | backend ai_service.py + DB backfill |
| 接口用例真实参数 | 3 个真实样本接口生成 72 条字段级用例（list_visible 33 / ads-activity 38 / client-general 1），api_body/api_assertions 完整（接口域 172 条含真实 body+断言） | production-xhr-samples.json + interface-cases-summary.json |
| 接口用例可视 | TestCase 新增 last_response_json/last_run_status；执行接口回填；前端详情「接口数据」Tab（请求参数/断言/请求结果 + 设计方法/正负向徽标） | backend schema + CaseDrawer.tsx |
| 全接口真实数据原则 | C103-4 登记：schema 为空时以真实样本字段驱动（generate_cases_from_real_sample），无意义 mock 禁止 | api_case_generation_service.py + test_api_case_real_sample.py |

## 2. 硬门禁

| 门禁 | 结果 |
|------|------|
| 后端受影响模块 pytest | ✅ 46+3 passed（apitest_generation/requirement/ai_chunked/openapi_import/real_sample） |
| ruff F821（7 个改动文件） | ✅ All checks passed |
| 前端 typecheck | ✅ tsc -b 通过 |
| 前端 build | ✅ 9.11s 构建成功 |
| 前端 vitest（testcase 模块） | ✅ 22 passed |
| Alembic | ✅ 单头；upgrade head → downgrade -1 → re-upgrade 全绿（幂等迁移，create_all 场景兼容） |
| audit-cconditions -RequireLatestBatch | ✅ hard errors 0 / warnings 0 |
| validate_repo_boundaries --check | ✅ PASS |

## 3. 缺陷/障碍（P0–P3）

| # | 级别 | 问题 | 实测证据 | 处理 |
|---|:----:|------|---------|------|
| B103-1 | P2 | DeepSeek 单次输出约 8K token 上限，25 FP/块在新增设计字段后截断严重（batch-102 时 92 FP 仅 77 条） | 本地复算 finish_reason=length 多次 | 分块上限 25→12，覆盖度提升至 2.3-2.5 条/FP；登记 C102-5 块级补全继续跟进 |
| B103-2 | P2 | Test5 契约 body schema 为空（如 list_visible properties={}），规则生成器无字段可覆盖 | /apitest/endpoints 实测 schema 空 | 新增真实样本字段级生成器（generate_cases_from_real_sample），以生产/测试真实请求为字段来源 |
| B103-3 | P2 | 生产后端部署前新字段不可见（Railway 旧代码） | API 返回无新字段 | 生产库已直连迁移+回填，部署后前端可见；本批合入后随部署生效 |

## 4. 诚实性说明

- 功能用例由本地 ai_service（规范提示词）生成并直连同步生产库（沿用 C102-1 期间的通道），最终经平台标准 import API 落库。
- 接口真实样本目前覆盖 3 个接口（用户提供的 list_visible + 生产抓取的 ads/activity、client/general）；其余接口按 C103-4 原则在后续批次补充真实样本后生成，未用 mock 填充。
- 新字段在部署前经直连生产库迁移+回填保证数据完整；前端展示随部署生效。

## 5. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 1d | 0/0/3/0 | 2 | 工具链+外部依赖 | 真实样本需批量采集（多接口）再生成；迁移先验证 create_all 幂等 |

**技能使用**：`cameltv-agent-team`、`test-case-design`（规范核对）、`playwright-cli`（生产 XHR 抓取）。
