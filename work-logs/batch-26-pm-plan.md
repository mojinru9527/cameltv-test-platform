# Batch 26 — PM Plan

> **PM (🟨)** | Date: 2026-07-21

## 规格摘要

**原始需求**: PRD §1-4 — 5 用例 UI 修复 + 证据采集工作流重构 + 原型预览/版本对比 + AI 仅处理变更 + 知识中心版本同步

**目标时间**: 2-3 slices，优先级 Phase 1 → 知识同步 → Phase 2 → Phase 3

**范围说明**: 本批次共 5 个用户故事 (US-1 ~ US-5)，包括 Phase 1/2/3 全部 + 知识中心同步。Phase 4（一站式工作台重构）不在本次范围。

---

## Slice 1: 用例服务 UI 修复 + 证据任务面板 (US-1 + US-2)

> 这两个 US 互不依赖，可并行开发。预计总工时 3-4h。

### [ ] Task 1.1: 修复重置后下拉框无法展开

**描述**: 当 `selDomain` 为空时 `selModules` 返回空数组，导致模块 Select 只有"全部模块"一个选项，Radix Select 检测到无可用选项而拒绝打开。

**验收标准**:
- 点击重置后，全部域下拉可展开显示所有域 + "全部域"选项
- 全部模块下拉可展开显示"全部模块"（选择域后显示对应模块）
- 全部优先级下拉可展开显示 P0-P3 + "全部优先级"选项

**涉及文件**:
- `test-platform-v2/frontend/src/pages/testcase/index.tsx:177-181` — `selModules` useMemo 逻辑
- `test-platform-v2/frontend/src/pages/testcase/index.tsx:268-302` — 三个过滤 Select

**参考**: PRD §US-1.1

### [ ] Task 1.2: 修复下拉框错位

**描述**: 过滤区域的三个 Select 使用默认 `item-aligned` 定位，在 `height: calc(100vh - 215px)` 的 flex 容器中导致下拉菜单偏移。需为每个 SelectContent 添加 `position="popper"`。

**验收标准**:
- 全部域/全部模块/全部优先级三个下拉框展开时，菜单定位在触发器正下方
- 分页选择器（每页20/50/100条）下拉框也不偏移

**涉及文件**:
- `test-platform-v2/frontend/src/pages/testcase/index.tsx:272,284,296` — 三个 SelectContent
- `test-platform-v2/frontend/src/pages/testcase/index.tsx:470` — 分页 SelectContent

**参考**: PRD §US-1.2

### [ ] Task 1.3: 调整用例表格行高

**描述**: 用例表格行的自然高度与左侧模块分类树的节点高度不一致。给表格行添加 `min-h` 或调整 padding 与树节点对齐。

**验收标准**:
- 20 条用例的行高与左侧模块分类节点高度视觉一致（误差 ≤4px）
- 单行内容过长时截断正常，不影响行高

**涉及文件**:
- `test-platform-v2/frontend/src/pages/testcase/index.tsx:374-461` — Table 区域

**参考**: PRD §US-1.3

### [ ] Task 1.4: 移除表格悬停时的横向滚动条

**描述**: 表格外层 `overflow-x-auto` + `min-w-[900px]` 导致悬停时底部出现横向滚动条闪现。去掉 `overflow-x-auto`，改用 `overflow-x-hidden` 或调整容器结构。

**验收标准**:
- 鼠标悬停在表格任意行上，表格底部不出现横向滚动条
- 表格内容在窄屏时仍可正常查看（内部横向滚动在需要时才出现）

**涉及文件**:
- `test-platform-v2/frontend/src/pages/testcase/index.tsx:374` — `overflow-x-auto`
- `test-platform-v2/frontend/src/pages/testcase/index.tsx:361` — `.flex-1.min-h-0.overflow-y-auto`

**参考**: PRD §US-1.4

### [ ] Task 1.5: 统一新建用例弹窗 Tab 高度

**描述**: 新建模式下 CaseForm 使用 `max-h-[60vh]`，编辑模式下 TabsContent 使用 `max-h-[50vh]`，切换时弹窗跳动。统一为 `max-h-[60vh]`。

**验收标准**:
- 新建用例弹窗在「基本信息」和「评审」两个 tab 之间切换时，弹窗高度不变
- 编辑已有用例时同样表现一致

**涉及文件**:
- `test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx:229` — 新建 form max-h
- `test-platform-v2/frontend/src/pages/testcase/CaseDrawer.tsx` — 编辑 TabsContent max-h（需定位精确行数）

**参考**: PRD §US-1.5

### [ ] Task 1.6: 新增 EvidenceTaskPanel 固定面板组件

