# DEV Kanban — Batch 25: 用例服务 + 接口测试优化

> Dev Department | 2026-07-21

## 进度

| Slice | 内容 | 状态 |
|-------|------|------|
| S1 | 用例列表 UI 重构 + 筛选 + 排序 | 🔄 编码 |
| S2 | 模块分类管理 + 弹窗 + 逻辑删除 | ⏳ 待开始 |
| S3 | 接口测试模块重构 | ⏳ 待开始 |

## 分支

`feature/batch-25-usecase-optimize` ← `origin/develop`

## S1 变更文件

- `frontend/src/pages/testcase/index.tsx` — 列表列顺序 + 排序 + 筛选 + 搜索
- `frontend/src/pages/testcase/caseListFormatters.ts` — 确认格式化
- `frontend/src/pages/mindmap/index.tsx` — 移除 Xmind 按钮

## S2 变更文件

- `frontend/src/pages/testcase/CategoryManagerDialog.tsx` — 过滤接口测试域
- `frontend/src/pages/testcase/CaseDrawer.tsx` — 弹窗修复

## S3 变更文件

- `frontend/src/pages/apitest/index.tsx` — 默认 tab
- `frontend/src/pages/apitest/components/AssetTab.tsx` — 三级层级 + 搜索 + 备注
- `frontend/src/pages/apitest/components/DebugTab.tsx` — URL 拼接 + 环境切换
