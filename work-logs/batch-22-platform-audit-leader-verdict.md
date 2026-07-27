# Batch 22 — 测试平台全面审查 Leader Verdict

> **Leader (🎯)** | Date: 2026-07-19 | Decision: **APPROVED ✅ — 有条件通过，进入 Slice 0**

---

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| **现状认知准确性** | ⭐⭐⭐⭐⭐ | 3 个 Agent 并行代码级探索，结论全部有文件:行号锚点 |
| **六部门产出质量** | ⭐⭐⭐⭐⭐ | Product(PRD) + PM(10 tasks) + Design(11 发现) + Dev(施工图) + QA(22 缺陷) — 全链路贯通 |
| **可执行性** | ⭐⭐⭐⭐⭐ | PM plan 含具体工时/文件/验收标准，Dev 可直接领用 |
| **覆盖广度** | ⭐⭐⭐⭐⭐ | 后端 85 service + 前端 59 .tsx + 测试 612 test + CI 5 workflow — 无死角 |
| **风险** | 🟢 低 | 本次审查是**只读分析**，零代码改动 |

---

## 核心发现：一句话总结

> **V2.2-V2.6 的 36 项交付已把平台底座做得很扎实——612 测试、安全基线全绿、三个专项引擎全部真实。但文档停滞在 V2.1 时代，且「功能用例自动执行」这个小白愿景的核心环节缺失。修好这两件事，平台就能进入「可演示的小白测试全链路」状态。**

---

## 四部门发现归并（去重后 16 条可执行项）

### 🔴 P0（3 项，阻断小白愿景）

| # | 项 | 来源部门 | 对应 Task |
|---|-----|---------|----------|
| L1 | **文档全量同步**：CLAUDE.md 模块表 + 现状 PRD + frontend CLAUDE.md + 代码审查 PRD 全部更新到 V2.6 状态 | Product/Dev/QA | Task 0b |
| L2 | **功能用例→Playwright 编译器**：LLM 把 `steps` JSON 编译为 `.spec.ts`，经 sandbox 验证后执行 | Product/Dev | Task 1a |
| L3 | **统一执行编排器**：API/UI/功能三种 case_type 走同一个 TaskQueue，一键「生成+执行」全流程 | Product/Dev | Task 1b |

### 🟠 P1（7 项，体验/质量基线）

| # | 项 | 来源部门 | 对应 Task |
|---|-----|---------|----------|
| L4 | 审查队列持久化（替 AiResultModal） | Product/Design | Task 2a |
| L5 | 智能分诊（LLM 分析失败用例 → 三级分类 + 一键提缺陷） | Product/QA | Task 2b |
| L6 | 前端 AsyncState 迁移（15+ 页面标准化） | Design/Dev | Task 3b |
| L7 | 新用户 onboarding wizard | Design | D9 |
| L8 | request-id/耗时日志中间件 | Dev | 新建议 |
| L9 | 前端组件/页面单元测试（vitest 0→≥10） | QA | 新建议 |
| L10 | 需求输入简化（"一句话需求" + 模板） | Product/Design | Task 2c |

### 🟡 P2（6 项，技术债务）

| # | 项 | 来源部门 | 对应 Task |
|---|-----|---------|----------|
| L11 | 双重主题系统合并（data-theme → data-theme-id） | Design/Dev | — |
| L12 | useChartColors 主题响应修复 | Dev | — |
| L13 | onboarding.md 路径修正 | QA | — |
| L14 | defect/index.tsx 988 行组件拆分 | Dev | — |
| L15 | AI 服务蓝湖路径配置化 | Dev | — |
| L16 | Playwright e2e 加深为业务功能验证 | QA | — |

---

## 重要决策（已批准）

### 决策 1：先修文档再修功能

**理由**：当前文档（CLAUDE.md / 现状 PRD / frontend CLAUDE.md）标注三引擎为「演示态/随机数」，而代码实际全部真实。如果新人或 AI 读到旧文档，会得出"平台不靠谱"的结论。**文档错误比代码 bug 更危险。**

**执行**：Slice 0 → Slice 1-3，不可调换顺序。

