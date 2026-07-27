# Batch 28 — PM Plan：延后项补漏

> **PM (🟨)** | Date: 2026-07-22 | 工时基准: ~6h

## 规格摘要

**原始需求**: 补漏 batch-25v2 + batch-26 延后项（6+2=8 项）+ 建立 C 条件追踪器
**目标时间**: 3 个 Slice 分阶段交付

---

## 开发任务

### Slice 1: 后端三连（US-1 + US-4 + US-7）— ~2h

三个改动在同一文件链路（diff_service → ingest_service → requirement），一起做效率最高。

#### [ ] Task 1.1: 感知哈希集成 (US-1)

**描述**: 在 `diff_service.py` 的 `compute_page_diff()` 中添加 `imagehash` 感知哈希对比通道
**关键改动**:
- `page_to_dict()` (L249): 将 `screenshot_hash` 从空字符串改为真实的 `imagehash.phash()` 值
- `compute_page_diff()` (L109-117): 在文本相似度判断后添加视觉相似度检查
- 新增阈值常量 `IMAGE_SIMILARITY_THRESHOLD = 0.85`
- 降级策略：无截图数据时跳过视觉对比，仅用文本

**涉及文件**:
- `test-platform-v2/backend/app/services/lanhu_evidence/diff_service.py`
- `test-platform-v2/backend/requirements.txt` — 添加 `imagehash` + `Pillow` 依赖

**估时**: 45min

#### [ ] Task 1.2: KnowledgeIteration 自动创建 (US-4)

**描述**: `ingest_lanhu_version_diff()` 在版本差异入库后自动创建/更新 KnowledgeIteration
**关键改动**:
- L521-522: 在 `_post_ingest_hooks()` 前调用 `snapshot_service.create_iteration()`
- 同一版本幂等：先查已有 iteration（按 project_id + version），有则更新 end_date，无则新建
- iteration 的 description 写入 diff_json 的 summary 文本

**涉及文件**:
- `test-platform-v2/backend/app/services/knowledge/ingest_service.py`

**估时**: 30min

#### [ ] Task 1.3: 继承匹配率监控日志 (US-7)

**描述**: 在 FP 继承和用例继承逻辑处添加 match/total/miss 日志
**关键改动**:
- `requirement.py` L209: `extract_features` 完成后 log `fp_inherit_match: {matched}/{total}`
- `requirement.py` L445: `generate_test_cases` 完成后 log `case_inherit_match: {matched}/{total}`
- 格式: `logger.info(f"fp_inherit_match_rate: {matched}/{total} ({pct:.1%}")`

**涉及文件**:
- `test-platform-v2/backend/app/api/v1/requirement.py`

**估时**: 15min

---

### Slice 2: 前端三件套（US-2 + US-3 + US-5）— ~3h

#### [ ] Task 2.1: VersionCompare 分屏对比组件 (US-2)

**描述**: 需求文档页新增「版本对比」按钮 → 打开分屏对比视图
**核心功能**:
- 左右分屏：左旧版本、右新版本
- 页面列表 + 点击展开差异详情
- 差异文本高亮：红色删除线（旧）、绿色背景（新）
- 左右同步滚动
- 状态标记：🆕新增 / ✏️修改 / ➡️不变 / ❌删除

**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/components/VersionCompare.tsx` (新建, ~350行)
- `test-platform-v2/frontend/src/pages/requirement/index.tsx` — 添加入口按钮
- `test-platform-v2/frontend/src/api/requirement.ts` — 添加获取 diff 的 API 调用

**估时**: 90min

#### [ ] Task 2.2: PrototypePreview 截图预览组件 (US-3)

**描述**: EvidenceTaskPanel 成功任务增加「查看截图」→ 弹窗预览蓝湖截图
**核心功能**:
- 截图轮播（左右翻页）
- 缩放（滚轮）+ 拖拽（鼠标 drag）
- 侧边栏 OCR 文字（已有数据）
- 键盘导航（← → 翻页，Esc 关闭）

**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/components/PrototypePreview.tsx` (新建, ~200行)
- `test-platform-v2/frontend/src/pages/requirement/components/EvidenceTaskPanel.tsx` — 添加按钮

