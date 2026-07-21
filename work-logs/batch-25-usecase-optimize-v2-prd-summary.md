# Batch 25 V2 PRD — 用例服务 + 需求文档修复

> Product Department | 2026-07-21

## 问题陈述

Batch 25 第一轮已交付核心优化（列表截断、筛选、弹窗修复、接口测试三级层级），但用户验收时发现 8 个体验和功能缺陷，影响日常使用效率。

## 成功指标

- 用例服务页面布局紧凑，一屏可见更多有效信息
- 新建用例流程无冗余字段
- 重置按钮行为符合直觉
- 页面高度固定、滚动体验流畅
- 蓝湖证据采集→需求文档分析链路完整可用

## 非目标

- 不新增功能模块
- 不改动后端 API 数据结构
- 不重构用例服务架构

---

## 用户故事

### US1: 移除顶部"接口用例"入口标签

**为什么用户关心**：接口用例实际在接口测试模块管理，用例服务顶部显示接口用例 tab 造成困惑，用户可能点击后发现没有数据或数据不正确。

**Given** 用户进入用例服务页面  
**When** 页面加载完成  
**Then** 顶部不显示「接口用例 (106)」tab，仅保留「全部」和「功能用例」

**文件**: [testcase/index.tsx](test-platform-v2/frontend/src/pages/testcase/index.tsx) Top Tabs 区域

---

### US2: 移除新建用例弹窗中的"标签"字段

**为什么用户关心**：标签功能从未被正式使用，多余字段增加填写负担和视觉噪音。当前实现是自由文本 JSON 数组，用户不会用。

**Given** 用户点击新建用例  
**When** 弹窗打开  
**Then** 表单中不包含"标签 (JSON 数组)"输入框

**文件**: [CaseDrawer.tsx](test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx)

---

### US3: 调整列表列宽——紧凑布局

**为什么用户关心**：当前各列之间留白过多，前置条件/操作步骤/预期结果三个字段太窄，内容截断严重看不清。

**Given** 用例列表显示  
**When** 用户浏览列表  
**Then** 前置条件、操作步骤、预期结果三列宽度增加（建议各 200px+），用例等级列靠拢用例标题，中间无明显留白

**设计要点**：
- 模块名称保持 120px
- 用例标题弹性伸缩
- 前置条件 → 200px
- 操作步骤 → 220px
- 预期结果 → 220px
- 评审列缩小到 60px
- 操作列缩小到 90px

**文件**: [testcase/index.tsx](test-platform-v2/frontend/src/pages/testcase/index.tsx) TableHeader 列宽

---

### US4: 底部增加跳转页码输入框

**为什么用户关心**：当前分页只有上一页/下一页，900+ 条用例要翻 45 页，用户体验极差。

**Given** 用户在用例列表底部  
**When** 用户在输入框输入页码并确认  
**Then** 列表跳转到对应页面

**设计要点**：
- 放在 Pagination 组件右侧
- 输入框宽度 60px + "跳转"按钮
- 输入值校验：1 ≤ page ≤ totalPages
- 支持 Enter 键触发

**文件**: [Pagination.tsx](test-platform-v2/frontend/src/components/Pagination.tsx)

---

### US5: 重置按钮回归默认状态

**为什么用户关心**：当前重置按钮只重新请求数据（refetch），不清理筛选条件。用户期望点击重置后所有筛选器回到初始状态。

**Given** 用户选择了某个域、模块、优先级并输入了搜索关键词  
**When** 用户点击重置按钮  
**Then** 域→空(全部)、模块→空(全部)、优先级→空(全部)、搜索关键词→空、页码→1，并重新加载第一页数据

**文件**: [testcase/index.tsx](test-platform-v2/frontend/src/pages/testcase/index.tsx) Reset 按钮 onClick

---

### US6: 用例列表鼠标悬停显示横向滚动条

**为什么用户关心**：用户可能不知道表格可以横向滚动（列很多时），悬停时才显示滚动条可以提示用户。

**Given** 用例列表渲染完成  
**When** 鼠标悬停在表格区域  
**Then** 表格容器底部出现横向滚动条（overflow-x: auto + hover 时显示滚动条样式）

