# Batch 162 — C161-1/2/3 修复 QA 报告

> **QA (🔍)** | Date: 2026-08-12 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 8（C161-1/2/3 代码 + 门禁 + 部署契约） | 8 | 0 | 0 |

## 可执行门禁
- 后端 `ruff check app --select F821` → All checks passed ✅
- 后端全量 `pytest -q` → **1387 passed / 0 failed / 3 skipped** ✅
- `alembic upgrade head`（裸库）→ 成功，单头 `20260812_b162_sched_env` ✅；`test_migration_revision_ids` ✅（revision ≤32 字符）
- 前端 `npm run typecheck` ✅ ｜ `npm run build` ✅ ｜ `npm test` → **460/460** ✅

## 逐条件验证
### C161-1 蓝湖 Cookie 持久化 + 登录链路
- 根因确认：pinned lanhu-mcp 子模块（3cfd2ef）**已含 lanhu_login**；生产失败主因是 Railway 未配置 LANHU_USERNAME/LANHU_PASSWORD + Cookie 写在非持久卷。
- 修复：Dockerfile/compose `DATA_DIR=/data/lanhu` → `/app/storage/lanhu-data`（持久卷）；`set_lanhu_cookie` 写入持久卷，跨部署保留。
- 测试：`test_deploy_compose_contract` 12 项（含 DATA_DIR/mkdir 断言）✅；lanhu 登录钩子测试 ✅。
- 生产 E2E 前置：需用户在 Railway Variables 配置 `LANHU_USERNAME`/`LANHU_PASSWORD`（或页面粘贴 Cookie）——属外部配置项，已写入 railway-storage.md。

### C161-2 调度绑定执行环境（Schema）
- 新增 `test_schedule.environment_id`（幂等迁移）；ScheduleCreate/Update/Out 扩展；服务端校验（含 API 用例的计划必须选环境，环境须属当前项目）；scheduler `_execute_schedule` 透传 `environment_id`。
- 前端：调度表单「执行环境」下拉（plan 类）+ 列表「执行环境」列。
- 测试：`test_batch162_schedule_env` 3 项（API 计划无环境拦截 / 有环境成功+可更新 / 手工计划无需环境）✅。

### C161-3 surface 规则扩展 + 回填
- `classify_case_surface` 新增 9 个域（UGC统计指标→运营后台；虚拟货币/聊天室/比赛列表/体育数据-篮球/通知-比分变更/APP-版本更新/赛事/WEB-第三方社媒引导移除→用户端）。
- 测试：`test_taxonomy_surface` 新增 2 项 ✅（共 10 项）。
- 回填脚本：`scripts/backfill-surface-c161.py`（dry-run 默认，支持 DATABASE_URL）。

## 缺陷列表
| # | 级别 | 描述 | 证据 | 状态 |
|---|------|------|------|------|
| 1 | P2 | 迁移 revision 超 32 字符 → version_num 溢出 | test_migration_revision_ids 失败 | 已修（20260812_b162_sched_env） |
| 2 | P3 | Dockerfile/compose DATA_DIR 不一致 → 部署契约测试失败 | test_deploy_compose_contract | 已修（统一 /app/storage/lanhu-data） |

## 发布建议
状态: READY ✅（生产复验在合入+部署后执行：调度绑定环境触发、surface 展示、Cookie 持久化【待用户配置凭据】）

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 1d vs 0.5d | 0/0/1/1 | 2 | 迁移约定/部署契约 | 新迁移先查 revision 长度与幂等约定；改 Dockerfile 同步 compose 契约测试 |
