# batch-23 QA 报告 — 接口测试模块优化

> 日期：2026-07-20 | QA 部门 | 7 项需求，3 个 Slice

## 测试覆盖

| 测试套件 | 状态 | 通过/总数 |
|----------|------|----------|
| AssetTab.test.tsx | ✅ PASS | 2/2 |
| ApiCaseTab.test.tsx | ✅ PASS | 1/1 |
| apiCaseGroups.test.ts | ✅ PASS | 2/2 |
| 后端 test_apitest_generation.py | ✅ PASS | 15/15 |

**总通过率**: 20/20 (100%)

## Slice 1: 接口资产层级重构

### ✅ 检查项
- [x] AssetTab `modulePathGroups` 已重构为 `hierarchy`，支持 Service → Module → PathGroup → Endpoint 四层
- [x] "全部服务" Tab 下服务名作为一级折叠（`defaultOpen={false}`），模块作为二级折叠
- [x] 单个服务 Tab 下直接显示模块列表（折叠状态）
- [x] PathGroup 改为内联标签，不再作为独立 Collapsible
- [x] 模块名/服务名均默认收起
- [x] `ep.path` 显示真实路径而非替换 `/` 为 `-`
- [x] Tab 切换时重新请求对应服务的 endpoints

### ⚠️ 发现的问题
无。AssetTab 测试全部通过。

## Slice 2: 接口用例 & 快速调试

### ✅ 检查项
- [x] apiCaseGroups 新增 `method`/`endpoint` 字段，优先按 `api_spec_ref` 分组，降级按 `method:endpoint`
- [x] ApiCaseTab 组头显示 Method Badge + Endpoint 路径
- [x] 组头显示用例数量（如"2 条用例"）
- [x] DebugTab ResponsePanel 添加 `id="response-panel"` 锚点
- [x] 请求完成后自动滚动到响应结果区域（`scrollIntoView`）
- [x] 地址拆分确认：4 字段网格（服务器地址/服务名/模块路径/接口路径）保持
- [x] 环境切换联动 baseUrl 保持

### ⚠️ 发现的问题
- `CollapsibleTrigger` 包含嵌套 `<button>`（checkbox），产生 DOM nesting warning。非本次引入（预存），建议后续用 `div` + `role` 重构

## Slice 3: 用例生成覆盖增强

### ✅ 检查项
- [x] 前端 `AssetTab` 生成模板从 4 个扩展到 6 个（basic/boundary/invalid/security/idempotency/extreme）
- [x] 后端新增 `_build_extra_boundary_cases` 函数：为每个参数生成 null/空值/零值/负数用例
- [x] 后端新增 `_build_combo_param_cases` 函数：多参数组合覆盖（全正常、全边界、混合）
- [x] 后端新增 `_get_invalid_value` 辅助函数
- [x] Query 参数必填校验扩展：增加 null 和空字符串用例
- [x] 数量下限保证：参数≥3 时至少 25 条；参数≥5 时至少 40 条
- [x] 15 个后端单元测试全部通过

## 缺陷清单

| 编号 | 严重度 | 描述 | 状态 |
|------|--------|------|------|
| B23-01 | P3 | ApiCaseTab CollapsibleTrigger 嵌套 button DOM warning（预存） | 已知/不修复（本次） |

## 性能影响

- AssetTab hierarchy `useMemo` 多了一层 service 维度，时间复杂度 O(n) 不变
- 用例生成新增 2 个函数调用，在最坏情况下（200 上限保护）不受影响
- DebugTab 新增的 `useEffect` 仅在 `result` 变化时触发，无性能影响

## QA 判决

**✅ APPROVED** — 3 个 Slice 实现完整，所有测试通过，无新引入缺陷。
