# Batch 125 — PM 计划（体育平台完整链路接入）

> **PM (🟨)** | Date: 2026-08-09 | Status: 执行中

## 1. 目标
所有体育平台模块用例统一走「功能用例规范 skill + 接口用例 skill」基座：先基座生成基础用例（正/负/边界），再叠加深度用例（Batch 122 模式），并全量体现到知识中心。

## 2. 切片计划

| 切片 | 内容 | 交付 | 状态 |
|------|------|------|------|
| S1 功能梳理 | 用户端+运营后台全量功能点清单（蓝湖导出 183 页） | sports-feature-inventory.json（38 模块/6429 功能点） | ✅ 已提交 |
| S2 二次探索+生产深度体验 | camel1.tv 生产走查（10 页/9 截图/差异/缺陷） | production-findings.json + 截图 | ✅ 已提交 |
| S3 用例生成链路 | 全 38 模块基座生成基础用例 + Batch 122 深度用例合并 | base-cases/*.json + module-cases-consolidated.json | 🔄 后台生成中 |
| S4 知识中心体现 | 需求/设计稿/模块树/生产发现/用例关联 入库 | 入库脚本 + C125 生产验证 | ⏳ 待 S3 完成后 |

## 3. 关键决策
- 基座 = `.claude/skills/test-case-design`（SKILL.md + functional-checklist v2 + api-checklist + 权威输出要求），ai_service 已加载。
- 生成链路：功能清单 → extraction(模块×功能点) → generate_test_cases（分块 ≤12 FP/块）→ 基础用例。
- 深度层 = Batch 122 SP- 用例（状态机/闭环/关联/权限），按模块合并。
- 生产站点 = camel1.tv（英文国际站）；原型 = 中文站（差异 C102-4）。

## 4. 风险
- 全量生成耗时（38 模块预计 3-5h）+ 部分块截断失败（已有重试/断点续跑）。
- 生产入库需 Batch 124 部署后（design-assets/import-tree），登记 C125。

## 5. 验收
- 38 模块每模块 base_count>0 且 deep_count>0。
- 知识中心可见：需求文本+设计稿、全量模块树、生产发现、用例（基础+深度）关联。
