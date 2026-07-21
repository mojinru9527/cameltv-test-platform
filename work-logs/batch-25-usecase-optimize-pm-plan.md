# Batch 25 PM Plan — 用例服务 + 接口测试优化

> PM Department | 2026-07-21 | 3 Slices

## Slice 1: 用例列表 UI 重构 + 筛选增强

**预估**: 45 分钟 | **优先级**: P0

### T1.1 — 列表列重构 (20min)
- [ ] 隐藏"编号"列 (case_id 列)
- [ ] 列顺序: 复选框 → 模块名称 → 用例标题 → 用例等级(Badge) → 前置条件 → 操作步骤 → 预期结果 → 评审 → 操作
- [ ] 每行仅一行展示，超出用 truncate + "......"
- [ ] 前置条件/操作步骤/预期结果用 `formatNumberedText` 显示为 "1、xx 2、xx 3、xx" 编号格式
- **文件**: `test-platform-v2/frontend/src/pages/testcase/index.tsx` (Table columns)

### T1.2 — 用例按时间倒序 (10min)
- [ ] 列表数据用 `sortCasesNewestFirst()` 排序 (函数已存在于 `caseListFormatters.ts:109`)
- [ ] 新增用例完成后列表刷新 → 新用例显示在第一条
- **文件**: `index.tsx` (items 排序)

### T1.3 — 筛选器默认"全部" + 独立搜索 (15min)
- [ ] 域/模块/优先级 Select 均保留 "全部" 选项（已存在），确保默认选中
- [ ] 搜索 placeholder 改为 "搜索标题/关键字"
- [ ] keyword 搜索已在后端支持域/模块/前置条件/步骤/预期结果模糊匹配 (`test_case_service.py:112-133`) — 仅需验证
- **文件**: `index.tsx` (filter bar)

**验收**: `npm run build` 零错误，列表正确显示

---

## Slice 2: 模块分类管理 + 新建用例弹窗 + 逻辑删除

**预估**: 60 分钟 | **优先级**: P0

### T2.1 — 模块分类管理修复 (20min)
- [ ] 修复 405 报错：已确认 `POST /domains` 路由存在，检查前端调用 URL 是否正确
- [ ] 修复 400 报错：`GET /domains/undefined` → 检查 CategoryManagerDialog 中 domain.id 为 undefined 的边界情况
- [ ] 接口测试域从模块分类树中隐藏（过滤 `domain === '接口测试'`）
- [ ] 删除域/模块时级联软删除关联用例（后端 `test_case_service.py` 已实现，确认前端调用正确）
- **文件**: `CategoryManagerDialog.tsx`, `index.tsx` (domain tree filter), `test_case_service.py` (验证)

### T2.2 — 新建用例弹窗修复 (20min)
- [ ] 修复下拉框遮挡：Select 组件的 `SelectContent` 添加 `position="popper"` 和合适的 z-index
- [ ] 模块改为必填：zod schema 中 `module` 已有 `min(1, '请选择模块')`，确认生效
- [ ] 移除 `case_id` 字段（用例编号不显式输入）
- [ ] 移除 `api_spec_ref` 关联引用字段
- **文件**: `CaseDrawer.tsx`

### T2.3 — 逻辑删除一致性 (10min)
- [ ] 删除域时确认级联软删除关联用例（已验证 `delete_domain` 在后端已实现）
- [ ] 删除模块时确认级联软删除关联用例（已验证 `delete_module` 在后端已实现）
- [ ] 接口用例（case_type='api'）默认从用例服务列表中过滤（已过滤但需确认 tab 切换时生效）
- **文件**: `test_case_service.py`, `index.tsx`

### T2.4 — 移除 Excel/Xmind 按钮 (10min)
- [ ] 确认用例列表页没有 Excel/Xmind 按钮（已确认仅注释占位 `// import/export`）
- [ ] 脑图页移除 Xmind 导出按钮 (`mindmap/index.tsx:162-170`)
- [ ] 后端 API 保留不删除（只移除前端 UI 入口）
- **文件**: `mindmap/index.tsx`

**验收**: `npm run build` 零错误，`pytest backend/tests/ -k test_case` 通过

---

## Slice 3: 接口测试模块重构

**预估**: 75 分钟 | **优先级**: P0

### T3.1 — 默认展示接口资产 tab (5min)
- [ ] `ApiTestPage` 的 `activeTab` 默认值从 `'assets'` 开始
- **文件**: `apitest/index.tsx`

### T3.2 — 接口资产三级层级 + 搜索 (30min)
- [ ] 重构 AssetTab 的层级显示：服务 → 模块 → 路径（当前是 4 层含 pathGroup）
- [ ] 模块名和路径名用 `-` 替换 `/` 显示：`ee/search` → `ee-search`，`synonyms/cou` → `synonyms-cou`
- [ ] 搜索功能：遍历服务名/模块名/路径做模糊匹配
- [ ] 接口备注（remark）独立显示为一个字段
- **文件**: `AssetTab.tsx`

### T3.3 — 调试 URL 拼接 + 环境切换 (25min)
- [ ] 从接口资产跳入调试 → 自动拼接完整 URL：`{base_url}/{service_name}/{module_path}/{endpoint_path}`
- [ ] 默认环境为"测试5"
- [ ] 环境切换仅变更 base_url，服务名/模块名/路径不变
- [ ] 直接进入快速调试（非从资产跳转）→ 所有字段为空
- **文件**: `DebugTab.tsx`, `apitest/index.tsx`

### T3.4 — Swagger 导入增强 (15min)
- [ ] ImportDialog 已有服务名输入 + URL 导入 + 文本导入 — 确认功能正常
- [ ] 导入后自动生成服务名/模块名/路径名存入平台（后端已有实现）
- [ ] 接口资产列表刷新显示新导入的接口
- **文件**: `ImportDialog.tsx` (验证), `AssetTab.tsx` (刷新)

**验收**: `npm run build` 零错误，接口资产 tab 默认显示，三级层级正确

---

## 涉及文件总览

| 文件 | Slice | 变更类型 |
|------|-------|---------|
| `testcase/index.tsx` | S1 | 列表列+筛选+排序 |
| `testcase/CaseDrawer.tsx` | S2 | 弹窗字段+下拉修复 |
| `testcase/CategoryManagerDialog.tsx` | S2 | 过滤接口测试域+修复 undefined |
| `mindmap/index.tsx` | S2 | 移除 Xmind 按钮 |
| `apitest/index.tsx` | S3 | 默认 tab |
| `apitest/components/AssetTab.tsx` | S3 | 三级层级+搜索+备注 |
| `apitest/components/DebugTab.tsx` | S3 | URL 拼接+环境切换 |
| `apitest/components/ImportDialog.tsx` | S3 | 验证导入流程 |
| `caseListFormatters.ts` | S1 | 确保编号格式化已生效 |

## 风险

- **下拉框遮挡**：shadcn/ui Select 的 portal 渲染可能在 Dialog 内被裁剪，需测试确认
- **405 报错**：后端路由 `POST /domains` 已存在，405 可能是前端调用了错误的方法或路径
- **400 报错**：`/domains/undefined` 来自 `domain.id` 为 undefined 时的前端调用
