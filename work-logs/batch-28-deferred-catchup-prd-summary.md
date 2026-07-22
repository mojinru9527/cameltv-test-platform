# Batch 28 — 延后项补漏 + C 条件追踪机制 PRD

> **Product (🟦)** | Date: 2026-07-22 | Status: Draft

## 1. 问题陈述

### 1.1 核心问题：跨批次延后项无人认领

Agent Team 流水线中，Leader 在每个批次末尾设定「下一批次 C 条件」，但下一批次的 Product 部门开工时从零收集需求，C 条件变成"孤儿"。跨 9 个批次累计 **22 个未追踪的 C 条件**，其中 **0 个被后续批次正式认领**。

### 1.2 本次聚焦：6+2 个最高优先级延后项

从 batch-25v2 和 batch-26 的 C 条件中，选取 8 项（原 6 项 + 2 个低 effort 顺手修复）：

| # | 延后项 | 来源 | 类型 | 用户影响 |
|---|--------|------|------|---------|
| 1 | 截图感知哈希对比 | batch-26 C2 | Backend | OCR-only 对比对图文差异无感，两张完全不同但 OCR 相同的截图被误判为 "unchanged" |
| 2 | VersionCompare 前端分屏对比组件 | batch-26 C1 | Frontend | 用户无法在 UI 中查看版本差异，只能通过 API 获取 diff_json |
| 3 | PrototypePreview 截图预览组件 | batch-26 C1 | Frontend | 蓝湖以图片为主，当前只有文本提取，无截图预览能力 |
| 4 | KnowledgeIteration 创建 | batch-26 C4 | Backend | 版本差异入库后不创建迭代记录，知识演化链断裂 |
| 5 | 前端版本标记展示 (🆕/✏️/➡️/❌) | batch-26 C3 | Frontend | AiResultModal 中看不到功能点的版本来源标记 |
| 6 | 预存在测试失败修复 (9个) | batch-25v2 C1 | Test | CaseDrawer/DebugTab/testcase 测试持续失败 |
| S1 | 用例继承匹配率监控日志 | batch-26 C5 | Backend | 无数据调优继承算法（与 #4 同文件，顺手做） |
| S2 | DebugTab + ApiCaseTab 测试修复 (5个) | batch-22 C1 | Test | Props 变更只需更新 mock，10 分钟 |

### 1.3 流程问题：C 条件追踪器

除了修代码，还需要**防止未来再产生孤儿**。本次将建立 `C-CONDITIONS.md` 追踪文件，Product 开工前必须先读。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| 感知哈希可用 | 无此能力 | 版本 diff 同时使用文本+视觉双通道对比 |
| VersionCompare 可交互 | 无此组件 | 分屏对比视图：左旧右新，差异高亮 |
| PrototypePreview 可预览截图 | 无此组件 | 点击页面节点 → 弹窗显示蓝湖截图 |
| KnowledgeIteration 创建 | 不创建 | 每次版本差异入库自动创建/更新迭代记录 |
| 前端版本标记可见 | 不可见 | AiResultModal 中 FP 显示版本来源标记 |
| 测试通过率 | 85/94 (90.4%) | 94/94 (100%) |
| 继承匹配率可观测 | 无日志 | 每次继承记录 match/total/miss 到日志 |
| C 条件可追踪 | 0/22 被追踪 | 100% 新 C 条件写入 C-CONDITIONS.md |

## 3. 非目标（本次不做）

- batch-24 主题 C1~C3：ThemeLab 需要专门设计走查
- batch-19 C1 验收数据清理：运维脚本，与代码无关
- batch-21 P1×4 安全项：需专门安全审查批次
- batch-client-perf 真机验证：需物理设备
- batch-25v2 C2 多分辨率验证：手动验收任务
- batch-26-KB C1~C3：依赖 batch-26 的 Slice 5 是否完成（待验证）
- batch-27 C1~C4：batch-27 代码尚未合入 develop，合入后单独处理

## 4. 用户故事 + 验收标准

### US-1: 感知哈希视觉对比

**As a** 产品经理/测试工程师
**I want** 版本对比能检测图片变化（不只看文字）
**So that** 两张截图不同但 OCR 文字相同的页面不会被误判为 "unchanged"

| # | 验收标准 |
|---|---------|
| US-1.1 | Given 两个版本的同一页面 / When OCR 文字相同但截图不同 / Then change_type 判定为 "modified" |
| US-1.2 | Given 两个版本的同一页面 / When OCR 文字相同且截图相同 / Then change_type 判定为 "unchanged" |
| US-1.3 | Given 页面无截图数据 / When 对比 / Then 降级为纯文本对比（保持现有行为，不报错） |

### US-2: VersionCompare 分屏对比

**As a** 测试工程师
**I want** 在 UI 中并排查看两个版本的页面变化
**So that** 不用通过 API 手动解读 diff_json

