# Batch 168 — Design Spec
> **Design (🎨)** | Date: 2026-08-13 | Status: 就绪（后端行为规范 + 前端反向回填走查）

## 0. 技术体系确认
后端 FastAPI + SQLAlchemy；前端 shadcn/ui（Radix + Tailwind + CVA）。本批主要后端行为修复，前端仅 Tab/Select 两处。

## 1. 后端行为规范
| 模块 | 行为 | 说明 |
|------|------|------|
| version_coverage_service | 键=(module_id,name,type)；fallback 顺序=bundle 绑定文档用例模块 → 项目 distinct | D1/D2 |
| generate_api_cases_from_linked_endpoints | is_deleted=false；变体独立行；模块级匹配 GET 优先 confidence>=0.4 | D3/D8 |
| import_cases | create_ui_cases 回填已导入 P0/P1 用例，幂等键 (title,module) | D4 |
| execute_all_cases | body.ui_environment_id 独立解析 UI base_url；notes 含 error/exit_code/stdout_tail | D6/D7 |

## 2. 前端组件规格
### 2.1 BundleDetail Tabs（修复 D5）
- 四个独立 `TabsTrigger`：模块树 / 版本链 / 版本差异 / 三类型覆盖；禁止 trigger 互相嵌套。
- 锚点：`src/pages/release-bundles/BundleDetail.tsx:577-586`。

### 2.2 PlanDetail 执行弹窗（D7）
- 在「执行环境」下增加「UI 执行环境」Select，空值 sentinel `__none__`；仅 auto_ui 开启时展示。
- 锚点：`src/pages/testplan/PlanDetail.tsx:247-293`、`654-692`；Select 遵循 Radix sentinel 规范（cameltv-ui-conventions）。
- 失败执行记录的 notes/错误摘要完整展示，不截断到「未知」。

## 3. 状态设计核对
| 场景 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 覆盖矩阵 | 已有“加载覆盖数据中...” | 已有空态 | 失败 toast | 无 |
| UI 环境 Select | 无 | sentinel「未绑定」 | 无 | auto_ui 关闭时隐藏 |

## 4. 设计 QA 走查发现
- P2-01 BundleDetail.tsx:577 错位嵌套（D5）→ 修复为两个平级 trigger。
- P2-02 PlanDetail.tsx:293 单一环境选择 → 增加 UI 环境选择。

## 5. 设计签核
结论：通过（前端变更小、按既有组件规范回填）。
