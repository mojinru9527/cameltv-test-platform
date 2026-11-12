# Batch 338（P1-3：QualityGate / NoiseRules 页面）— PRD / Design / Dev

> mode: **full**（新增 PATCH 接口 + 错误码契约）· 分支：`feature/batch-338-quality-noise` · 基线：batch-337 head
> 排期来源：`session-a7cc2999` P1 拆批表（batch-338 质量门禁 / 噪音规则页面）

## 1. 背景

batch-330 提供了质量门禁判定与噪音规则 CRUD 的 HTTP API，但存在三个问题：

1. 前端没有任何页面：QA 只能用 curl 调 `/aiqe/admin/quality-gate` 与 `noise-rules`；
2. 规则写接口没有错误映射：`NoiseRuleError`（空 pattern / quarantine 无到期 / 超 90 天）会冒泡成 500；
3. 列表不返回"是否生效"，前端无法标红临期/过期规则；也没有更新规则（PATCH）能力。

## 2. 目标与非目标

**目标**

1. 新增 `/aiqe/quality-gate` 页面：P0 统计输入 → 调真实 API → PASS/FAIL/BLOCKED 徽标 + reasons；
2. 新增 `/aiqe/noise-rules` 页面：列表、创建、续期、删除；临期 7 天内与已过期标红；
3. 后端：噪音规则写接口错误映射（400/404）；新增 `PATCH /noise-rules/{id}`；列表补 `effective`；
4. 两个页面沿用 `menu:aiqe_runs` 守卫与 ConsoleTabs 导航。

**非目标**

- 不改质量门禁判定规则（P0 全通过才 PASS）；
- 不做规则批量导入/导出；
- 不改 NoiseRule 表结构与 90 天上限。

## 3. 设计

| 层 | 变更 |
|----|------|
| API | `PATCH /aiqe/admin/noise-rules/{id}`；create/renew/delete 捕获 `NoiseRuleError` → 400/404 |
| 响应 | 列表项补 `effective`（`status=active` 且未过期） |
| 前端 | `pages/aiqe/quality-gate.tsx`、`pages/aiqe/noise-rules.tsx`；`api/aiqeConsole.ts` 增 5 个函数 |
| 导航 | ConsoleTabs 增"质量门禁 / 噪音规则"；路由 `/aiqe/quality-gate`、`/aiqe/noise-rules` |

**到期展示口径**：`expires_at - now` ≤ 7 天或已过期 → 红色文本 + "（已过期）/（剩 N 天）"；`effective=false` → "已过期"徽标。

## 4. 实现清单

后端：

- `app/api/v1/aiqe_admin.py`：`_noise_rule_out`（含 effective）、错误映射、PATCH 端点。
- `tests/test_aiqe_console_admin_api.py`：11 条（门禁 5 态参数化、CRUD、空 pattern、quarantine 无到期、超 90 天、过期标记、权限 403）。

前端：

- `src/api/aiqeConsole.ts`：`evaluateQualityGate` / `listNoiseRules` / `createNoiseRule` / `renewNoiseRule` / `deleteNoiseRule`。
- `src/pages/aiqe/quality-gate.tsx`：5 个 P0 输入 + 判定结果卡片。
- `src/pages/aiqe/noise-rules.tsx`：创建表单 + 列表（续期/删除/到期标红）。
- `src/pages/aiqe/__tests__/qualityGate.test.tsx`（2 条）、`noiseRules.test.tsx`（3 条）。

## 5. 风险

| 风险 | 等级 | 处置 |
|------|:----:|------|
| 前端按本地时区计算"剩余天数"与后端 UTC 偏差 | 低 | 统一用 `Date` 解析 ISO；仅展示用途，判定以后端 `effective` 为准 |
| 旧客户端依赖 create 响应仅 id/expires_at/status | 低 | 响应为超集（新增字段），不破坏兼容 |
| 90 天上限导致续期永远 90 天 | 低 | 与 `renew_rule` 既有语义一致（强制复核） |

## 6. 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 门禁 5 态（PASS/FAIL/BLOCKED×3） | `test_quality_gate_status` |
| A2 | 规则 CRUD + 续期 + PATCH | `test_noise_rule_crud` |
| A3 | 非法输入 400、不存在 404 | 3 条错误用例 |
| A4 | 过期规则 `effective=false` | `test_noise_rule_expired_flag` |
| A5 | 无 `menu:aiqe_runs` → 403 | `test_console_admin_requires_menu_permission` |
| A6 | 前端判定展示与规则操作 | `qualityGate.test.tsx` / `noiseRules.test.tsx` |
