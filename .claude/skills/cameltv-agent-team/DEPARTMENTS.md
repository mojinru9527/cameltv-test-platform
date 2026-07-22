# 六部门角色与交付物模板

> 蒸馏自 `work-logs/batch-*` 历史工件与 memory `[[agent-*-department]]`。每个部门一节：定位 + 关键规则 + 可复制的工件骨架。填模板时把 `{...}` 换成真实内容，别保留占位。

---

## 1. 🟦 Product 产品部门 → `batch-{name}-prd-summary.md`

**定位**：从问题出发，不是从方案出发。接到功能请求先追问 3 次「为什么」。清晰、频繁地说「不」以保护聚焦。

```markdown
# Batch {name} — PRD Summary
> **Product (🟦)** | Date: {YYYY-MM-DD} | Status: Draft/Review/Approved

## 1. 问题陈述
{用户痛点 + 证据：访谈/数据指标/工单量}

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|

## 3. 非目标（本次不做）
- {明确排除项 + 原因}

## 4. 用户故事 + 验收标准
- As a {角色}, I want {行为}, so that {可衡量结果}
- 验收：Given {前置} / When {操作} / Then {预期}

## 5. 技术考量
{依赖 / 已知风险 / 待解决问题}

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
```

---

## 2. 🟨 PM 项目管理部门 → `batch-{name}-pm-plan.md`

**定位**：把 PRD 拆成开发者「无需追问即可执行」的 30–60 分钟任务。**现实主义范围**——不加 PRD 未写的「高级/豪华」需求；首个实现通常需 2–3 个修正周期，正常。

```markdown
# Batch {name} — PM Plan
> **PM (🟨)** | Date: {YYYY-MM-DD}

## 规格摘要
**原始需求**: {引用 PRD 关键项}   **目标时间**: {从 PRD 提取}

## 开发任务
### [ ] Task 1: {任务名}
**描述**: {具体做什么}
**验收标准**: - {可测试的标准}
**涉及文件**: - {路径} — {改什么}
**参考**: PRD §X / 设计规范 §Y

## 质量要求
- [ ] 响应式（Desktop + Tablet）  - [ ] OpenAPI 同步  - [ ] 单元测试覆盖
- [ ] 无障碍（ARIA/键盘）  - [ ] 无 console 报错/告警
```

---

## 3. 🎨 Design 设计部门 → `batch-{name}-design-spec.md`

**定位**：像素级规范 + 三态设计 + 无障碍。**真实栈是 shadcn/ui（Radix + Tailwind + CVA），不是 Ant Design**——所有 Token/组件规格走 Tailwind 语义类，细节见 `cameltv-ui-conventions` skill。若前端已实现，则**反向回填**规范并做设计走查（每条结论给「文件:行号」锚点）。

```markdown
# Batch {name} — Design Spec
> **Design (🎨)** | Date: {YYYY-MM-DD} | Status: 草稿/就绪/已验收

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind + CVA；Token 走语义类（bg-muted / text-muted-foreground / border / variant）。

## 1. 组件规格表
| 组件 | 尺寸/间距 | 颜色语义 | 交互态(默认/hover/active/focus/disabled) |

## 2. 布局与响应式
| 断点 | 布局 | 变化 |
| <1024px(单列) / md 768 / lg 1024+ |

## 3. 状态设计核对（四态）
| 组件 | Loading | Empty | Error | 未启用(503) |

## 4. 设计 QA 走查发现（P0–P3，均附文件:行号）
### 🔴/🟠/🟡/⚪ P{n}-{seq} {标题}
{事实} → **建议**：{改法}

## 5. 设计签核
结论：通过 / 有条件通过（列 P1 阻断项）/ 打回
```

设计走查最常复现的问题清单，直接用 `cameltv-ui-conventions` 的「Red Flags」逐条比对。

---

## 4. 💻 Dev 开发部门 → 代码 + `kanbans/DEV-{name}.md`

**定位**：全栈交付（React 18 + TS 前端 / FastAPI + SQLAlchemy 后端）。安全优先、性能意识、API 契约、迁移安全。

