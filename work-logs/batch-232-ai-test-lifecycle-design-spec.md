# Batch 232 - AI Test Lifecycle Design Spec
> **Design** | Date: 2026-09-07 | Status: Ready

## 0. 技术体系确认

shadcn/ui + Radix + Tailwind + CVA。颜色使用 `bg-muted`、`text-muted-foreground`、`border`、状态语义 Token；不引入裸色阶或新的视觉体系。

## 1. 信息架构

概览按测试人员的问题顺序组织，而不是按数据库表组织：

1. 顶部身份条：任务类型、当前状态、验收状态、所属版本任务。
2. 测试阶段条：需求测试、版本回归、生产回归；当前 Mission 高亮，缺失阶段显示“未创建”。
3. AI 主链：资料、需求分析、测试契约、用例设计、执行证据、验收结论；每格展示真实计数、状态、缺口。
4. 覆盖统计：功能/API/UI 与新增/变更/受影响基线两个维度。
5. 逐用例表：类型、需求角色、模块、来源数、执行次数、最新结果、证据数、缺陷数、复验状态。

## 2. 组件规格表

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| 身份指标 | `grid gap-3 md:grid-cols-4`，内容 `p-3` | Badge 语义色 | 只读 |
| 三阶段条 | `grid gap-2 md:grid-cols-3` | 当前阶段 `border-primary`，缺失 `bg-muted` | 关联阶段可点击进入 |
| 六阶段主链 | `grid gap-2 md:grid-cols-3 xl:grid-cols-6` | 完成 success、处理中 info、阻塞 danger、未开始 muted | 点击对应 Tab |
| 覆盖统计 | 两组紧凑横向指标 | 成功/警告/中性语义 | 只读 |
| 用例表 | 宽屏 Table；窄屏横向滚动 | 结果使用 OutcomeBadge | 行点击进入执行详情（有 run 时） |
| 错误态 | `ErrorState` + 重试 | destructive 语义 | 重试按钮可操作 |

## 3. 状态设计

| 区域 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 整页 | 三段 Skeleton | 显示任务存在但链路尚未开始及下一步 | ErrorState + 重试 | AITDE 503 提示管理员启用 |
| 阶段 | 不单独加载 | 0 数量并写明缺口 | 随整页错误 | 不伪装为 0 |
| 用例表 | Skeleton rows | “尚未生成用例” | 随整页错误 | 不挂载表 |

## 4. 文案与状态映射

- Mission type：FEATURE=需求测试，VERSION=版本回归，REGRESSION=生产回归。
- Case type：FUNCTIONAL=功能，API=接口，UI=UI 自动化，UNCLASSIFIED=未分类。
- Requirement role：NEW=本次新增，CHANGED=本次变更，IMPACTED_BASELINE=受影响旧功能，UNCLASSIFIED=未分类。
- 复验：无失败=不需要；失败且无子运行=待复验；有子运行且最新 PASS=复验通过；否则=复验未通过。
- 缺口文案必须陈述事实，例如“3 条用例未执行”“2 条失败用例尚无证据”，不写泛化说明。

## 5. 响应式与无障碍

- 390px 下阶段条和主链单列；表格放在 `overflow-x-auto` 容器，不压缩文字到重叠。
- 所有可点击阶段含明确文本；图标仅辅助，不依赖颜色传达状态。
- 表头和 Badge 使用中文；链接/按钮焦点沿用全局 focus ring。
- 加载失败不得被吞成空态；请求使用 React Query signal 取消。

## 6. 设计 QA 预检

- P1：当前静态主链会造成“已做完”的错觉，必须全部替换为实时数据。
- P1：逐用例执行表必须一次接口返回，禁止每行发请求。
- P2：历史未分类数据必须显式显示“未分类”，不能默认归为功能。
- P2：失败与阻塞使用不同文案和色调。

## 7. 设计签核

结论：有条件通过。实现必须满足四态、中文状态、三视口无重叠和单请求聚合，缺任一项则 QA 打回。
