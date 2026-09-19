# Batch 266 — QA 报告

> **QA (🔍)** | Date: 2026-09-19 | Verdict: **PASS（链路）／如实登记样本质量缺口**
> 档位：完整批次（执行链路变更）

## 可执行门禁

| 命令 | 结果 |
|------|------|
| `python -m pytest tests/test_batch266_executor_payload_and_isolation.py tests/test_batch258_node_cli.py tests/test_batch258_execution_job_protocol.py -q` | **54 passed**（新增 8 例 + 既有 46 例，无回归） |
| `python -m ruff check app --select F821` | All checks passed |
| `pwsh scripts/git/scan-common-bugs.ps1` | HARD **0** / WARN 344（= 主干基线） |
| `pwsh scripts/git/audit-cconditions.ps1` | hard errors 0 / warnings 0 |

## A1 断言修复 ✅

```
节点新增支持：status_code + operator(eq/gte/gt/lte/lt) · json_path/jsonpath（expected=null=存在性）· response_time(≤ms)
未知类型/算子：仍然失败（fail-loud，不静默放过）——由 3 例测试守护
```

## A2 Web 用例隔离 ✅

```
test_web_cases_get_fresh_context_per_case：3 条用例 → 工厂被调用 3 次（每条独立上下文）
单步/单用例异常：收敛为该用例失败（error 字段），不再让 job 崩掉（实跑中曾因超时崩过节点）
expect_visible：改为任一匹配可见；对无 locator 的替身回退旧语义（既有测试不受影响）
```

## A3 驱动 payload ✅

```
_load_executable_cases：api→{method,url,headers,body,assertions}；web→steps[{action,...}]
缺 api_endpoint 或缺 steps[].action → SystemExit 并列出用例（不再空跑）
```

## A4 真实 Test5 实跑（job 21 / 22，1 个版本）✅（链路）／⚠️（样本）

```
[version 16.1] jobs=[21, 22] evidence_complete=True        ← 证据完整性 100%
API job 21：passed 5 / failed 45 / total 50
Web job 22：passed 28 / failed 30-28 = 2 / total 30        ← 逐用例独立 Chromium；截图不再相同

API 失败归因（逐断言统计）：
  59× jsonpath expected=None actual=None   ← 自动生成的"正向"用例假定空 body 也能成功，
                                             真实接口缺参数返回业务错误 → $.data.* 不存在
   4× status_code / response_time actual=None ← 这些 POST 端点请求直接失败（同一根因）
Web 失败归因：case 601/602「打开比赛详情页」——Batch 264 采集的 match 详情链接已失效（站点数据变化）
```

**判定**：**执行链路修复达标**（真实 URL、真实断言、逐用例隔离、失败不再被伪造成通过、证据完整）；
剩余差异是**样本质量**（真实参数缺失、详情页链接时效），不属执行链路缺陷 → 登记 `C266-1` / `C266-2`。

## 缺陷列表

| # | 严重级 | 描述 | 状态 |
|---|:------:|------|------|
| D1 | **P1** | 驱动 payload 不含可执行定义（C264-3） | ✅ 本批修复（缺定义即失败） |
| D2 | **P1** | 节点断言不支持 `status_code+operator` / `jsonpath` / `response_time` | ✅ 本批修复 + 测试 |
| D3 | **P1** | Web 用例共享上下文导致状态串味（C264-4） | ✅ 本批修复（逐用例隔离） |
| D4 | P2 | 单条用例异常会让整个节点崩溃 | ✅ 本批修复（异常收敛） |
| D5 | **P1** | 试点 API 用例缺真实参数（自动生成）→ 45/50 失败 | ⏳ 登记 `C266-1` |
| D6 | P2 | 用例内写死的比赛详情链接会失效 | ⏳ 登记 `C266-2` |

## bug-guard「未关闭已知风险」表核对（三问）

**1) 本批是否新增清单中任一项？** 否——改动集中在节点执行器与 QA 驱动。
**2) 本批是否修复/关闭任一项？** 关闭 `C264-3`（payload）与 `C264-4`（隔离/可见性语义）。
**3) 新增路径是否过铁律？** 驱动新增"从库取用例定义"的读取路径（只读、无网络外发）；仍不落任何被测系统凭据。

## 复盘卡

## 追加：3 版本实跑结果（Batch 266 收尾）

```
[version 16.1] jobs=[23,24] evidence_complete=True   API 5/50 ｜ Web 29/30
[version 16.2] jobs=[25,26] evidence_complete=True   API 5/50 ｜ Web 26/30
[version 16.3] jobs=[27,28] evidence_complete=True   API 5/50 ｜ Web 21/30
SLO：plan_within_2h ✓ · execution_within_3h ✓（0.141/0.274/…）· evidence_complete ✓ · reuse_hit_rate ✗(null)
     meets_all=false（唯一缺口是复用命中率，属 C265-1）
```

**新增发现（登记 `C266-4`）**：Web 用例通过数逐版下降（29→26→21），失败集中在**首页标签可见性**断言（News/BBall/Scores/Fixtures/主标题）——目标页动态渲染，标签出现时机不稳定；这与"上下文隔离"无关（已修），属用例稳定性问题。证据：`evidence/batch-266/three-version-run-20260919.json`

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 5h / ~4h | 0/4/2/0 | 3 | 需求（断言语义未与生成器对齐）+ 环境（本机 OOM、僵尸任务） | 动执行链路前先跑一遍"真实 payload"冒烟；本机跑逐用例浏览器前先释放 Docker 内存；清理僵尸任务再启动新轮次 |