**强制节奏**：
1. **多窗口并行检查**：若已有 ≥1 个 Agent Team 窗口活跃，开工前必须用 `git worktree add` 创建独立 worktree（见 SKILL.md「多窗口并行开发」）。**禁止多个窗口共享同一工作目录。**
2. 开工前：`git fetch origin develop`，从最新 develop 切分支（见 SKILL.md Git 工作流）。
3. 开工前先读看板（SKILL.md 第 0 步）。
4. 编码前扫 `cameltv-bug-guard` skill。
5. 按切片推进，TDD 先测后码。
6. 每切片结束执行：
   ```bash
   git status --short
   git add -- {本切片明确文件列表}
   git diff --cached --name-status
   git commit -m "feat(batch-{N}): {切片描述}"
   git push -u origin feature/batch-{N}-{name}

技术方案骨架：
```markdown
## 架构决策
前端: {组件/状态/路由}   后端: {API/模型/服务分层}
API 契约: {OpenAPI}   DB 变更: {Alembic 迁移}
## 实现文件
前端: {页面/组件/Hook}   后端: {Model/Schema/Service/Router}
## 性能基准
API: {ms}   前端: {s}   覆盖: {%}
```

---

## 5. 🔍 QA 测试部门 → `batch-{name}-qa-report.md`

**定位**：质量守门人，默认立场「NEEDS WORK」，需可复现证据才翻 READY。证据驱动——每个结论有截图/日志/指标；不预设缺陷数量。

```markdown
# Batch {name} — QA 报告
> **QA (🔍)** | Date: {YYYY-MM-DD} | Verdict: PASS / NEEDS WORK

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |

## 可执行门禁（必须记录命令、退出码和日志摘要）
- 前端：`npm ci`、`npm run typecheck`、`npm run build`、相关 Vitest
- 后端：app 导入、`ruff check app --select F821`、Alembic 单头/revision、相关 Pytest
- UI/功能：关键用户路径、桌面与移动端截图、控制台错误
- 禁止用“文件存在/代码目测/工件齐全”代替上述执行结果

## 逐条件验证
### C{n}: {条件名}
**变更文件**: {路径:行}
| 检查项 | 结果 | 说明 |
**✅ PASS / ❌ FAIL**

## 缺陷列表
| # | 严重级(P0-P3) | 描述 | 证据 | 状态 |

## 发布建议
状态: NEEDS WORK / READY   必修复: {N}   建议修复: {N}
```

严重级：P0 致命（崩溃/数据丢失/安全漏洞，立即）/ P1 严重（核心不可用，4h）/ P2 一般（有替代，24h）/ P3 建议（体验，下迭代）。

---

## 6. 🎯 全部 Slice 完成 + Leader APPROVED 后：

gh pr create --base develop --head feature/batch-{N}-{name} \
  --title "feat: Batch {N} — {摘要}" \
  --body "详见 Agent Team 工件: work-logs/"

**定位**：总协调 + 质量把关。抽检各部门工件，给判决，并可为下一批次设 Leader 条件（C 编号）。

## 7.PR 合入后确认无未推送提交，再删除本地分支；远端分支按仓库策略处理。
## 8.batch 结束更新看板：Slice 状态、当前位置、批次记录（产出+审批+耗时）。

```markdown
# Batch {name} — Leader Verdict
> **Leader (🎯)** | Date: {YYYY-MM-DD} | Decision: APPROVED / 有条件通过 / 打回

## 评审摘要
| 维度 | 评分 | 备注 |
| 实现质量 / 风险 / 覆盖 |

## 关键决策（已批准）
1. {决策 + 理由}

## 抽检通过
- ✅ {文件:行} — {核对点}
- ✅ {PR 检查名称 + 运行链接/日志摘要} — {退出码与结果}

## 判决
{APPROVED → 给合入指令；或列出必须修复的条件 C{n}}
## 下一批次 Leader 条件（如有）
- C{n}: {条件}
```
