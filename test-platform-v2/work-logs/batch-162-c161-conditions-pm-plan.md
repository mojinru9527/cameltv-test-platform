# Batch 162 — PM Plan

> **PM (🟨)** | Date: 2026-08-12

## 规格摘要
**原始需求**: PRD §1（C161-1/2/3）  **目标时间**: 1 天

## 开发任务
### [ ] T1: C161-1 蓝湖 Cookie 持久化 + 配置文档
**描述**: Dockerfile DATA_DIR 改到 /app/storage 持久卷；lanhu_provider 读取路径不变（DATA_DIR 生效）；文档登记 Railway 变量。
**验收**: 容器内 set_lanhu_cookie 写入 /app/storage/lanhu-data/lanhu_cookie.txt；redeploy 后 get_lanhu_cookie 仍可读。
**涉及文件**: test-platform-v2/backend/Dockerfile、docs/ops/railway-storage.md、docs/测试平台全功能验收文档-环境链接与账号汇总.md

### [ ] T2: C161-2 调度环境绑定（Schema）
**描述**: test_schedule.environment_id + 迁移 + schemas + service 校验/透传 + scheduler 传环境 + 前端表单/列表。
**验收**: 含 API 计划未选环境创建/编辑被拦；触发时 execute_all_cases(environment_id)；前端可选环境。
**涉及文件**: backend/models/test_schedule.py、alembic/versions/新增迁移、schemas/test_schedule.py、services/schedule_service.py、core/scheduler.py、api/v1/schedule.py、frontend/pages/schedule/index.tsx

### [ ] T3: C161-3 surface 规则扩展 + 回填
**描述**: classify_case_surface 增加 9 个域；单测；回填脚本 scripts/backfill-surface-c161.py。
**验收**: 新域分类正确；单测通过；脚本可将存量 79 条回填为正确 surface。
**涉及文件**: backend/services/test_case_taxonomy.py、tests/test_taxonomy_surface.py、scripts/backfill-surface-c161.py

## 质量要求
- [ ] Alembic 迁移单头 + 离线校验  - [ ] 后端全量 pytest  - [ ] 前端 typecheck/build/vitest  - [ ] ruff F821
