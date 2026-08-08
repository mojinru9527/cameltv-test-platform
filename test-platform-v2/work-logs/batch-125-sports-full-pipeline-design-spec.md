# Batch 125 — Design Spec（全链路接入设计）

> **Design (🎨)** | Date: 2026-08-09 | Status: 就绪

## 1. 功能梳理（Slice 1）
- `build_sports_feature_inventory.py`：从蓝湖导出 hierarchy.json + HTML 提取功能点（action/state/field/list），过滤导航噪音。
- 输出：`sports-feature-inventory.json`（38 模块/183 页/6429 功能点；运营后台 17 模块 2153、用户端 21 模块 4276）。

## 2. 生产深度体验（Slice 2）
- Playwright/应用内浏览器走查 camel1.tv：10 页（首页/赛事详情/预测更多/联赛/球队/球员/直播/资讯/个人中心）+ 9 截图。
- 输出：`production-findings.json`（页面结构/状态/发现/差异/缺陷）。
- 关键发现：预测三选项+赔率、未登录拦截登录、联赛 7 tab、球队 7 tab+赛事筛选、球员 4 tab+转会、直播 10 tab+聊天、个人中心菜单、生产 "test test" 残留（P2）、英文站 vs 中文原型差异。

## 3. 用例生成链路（Slice 3）
- `run_base_case_generation.py`：功能清单 → extraction(模块×功能点) → `ai_service.generate_test_cases`（加载功能用例规范 skill 权威输出要求 + 深度用例层）→ 分块生成（≤12 FP/块）基础用例。
- `run_all_base_cases.py`：38 模块批量（断点续跑/失败重试/汇总）。
- `consolidate_module_cases.py`：每模块 = 基础用例 + Batch 122 SP- 深度用例。
- 用例字段：title/priority/domain/module/positive_negative/preconditions/steps/expected_result/client_scope。

## 4. 知识中心体现（Slice 4）
- 需求/设计稿：`import-requirement-design.py`（C124-1 链路，部署后执行）。
- 模块树：`/requirement-modules/import-tree`（218 节点全量）。
- 生产发现：作为 knowledge source 入库（source_type=requirement，文本=production-findings）。
- 用例：基础+深度用例批量导入 test_case（复用 batch-122 import-case-batch-api 模式）。
- 关联：用例-模块-需求页 tested_by 图谱关系。

## 5. 数据流
```
蓝湖导出(183页) → 功能清单(38模块/6429FP)
  → 基座生成基础用例(两 skill) → 深度用例(Batch 122 SP-) → 合并
  → 知识中心：需求文本+设计稿 + 模块树(218) + 生产发现 + 用例(基础+深度) + 图谱关联
```
