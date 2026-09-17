# Batch 249 — QA Report

> **QA (🔍)** | Date: 2026-09-17 | 立场：默认「需要改进」
> 分支：`feature/batch-249-release-console-migration`（base `156adea2`）| worktree：`F:\CamelTv-worktrees\codex-batch-249-release-console-migration`

## 1. 结论

**PASS（可进入一次总确认）**。本批交付「发布控制面强制迁移作业」+「本地 Agent CLI 登录修复」；
控制面全部测试通过、改动文件 lint 干净、`release.ps1` 真实 revision 实测成功。

## 2. 硬门禁证据

| 门禁 | 命令 | 结果 |
|---|---|---|
| 控制面全量测试 | `cd deploy/release-console && pytest tests -q` | **45 passed, 2 subtests passed** |
| 本批新增测试 | `pytest tests/test_migrations.py -q` | 9 passed（revision 校验 4 / 单头解析 3 / 命令构造 2） |
| 改动文件 lint | `ruff check migrations.py tencent_executor.py app.py tests/test_migrations.py tests/conftest.py` | All checks passed |
| 控制面导入冒烟 | `python -c "import app, tencent_executor, migrations"` | imports ok |
| release.ps1 语法 | PowerShell Parser | 语法 OK |
| release.ps1 真实 revision | 实跑首行输出 | `==> Alembic head: 20260922_ai_agent_token` ✅ |
| CLI 登录（S3） | 生产实测 | `login → register → doctor → next → report → import` 全通（导入 2 条用例） |
| 既有测试夹具更新 | `test_console_manifest.py` / `test_capacity_integration.py` | 补真实 revision 后全绿（契约变更导致的用例更新，非掩盖） |

## 3. 缺陷清单

### 🟠 P1-1（本批发现并修复）控制面完全没有迁移执行能力
- **现象**：`deploy/release-console/` 只有"必须校验旧镜像兼容新 schema"的文字约定，manifest 用占位值 `see-verified-head`；
  发布不做任何迁移 → 2026-09-17 出现"代码已上线、库未迁移"（`ai_jobs.model_name` 不存在 → `/api/v1/ai/jobs` 500）。
- **修复**：新增 `migrations.py`（真实 revision 校验 / 单头解析 / 迁移+校验命令）、`validate` fail-closed、
  `deploy()` 在 `_activate` 停止容器前执行迁移、回滚路径不迁移。

### 🟠 P1-2（本批发现并修复）CLI 缺登录 → register/health/import 必然 401
- **修复**：`login` 子命令（JWT）+ 请求头携带 `Authorization` + `doctor` 报告 `jwt_configured`。

### 🟡 P2-1（操作失误，已止损）误触真实发布流程
- **现象**：QA 实测 `Get-AlembicHead` 时直接跑 `release.ps1`（脚本无 dry-run），它开始构建镜像。
- **止损**：约 30 秒内终止；核对 **假 tag 制品 0 个、控制面记录 0 条、生产 ok / v2.3.0**，无副作用。
- **登记条件**：`release.ps1` 应提供 `-DryRun`（只算 manifest/digest，不构建）。

### ⚪ P3-1（范围外，已登记）控制面既有测试目录历史 E402
- `tests/test_capacity.py` 等既有文件 `sys.path.insert` 后 import 触发 E402；属 main 既有债，不在本批范围
  （本批新增文件已用 `conftest.py` 规避）。

## 4. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 6h / 实际约 5h | 0/2/1/1 | 2（S1 合并试探→取消；测试夹具契约更新） | 流程 + 技术债 | 合并前先比对两侧同名文件的行数/内容，判断分支是否已被取代 |
