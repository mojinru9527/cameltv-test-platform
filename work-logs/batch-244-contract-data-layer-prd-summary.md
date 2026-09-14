# Batch 244 — Contract & Data Layer Hardening（第二阶段）

> **Product (🟦)** | Date: 2026-09-14 | Status: Approved

## 0. 批次模式

`mode: full`。本批引入新的前端契约类型来源、查询策略和批量数据读写行为，命中「新行为/新接口约束/重构」判定。

## 1. 问题陈述

第一阶段完成后，平台仍存在三类契约与数据层问题：

1. `src/types/api.d.ts` 已生成，但业务代码没有实际使用，前端 API 层仍有大量手写响应结构和 `any`，后端字段漂移无法被 TypeScript 拦截。
2. OpenAPI 导入、测试计划执行准备、dashboard 统计存在循环内查询，数据量增大后出现明显 N+1。
3. 自定义 GET cache 只对少数端点失效，React Query 与手写缓存并存，mutation 后可能读取旧数据。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| 生产 API 模块 `any` | 34 处 | 0 处（测试文件除外） |
| OpenAPI 生成类型使用 | 0 个业务 import | 核心 schema 经统一 `contract.ts` 被 API 层引用 |
| OpenAPI 导入查询 | 每个 endpoint 1 次 SELECT | 固定次数：预取 + 批量写入 |
| 计划执行用例查询 | 循环内 `db.get` | 固定次数：`IN` 批量映射 |
| Dashboard 趋势查询 | 7 天 × 项目循环查询 | 固定次数：聚合查询 |
| 缓存失效 | 仅 domain 等少数前缀 | 统一 query key/prefix invalidation，写后不读旧数据 |

## 3. 非目标

- 不迁移两套 UI 组件体系。
- 不重做公开首页、登录页和视觉设计。
- 不清除页面组件层的所有 `any`；本批只清理 `src/api` 生产模块。
- 不改变后端业务响应结构或现有 API 路径。

## 4. 用户故事 + 验收标准

- As a 前端开发者, I want API 类型来自 OpenAPI schema, so that 字段改名会在 typecheck 暴露。
  - Given 生成 `api.d.ts` / When 修改核心响应类型 / Then API 模块返回类型同步失败或通过。
- As a 测试工程师, I want 大量导入/执行不随条数线性增加查询, so that 大规模用例仍可接受。
  - Given 900 个 endpoint / When 导入 / Then 查询次数不随 endpoint 数量线性增长。
- As a 用户, I want 写入后列表和统计及时更新, so that 看不到旧数据。
  - Given mutation 成功 / When 重新读取 / Then 相关缓存已失效或被 React Query invalidation 覆盖。

## 5. 技术考量

- 采用 `components['schemas']` 作为生成契约的单一类型入口。
- 保持现有响应 envelope，不把生成类型强行套到不匹配的端点。
- 批量查询优先一次 `IN` + 内存映射；不引入新的数据库依赖。
- 缓存先收敛到明确的 `apiCacheKey` / invalidation helper，避免一次迁移全部页面到 React Query。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| S1 | 前端开发者 | `contract.ts` + 核心 API 类型迁移，typecheck 通过 |
| S2 | 前端开发者 | 生产 API `any` 清零，API 层 lint 硬门禁 |
| S3 | 后端/测试工程师 | 导入/计划/dashboard 查询计数回归 |
| S4 | 全部用户 | 缓存失效测试通过，既有功能回归无回归 |

## 7. 技能使用

- `cameltv-agent-team` → 六部门流水线。
- `cameltv-bug-guard` → N+1、缓存和契约漂移检查。
- `karpathy-guidelines` → 保持改动最小、可验证，不趁机重写 UI。