**估时**: 60min

#### [ ] Task 2.3: 前端版本标记展示 (US-5)

**描述**: AiResultModal 中功能点卡片显示版本来源标记
**核心功能**:
- ➡️ 蓝色标签 `沿用自 vX.Y.Z`（`_inherited=True`）
- ✏️ 橙色标签 `本版本变更`（`_inherited=False` + diff_status="update"）
- 🆕 绿色标签 `首次提取`（无 diff）
- ❌ 红色标签 `已移除`（仅在对比视图中显示旧版本有但新版本无的 FP）

**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/components/AiResultModal.tsx` — 添加标记逻辑
- `test-platform-v2/frontend/src/types/requirement.ts` — 类型扩展（如需要）

**估时**: 30min

---

### Slice 3: 测试修复 + 流程工具（US-6 + US-8）— ~1h

#### [ ] Task 3.1: 预存在测试修复 (US-6)

**描述**: 修复 9 个预存在测试失败
**具体修复**:
- **DebugTab.test.tsx (3个)**: Props 接口新增 `serviceName` 可选字段，更新 mock 数据
- **CaseDrawer.test.tsx (3个)**: 测试期望与当前 UI 不完全匹配，更新断言
- **testcase.test.ts (3个)**: API guard mock 与 vi.mock 不兼容，改用 vi.hoisted mock

**涉及文件**:
- `test-platform-v2/frontend/src/__tests__/DebugTab.test.tsx`
- `test-platform-v2/frontend/src/__tests__/CaseDrawer.test.tsx`
- `test-platform-v2/frontend/src/__tests__/testcase.test.ts`

**估时**: 30min

#### [ ] Task 3.2: C 条件追踪器 (US-8)

**描述**: 创建 `C-CONDITIONS.md` 追踪文件，汇总所有现有孤儿 C 条件
**内容**:
- 按状态分组：Open / In Progress / Closed
- 每条记录：来源批次、条件编号、内容、优先级、负责人、创建日期
- 全量导入现有 22 个孤儿 C 条件（标记为 Open）
- 在 AGENTS.md 或 CLAUDE.md 中添加引用，确保 Product 开工前先读

**涉及文件**:
- `C-CONDITIONS.md` (新建)
- `AGENTS.md` — 添加 Product 开工检查步骤

**估时**: 20min

---

## 任务依赖图

```
Slice 1 (后端)
├─ Task 1.1 感知哈希 ← 独立
├─ Task 1.2 KnowledgeIteration ← 独立
└─ Task 1.3 继承日志 ← 独立
        ↓ (后端完成，前端可开始)
Slice 2 (前端)
├─ Task 2.1 VersionCompare ← 依赖 Task 1.1 的哈希数据
├─ Task 2.2 PrototypePreview ← 独立
└─ Task 2.3 版本标记 ← 依赖 Task 1.2 的迭代信息
        ↓
Slice 3 (收尾)
├─ Task 3.1 测试修复 ← 独立
└─ Task 3.2 C-CONDITIONS ← 独立
```

## 质量要求

- [ ] 感知哈希不破坏现有纯文本对比逻辑（feature flag 控制）
- [ ] 新前端组件需包含 Loading/Empty/Error 三态
- [ ] TypeScript 编译零错误
- [ ] 后端启动正常，现有 API 无回归
- [ ] 94/94 单元测试通过（当前 85/94）
- [ ] 无 console.log 残留
- [ ] 遵循 shadcn/ui + Tailwind 组件规范

## 风险

| 风险 | 缓解 |
|------|------|
| `imagehash` 依赖可能在 Windows 上安装困难 | 用 `try/except` 降级，安装失败时自动跳过视觉对比 |
| VersionCompare 同步滚动实现复杂 | 用 `scrollTop` 双向绑定，限制在 200 行内 |
| 前端测试修复可能暴露更多问题 | 如超过 30min 未解决，记录发现并留到后续 |
