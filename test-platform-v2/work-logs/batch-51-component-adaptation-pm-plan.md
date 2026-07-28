# Batch 51 — PM Plan

> 🟨 PM | Date: 2026-07-28 | Est: 6 slices × 30min

## Tasks

### Slice 1: Badge 基元增强 (20min)
- [x] Badge 组件：添加 `variant` prop 作为 `tone` 的 fallback alias（透明兼容 shadcn）
- **验收**: `variant="default"` → `tone="neutral"`, `variant="destructive"` → `tone="danger"`
- **文件**: `ui/primitives/Badge.tsx`

### Slice 2: 新增 @/ui 基元 (30min)
- [x] Card → 复用成熟 Card 复合 API，保留 `size`/`CardAction`
- [x] Textarea → 复用成熟输入组件 API
- [x] Label → 复用 Radix Label 的 `htmlFor` 能力
- [x] Select → 导出完整 Radix Select 复合 API
- [x] Skeleton → 复用成熟占位组件
- **验收**: 每个组件有 Story/export，构建通过
- **文件**: `ui/primitives/Card.tsx`, `ui/primitives/Textarea.tsx`, `ui/primitives/Label.tsx`, `ui/primitives/Select.tsx`, `ui/primitives/Skeleton.tsx`, `ui/index.ts`

### Slice 3: Badge 批量替换 (30min)
- [x] 全局扫描所有 `from '@/components/ui/badge'` → `from '@/ui'`
- [x] 全局替换 `variant="default"` → `tone="neutral"` (或删除 variant 用默认)
- [x] 全局替换 `variant="destructive"` → `tone="danger"`
- [x] 全局替换 `variant="outline"` → `tone="neutral"`
- [x] 全局替换 `variant="secondary"` → `tone="neutral"`
- [x] 动态表达式修复: `variant={x ? 'default' : 'destructive'}` → `tone={x ? 'neutral' : 'danger'}`
- **涉及文件**: ~50 files

### Slice 4: PageShell 列表页接入 (30min)
- [x] testcase/index.tsx → PageShell
- [x] defect/index.tsx → PageShell
- [x] testplan/index.tsx → PageShell
- [x] environment/index.tsx → PageShell
- [x] report/index.tsx → PageShell
- [x] trace/index.tsx、requirement/index.tsx → PageShell
- **验收**: 5 页标题/副标题/操作栏一致

### Slice 5: Card/Textarea/Label/Select/Skeleton 兼容层 (30min)
- [x] `@/ui` 提供完整兼容导出
- [x] 避免在本批次机械替换成熟 Radix/shadcn 消费者
- **验收**: API 兼容测试与生产构建通过

### Slice 6: tsc 零错误 + 收尾 (20min)
- [x] 使用仓库标准 `npm run typecheck` 验证类型
- [x] 类型检查零错误
- [x] Vite build 通过
- [x] QA 报告 + Leader Verdict

## 风险

| 风险 | 缓解 |
|------|------|
| Badge variant→tone 语义不匹配 | Slice 1 加 alias，向后兼容 |
| PageShell 破坏现有布局 | 保持最小侵入，仅包装标题区域 |
| Select 实现复杂 | 仅做 trigger/content/item，非受控逻辑 |
