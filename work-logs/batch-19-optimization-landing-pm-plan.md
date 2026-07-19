# Batch 19 — PM Plan
> **PM (🟨)** | Date: 2026-07-20

## 规格摘要
**原始需求**: 将 12 项已声明但未落地的优化实际编码实现（PRD batch-19 §US-1 ~ US-7）
**目标时间**: 本次 batch 全部完成
**测试数据策略**: 验收过程可创建测试数据，验收通过后全部删除（见 Task 0）

## 开发任务

### [ ] Task 0: 测试数据隔离与清理机制
**描述**: 在验收开始前记录数据库基线状态，验收通过后恢复。创建专用的测试数据清理脚本。
**验收标准**:
- 验收前：记录 `cameltv.db` 基线（文件 hash + 关键表行数）
- 验收后：执行清理脚本，删除本 batch 创建的所有测试数据
- 验证：清理后数据库关键表行数与基线一致
**涉及文件**:
- Create: `backend/scripts/cleanup_batch19_test_data.py` — 清理脚本
**参考**: PRD §5（测试数据考量）

### [ ] Task 1: 接口资产 — 服务 Tab + 模块层级
**描述**: 将 AssetTab 从 Select 下拉选服务 + 平面端点列表改为 Radix Tabs 选服务 + Collapsible 模块分组 + 接口列表。模块默认收起。Tab 支持水平滚动。
**验收标准**:
- 服务以 Tabs 展示（非 Select 下拉）
- 切换 Tab 仅显示对应服务的模块
- 模块默认关闭，点击展开显示接口列表
- Tab 区域支持触控滑动和鼠标滚轮水平滚动
- 左右箭头按钮在溢出时显示
**涉及文件**:
- Modify: `frontend/src/pages/apitest/components/AssetTab.tsx` — 核心重构
**参考**: 实施计划 Task 1 / PRD §US-1

### [ ] Task 2: 快速调试 — 地址拆分 + 响应移底
**描述**: 将 DebugTab 单一 URL 输入框拆分为服务器地址/服务名/模块路径/接口路径四个独立字段。发送时用 composeAssetUrl 组装。环境切换仅更新服务器地址。响应面板从右侧移至底部。
**验收标准**:
- 四个独立输入框（服务器地址、服务名、模块路径、接口路径）
- 环境切换仅更新服务器地址字段（保留其他三字段值）
- 默认测试数设为 5
- 响应面板位于请求配置下方（非右侧）
**涉及文件**:
- Modify: `frontend/src/pages/apitest/components/DebugTab.tsx` — 核心重构
**参考**: 实施计划 Task 2 / PRD §US-2

### [ ] Task 3: 接口用例 — 按接口分组 + 收起
**描述**: 将 ApiCaseTab 平面列表改为按接口（api_spec_ref）聚合的 Collapsible 分组。每组默认关闭，显示接口名+用例数 Badge。保留单条执行、接口组批量执行、全量执行。
**验收标准**:
- 同 `api_spec_ref` 的用例归入同一 Collapsible 组
- 每组默认关闭，标题显示接口名和用例数 Badge
- 响应面板默认隐藏，执行后弹窗展示结果
- 可单条执行、按组执行、全量执行
**涉及文件**:
- Create: `frontend/src/pages/apitest/components/apiCaseGroups.ts` — 分组工具函数
- Modify: `frontend/src/pages/apitest/components/ApiCaseTab.tsx` — 核心重构
**参考**: 实施计划 Task 3 / PRD §US-3

### [ ] Task 4: 自动生成 — 全参数覆盖 + 上限 200
**描述**: 后端生成器扩展覆盖：对每个 Body 属性、Query 参数、Path 参数、Header 参数各生成空值和类型异常用例。安全上限从 30 调至 200。
**验收标准**:
- Body/Query/Path/Header 每个参数至少一条空值或类型异常覆盖
- `_MAX_CASES_PER_ENDPOINT = 200`
- 总数不超过 200
- 现有测试继续通过
**涉及文件**:
- Modify: `backend/app/services/api_case_generation_service.py` — 核心重构
**参考**: 实施计划 Task 4 / PRD §US-4

### [ ] Task 5: 用例列表 — 20/50/100 分页 + 预留高度
**描述**: 用例列表 page_size 从硬编码 20 改为可切换 20/50/100。表格容器设置固定高度避免切换分页时页面跳动。
**验收标准**:
- 分页大小可选择 20/50/100
- 表格容器 min-height 预留足够空间
- 切换分页大小后列表正确刷新
**涉及文件**:
- Modify: `frontend/src/pages/testcase/index.tsx` — 分页控件+高度
**参考**: PRD §US-5

### [ ] Task 6: 用例编辑 — 步骤格式化回显
**描述**: CaseDrawer 步骤字段从原始 JSON Textarea 改为格式化显示。读取时解析 JSON 为"1、操作描述 — 预期结果"格式，编辑时在格式化视图和 JSON 视图间切换，提交时保留原始 JSON 结构。
**验收标准**:
- 打开已有用例：步骤显示为"1、xxx — yyy"格式
- 用户修改后提交：保留 JSON 数组结构
- 新建用例：默认 placeholder 引导 JSON 格式
**涉及文件**:
- Modify: `frontend/src/pages/testcase/CaseDrawer.tsx` — 步骤字段重构
**参考**: PRD §US-6

### [ ] Task 7: 需求列表 — 来源智能压缩
**描述**: 需求来源列智能显示。蓝湖 URL 提取版本显示为"蓝湖 v{版本号}"；其他 URL 提取域名显示。添加 title 属性悬停显示完整 URL。表格固定宽度或 max-width 约束。
**验收标准**:
- 蓝湖 URL（含 `lanhuapp.com`）显示为"蓝湖 v{版本号}"
- 非蓝湖 URL 显示域名（如 `camel1.to`）
- 悬停时 tooltip 显示完整 URL
- 表格不因长 URL 而撑开
**涉及文件**:
- Modify: `frontend/src/pages/requirement/index.tsx` — 来源列渲染逻辑
**参考**: PRD §US-7

## 质量要求
- [x] 响应式（Desktop + Tablet）
- [ ] 现有功能无回归（前端 95+ 后端 66+ 测试通过）
- [ ] 无 console 报错/告警
- [ ] 遵循 shadcn/ui + Radix + Tailwind 规范
- [ ] 验收后测试数据零残留
