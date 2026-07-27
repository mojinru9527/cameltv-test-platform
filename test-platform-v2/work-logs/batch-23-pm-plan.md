# batch-23 PM Plan — 接口测试模块优化

> 日期：2026-07-20 | PM 部门 | 7 项需求 → 3 个 Slice

## Slice 1: 接口资产层级重构 (问题 1-3)

| 任务 | 文件 | 描述 | 验收 |
|------|------|------|------|
| T1.1 | `AssetTab.tsx` | `modulePathGroups` → `hierarchy` useMemo（Service→Module→PathGroup→Endpoint 四层）；新增 `renderModules()`、`renderEndpointRows()`、`renderTabContent()` 辅助函数 | 服务名/模块名 `defaultOpen={false}` |
| T1.2 | `AssetTab.tsx` | "全部服务" Tab 下渲染服务组折叠 + 模块折叠；单服务 Tab 直接渲染模块折叠 | 切换 Tab 后只显示对应内容 |
| T1.3 | `AssetTab.tsx` | 路径显示改为 `ep.path` 原始格式 | 不替换 `/` 为 `-` |
| T1.4 | `AssetTab.test.tsx` | 适配新层级测试 | 测试通过 |

## Slice 2: 接口用例 & 快速调试 (问题 4-6)

| 任务 | 文件 | 描述 | 验收 |
|------|------|------|------|
| T2.1 | `apiCaseGroups.ts` | 新增 `method`/`endpoint` 字段；优先按 `api_spec_ref` 分组，降级按 `method:endpoint` | `groupApiCases` 返回包含 method/endpoint |
| T2.2 | `ApiCaseTab.tsx` | 组头显示 Method Badge + Endpoint 路径 + 用例数 | 视觉确认 |
| T2.3 | `DebugTab.tsx` | ResponsePanel Card 添加 `id="response-panel"`；新增 useEffect 自动滚动 | 发送请求后页面自动滚动 |
| T2.4 | 测试文件 | 适配新分组格式 | 测试通过 |

## Slice 3: 用例生成覆盖增强 (问题 7)

| 任务 | 文件 | 描述 | 验收 |
|------|------|------|------|
| T3.1 | `AssetTab.tsx` | 模板列表从 4 个扩展到 6 个（+security +extreme） | 调用 generateApiCases 时传入 6 个模板 |
| T3.2 | `api_case_generation_service.py` | 新增 `_build_extra_boundary_cases`（null/空/零/负） | 每个参数生成边界用例 |
| T3.3 | `api_case_generation_service.py` | 新增 `_build_combo_param_cases`（多参数组合） | 参数≥2 时生成组合用例 |
| T3.4 | `api_case_generation_service.py` | 数量下限保证（≥3 参数→25+，≥5 参数→40+） | 满足最小数量要求 |
| T3.5 | `api_case_generation_service.py` | `_build_query_required_cases` 补充 null/空字符串 | query 参数覆盖完整 |

## 预估工作量

- Slice 1: 45 min
- Slice 2: 30 min
- Slice 3: 45 min
- 总计: 2h
