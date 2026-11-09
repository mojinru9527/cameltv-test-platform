# Batch 278 — AIQE TA-001 代码基线审计：Dev 执行计划与记录

> **部门**：🟩 Dev
> **日期**：2026-11-09
> **基线**：`origin/main @ 0af75a821`（batch-276 合入后）
> **实际耗时**：≈ 1.5h（计划 5 人日，靠脚本化盘点压缩）

---

## 1. 审计方法（可复核）

| 步骤 | 工具 | 输出 | 复现命令 |
|------|------|------|---------|
| S1 模型盘点 | Python `ast`（**不导入 ORM**） | 43 文件 / 73 表 / 每表列清单 | `python ta001_models.py <repo> out.json` |
| S2 路由盘点 | 导入 `app.main` + `app.openapi()` | 265 paths / 323 operations | 见 §2 |
| S3 前端盘点 | 目录 + `router/index.tsx` | 19 域 / 153 页面 / 30 路由 | `Get-ChildItem frontend/src/pages -Recurse` |
| S4 服务/接入点 | `Test-Path` + 关键函数 grep | 8/8 接入点存在 | 见 §2 |
| S5 表对账生成 | Python（解析 13 号 §4 表格 + 模型 JSON） | 25 节 × 5 要素 | `python ta001_baseline_tables.py` |
| S6 手工裁决 | 读实现（version_task_service / execution_job_service / cameltv_node） | C-01..C-10 + D-278-1..3 | — |

**为什么用 AST 而不是导入 ORM**：避免 `app.models` 导入触发 `Base.metadata` 建表、环境变量与 DB 连接副作用；AST 只读源码，结果可复现。

**为什么路由要导入 `app.main`**：FastAPI 0.139 的 `include_router` 是懒加载（`_IncludedRouter`），静态 grep 会漏掉前缀与自动生成路径；`app.openapi()` 才是运行期真实路由。

---

## 2. 关键脚本与命令

### 2.1 模型盘点（AST）

```python
# 核心：ClassDef(base=Base) → __tablename__ → AnnAssign(mapped_column)
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and any(b.endswith("Base") for b in node.bases):
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign):
                yield node.name, stmt.target.id, ast.unparse(stmt.annotation)
```

结果：`files=43 classes=73 with_table=73`，主键分布 `Mapped[int]×72 / Mapped[str]×1`（`ai_task`）。

### 2.2 路由盘点

```powershell
$env:DATABASE_URL='sqlite:///./data/ta001-audit.db'; $env:ENVIRONMENT='test'
python -c "from app.main import app; s=app.openapi(); print(len(s['paths']))"   # 265
```

结果：`paths 265 / operations 323 / aiqe 前缀 0`。

### 2.3 表对账生成

解析 13 号 §4 的 "| 字段 | 类型 | 说明 |" 表（含 4.11/4.16/4.19 多表拆分），与模型 JSON 做**字段名级 diff**，产出 §5 的 25 节。

统计：`targets 25 / fields 315 / est_lines 2090`；处置分布 `new 20 / new+compat 2 / alter 3`。

### 2.4 接入点存在性

```powershell
foreach ($p in @('app/services/ai_client.py','app/services/ai_config_service.py',
  'app/services/ai_service.py','app/services/requirement_service.py',
  'app/services/openapi_import_service.py','app/services/playwright_executor.py',
  'app/services/evidence_bundle_service.py','app/services/defect_service.py',
  'app/modules/campaign_execution/contracts.py')) { "{0} {1}" -f $p,(Test-Path $p) }
```

结果：9 个路径（含 `ai_service` 单独计）全部 `True`；`_load_skill_context_for` 在 `ai_service.py:61`。

---

## 3. 实现细节与偏差

| 项 | 计划 | 实际 | 偏差说明 |
|----|------|------|---------|
| 表数口径 | "43 张真实表" | **73 张**（43 文件） | 文件数被当成表数；已在 baseline §2/C-10 修正 |
| ID 类型 | 规格假设 UUID | **INT×72 / str×1** | 基线提出 C-01，建议新建 UUID + 旧 FK BIGINT |
| 时间 | 规格 timestamptz | **naive UTC** | C-02，跟随现有 `task_queue.utcnow` 口径 |
| JSON | 规格 JSONB | **TEXT（`Mapped[str]`）** | C-03，新表用 `sa.JSON`，旧表不迁 |
| 执行链 | 规格假设 VersionTask→ExecutionJob→Node→Runner→Artifact | 三条**并存**链（同步循环 / 节点 / uitest subprocess） | C-04 + §10，Run 是新事实层不是改名 |
| 服务文件数 | "60+" | **71 顶层 / 123 递归** | §6 数量修正 |
| 路由数 | "20+ endpoint" | **265 paths / 323 ops** | §7 量化；30 个规格端点里 29 个净新增 |

---

## 4. 已交付

| 文件 | 内容 |
|------|------|
| `docs/aiqe/baseline.md` | 14 节 / 860 行 / 12 张表 / 25 表对账 |
| 本批六件工件 + 看板 | PRD / PM / Design / Dev / QA / Leader / 看板 |

---

## 5. DoD 自检

- [x] 25/25 表有"现有/目标/差异/策略/预估"；
- [x] 8/8 接入点有存在性与结论；
- [x] 30/30 端点有归属；
- [x] 前端 / Driver / Node 有对账；
- [x] 3 条执行链时序 + 状态/心跳/取消/错误路径；
- [x] 不冲突项打钩（§12）；
- [x] 表格 / 锚点 / 链接校验 0 问题；
- [ ] 用户阅读确认（D-278-1..3）。
