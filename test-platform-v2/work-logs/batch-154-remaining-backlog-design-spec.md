# Batch 154 — Design Spec（四项收口）

> **Design (🎨)** | Date: 2026-08-11 | Status: 就绪

## 0. 技术体系确认
shadcn/ui + Radix + Tailwind；FastAPI + SQLAlchemy。

## 1. WS1 数据集 UI
| 组件 | 规格 |
|------|------|
| CaseDrawer 数据集 Select | case_type=api 时显示；options=未绑定/数据集；值存 dataset_id |
| ApiCaseTab 数据集 Select | 环境旁，w-[180px]；未选=用用例默认/不批量 |

## 2. WS2 图谱
- backfill：实体名匹配 TestCase.case_id/title、RequirementDocument.title → 回填 source_id/source_ref；未匹配保持 None 并计数。
- evolve 加固：source_id 悬空实体跳过关系发现；异常返回 error 字段不崩。
- 删除级联：knowledge_source.status=deprecated。

## 3. WS3 UI 映射
| 组件 | 规格 |
|------|------|
| 任务表单 | 关联用例 Select（ui 类型用例） |
| 任务列表 | 用例标题列 |
| 回写 | run done/fail → case.last_run_status + last_response_json |

## 4. WS4 env
- guide 表：入口 launcher(config/runtime/{target}.env) → backend .env → frontend .env.local。
- inventory 脚本输出清单 + 缺项。

## 5. 设计签核
结论：通过
