# Batch 279（M1 / TA-005）— QA Report

> **部门**：🔍 QA · **日期**：2026-11-10

## 1. 验收结果

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 合法迁移 14 组 | ✅ | `pytest tests/test_aiqe_run_state.py` |
| A2 | 非法迁移 10 组 + 未知/同状态 | ✅ | 同上 |
| A3 | COMPLETED 必须 outcome；终态无 outcome | ✅ | 同上 |
| A4 | 四表/唯一约束/级联删除 | ✅ | `pytest tests/test_aiqe_run_models.py` |
| A5 | NodeRun ↔ ExecutionJob 关联 | ✅ | 同上 |
| A6 | `upgrade head → downgrade -1 → upgrade head` | ✅ | 本地 SQLite 链，退出码 0/0/0 |
| A7 | 全量后端回归 | ✅ | `1376 passed, 43 skipped`（187s） |
| A8 | quality ratchet | ✅ | `increased_keys=0` |

## 2. 环境与命令

```text
ENVIRONMENT=test
DATABASE_URL=sqlite:///./data/b279-full.db
SECRET_KEY=<64 chars>

python -m pytest tests/test_aiqe_run_state.py tests/test_aiqe_run_models.py -q  → 37 passed
python -m pytest -q                                                             → 1376 passed, 43 skipped
python -m alembic upgrade head                                                  → OK
python -m alembic downgrade -1                                                  → OK
python -m alembic upgrade head                                                  → OK
python scripts/ci/quality_ratchet.py                                            → PASS
```

## 3. 迁移兼容性专项

| 场景 | 结果 |
|------|------|
| 全新 SQLite（初始 create_all 预建四表） | ✅ 迁移检测 `run_key` 后跳过 |
| 旧 AITDE 同名表（无 `run_key`） | ✅ 先清理再重建（PG CASCADE / SQLite drop） |
| 生产 PG（四表不存在） | ✅ CREATE 四表 + 索引（待部署验证） |
| downgrade 后 re-upgrade | ✅ 表删除后正常重建 |

## 4. 缺陷记录

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | 迁移报 `table test_runs already exists` | 初始迁移 `Base.metadata.create_all` 预建全量表 | D-279-3 跳过逻辑 + 遗留表清理 |
| 2 | `Upgrading` 时 `RuntimeError`（guard 误判） | guard 未区分“预建”与“遗留” | 改为检测 `run_key` 后 return |
| 3 | ratchet RUF100/UP017/UP037 | 新代码风格 | 已修（`UTC`、去引号、去无用 noqa） |

## 5. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 1.5 人日 / 实际 ≈ 3h |
| 缺陷 | 3（均未流出本批） |
| 返工 | 3（迁移策略 2 次、lint 1 次） |
| 根因分类 | 历史迁移用 create_all 建全量表（隐式 schema 预建） |
| 下次避免 | 新表迁移一律先 inspect：已存在且列匹配则跳过 |

## 6. 判定

A1–A8 全绿，**建议 Leader APPROVED**。生产部署留到 M1 批次合并后统一窗口。
