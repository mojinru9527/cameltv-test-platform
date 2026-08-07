# Batch 116 — Design Spec（AI 生成链路加固 + 平台采集）

> **Design (🎨)** | Date: 2026-08-07 | Status: 就绪

## 1. C102-1 异步生成

- 后台任务：`BackgroundTasks` 不够（请求结束即杀）→ 用线程池（`ThreadPoolExecutor`）+ 进程内任务表
  （`{task_id: {status, progress, result, error}}`）+ `GET /requirements/generate/status/{task_id}` 轮询。
- 前端：生成按钮改为创建任务 → 轮询状态（2s/次）→ 完成刷新。
- 大文档分块逻辑复用现有 `_split_extraction_chunks`（不重复实现）。

## 2. C103-6 截断补全 + 缺口报告

- `_run_chunk` 已做 truncated retry；补全：retry 上限内对截断块再请求（复用现有 retry 分支）；
- 缺口报告：生成完成后输出 `coverage_report`（功能点 vs 生成的用例数矩阵，缺口>0 列清单）。

## 3. C115-3 平台采集

- `POST /uitest/capture`：body={pages:[...], env_id} → 后台线程跑 capture-page-xhr 逻辑 → 样本 JSON 存
  `backend/storage/xhr-capture/{id}.json`；`GET /uitest/capture/{id}` 返回样本数/文件/预览。
- 复用 B112-4 只读口径；仅记录元数据，不执行写操作。

## 4. 设计签核

结论：通过（无 P0/P1 阻断）。