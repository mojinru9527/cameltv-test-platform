# batch-23 PM 计划 — 接口测试模块优化

> 日期：2026-07-20 | PM 部门 | 7 项改进，3 个 Slice

## 任务拆分

### Slice 1: 接口资产 Tab 层级重构（US-1, US-2, US-3）

| # | 任务 | 描述 | 验收标准 | 涉及文件 | 预估 |
|---|------|------|---------|---------|------|
| T1.1 | 重构 AssetTab 模块展开逻辑 | 将 modulePathGroups 从全局改为按 service 过滤，服务 Tab 选中后仅展示该服务下的模块；"全部服务" Tab 按服务名分组显示 | 切换服务Tab后仅显示对应服务的模块列表，折叠状态 | `AssetTab.tsx` | 45min |
| T1.2 | 简化三级层级为模块→接口 | 移除中间 pathGroup 层级作为独立折叠项，改为模块折叠内显示 pathGroup 标签 + 接口行 | 每个模块展开后显示 pathGroup 子标题 + 接口列表 | `AssetTab.tsx` | 30min |
| T1.3 | 全部服务 Tab 增加服务名分组 | "全部服务" Tab 下按服务名分组，每个服务作为一级折叠，下面展示该服务的模块 | 全部服务Tab能看到服务→模块→接口三层 | `AssetTab.tsx` | 30min |

### Slice 2: 接口用例 & 快速调试优化（US-4, US-5, US-6）

| # | 任务 | 描述 | 验收标准 | 涉及文件 | 预估 |
|---|------|------|---------|---------|------|
| T2.1 | 用例按接口分组增强 | 改进 apiCaseGroups 的分组逻辑，按 api_endpoint 分组并在组名中展示接口路径和方法 | 接口用例列表按"方法+路径"维度分组展示 | `apiCaseGroups.ts`, `ApiCaseTab.tsx` | 30min |
| T2.2 | 快速调试响应确认底部 | 确认 ResponsePanel 在 DebugTab 页面最底部（代码审查确认），必要时增强自动滚动 | 响应结果区域在页面底部，发送后可自动滚动 | `DebugTab.tsx` | 15min |
| T2.3 | 地址拆分加固 | 确认 composeAssetUrl 地址拼接正确；加固从接口资产跳转时字段预填；确认环境切换联动 | 资产→调试预填；环境切换URL联动；发送拼接正确 | `DebugTab.tsx` | 30min |

### Slice 3: 用例生成覆盖增强（US-7）

| # | 任务 | 描述 | 验收标准 | 涉及文件 | 预估 |
|---|------|------|---------|---------|------|
| T3.1 | 前端启用全部模板 | AssetTab 中 generateApiCases 调用加入 'security' 和 'extreme' 模板 | 调用6个模板生成用例 | `AssetTab.tsx` | 10min |
| T3.2 | 后端增强参数类型覆盖 | 为 query 参数的必填字段补全缺失/null/空值用例；为每个参数至少生成3条用例 | 每个参数至少覆盖缺失+空值+类型错误 | `api_case_generation_service.py` | 45min |
| T3.3 | 后端增强边界值覆盖 | 为每个参数增加 null 值传输用例、空值用例；integer/number 参数的 0 值、负数边界 | 边界覆盖更全面 | `api_case_generation_service.py` | 30min |
| T3.4 | 生成数量下限保证 | 如果 schema 有 ≥3 个参数，确保至少生成 25 条用例；如有 ≥5 个参数，至少 40 条 | 多参数接口生成更全面 | `api_case_generation_service.py` | 30min |

## 依赖关系

```
Slice 1 (无依赖) → Slice 2 (无依赖，可并行) → Slice 3 (无依赖，可并行)
```

三个 Slice 之间无强依赖，可独立开发验证。

## 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 前端 Collapsible 组件与 Tab 切换状态冲突 | 中 | 中 | 使用 key prop 强制重新挂载 |
| 用例生成数量增加导致前端卡顿 | 低 | 低 | 已有 _MAX_CASES_PER_ENDPOINT=200 上限保护 |
| git fetch 网络不通 | 已发生 | 低 | 基于本地 latest develop 开发，后续同步 |

## 预估总工时

| Slice | 任务数 | 预估 |
|-------|--------|------|
| Slice 1 | 3 | 105 min |
| Slice 2 | 3 | 75 min |
| Slice 3 | 4 | 115 min |
| **合计** | **10** | **~5 hours** |
