# Batch 25 V2 PM Plan — 用例服务 + 需求文档修复

> PM Department | 2026-07-21 | 2 Slices

## Slice 1: 用例服务 UI 修复 (7 项)

**预估**: 45 分钟 | **优先级**: P0

### T1.1 — 移除顶部"接口用例"入口 (5min)
- [ ] `index.tsx` 顶部 Tabs 区域移除 `['api', '接口用例 (106)']` 选项
- [ ] 移除后 actTab 默认保持 'manual'（或空字符串全部）

### T1.2 — 移除新建用例弹窗"标签"字段 (5min)
- [ ] `CaseDrawer.tsx` formSchema 移除 `tags` 字段
- [ ] `CaseForm` 移除标签 Input UI（第422-426行）

### T1.3 — 调整列宽紧凑布局 (10min)
- [ ] 前置条件: 140px → 200px
- [ ] 操作步骤: 160px → 220px  
- [ ] 预期结果: 160px → 220px
- [ ] 评审: 80px → 60px
- [ ] 操作: 120px → 90px
- [ ] 移除表格 `min-h-[XXXpx]` 动态类替代为固定高度方案（见 T1.7）

### T1.4 — 底部增加跳转页码输入框 (10min)
- [ ] `Pagination.tsx` 右侧增加 "跳转到 [input] 页" 按钮
- [ ] 输入框宽度 50px，校验 1 ≤ page ≤ totalPages
- [ ] 支持 Enter 键触发跳转

### T1.5 — 重置按钮回归默认状态 (5min)
- [ ] Reset 按钮 onClick 改为: `setSelDomain(''); setSelModule(''); setPriority(''); setKeyword(''); setPage(1); refetch()`

### T1.6 — 列表悬停显示横向滚动条 (5min)
- [ ] 表格容器添加 CSS: `overflow-x-auto` + hover 时滚动条可见性

### T1.7 — 固定高度一屏显示 (5min)
- [ ] 左侧 Card: `max-h-[calc(100vh-230px)]` → `h-[calc(100vh-215px)]`
- [ ] 右侧表格: `min-h-[650px]` → `h-[calc(100vh-350px)] overflow-y-auto`
- [ ] 右侧整体容器 `space-y-3` 改为固定布局

**验收**: `npm run build` 零错误，7 项全部视觉验证通过

---

## Slice 2: 蓝湖证据采集修复 (1 项)

**预估**: 25 分钟 | **优先级**: P0

### T2.1 — retry 端点容错 + 前端取消按钮 (25min)

**后端修复**:
- [ ] `lanhu_evidence.py` `retry_job`: 若旧任务 `status == "running"` 且 `heartbeat_at` 超过 `stale_after_seconds`，自动将旧任务标记为 `failed`，然后允许重试
- [ ] `worker.py` `recover_stale_jobs`: 确保恢复逻辑正确执行

**前端修复**:
- [ ] `LanhuEvidenceJobDrawer.tsx` 增加"取消任务"按钮（调用 cancel API），用于手动取消卡住的 pending/running 任务

**验收**: 
- 模拟旧任务 stuck running → retry 不再 409 → 创建新 pending 任务
- 前端可手动取消 pending/running 任务

---

## 涉及文件总览

| 文件 | Slice | 变更类型 |
|------|-------|---------|
| `testcase/index.tsx` | S1 | UI 调整 (T1.1, T1.3, T1.5, T1.6, T1.7) |
| `testcase/CaseDrawer.tsx` | S1 | 移除 tags 字段 (T1.2) |
| `Pagination.tsx` | S1 | 增加页码跳转 (T1.4) |
| `lanhu_evidence.py` | S2 | retry 容错 (T2.1) |
| `LanhuEvidenceJobDrawer.tsx` | S2 | 取消按钮 (T2.1) |

## 风险

- **T1.7 固定高度**: 不同屏幕分辨率可能需要调偏移量，建议用 `calc(100vh - Xpx)` 适应
- **T2.1 stale 判断**: `heartbeat_at` 可能为 None（从未执行），需兼容处理