| # | 验收标准 |
|---|---------|
| US-2.1 | Given 有 diff_json 的需求文档 / When 用户点击「版本对比」按钮 / Then 打开分屏视图：左旧版本、右新版本 |
| US-2.2 | Given 分屏视图已打开 / When 用户滚动 / Then 左右同步滚动 |
| US-2.3 | Given 某页面 change_type="modified" / When 显示对比 / Then 差异文本高亮（红色删除、绿色新增） |
| US-2.4 | Given 某页面 change_type="new" / Then 右侧显示完整内容，左侧显示「新增页面」占位 |
| US-2.5 | Given 某页面 change_type="deleted" / Then 左侧显示完整内容，右侧显示「已删除」占位 |

### US-3: PrototypePreview 截图预览

**As a** 产品经理
**I want** 在需求页面看到蓝湖原型的截图
**So that** 不离开平台就能对照原型审阅功能拆分结果

| # | 验收标准 |
|---|---------|
| US-3.1 | Given EvidenceTaskPanel 中某任务已完成且有截图 / When 点击「查看截图」/ Then 弹窗显示蓝湖原型截图，支持左右翻页 |
| US-3.2 | Given 截图预览弹窗 / When 用户缩放/拖拽 / Then 截图可缩放（滚轮）和拖拽（鼠标） |
| US-3.3 | Given 页面有关联的 OCR 文本 / When 显示截图 / Then 侧边栏显示 OCR 提取的文字 |

### US-4: KnowledgeIteration 自动创建

**As a** 系统
**I want** 每次版本差异入库时自动创建迭代记录
**So that** 知识演化链可追溯：v1 → v2 → v3 的知识变化有记录

| # | 验收标准 |
|---|---------|
| US-4.1 | Given `ingest_lanhu_version_diff()` 被调用 / When diff_json 非空 / Then 自动创建或更新 KnowledgeIteration 记录 |
| US-4.2 | Given 同一版本多次导入 / When 再次导入 / Then 更新已有迭代而非创建重复记录 |
| US-4.3 | Given 迭代记录已创建 / When 查询知识图谱 / Then version 节点关联到对应迭代 |

### US-5: 前端版本标记

**As a** 测试工程师
**I want** 在 AiResultModal 中看到每个功能点的版本来源
**So that** 知道哪些 FP 是新增的、哪些是继承的

| # | 验收标准 |
|---|---------|
| US-5.1 | Given 功能点有 `_inherited=True` / When 显示在 AiResultModal / Then 标记为 ➡️「沿用自 vX.Y.Z」 |
| US-5.2 | Given 功能点无 `_inherited` 且 diff_status="update" / When 显示 / Then 标记为 ✏️「本版本变更」 |
| US-5.3 | Given 首次导入（无 diff）/ When 显示 / Then 标记为 🆕「首次提取」 |
| US-5.4 | Given 功能点在旧版本存在但新版本中消失 / When 显示 / Then 标记为 ❌「vX.Y.Z 中已移除」 |

### US-6: 预存在测试修复

**As a** 开发团队
**I want** 所有单元测试通过
**So that** CI 不会因已知预存在问题误报

| # | 验收标准 |
|---|---------|
| US-6.1 | Given 运行 `npm test` / When 全部测试执行 / Then 94/94 通过 |
| US-6.2 | Given DebugTab.test.tsx / When 测试运行 / Then 3/3 通过 |
| US-6.3 | Given CaseDrawer.test.tsx / When 测试运行 / Then 3/3 通过 |
| US-6.4 | Given testcase.test.ts / When 测试运行 / Then 3/3 通过 |

### US-7: 继承匹配率监控

**As a** 开发团队
**I want** 日志记录每次用例继承的匹配/未匹配数量
**So that** 有数据支撑后续优化继承算法

| # | 验收标准 |
|---|---------|
| US-7.1 | Given `extract_features` 执行继承 / When 完成 / Then 日志记录 `fp_inherit_match_rate: X/Y (Z%)` |
| US-7.2 | Given `generate_test_cases` 执行用例继承 / When 完成 / Then 日志记录 `case_inherit_match_rate: X/Y (Z%)` |

### US-8: C 条件追踪器

**As a** Agent Team
**I want** 所有 C 条件集中追踪
**So that** 不会产生新的孤儿条件

| # | 验收标准 |
|---|---------|
| US-8.1 | Given 创建 `C-CONDITIONS.md` / When Product 开工 / Then PRD 必须包含或豁免所有 open C 条件 |
| US-8.2 | Given Leader 设定新 C 条件 / When 写入 verdict / Then 同步追加到 C-CONDITIONS.md |
| US-8.3 | Given PR 合入 / When C 条件被满足 / Then 标记为 ✅ closed |

## 5. 依赖关系

```
US-1 (感知哈希) ──→ US-2 (VersionCompare) 使用哈希结果展示视觉差异
US-4 (KnowledgeIteration) ←→ US-7 (继承日志) 同文件，一起做
US-3 (PrototypePreview) 独立 ──→ 可用 US-1 的截图哈希
US-5 (版本标记) 独立 ──→ 消费 US-4 的迭代信息
US-6 (测试修复) 独立，无依赖
US-8 (C-CONDITIONS.md) 独立，纯流程
```

建议执行顺序：US-6 → US-1+US-4+US-7 (后端) → US-2+US-3+US-5 (前端) → US-8