**描述**: 在需求管理页面左侧新建固定任务面板组件（替代现有的 Sheet 侧边栏临时查看方式）。面板固定在页面左侧，始终可见。

**验收标准**:
- 任务面板固定在需求管理页左侧（类似用例服务的模块分类树）
- 显示当前活跃任务 + 历史任务列表
- 每个任务显示：ID、版本号、状态徽标、进度条、创建时间
- 点击任务可展开/跳转到详情

**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/components/EvidenceTaskPanel.tsx` — 新建
- `test-platform-v2/frontend/src/pages/requirement/index.tsx` — 集成面板

**参考**: PRD §US-2.2, §US-2.3

### [ ] Task 1.7: 任务列表 API + 实时轮询

**描述**: 前端 3s 间隔轮询任务列表 API，自动刷新状态。任务创建后不需要手动刷新。

**验收标准**:
- 任务创建后 5 秒内自动从 pending → running
- 任务面板内状态实时更新（3s 间隔，仅在面板打开时轮询）
- 状态变化时进度条动画过渡

**涉及文件**:
- `test-platform-v2/frontend/src/api/lanhuEvidence.ts` — 可能需新增 list endpoint
- `test-platform-v2/frontend/src/pages/requirement/components/EvidenceTaskPanel.tsx` — useApi 轮询
- `test-platform-v2/frontend/src/pages/requirement/index.tsx` — 传递 job 创建回调

**参考**: PRD §US-2.1, §US-2.2

### [ ] Task 1.8: 任务操作（重试/取消/查看提取）+ 错误展示

**描述**: 每个任务卡片的操作按钮和错误信息展示。

**验收标准**:
- 失败任务显示红色错误信息 + 「重试」按钮
- 运行中任务显示「取消」按钮
- 成功任务显示「查看功能拆分」入口按钮
- 操作按钮有 loading 态

**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/components/EvidenceTaskPanel.tsx`
- `test-platform-v2/frontend/src/pages/knowledge/components/LanhuEvidenceJobDrawer.tsx` — 保留作为详情抽屉

**参考**: PRD §US-2.4, §US-2.5

---

## Slice 2: 原型预览 + 版本对比 + 知识中心同步 (US-3 + US-5)

> 预计总工时 4-5h。

### [ ] Task 2.1: 后端 — 版本检测 + diff_json 生成

**描述**: 证据采集完成后自动检测版本并生成差异数据。

**验收标准**:
- 从 URL 解析 version（`/updates/{version}` 或 query param `?v=`)
- 查找同 doc_id 的上一版本 RequirementDocument
- 若存在上一版本的证据采集结果，执行页面级差异对比
- 生成 diff_json 保存到 RequirementDocument.diff_json
- 若为首次上传（无上一版本），diff_status = "initial"

**涉及文件**:
- `test-platform-v2/backend/app/services/lanhu_evidence/job_runner.py` — 采集完成后触发 diff
- `test-platform-v2/backend/app/services/lanhu_evidence/diff_service.py` — 新建，差异对比逻辑
- `test-platform-v2/backend/app/models/requirement.py` — RequirementDocument 模型（如需要新字段）
- `test-platform-v2/backend/app/services/requirement_service.py` — diff 保存方法

**参考**: PRD §4.2 差异检测流程

### [ ] Task 2.2: 后端 — 页面文本相似度 + 截图感知哈希对比

**描述**: 实现页面级对比算法。

**验收标准**:
- `difflib.SequenceMatcher` 计算 OCR 文本相似度（0~1）
- `imagehash.average_hash` + 汉明距离判断截图是否变化
- 综合文本+截图判定 change_type（new/modified/unchanged/deleted）
- 阈值可配置：text_similarity > 0.90 → unchanged；截图汉明距离 < 5 → 视觉未变

**涉及文件**:
- `test-platform-v2/backend/app/services/lanhu_evidence/diff_service.py`
- `test-platform-v2/backend/requirements.txt` — 可能需加 imagehash/Pillow

**参考**: PRD §4.2 Step 4

### [ ] Task 2.3: 前端 — 原型预览 Tab（截图 + OCR 文本双栏）

**描述**: 在需求文档详情中出现原型预览能力。分页浏览蓝湖截图，右侧显示对应 OCR 文本。

**验收标准**:
- 截图可通过后端图片代理加载（已有 download_asset API）
- 分页导航（上一页/下一页 + 页码指示器）
- 右侧 OCR 文本面板可滚动
- 页面导航条上显示变动标记（🆕/✏️/✓/❌）

