---
name: interaction-case-augmenter
description: 功能用例生成过程中的交互校验增强层 + 项目历史缺陷模式检索层。在既有功能用例生成链路里补齐页面/控件/状态/反馈/导航/输入/角色权限/平台差异等交互校验，并按项目 Bug Pattern Library 做覆盖判定（强覆盖跳过、部分覆盖增强、真实缺口才新增）。适用于 Web 管理后台、小程序、门店平板、C 端 H5、接口。不另建平行测试体系，不以用例数量增长为目标。
owner: qa-team
last_reviewed: 2026-11-06
status: active
expires: 2027-05-05
tags: [case-generation, interaction, bug-pattern, coverage-dedup]
related: ["../test-case-design/SKILL.md", "../../tests/test-case-standards/interaction-testing/"]
---

# 功能用例交互增强与历史缺陷学习（interaction-case-augmenter）

> 版本：适配自 `cameltv-qa-skill-pack v1.1.0`（2026-11-05），接入本仓库 `test-case-design` 生成链路。
> 本 Skill 是**增强层**，不是第二个用例生成器。

## 1. 定位

在既有功能用例生成过程中工作：

- 保留原有功能点、用例编号规则、字段、优先级、目录和导入 Schema（见 `../test-case-design/case-template.md`）。
- 把交互校验**融入**原功能用例；只有独立失效机制、独立可观察 oracle 无法合并时才新增用例。
- 把历史 Bug 当作可检索的缺陷知识：回答「在哪里测、怎样触发、看什么断言」，而不是按 Bug 数生成测试。
- 先做覆盖判定：`COVERED_STRONG` 只关联不新增；`COVERED_PARTIAL` 优先增强原用例；`GAP` 才新增最小用例。
- 优化目标是**单位用例的缺陷发现能力**，不是用例总数、步骤数或执行时长。

## 2. 生成前必须读取的项目知识（按优先级）

1. 仓库 `CLAUDE.md` / `AGENTS.md`、`test-platform-v2/CLAUDE.md`。
2. `tests/test-case-standards/` 现行规范：`功能测试输出用例要求.md`、`接口测试输出用例要求.md`、`接口用例必填真实数据规范.md`。
3. `../test-case-design/SKILL.md`、`case-template.md`、`functional-checklist.md`、`api-checklist.md`（现行基座）。
4. `tests/test-case-standards/interaction-testing/`：
   - `interaction-methodology.md`（方法论）
   - `platform-profiles.md`（跨平台 Profile，含本项目平台裁剪）
   - `admin-and-consumer-interaction.md`（后台↔C 端联动）
   - `role-permission-coverage.md`（角色权限 L1–L8 层级）
   - `interaction-coverage-matrix-template.csv`（覆盖矩阵模板）
5. 本 Skill `references/`：
   - `universal-interaction-checklist.md`（A–I 通用检查点）
   - `historical-bug-pattern-library.json`（机器检索唯一事实源）
   - `historical-bug-pattern-library.md`（人工评审摘要）
   - `historical-bug-pattern.schema.json`（结构校验）
   - `bug-pattern-coverage.csv`（模式↔用例覆盖映射）
6. 当前模块已有功能用例、已执行记录、缺陷 ID、需求文档。

若某知识文件不存在，**明确标记缺失**，不得声称已完成历史 Bug 全量学习。项目已有同类 Bug 库/覆盖台账时以项目现存数据为准，合并而不是新建重复副本。

## 3. 本项目平台裁剪（只测真实存在的端）

| 平台 | 范围 | 交互重点 |
|---|---|---|
| 管理后台 Web（Vue3 + Element Plus + RuoYi） | `https://xinyuwadao.com` | 列表筛选/分页/排序、抽屉与弹窗关闭态、表单校验时机与长度、批量操作、导出、富文本、上传与精修任务、角色菜单/按钮/路由/API 四层一致性 |
| 微信小程序 | 体验版/正式版 | 生命周期 onShow/onHide、页面栈与返回、分享/扫码进入、订阅消息、支付与自提、软键盘与安全区、弱网重连、分包加载失败 |
| 门店平板 App | 1.3.x | 扫码会员码、微信支付、小票打印、叫号、断网重试、设备绑定 |
| 叫号屏（浏览器） | `/screen` 等 | 轮询/推送刷新、断线重连、字号与可视距离、夜间模式 |
| C 端 H5 / 商城（有赞） | 有赞商城 + 小程序商城 | 商品可售性、购物车、优惠券、支付回调、退款状态 |
| 接口 | `https://xinyuwadao.com/hz-api` | 鉴权与越权、参数校验、幂等、状态机、回调验签、数据一致性 |

