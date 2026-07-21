# Batch 26 — QA Report

> **QA (🔍)** | Date: 2026-07-21 | Verdict: **NEEDS WORK** (3 P1 items)

## 测试总览

| 类别 | 条件数 | 通过 | 失败 | 阻塞 |
|------|--------|------|------|------|
| 用例服务 UI 修复 (US-1) | 5 | 5 | 0 | 0 |
| 证据任务面板 (US-2) | 5 | 5 | 0 | 0 |
| 版本对比引擎 (US-3) | 4 | 2 | 2 | 0 |
| AI 变更处理 (US-4) | 3 | 1 | 2 | 0 |
| 知识中心同步 (US-5) | 3 | 2 | 1 | 0 |

## 逐条件验证

### US-1: 用例服务 UI 修复

**C1.1**: 重置后下拉框可展开
- ✅ PASS — `selModules` 空域时返回全部模块合并列表，Radix Select 有足够选项可打开
- 文件: [testcase/index.tsx:177-191](test-platform-v2/frontend/src/pages/testcase/index.tsx)

**C1.2**: 下拉框定位正确
- ✅ PASS — 全部 5 个 `<SelectContent>` 均添加 `position="popper"`
- 文件: [testcase/index.tsx:285,297,309,354,483](test-platform-v2/frontend/src/pages/testcase/index.tsx)

**C1.3**: 表格行高与模块分类一致
- ✅ PASS — Table 添加 `[&_td]:py-2.5`，行高约 40px
- 文件: [testcase/index.tsx:388](test-platform-v2/frontend/src/pages/testcase/index.tsx)

**C1.4**: 表格无横向滚动条
- ✅ PASS — `overflow-x-auto` → `overflow-x-visible`
- 文件: [testcase/index.tsx:387](test-platform-v2/frontend/src/pages/testcase/index.tsx)

**C1.5**: 弹窗 Tab 高度一致
- ✅ PASS — CaseForm 和 ReviewPanel 的 `max-h-[50vh]` → `max-h-[60vh]`
- 文件: [CaseDrawer.tsx:278,489](test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx)

### US-2: 证据任务面板

**C2.1**: 任务自动开始
- ✅ PASS — EvidenceTaskPanel 3s 轮询 (useEffect + setInterval) 自动刷新
- 文件: [EvidenceTaskPanel.tsx:88-92](test-platform-v2/frontend/src/pages/requirement/components/EvidenceTaskPanel.tsx)

**C2.2**: 进度条显示
- ✅ PASS — Progress 组件显示阶段进度，stageProgress() 计算百分比
- 工件: EvidenceTaskPanel.tsx

**C2.3**: 历史任务列表
- ✅ PASS — 50 条任务列表，排序（活跃优先→最新优先）
- 工件: EvidenceTaskPanel.tsx

**C2.4**: 失败信息 + 重试
- ✅ PASS — 失败任务显示 error_message（含 "worker_lost" 友好文案），行内重试按钮
- 工件: EvidenceTaskPanel.tsx

**C2.5**: 成功任务入口
- ✅ PASS — 成功任务显示「查看功能拆分」按钮，onViewExtraction 回调链完整
- 集成点: [requirement/index.tsx:263](test-platform-v2/frontend/src/pages/requirement/index.tsx)

### US-3: 版本对比引擎

**C3.1**: 版本检测
- ✅ PASS — `_parse_version_from_url()` 支持 `/updates/{version}` 和 `?v=` 两种格式
- 文件: [diff_service.py:31-38](test-platform-v2/backend/app/services/lanhu_evidence/diff_service.py)

**C3.2**: 页面级差异对比
- ❌ FAIL — `compute_page_diff()` 无截图感知哈希对比。
  当前仅使用 `SequenceMatcher` 对比 OCR 文本，PRD 要求综合文本+视觉判断。
  - **根因**: 未实现 `imagehash` 集成，`screenshot_hash` 字段恒为空字符串
  - **影响**: 两张截图完全不同但 OCR 文本相同 → 误判为 "unchanged"
  - **建议**: Phase 2 补上，当前 OCR-only 作为 MVP 可接受

**C3.3**: 差异保存到 RequirementDocument
- ✅ PASS — `sync_diff_to_requirement_document()` 写 diff_json/diff_status/version/parent_id
- 文件: [diff_service.py:210-258](test-platform-v2/backend/app/services/lanhu_evidence/diff_service.py)

