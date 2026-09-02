# Batch 225 — Design Spec
> **Design (🎨)** | Date: 2026-09-05 | Status: 就绪 | Executor: Codex | 完整批次

## 0. 技术体系
前端 `@/ui` 语义组件；后端 FastAPI + SQLAlchemy。

## 1. 组件规格
| 组件 | 说明 |
|------|------|
| 4 步步骤条 | Badge default/secondary + 文本 |
| 登记表单 | Input/Textarea |
| 接入列表 | 已接入业务条目（service_key badge + 状态） |

## 2. 状态设计（四态）
表单空态提示；推进 toast；基线显示。

## 3. 设计 QA 走查发现
### ⚪ P3-1 未用 import Query
onboarding.py 无用 Query。→ 移除。

## 4. 设计签核
结论：**通过**。
