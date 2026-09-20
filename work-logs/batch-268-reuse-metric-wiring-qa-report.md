# Batch 268 — QA 报告

> **QA (🔍)** | Date: 2026-09-20 | Verdict: **PASS**
> 档位：完整批次（平台行为 + 测量链路变更）

## 可执行门禁

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/test_batch268_reuse_metric_wiring.py tests/test_batch260_reuse_metrics.py tests/test_version_task.py -q` | **75 passed**（本批新增 6 例 + 既有 69 例，无回归） |
| `python -m ruff check app/services/reuse_metrics_service.py app/services/version_task_service.py scripts/drill_three_versions.py --select F` | All checks passed |
| `python -m ruff check app --select F` | 9 errors —— **全部在既有文件**（`requirement_ai.py` 等，属棘轮基线，本批未触碰） |
| `pwsh scripts/git/scan-common-bugs.ps1` | HARD **0** / WARN 344（= 主干基线） |
| `pwsh scripts/git/audit-cconditions.ps1` | hard errors 0 / warnings 0 |
| API 级端到端（本批代码起平台） | 建任务 → `suggested 0→4` → 采纳 → `hit_rate` 可算；修 C268-2 后聚合 **0.625（≤1）** |

## 逐条验证（A1–A5）

### A1 建任务写建议事件 ✅
`test_create_task_records_suggested_events`：预置含 2 个复用条目的知识记录 → 建任务 → 断言 **2** 条 `suggested` 事件、标题正确。API 实测：`suggested 0 → 4`。

### A2 命中率可判定 ✅
`test_hit_rate_measurable_after_decision`：2 建议 + 1 采纳 → `hit_rate == 0.5`、`meets_50pct is True`。API 早期口径 `0.25` 亦照实记录（不美化）。

### A3 无上版知识记录不虚增 ✅
`test_no_previous_knowledge_means_no_suggestion_events`：空项目建任务 → 0 条事件。

### A4 驱动读数与回退 ✅
`test_driver_reads_platform_reuse_stats`：200 → `(6,4)`；500 → `(0,0)`；`httpx.ReadError` → `(0,0)`。

### A5 命中率有界（本批就地发现的第二个缺陷，登记 `C268-2`）✅

```
现象：本地流程跑出 hit_rate 2.5（adopted 10 / suggested 4），随后 1.1875 —— **命中率 > 1**
根因：① record_decision 不校验建议是否被带出过；② reuse_stats 直接按 decision 计数（历史脏数据也进分子）
修复：① record_decision 加守卫（无对应 suggested → APIException 400）；② reuse_stats 只统计**有对应带出事件**的决策
复测：新任务 6/7/8 = suggested 4 / adopted 3 / rejected 1（75%，平衡）
     聚合：suggested 16 / adopted 10 / rejected 3 / **hit_rate 0.625**（≤1）/ meets_50pct true
     守卫前写入的 task 3/4/5（adopted 3 > suggested 1）仍在本地库中，但**已不影响聚合**（生产该表 0 行，无此历史）
```

## 缺陷列表

| # | 严重级 | 描述 | 状态 |
|---|:------:|------|------|
| D1 | **P1** | `record_suggestion` 无调用点 → 命中率恒 0（`C267-3`） | ✅ 本批接线 + 端到端验证 |
| D2 | **P2** | 命中率可 >1（决策无校验 + 聚合不看对应关系）（`C268-2`） | ✅ 本批就地修复 + 历史数据免疫 |
| D3 | P3 | 命中率粒度未定义（记录级 vs 条目级） | ✅ 本批定为**条目粒度**并写入 Design |

## bug-guard「未关闭已知风险」表核对（三问）

**1) 本批是否新增清单中任一项？** 否——新增写入在服务内部，无"用户输入→出网"路径。
**2) 本批是否修复/关闭任一项？** 关闭 `C267-3`；就地修复 `C268-2`。
**3) 新增路径是否过铁律？** 新增一次 DB 写入（无外发、无凭据）；**不吞异常**（避免 S7 静默吞异常复发）。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 4h / ~3h | 0/1/1/1 | 2 | 需求（"定义埋点"被当成"已接线"）+ 设计（比率类指标未做边界校验） | ① 验收"指标可统计"必须问"谁在什么时候写这条埋点"；② 任何比率型指标都要有 `rate ≤ 1` 的断言与"分母来源"校验 |
