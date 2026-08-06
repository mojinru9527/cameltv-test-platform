# Batch 103 — Design Spec（用例质量与接口可视优化）

> **Design (🎨)** | Date: 2026-08-06 | Status: Review

## 1. AI 生成规范注入（backend ai_service）

- 生成系统提示词追加「用例设计规范」段：等价类划分、边界值、场景法、错误推测、正负向成对；
  每功能点（FP）至少产出 2 条用例（正向 + 负向/边界），复杂状态机模块 ≥3 条。
- 输出契约：`AIGeneratedCase` 增加 `case_design_method`（等价类/边界值/场景法/错误推测）、
  `positive_negative`（positive/negative/boundary）字段；`title` 前缀标注（[正向]/[负向]/[边界]）。
- 生成后校验：按 extraction FP 对齐统计覆盖缺口（未覆盖 FP 清单），产出覆盖缺口报告。

## 2. 接口用例可视（backend + frontend）

- `TestCase` 增加 `request_params_json`（请求参数示例/约束，如 header/query/body 字段）、
  `assertions_json`（断言列表：状态码/字段/值匹配）、`last_response_json`（最近执行实际响应）。
- 接口用例执行后回填 `last_response_json` + `last_run_status`；前端用例详情页新增
  「请求参数 / 断言 / 请求结果」三栏（shadcn/ui Tab，遵循 cameltv-ui-conventions）。
- 迁移：Alembic 新增迁移（含回滚）；API 序列化同步字段。

## 2b. 接口用例真实参数驱动（生产基线）

- 参数基线来源：真实生产请求样本（如 `/camel-service/ee/news/list_visible`）：
  `{"sorts":[{"key":"top","sort":"desc"},{"key":"updateTime","sort":"desc"}],"page":2,"size":30,
  "queryList":[{"isOrNotRange":0,"key":"language","type":"String","value1":"0","value2":""}],
  "locale":"en"}`。
- 按 `API接口测试方案.md` 必选设计（每字段）：
  | 维度 | 字段示例 | 用例方向 |
  |------|---------|---------|
  | 分页 | page=1/0/-1/非数字/超界；size=1/30/0/负数/超上限 | 正/负/边界 |
  | 过滤 | queryList 空/缺省/多条件 AND 组合/key 非法/type 枚举/value 越界 | 正/负/边界/组合 |
  | 排序 | sorts 空/单 key/多 key/非法 sort 值 | 正/负/边界 |
  | 语言 | locale=en/zh/缺省/非法 | 正/负/边界/枚举 |
  | 类型 | 数字字段传字符串/字符串传数字/布尔/数组/对象 | 类型校验 |
- 生成流程：契约参数 schema + 真实样本 → AI 按规范设计字段级用例 → 人工评审 → 执行回填实际响应做断言。

## 3. 覆盖度补强流程（复用 Batch 102 通道）

```text
本地 ai_service（规范提示词）→ 生成（用户端/运营后台）
  → 直连生产库同步 ai_raw + review（C102-1 期间沿用）
  → 平台 import API 导入 → /test-cases/domains 核对计数
  → 覆盖缺口报告（每 FP 正向/负向/边界计数）
```

## 4. 平台使用障碍关联

- C102-1（AI 生成 300s 网关超时）：本期继续用本地生成+同步通道，异步化改造另排期。
- C102-5（AI 截断）：本期覆盖缺口报告显式暴露，块级补生成。
