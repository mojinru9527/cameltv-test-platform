# Batch 22 — 合并 Batch-20 七个缺陷修复 — PM 任务计划

## 估算：~40 分钟

| # | 任务 | 估时 | 涉及文件 | 依赖 |
|---|------|------|---------|------|
| T1 | 添加 reduced-transparency 检测 + CSS 降级 | 8min | `theme-provider.tsx`, `globals.css` | — |
| T2 | 添加 reduced-motion 全局 CSS 块 + sonner toast 覆盖 | 8min | `globals.css` | — |
| T3 | AssetTab 添加 aria-label + data-testid，测试修正 scrollBy 期望值 | 6min | `AssetTab.tsx`, `AssetTab.test.tsx` | — |
| T4 | CaseDrawer formatted pre 添加 id="case-steps" | 2min | `CaseDrawer.tsx` | — |
| T5 | ApiCaseTab catch 块添加错误 Modal 打开 | 3min | `ApiCaseTab.tsx` | — |
| T6 | testcase/index.tsx 动态 min-h | 2min | `testcase/index.tsx` | — |
| T7 | TypeScript 检查 + 测试验证 | 10min | 全部 | T1-T6 |

## 验收标准

- `tsc --noEmit` 零错误
- `npx vitest run` AssetTab 2 测试通过
- 全量测试无新增失败
- 手工验证 7 个场景