### 决策 2：用例→脚本编译器走 LLM，不走模板

**理由**：功能用例 `steps` JSON 格式不统一（有的写「点击登录按钮」，有的写「Click login button」），模板引擎无法覆盖。LLM 是唯一可行的编译器。

**风险**：LLM 生成的 Playwright 代码可能语法错误。**缓解**：sandbox 执行验证——编译结果先在 headless Chromium 跑一次，通过的才算编译成功，不通过的返回错误行号 + 修复建议。

### 决策 3：统一编排器基于现有 TaskQueue 扩展

**理由**：`api_task_worker.py` 已有轮询执行、取消、重试、超时机制。不新建调度系统，在此基础扩展为通用 `TaskQueue`——支持 API/UI/功能性三种 `case_type` 的执行。

### 决策 4：文档更新后立即归档过时的「代码审查PRD」

**理由**：2026-06-22 的代码审查 PRD 是 V2.1 时代的快照。6 条 P0 结论全部过时。**保留为历史参考**（加 `status: superseded` 水印），不要删。新建一份 V2.6 基准的技术审查。

---

## 各工件抽检通过

- ✅ `batch-22-platform-audit-prd-summary.md` — 用户旅程逐段诊断，RICE 评分，差距分析清晰
- ✅ `batch-22-platform-audit-pm-plan.md` — 10 tasks，4 Slices，工时估算合理，依赖关系正确
- ✅ `batch-22-platform-audit-design-spec.md` — 逐页 UI 走查 + cameltv-ui-conventions 8 Red Flags 逐条比对 + 两个新增页面线框
- ✅ `batch-22-platform-audit-dev-review.md` — 全栈代码级审查，后端 85 service + 前端 59 .tsx，有文件:行号
- ✅ `batch-22-platform-audit-qa-report.md` — 22 项发现，6 维度 × 证据驱动，P0-P3 分级正确

---

## 判决：APPROVED ✅ — 进入 Slice 0

**Slice 0 验收标准**（Task 0a + 0b）：
- [ ] 三个引擎代码级核查完成，事实报告附行号
- [ ] CLAUDE.md 模块表更新（3 项成熟度修正）
- [ ] 现状功能 PRD 模块 11-13 更新（API/UI/AV 真实状态 + 行号锚点）
- [ ] frontend CLAUDE.md 移除「演示态」标注
- [ ] 代码审查 PRD 加 `superseded` 水印
- [ ] onboarding.md curl 路径修正

**Slice 1 前置条件**：Slice 0 通过

**Slice 2/3 前置条件**：Slice 1 通过

---

## 下一批次 Leader 条件

1. **C1**：文档同步完成后，运行 `cameltv-doc-check` skill 确认 0 过期文档
2. **C2**：用例→Playwright 编译器的第一条成功编译链路（一个 P0 功能用例 → 可执行的 `.spec.ts` → headless Chromium 跑通 → 截图证据）
3. **C3**：统一编排器的一次完整批量执行（3 条 API + 3 条功能 → 6/6 有结果 → 报告自动生成）

---

## 最后：关于"小白测试"愿景的实现路径

经过六部门全面审查，结论是清晰的：

```
当前状态（V2.6）:
  提交需求 → AI生成用例 → 用例库 → 测试计划 → 手工逐条执行 → 报告
  ✅          ✅            ✅        ✅          ❌ (断裂)       ✅

Slice 1 后（VNext-1）:
  提交需求 → AI生成用例 → 用例库 → 测试计划 → 一键全部执行 → 报告 → 智能分诊
  ✅          ✅            ✅        ✅          ✅              ✅      ✅ (新增)

  小白做的事: 提交需求 ──────────→ 审查 AI 分诊结果 ──→ 决定提缺陷 or 放行
               (5 min)              (10 min)              (5 min)
```

**平台已经 80% 完成。剩下 20% 是把「手工执行」变成「自动执行」，把「逐条审查」变成「只看 AI 标的」。**

---

**Leader Agent**: 团队领导 🎯 | **日期**: 2026-07-19 | **决策**: APPROVED | **下一步**: 用户确认后进入 Slice 0 实施
