## 概述

P1 安全加固 PRD（8 项）剩余缺口补全。经全面代码审查，P1-1/2/3/6 已 100% 完成，本 PR 补全 P1-4/5a/5b/8 共 4 处。

### P1-4: test_plan.py fire-and-forget → BackgroundTasks
- `execute_case` 中的 `asyncio.create_task(notify(db, ...))` 改为 `background_tasks.add_task(_run_notify_in_new_session, ...)`
- 新增 `_run_notify_in_new_session` helper（独立 DB session，异常静默日志）
- **修复:** 裸 task 丢失 / DB session 关闭后访问

### P1-5a: dataset.py Content-Length 前置检查
- `upload_dataset` 在 `file.file.read()` 前加 `Content-Length` header 检查 (max 10MB)
- 超过限制返回 413（与其他上传端点一致）

### P1-5b: defect.py 简化附件读取
- 移除冗余 temp file 中转（写入磁盘→读回内存→再写磁盘）
- 已有 Content-Length 50MB 前置检查保障 OOM 防护

### P1-8: environment 页面三态统一
- 改用 `useApi` hook 替代手动 `useEffect + useState`
- 环境列表用 `AsyncState` 统一 loading/error/empty
- 变量空态用 `EmptyState` 组件

### 验证
- 后端: 157/157 passed（6 个 M2 失败为预存 fastembed 缺失）
- 前端: environment 页面 tsc 通过