**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/components/PrototypePreview.tsx` — 新建
- `test-platform-v2/frontend/src/api/lanhuEvidence.ts` — 可能需要新增 pages API

**参考**: PRD §4.3 原型截图预览

### [ ] Task 2.4: 前端 — 版本对比视图

**描述**: 分屏显示两个版本的截图，标注变动。在 AiResultModal 或独立 Modal 中展示。

**验收标准**:
- 分屏对比：左 v14.1.0 / 右 v14.2.0
- 变动页面有明确的视觉标记（绿色边框=新增，黄色边框=修改，灰色=不变，红色=删除）
- 底部汇总统计卡片

**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/components/VersionCompare.tsx` — 新建
- `test-platform-v2/frontend/src/pages/requirement/AiResultModal.tsx` — 集成或入口

**参考**: PRD §4.4 版本对比视图

### [ ] Task 2.5: 知识中心 — 版本差异同步入库

**描述**: 每次蓝湖证据采集完成并生成 diff_json 后，自动将差异数据同步到知识中心。

**验收标准**:
- diff_json 中 new + modified 的页面文本入库为知识切片（source_type="lanhu_version_diff"）
- 上一版本的对应切片标记为 superseded（不删除）
- KnowledgeIteration 表记录版本迭代事件
- 知识中心「知识差异对比」tab 可查看本次变更
- 知识中心「迭代」tab 显示版本迭代记录

**涉及文件**:
- `test-platform-v2/backend/app/services/knowledge/ingest_service.py` — 新增 ingest_lanhu_version_diff
- `test-platform-v2/backend/app/services/lanhu_evidence/job_runner.py` — 采集完成后调用入库
- `test-platform-v2/backend/app/models/knowledge.py` — KnowledgeIteration（如需要新字段）

**参考**: PRD §US-5

---

## Slice 3: AI 仅处理变更 (US-4)

> 预计总工时 2-3h。

### [ ] Task 3.1: 后端 — AI prompt 注入版本变更上下文

**描述**: Stage 1 功能拆分时，若存在 diff_json，将变更摘要注入 AI prompt。

**验收标准**:
- prompt 包含「本次变更摘要」（新增/修改/删除的页面列表）
- prompt 包含「上一版本的功能拆分结果」（作为参考，不重新拆分）
- prompt 指令明确：「仅对标记为 new/modified 的页面做功能拆分」
- unchanged 功能点自动从上一版本继承

**涉及文件**:
- `test-platform-v2/backend/app/services/ai_service.py` — prompt 构建逻辑
- `test-platform-v2/backend/app/api/v1/requirement.py:152-221` — extract_features 端点

**参考**: PRD §6.1 功能拆分 Prompt 改进

### [ ] Task 3.2: 后端 — 功能点继承 + 用例继承

**描述**: Stage 2 用例生成时，沿用的功能点直接继承上一版本的用例。

**验收标准**:
- unchanged 功能点的用例从 requirement_documents(上一版本).ai_raw 中提取并继承
- 继承的用例标注 source="inherited" + inherited_from_version="14.1.0"
- AI 仅对 new + modified 功能点生成新用例
- 前端展示时区分「新生成」和「继承」的用例

**涉及文件**:
- `test-platform-v2/backend/app/api/v1/requirement.py:277-365` — generate_test_cases
- `test-platform-v2/backend/app/services/ai_service.py` — 功能点/用例继承逻辑
- `test-platform-v2/frontend/src/pages/requirement/AiResultModal.tsx` — 展示继承标记

**参考**: PRD §5 功能拆分 — 仅处理变动, PRD §US-4

### [ ] Task 3.3: 前端 — 功能拆分结果标注版本来源

**描述**: 在 AiResultModal 和 ExtractionModal 中标注每个功能点的版本来源。

**验收标准**:
- 🆕 新增功能点显示绿色「新增」标记
- ✏️ 修改功能点显示黄色「变更」标记
- ➡️ 沿用的功能点显示灰色「v14.1.0」来源标记
- ❌ 删除的功能点显示红色「已删除」标记

**涉及文件**:
- `test-platform-v2/frontend/src/pages/requirement/AiResultModal.tsx`
- `test-platform-v2/frontend/src/pages/requirement/ExtractionModal.tsx`

**参考**: PRD §5 变更前后对比, PRD §US-4.3

---

## 质量要求

- [x] 响应式（Desktop + Tablet）
- [ ] OpenAPI 同步 — 新增 API 端点需同步
- [ ] 单元测试覆盖 — Task 1.x 不需要（纯 UI），Task 2.x 需要后端 diff 算法单测
- [ ] 无障碍（ARIA/键盘） — 新增组件需满足
- [ ] 无 console 报错/告警
- [ ] 感知哈希库选择 — 评估 `imagehash` vs `Pillow` 内置能力

---

> **下一步**: Design Spec — 像素级规范 + 组件规格
