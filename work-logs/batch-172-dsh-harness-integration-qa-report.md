# Batch 172 — QA 报告
> **QA (🔍)** | Date: 2026-08-14 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 22 | 22 | 0 | 0 |

## 可执行门禁（命令 + 退出码 + 日志摘要）
| 门禁 | 命令 | 退出码 | 结果 |
|------|------|:------:|------|
| 后端 F821 | `.venv\Scripts\python.exe -m ruff check app/ --select F821` | 0 | All checks passed |
| 后端全量 | `.venv\Scripts\python.exe -m pytest -q` | 0 | **1459 passed, 3 skipped, 0 failed**（含既有 6 失败基线修复：lanhu 子模块初始化 + agent types 契约同步） |
| 前端 typecheck | `npm run typecheck` | 0 | tsc -b 通过 |
| 前端 build | `npm run build` | 0 | ✓ built in 8.94s |
| 前端全量 | `npm test` | 0 | **114 files / 460 tests passed** |
| Alembic 单头 | `alembic heads` | 0 | 单 head：20260814_b172_dsh_task |
| 迁移验证 | 临时库 `alembic upgrade head` | 0 | dsh_task 表 + 索引创建成功 |
| 调试残留 | 新文件 grep console.log/print/breakpoint/debugger | — | 无匹配 |
| 真实链路 | `dsh_runner` node runtime 真实调用 DeepSeek | 0 | Slice1 冒烟 + C 模块真实 E2E（见下） |

## 逐条件验证

### C-A1: 用例生成 harness 模式（可选开关）
- 单测 `test_ai_harness_mode.py` 4/4：关闭保持直连行为 / 开启走 runner / runner 失败降级直连 / 输出非 JSON 降级直连。
- 默认 `DSH_ENABLED=false` 行为与现状一致（`_call_ai_api` 路径未改）。
- ✅ PASS

### C-A2: 异步链路透传
- `ai_tasks._run_generate` 调用 `generate_test_cases(use_harness=None)` → 跟随全局 `DSH_ENABLED`；既有 `test_ai_tasks.py` 全绿。
- ✅ PASS

### C-B1: Agent 工作台执行型 Agent
- `AGENT_META.dsh_execution` 注册；`GET /agents/types` 返回且 `available` 随 `runtime_available()`（单测断言 dsh_execution 不可用时 reason=「DSH 服务未启用」）。
- orchestrator 分发单测 `test_agent_dsh_execution.py` 4/4：成功建 AiArtifact / 失败留痕 / 不可用快速失败 / 空任务拒绝。
- ✅ PASS

### C-B2: 前端入口
- `pages/agent-workbench/index.tsx` 补 dsh_execution 图标/颜色/描述；typecheck+build 通过。
- ✅ PASS

### C-C1: DSH 任务模块 API
- 单测 `test_dsh_tasks.py` 8/8：submit/claim/execute 成功与失败 / cancel 仅 pending / 项目隔离 / health / 404 envelope / 503 不可用。
- 静态路径 `/health` 先于 `/{id}` 注册（避坑规则）。
- ✅ PASS

### C-C2: 前端页面 + 菜单
- `pages/dsh-tasks/index.tsx` 四态（Loading/Empty/Error/未启用503）+ 状态徽标中文映射 + running 轮询（3s，cleanup 齐全）+ 详情 Sheet；`menu:dsh_tasks` seed + MainLayout 图标映射；typecheck+build 通过。
- ✅ PASS

### C-R1: 真实链路证据（C 模块）
- 脚本驱动真实 SQLite + 真实 `dsh_runner`（node runtime + 真实 DeepSeek Key）提交→认领→执行：**status=success**，输出/会话目录落库。
- 证据：`work-logs/evidence/batch-172/dsh-task-real-e2e.json`
- ✅ PASS

### C-R2: dsh_runner 真实冒烟（Slice 1）
- node runtime 真实调用读取工作区并返回结构化结果（exit 0）。
- ✅ PASS

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P2 | `dsh_runner._run_python_sdk` 通过改 `os.environ` 传凭据，多线程并发时可能互相覆盖；生产启用 python-sdk 前需加锁或改为显式传参 | dsh_runner.py `_run_python_sdk` | 建议 → Leader 登记 C172-2 |
| 2 | P3 | `claim_next_task` 对卡在 running 的任务无 watchdog 回收（与 ai_tasks 现状一致）；进程崩溃会留 running | dsh_task_service.py | 建议后续批次 |
| 3 | P3 | `alembic check` 对本地 dev 库报「Target database is not up to date」：dev 库由 auto_create_tables 建表、alembic_version 落后属预期，迁移本身在临时库已验证 | alembic check | 环境说明，不阻断 |
| 4 | P3 | 真实 E2E 仅覆盖 C 模块；B 的 orchestrator 真实执行与 A 的 harness 真实生成未做（成本控制，逻辑由单测覆盖） | — | 建议后续批次补真实回归 |

## 发布建议
状态: **READY**
必修复: 0
建议修复: 4（均为 P2/P3，不阻断合入；P2-1 由 Leader 登记 C 条件）

## 复盘卡（Batch 75 起强制）
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 16h / 实际 ~10h | 0/0/1/3 | 2 | ① 后台 worker 线程在单测中抢任务（测试隔离不足）② _parse_ai_response 返回 None 未捕获（对既有函数行为假设不足） | 新增带全局 worker 的服务时，测试 fixture 一律打桩 ensure_worker_running；复用既有解析函数先读其异常语义 |

**技能使用**: `cameltv-bug-guard` → 后端 envelope 404 / StaticPool 测试 / 路由静态段先行；`cameltv-ui-conventions` → 状态徽标中文映射 / 四态 / JSON 格式化 / useEffect cleanup；`test-case-design` → A 的输出规范对齐（tests/test-case-standards 通过 ai_service 既有 prompt 复用）。
