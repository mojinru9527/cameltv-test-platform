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

## 2c. 全字段语义覆盖 + 生产回填（修订口径）

- **接口清单**：按功能需求（Batch 102 功能模块地图）确定要覆盖的接口，不是全量 899 端点无差别堆砌。
- **生产回填**：能通过生产环境接口获取的真实请求/响应，优先回填为测试数据基线
  （样本通道：用户/业务提供、Playwright 生产页面抓 XHR、契约 schema 作校验维度）。
- **全字段覆盖**：每个接口的用例与调试数据必须覆盖该接口**全部字段**，逐字段回答：
  | 问题 | 示例（news/list_visible） |
  |------|--------------------------|
  | 字段业务含义 | page=页码；size=每页条数；sorts[].key=排序字段（top/updateTime）；queryList[].key=过滤字段（language）；locale=语言；value1/value2=查询值/区间边界 |
  | 类型与校验 | String/Integer/数组/对象；page 传字符串/小数/负数；queryList 缺省/空数组 |
  | 取值范围/枚举 | page≥1；size 1~上限；language 枚举（生产回填确认 0/1…）；sort desc/asc；isOrNotRange 0/1 |
  | 边界 | page=1 首页、超总页数；size=1/0/负数/超上限；value1 为空/超长/特殊字符 |
  | 组合 | sorts 多字段排序、queryList 多条件 AND、分页+过滤+排序+语言组合 |
  | 默认值 | locale 缺省、size 缺省、queryList 缺省时的行为 |
- **构造贴合数据，禁止无意义 mock**：每个用例的数据必须可解释其业务语义
  （如 size=30 是业务常用页大小、page=2 是翻页场景、language=0 是语言枚举值），
  不允许随机占位字符串/数字。生产回填不可达的字段用例仍按语义构造，但标注
  「无生产回填样本，语义按契约推断」，由 QA 报告汇总待生产验证项。

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