**禁止**把 Web 交互规则无条件套到小程序/平板/硬件；也禁止把小程序手势规则套到 Web。

## 4. 主生成流程

### Phase A — 需求对象识别
识别：业务功能点与用户任务；产品面（C 端/管理后台/门店平板/叫号屏/第三方/接口）；页面/路由/弹窗/抽屉/列表/表单；控件及其真实输入方式；角色、数据范围、对象状态；数据输入输出与跨端关系；网络/生命周期/设备能力/外部依赖。

未知角色、未知状态、未定义预期行为**不得自行补造**，写入待确认项（`OPEN`）。

### Phase B — 生成基础功能用例
先按 `test-case-design` 原有规则生成业务功能用例（正/负/边界 + 深度层）。此步不提前展开所有交互维度。

### Phase C — 交互风险扫描（按对象，不按清单无差别加用例）
逐对象选取适用维度（对应 `universal-interaction-checklist.md` A–I）：

1. 可发现性与可理解性（入口、标题、当前位置、对象身份）
2. 控件操作与状态转换（默认/禁用/只读/加载/选中）
3. 操作反馈及反馈时机（成功/失败/pending/进度）
4. 导航、返回、关闭与上下文保持（含抽屉关闭后页面是否可继续操作）
5. 输入、校验、边界与错误提示（时机、锚点、跨字段、长度一致性）
6. 连续操作、重复触发、并发与防抖
7. 取消、中断、超时、重试与恢复
8. 刷新、重进、切后台/前台、重启后的状态与持久化
9. 角色/权限：菜单可见性、按钮可用性、直接路由、直连 API、数据范围（L1–L8）
10. 视口、缩放、方向、输入法、键盘/触控/手势/扫码
11. 空/加载/成功/失败/无权限/无数据/资源异常状态
12. 后台配置→C 端结果（保存≠处理完成≠审核通过≠发布完成≠C 端可读≠实际展示）

不适用维度不进入用例；不生成「所有按钮都测 hover/双击/读屏」这类机械清单。

### Phase D — 历史 Bug 模式检索与定位
从 `historical-bug-pattern-library.json` 提取检索特征：
`模块/页面/控件 + 操作序列 + 数据类型 + 状态转换 + 角色权限 + 平台/设备 + 接口/缓存/外部依赖`。

对每个命中模式回答四问：
1. **哪里测**（`detection_point`）
2. **怎样触发**（`trigger_signature`）
3. **观察什么**（`test_oracle`，含用户可见现象 + 必要数据/API/状态断言）
4. **现有是否覆盖**（`existing_test_ids` + 该用例步骤是否真正触发相同条件、断言能否捕获同种失效）

只按真实 Bug 记录或有证据的项目模式匹配。通用经验风险标 `GENERIC-RISK`，不得伪装成项目历史 Bug。

### Phase E — 覆盖判定（控制用例数量的关键）
每个模式对当前功能只允许一个判定：

| 判定 | 处理 |
|---|---|
| `COVERED_STRONG` | 仅登记 Pattern ID / Bug ID 关联，**不新增用例** |
| `COVERED_PARTIAL` | 增强该用例的步骤/预期结果，**不新增平行用例** |
| `GAP` | 仅此时生成一条最小、可判定的补充用例（必要时拆独立 oracle） |
| `NOT_APPLICABLE` | 当前需求不存在该机制，说明理由，不生成 |
| `NEEDS_CONFIRMATION` | 证据/预期行为不足，标记待确认，不猜测 |

