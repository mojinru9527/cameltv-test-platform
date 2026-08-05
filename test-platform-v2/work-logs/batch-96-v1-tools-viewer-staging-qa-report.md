# Batch 96 — QA 报告（V1 工具审计 / viewer / staging / diff 基线）

> **QA (🔍)** | Date: 2026-08-05 | Verdict: PASS

## 测试总览

| 项 | 通过 | 失败 | 阻塞 |
|:---|:----:|:----:|:----:|
| viewer 只读角色测试 | 3/3 | 0 | 0 |
| diff 标注基线 | 2/2（召回 1.0/误报 0） | 0 | 0 |
| 凭据生命周期（seed） | 全绿（扩展至 viewer） | 0 | 0 |
| 后端全量 pytest | 1066 passed | 0 | 0 |
| ruff / scan / audit | ✅ / HARD 0 / 0 硬错 | 0 | 0 |

## 可执行门禁（命令 + 退出码）

| # | 门禁 | 命令 | 退出码 | 结果 |
|---|------|------|:------:|------|
| G1 | viewer | `pytest test_viewer_role.py` | 0 | 3 passed（查看 200/建用例 403/建缺陷 403） |
| G2 | diff 基线 | `pytest test_diff_classifier_baseline.py` | 0 | 2 passed；10 组标注/9 显著差异全部命中，FP 0 |
| G3 | seed 凭据 | `pytest test_seed_credentials.py` | 0 | 全绿（admin+tester+viewer 三用户生命周期） |
| G4 | pytest 全量 | `pytest -q` | 0 | 1066 passed, 3 skipped（lanhu 环境项经子模块 init 解决） |
| G5 | ruff F821 / scan / audit | — | 0 | All passed / HARD 0 WARN 209 / 0 硬错 |

## 逐项验证

- **C64-1**：11 个 V1 工具 `rg` 审计——V2 app/frontend/scripts 均无引用（命中为 V2 自身功能词汇）；用户批准废弃记录 + 移除计划落盘（删除走清理批次）。
- **C31-3**：viewer 角色（_VIEWER_MENUS/_VIEWER_ACTIONS 只读集）+ 账号（seed，密码由 env VIEWER_PASSWORD 提供，不打印）；测试：列表 200、写 403。
- **batch-18-C8**：10 组标注对 → 显著差异召回 1.0 / 精度 1.0 / 误报 0（evidence JSON：`work-logs/evidence/batch-96/diff-classifier-baseline.json`）。
- **C64-3**：交付清单 §3 澄清（业务 DB/Redis/MQ = 被测系统地址；测试平台 DB=Supabase PG ✅）。
- **staging/C27**：test 环境登记为 staging 替代 + 本地全栈排期（C96-1）。

## 缺陷与遗留

| # | 级别 | 内容 | 处理 |
|---|:----:|------|------|
| B96-Q1 | P3 | C27-C1~C4 四项验证需数据/性能测量，本批仅登记 staging 替代 | C96-1 排期执行 |
| B96-Q2 | P3 | viewer 账号在部署环境需设置 VIEWER_PASSWORD 方可登录 | 文档化（seed 注释 + QA） |

## 发布建议

状态：**READY**。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 2d / 实际 1d | 0/0/0/2 | 2（凭据测试/打印 WARN） | 契约漂移 | 加种子用户先扩展凭据生命周期测试；打印用 logger 避免 WARN |

**技能使用**：`cameltv-agent-team`、`cameltv-bug-guard`
