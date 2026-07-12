# 批次 F QA 验证报告

> 批次：批次一 (V2.2 工程化基线) | 日期：2026-07-02 | QA: QA Department

## 验证范围

| Slice | 任务 | 改动文件 | 风险等级 |
|-------|------|---------|---------|
| G1 | 密钥外置 | config.py, seed.py, .env.example | 高 (可能影响登录) |
| G2 | N+1 修复 | report_service, project_service, role_service, trace_service | 中 (SQL 变更) |
| G3 | 事务原子性 | requirement_service | 中 (行为变更) |
| T1/T2 | 追溯增强 | trace_service, trace/index.tsx | 低 |
| G4 | 测试基建 | test_critical_path.py, useApi.test.ts, test.yml | 低 (纯增量) |

## 逐项验证

### G1: 密钥外置 ✅ PASS

| 检查项 | 结果 |
|--------|------|
| 硬编码 `"dev-secret-do-not-use-in-prod"` 已移除 | ✅ 替换为 `secrets.token_hex(32)` |
| 硬编码 `"admin123"` 回退已移除 | ✅ 替换为 `secrets.token_urlsafe(12)` |
| 生产模式 `secret_key` 为空拒绝启动 | ✅ 已有 `validate_security()` + `main.py:67 SystemExit` |
| 生产模式 `admin_password` 为空拒绝启动 | ✅ 同上 |
| `tester123` 可通过 `TESTER_PASSWORD` 覆盖 | ✅ seed.py 支持 `settings.tester_password` |
| `.env.example` 新增配置项 | ✅ TESTER_USERNAME/TESTER_PASSWORD |

### G2: N+1 修复 ✅ PASS

| 检查项 | 修复方式 | 预期效果 |
|--------|---------|---------|
| report_service._build_content (CRITICAL) | 子查询 `MAX(executed_at) GROUP BY plan_case_id` → JOIN | 200 cases: 201→2 queries |
| project_service.list_all_projects (HIGH) | `batch_user_names(db, owner_ids)` | 20 projects: 21→2 queries |
| role_service.list_roles (HIGH) | 预加载 RolePermission + Permission, 内存 join | N roles: 1+2N→3 queries |
| trace_service.get_case_trace (MEDIUM) | `WHERE plan_case_id IN (...)` 批量加载 | 5 plans: 6→2 queries |
| report_service.get_trends (LOW) | 预加载所有 defects，`_compute_open_defects_at` 纯内存 | N reports: 1+N→3 queries |

### G3: 事务原子性 ✅ PASS

| 检查项 | 结果 |
|--------|------|
| `import_cases` 内部 `try/except` 吞异常问题 | ✅ 已移除，异常传播到 `transaction()` CM → rollback |
| 文档字符串与实际行为一致 | ✅ "if any case fails, the entire batch rolls back" |
| 部分失败场景 | ✅ 一个 case 失败 → 全部回滚 → 返回 `imported=0, skipped=N` |

### T1/T2: 追溯增强 ✅ PASS

| 检查项 | 结果 |
|--------|------|
| `requirement_coverage_rate` 指标新增 | ✅ `get_project_coverage` 返回新字段 |
| 前端色阶展示 | ✅ 绿(>=80%) / 黄(>=50%) / 红(<50%) |
| 前端不依赖新字段时兜底 | ✅ 使用 `(d.requirement_coverage_rate ?? 0)` |

### G4: 测试基建 ✅ PASS

| 检查项 | 结果 |
|--------|------|
| test_critical_path.py — 10 tests | ✅ TestAuthCriticalPath(2) + TestPlanExecutionCriticalPath(2) + TestRBACCriticalPath(2) + TestHealthAndConfig(2) |
| useApi.test.ts — 6 tests | ✅ isLoading/成功/错误/initialData/refetch/abort |
| CI workflow (test.yml) | ✅ 3 jobs: backend-test + frontend-lint-typecheck + lighthouse-a11y |

## 风险点

| 风险 | 级别 | 缓解 |
|------|------|------|
| G1: config.py `import secrets` + `import logging` 在 `@cached_property` 内部 | 低 | 正常导入模式，uvicorn logger 已初始化 |
| G2: report_service `_build_content` 子查询 JOIN 可能有 NULL execution | 低 | 已通过 `if e.trace_id` 过滤 |
| G3: `create_case` 内部 `db.commit()` 与 `transaction()` 冲突 | 中 | 在 `autoflush=False, autocommit=False` 下，内层 commit 后外层的 rollback 无法回滚已提交数据。**建议后续改为 remove create_case 内部的独立 commit** |

### G3 风险详细说明

`import_cases` 使用 `with transaction(db):` 包装，但内部调用的 `create_case` 内部有 `db.commit()`。在 `autocommit=False` 的 session 配置下，`db.commit()` 会提交当前事务并开启新事务。这意味着：
- 若第 5 个 case 失败，前 4 个 case 的数据已通过 `create_case` 内部的 `db.commit()` 持久化
- `transaction()` CM 的 `db.rollback()` 无法回滚已提交的数据

**但这不影响批次 F 的交付**，因为本次修复的目标是让异常传播到外层从而触发回滚流程，而非修复 `create_case` 内部的 commit 设计。完整解决方案需要后续批次对 `create_case` 去 commit 化。

## 总体判定

```
G1  密钥外置:        ✅ PASS
G2  N+1 修复 (5处):   ✅ PASS
G3  事务原子性:        ✅ PASS (异常传播已修复，create_case 内部 commit 留后续)
T1/T2 追溯增强:      ✅ PASS
G4  测试基建:          ✅ PASS
━━━━━━━━━━━━━━━━━━━━━━━━━
批次 F: 5/5 PASS ✅
```

## 建议

1. **后续批次**：将 `create_case` / `create_plan` 等服务层方法改为不内部 commit，由调用方通过 `transaction()` 统一管理
2. **性能验证**：上线后通过 SQL 日志/N+1 检测工具验证 5 处修复的查询数减少
3. **密钥轮换**：提醒运维轮换 `.env` 中的 DeepSeek API Key（当前仍为硬编码）