过滤规则：
- 已入库且映射为 `COVERED_STRONG` 的模式，本轮跳过生成。
- 多条 Bug 属同一失效模式且同一条用例强覆盖时，只关联多个 Bug ID。
- 一个新需求命中多个模式但可由同一操作路径 + 同一组独立可观察断言验证时，合并进已有用例。
- 不得为「历史 Bug 全覆盖」把无关旧 Bug 拉进本轮。
- **不得**因标题相似就判强覆盖；必须核对触发条件与断言。

### Phase F — 合并交互校验与 Bug 派生知识
优先级：
1. 增强原用例（同时验证业务结果 + 关键交互状态/反馈/恢复），一条用例尽量沿一条真实操作路径覆盖多个检查点。
2. 用例内混入多个无法独立判定的失效机制 → 拆最小必要用例。
3. 仅 `GAP` 生成新用例。
4. 同一用例可关联多个 Pattern ID；同一模式可被不同平台/独立状态实现的用例覆盖。

用例描述必须让执行者可独立理解，不要求执行者阅读 Bug 历史。Bug 关联信息写入备注/标签/关联字段；Schema 不支持则维护在 `bug-pattern-coverage.csv`，**不得擅自改变导入字段**。

### Phase G — 去重与用例预算检查
输出前自检：
- 新用例是否与既有用例在触发条件、操作、oracle 上重复；
- 能否通过增强既有用例解决；
- 每条新增是否对应真实覆盖缺口；
- 是否误加了不适用的角色/平台/控件状态；
- 是否引入无需求/标准/项目证据的预期结果。

不设「用例必须增加 X%」目标。允许本轮只增强旧用例、只更新台账、或零新增。
输出：`保留数 / 增强数 / 新增数 / 强覆盖跳过数 / N/A 数 / 待确认数` 及原因。

## 5. 预期结果证据标签

`REQ` 明确需求；`STD` 采用标准；`PROJECT-PATTERN` 项目既有交互惯例；`BUG-PATTERN` 历史缺陷知识；`HEURISTIC` 可用性启发式；`OPEN` 需产品/研发确认。
根因置信度只能 `confirmed` / `probable` / `unknown`，不得从症状臆造根因。

## 6. 输出

保留 `test-case-design` 原有用例 Schema，另输出旁路产物：

- 功能用例（既有格式，原字段不变）
- 交互覆盖矩阵（仅适用时，模板 `interaction-coverage-matrix-template.csv`）
- `bug-pattern-coverage.csv`：本轮命中模式、关联 Bug、检测位置、既有用例、覆盖判定、处理动作
- 摘要：保留/增强/新增/强覆盖跳过/不适用/待确认

## 7. 质量门禁

- 不减少原功能需求覆盖。
- 不因历史 Bug 知识机械增加用例数量。
- `COVERED_STRONG` 不新增重复用例。
- `COVERED_PARTIAL` 优先增强原用例。
- 只有 `GAP` 允许新增 Bug 派生用例。
- 所有 Bug 派生判断可追溯到 Bug ID / Pattern ID；无历史记录只标 `GENERIC-RISK`。
- 不伪造 Bug、根因、角色、预期行为、测试证据。
- 输出必须兼容项目原有用例格式与导入流程。

## 8. 与 Bug Pattern Curator 的分工

- **正常生成**：只读 Pattern Library + Coverage Map，不挖掘历史 Bug。
- **首次导入 / 新增缺陷沉淀 / 覆盖复核**：调用 `../bug-pattern-curator/SKILL.md`（按需，不在每次生成时运行）。

## 9. 运行时接入

本 Skill 的可执行契约见 `integration/functional-case-generator-hook.md`。
本仓库的运行时接入点：
- 平台 AI 生成：`test-platform-v2/backend/app/services/ai_service.py::_load_skill_context_for`
- 运行时清单：`.claude/skills/test-case-design/interaction-checklist.md`、`api-interaction-checklist.md`、`bug-pattern-digest.md`
- 回归守卫：`test-platform-v2/backend/tests/test_interaction_skill_context.py`

> 只复制 Markdown 到 `.claude/skills/` 而未接入加载器，不等于运行时生效。
