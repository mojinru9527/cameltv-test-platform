# Batch 81 — PRD Summary（WARN 清单长期维护机制，C80-1）

> **Product (🟦)** | Date: 2026-08-04 | Status: Approved

mode: light
豁免理由: 内部流程工具 + 文档（scan 基线模式、WARN 清单、C 条件口径），不涉及产品行为/接口/配置/依赖；按 SKILL.md「批次模式」判定为轻量批次，PM/Design 工件省略，QA/Leader/看板照常。

## 1. 问题陈述

C80-1 要求"长期维护 WARN 清单"，但当前只有一次性分类结论（230 项），缺少：

1. **可追踪的基线**：没有固化 WARN 分类与数量的机器可读基线，无法对比"新增 vs 存量"。
2. **趋势记录**：没有定期审计节奏，WARN 增长会静默发生。
3. **归因机制**：新代码引入新 WARN 类别时无人复核。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量 |
|------|------|------|------|
| warn-baseline.json | 无 | 建立（230 项分类） | 文件 + 校验 |
| scan 对比模式 | 无 | -BaselinePath 可报新增类别 | 脚本运行 |
| inventory 文档 | 无 | 分类/节奏/趋势表 | 结构检查 |
| C80-1 口径 | 一次性 | 长期维护（周/10 批次审计） | C-CONDITIONS |

## 3. 非目标（本次不做）

- **不减少 WARN 数量**：本批只建机制；数量消化按 C80-1 长期进行。
- **不处理 C74-1/2/3**（外部依赖验收项）：继续豁免。

## 4. 用户故事 + 验收标准

- As 维护者, I want 一条命令对比 WARN 基线, so that 新增类别立即可见。
  - 验收：Given 基线 JSON / When 运行 `scan-common-bugs.ps1 -BaselinePath ...` / Then 输出新增类别与数量差异。
- As Leader, I want WARN 趋势有记录, so that 长期维护可复盘。
  - 验收：Given inventory 文档 / When 审计 / Then 趋势表追加条目。
