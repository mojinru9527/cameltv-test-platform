# Batch 156 — PM 计划（P3 打磨项收口）

> **PM (🟨)** | Date: 2026-08-12

**原始需求**: PRD batch-156（P3 剩余 8 项 + 验收登记）  **目标时间**: 本批次（约 4h）

## 开发任务
### [ ] S1: 脚手架（PRD/看板 + C155-1 关闭）
**涉及**: work-logs/batch-156-*、kanbans/DEV-batch-156、C-CONDITIONS.md

### [ ] S2: P3-01 404 路由
- router/index.tsx `*` → NotFound 页；新建 pages/NotFound.tsx（404 + 返回工作台）

### [ ] S3: P3-04 报告时区统一
- report_service generated_at 改本地 naive ISO；核对 test_report 断言

### [ ] S4: P3-08 脑图键盘可达
- mindmap/index.tsx SVG 容器 tabIndex/role/aria + 键盘提示文案

### [ ] S5: P3-10 Playground TODO 显式化
- playground_service 未识别步骤注释改为「未识别步骤」；Playground 页面检测 TODO 显示提示条

### [ ] S6: P3-13 用例搜索提示
- testcase/index.tsx 搜索区在筛选生效时显示提示

### [ ] S7: P3-14 主题实验室统一说明
- router/theme-lab 未启用时显示统一「未开放」说明页

### [ ] S8: 验收登记（P3-02/03/05/06/07/09/11/12/15/16/17/18 + 菜单种子）
- QA 报告逐项登记证据

### [ ] S9: QA 硬门禁 + 证据
- typecheck/build/vitest；后端 ruff/受影响 pytest

## 质量要求
- [x] 无新依赖/无迁移
- [x] 无障碍（aria/键盘）
- [x] React 副作用四律
- [x] 无 console.log 调试残留
