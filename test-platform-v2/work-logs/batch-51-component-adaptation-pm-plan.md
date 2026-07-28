# Batch 51 — PM Plan

> 🟨 PM | Date: 2026-07-28 | Est: 6 slices × 30min

## Tasks

### Slice 1: Badge 基元增强 (20min)
- [ ] Badge 组件：添加 `variant` prop 作为 `tone` 的 fallback alias（透明兼容 shadcn）
- **验收**: `variant="default"` → `tone="neutral"`, `variant="destructive"` → `tone="danger"`
- **文件**: `ui/primitives/Badge.tsx`

### Slice 2: 新增 @/ui 基元 (30min)
- [ ] Card → `ui-surface` + `rounded-xl` 简单包装
- [ ] Textarea → 复用 Input 样式
- [ ] Label → text-secondary 文本
- [ ] Select → trigger/content/item 骨架
- [ ] Skeleton → 脉冲动画占位
- **验收**: 每个组件有 Story/export，构建通过
- **文件**: `ui/primitives/Card.tsx`, `ui/primitives/Textarea.tsx`, `ui/primitives/Label.tsx`, `ui/primitives/Select.tsx`, `ui/primitives/Skeleton.tsx`, `ui/index.ts`

### Slice 3: Badge 批量替换 (30min)
- [ ] 全局扫描所有 `from '@/components/ui/badge'` → `from '@/ui'`
- [ ] 全局替换 `variant="default"` → `tone="neutral"` (或删除 variant 用默认)
- [ ] 全局替换 `variant="destructive"` → `tone="danger"`
- [ ] 全局替换 `variant="outline"` → `tone="neutral"`
- [ ] 全局替换 `variant="secondary"` → `tone="neutral"`
- [ ] 动态表达式修复: `variant={x ? 'default' : 'destructive'}` → `tone={x ? 'neutral' : 'danger'}`
- **涉及文件**: ~50 files

### Slice 4: PageShell 列表页接入 (30min)
- [ ] testcase/index.tsx → PageShell
- [ ] defect/index.tsx → PageShell  
- [ ] testplan/index.tsx → PageShell
- [ ] environment/index.tsx → PageShell
- [ ] report/index.tsx → PageShell
- **验收**: 5 页标题/副标题/操作栏一致

### Slice 5: Card/Textarea/Label/Select/Skeleton 替换 (30min)
- [ ] Card 导入替换 (~30 files)
- [ ] Textarea 导入替换 (~10 files)
- [ ] Label 导入替换 (~15 files)
- [ ] Skeleton 导入替换 (~8 files)
- **验收**: 每轮构建通过

### Slice 6: tsc 零错误 + 收尾 (20min)
- [ ] deep-eql 类型定义：安装 `@types/deep-eql` 或 `skipLibCheck`
- [ ] `tsc --noEmit` 零错误
- [ ] Vite build 通过
- [ ] QA 报告 + Leader Verdict

## 风险

| 风险 | 缓解 |
|------|------|
| Badge variant→tone 语义不匹配 | Slice 1 加 alias，向后兼容 |
| PageShell 破坏现有布局 | 保持最小侵入，仅包装标题区域 |
| Select 实现复杂 | 仅做 trigger/content/item，非受控逻辑 |