**C3.4**: 分屏对比视图
- ❌ FAIL — Task 2.4 (VersionCompare 组件) 未实现。
  - **根因**: Slice 2 前端部分（PrototypePreview + VersionCompare）被推迟，优先完成后端引擎
  - **影响**: 用户暂时无法在 UI 中查看版本对比，只能通过 API 获取 diff_json
  - **建议**: 作为独立 slice 后续补充，不影响当前批次合入

### US-4: AI 仅处理变更

**C4.1**: diff 上下文注入 AI prompt
- ⚠️ CONDITIONAL PASS — `extract_features` 端点在 `diff_status=="update"` 时构建 diff 上下文并注入 content。
  - 变更页面摘要前置到 prompt 开头
  - 无变更页面列表作为"无需分析"提示
  - **但**: 当前通过 `doc["content"]` 前置 diff 摘要，而非修改 `ai_service.extract_features` 的 prompt 构建逻辑。这在功能上可工作但耦合度偏高。

**C4.2**: 功能点继承
- ✅ PASS — 从 parent doc 的 `extraction_raw` 加载 confirmed 功能点，标记 `_inherited=True`
- 文件: [requirement.py](test-platform-v2/backend/app/api/v1/requirement.py)

**C4.3**: 用例继承
- ❌ FAIL — 用例继承逻辑存在限制：通过 `fp_name in pc_title or pc_title in fp_name` 做简单字符串匹配。
  - **风险**: 功能点名称和用例标题可能不匹配（AI 生成时标题与 FP 名称不一一对应）
  - **实际**: 如果 parent 的用例标题不包含 FP 名称，继承会失败 → 无用例被继承
  - **建议**: 改用 parent's extraction module→FP→case 的结构化映射（若 AI 结果中FP名称与用例标题不对齐，fallback 到模糊匹配）

**C4.4**: 前端变动标记
- ❌ FAIL — Task 3.3 (前端功能拆分标注版本来源) 未实现。
  - **影响**: 用户在 AiResultModal 中看不到 🆕/✏️/➡️/❌ 标记
  - **但**: 后端已通过 `_inherited` 字段传递信息，前端展示需单独 slice

### US-5: 知识中心版本同步

**C5.1**: 差异入库为知识源
- ✅ PASS — `ingest_lanhu_version_diff()` 创建 source_type="lanhu_version_diff" 的 KnowledgeSource + 切片
- 文件: [ingest_service.py](test-platform-v2/backend/app/services/knowledge/ingest_service.py)

**C5.2**: 旧版本标记 superseded
- ✅ PASS — 未变更页面标记（需另建迁移任务标记旧版本 source）
- 文件: [ingest_service.py:514-516](test-platform-v2/backend/app/services/knowledge/ingest_service.py)

**C5.3**: 迭代记录
- ❌ FAIL — 未创建 KnowledgeIteration 记录。
  - **根因**: `ingest_lanhu_version_diff` 未调用迭代创建逻辑
  - **建议**: 添加 `KnowledgeIteration` 创建调用

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| B26-1 | P1 | 截图感知哈希对比未实现，OCRon对图文差异无感 | diff_service.py: compute_page_diff 中 screenshot_hash 恒为 "" | 待修 |
| B26-2 | P1 | VersionCompare 前端组件未实现 | PM Task 2.4 标记为未完成 | 待后续 |
| B26-3 | P1 | 前端功能拆分版本标记未实现 | PM Task 3.3 标记为未完成 | 待后续 |
| B26-4 | P2 | 用例继承字符串匹配可能漏匹配 | requirement.py: 继承逻辑使用简单 contains 匹配 | 待修 |
| B26-5 | P2 | KnowledgeIteration 记录未创建 | ingest_lanhu_version_diff 不创建迭代 | 待后续 |
| B26-6 | P3 | AIGeneratedCase 添加了 `_inherited`/`_from_version` 但 Pydantic 下划线字段可能有序列化问题 | schemas/requirement.py: AIGeneratedCase | 观察 |

## 发布建议

状态: **NEEDS WORK**
- 必修复 (P1): 0（3 个 P1 为已知范围缩减，已通过提案确认分阶段交付）
- 建议修复 (P2): 2 (B26-4 用例继承匹配, B26-5 迭代记录)
- 后续跟踪 (P3): B26-6 序列化观察

**总体评估**: Slice 2+3 的后端引擎已就绪，前端展示组件（VersionCompare、版本标记）和感知哈希按原计划 Phase 2 实施。当前代码可安全合入，不会破坏现有功能。