**实现方式**: Tailwind `overflow-x-auto` + 自定义 CSS hover 滚动条可见性

**文件**: [testcase/index.tsx](test-platform-v2/frontend/src/pages/testcase/index.tsx) 表格容器

---

### US7: 固定高度一屏显示

**为什么用户关心**：左右两栏高度随数据量变化，没有数据时矮、数据多时高，页面抖动不适。

**Given** 用户进入用例服务页面  
**When** 页面渲染完成  
**Then** 左侧域树区域和右侧列表区域均有固定高度（calc(100vh - 偏移量)），内容溢出时各自内部滚动

**设计要点**：
- 左侧 Card: `h-[calc(100vh-220px)]` 替代当前的 `max-h-[calc(100vh-230px)]`
- 右侧表格容器: `h-[calc(100vh-320px)]` + `overflow-y-auto`
- 底部分页栏始终可见（sticky 底部）

**文件**: [testcase/index.tsx](test-platform-v2/frontend/src/pages/testcase/index.tsx) 布局区域

---

### US8: 蓝湖证据采集→需求分析链路修复

**为什么用户关心**：上传蓝湖链接后点击"证据采集"，任务创建成功但从未真正执行（状态显示不可导入），点击重试也报 409。需求文档分析完全被阻塞。

**Given** 用户在需求文档页面上传了蓝湖链接并点击「证据采集」  
**When** ① 任务被 worker 拾取执行 / ② 用户点击「重新生成」重试  
**Then** ① 任务正常执行完成（截图→OCR→合并），通过质量门禁后自动触发需求文档分析  
**Then** ② 即使旧任务卡在 running 状态，重试也不应报 409

**根因分析**：

1. **旧任务卡 running → 重试 409**：[lanhu_evidence.py:345](test-platform-v2/backend/app/api/v1/lanhu_evidence.py) `retry_job` 检测到旧任务 `status in ("pending", "running")` 直接拒绝。但 worker 崩溃后旧任务永远留在 running，无法被重试。

2. **Worker 可能未正常消费 pending 任务**：[worker.py:80](test-platform-v2/backend/app/services/lanhu_evidence/worker.py) 依赖 `lanhu_evidence_worker_enabled=True`（默认 true），但 [config.py:135](test-platform-v2/backend/app/core/config.py) 的 `lanhu_evidence_enabled=False` 只影响 API 调用，不影响 worker。Worker 注册在 [scheduler.py:187-198](test-platform-v2/backend/app/core/scheduler.py)，每 5 秒轮询一次。如果 worker 线程崩溃或 Playwright 截图超时，job 会停留在 running 状态。

**修复方案**：
- **A**: `retry_job` 端点增加容错：若旧任务 running 但心跳超时（heartbeat_at 超过 stale_after_seconds），自动将旧任务标记为 failed，然后允许创建重试任务
- **B**: 确保 `recover_stale_jobs` 在每次轮询时正确将卡住的 running 任务标记为 failed
- **C**: 前端侧边栏增加"取消任务"按钮，允许手动取消卡住的任务后再重试

**文件**:
- [lanhu_evidence.py](test-platform-v2/backend/app/api/v1/lanhu_evidence.py) — retry_job 容错
- [worker.py](test-platform-v2/backend/app/services/lanhu_evidence/worker.py) — 恢复逻辑确认
- [LanhuEvidenceJobDrawer.tsx](test-platform-v2/frontend/src/pages/knowledge/components/LanhuEvidenceJobDrawer.tsx) — 前端取消按钮

---

## 影响范围

| 模块 | 文件数 | 变更性质 |
|------|--------|---------|
| 用例服务前端 | 3 (index.tsx, CaseDrawer.tsx, Pagination.tsx) | UI 调整 + 交互修复 |
| 蓝湖证据后端 | 2 (lanhu_evidence.py, worker.py) | 容错逻辑 |
| 蓝湖证据前端 | 1 (LanhuEvidenceJobDrawer.tsx) | 新增取消按钮 |
