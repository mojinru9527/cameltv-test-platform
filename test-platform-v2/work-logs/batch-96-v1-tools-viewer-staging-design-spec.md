# Batch 96 — Design Spec（viewer 只读角色契约 + 文档基线）

> **Design (🎨)** | Date: 2026-08-05 | Status: 就绪

## 1. viewer 只读角色契约（C31-3）

| 维度 | 内容 |
|------|------|
| 菜单 | workbench/trace/requirement/report/defect/dataset/knowledge（含子项） |
| 动作（仅查看） | testcase/testplan/report/defect/schedule/dataset 的 list+detail；knowledge:view；wiki:view；lanhu_evidence:view；perftest:list；apitest:view；uitest/avcheck/mission:list |
| 明确不授予 | 全部 create/update/delete/execute/import/manage/approve/run |
| 数据范围 | project（成员项目内） |
| 用户 | `viewer`（seed 创建，密码由部署 env VIEWER_PASSWORD 或启动日志提供） |

## 2. 交互/校验

- 查看类端点 200；写类端点 403（require_permission 拒绝）。
- 前端菜单按权限下发，viewer 看不到写入口。

## 3. diff 基线口径（batch-18-C8）

- 显著差异类型：missing_in_left / missing_in_right / changed / conflict
- 次级信号（coverage_gap/ambiguous）单独记录，不计入召回/误报

## 4. 设计签核

结论：**通过**。
