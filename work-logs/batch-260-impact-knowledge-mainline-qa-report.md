# Batch 260 — QA 报告

> **QA (🔍)** | Date: 2026-09-19 | Verdict: **PASS（附 1 条 C 条件）**
> 批次档位：完整批次（六件）。范围：`docs/platform-refactor/10-...backlog.md` §2 的 B3-1…B3-5。

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 5（B3-1…B3-5） | 5 | 0 | 0（1 条度量项转 C 条件，未伪造成通过） |

## 可执行门禁（命令 / 退出码 / 摘要）

### 后端

| 命令 | 退出码 | 摘要 |
|------|:------:|------|
| `python -m ruff check app/ --select F821` | 0 | All checks passed! |
| `python -c "import app.main"` | 0 | import OK |
| `python -m alembic heads` | 0 | `20260926_batch260_reuse_suggestion_events (head)` —— 单头 |
| 迁移演练（独立临时 SQLite） | 0 | `impact_edge` from-base upgrade（9 列）/ downgrade 落表 / 再 upgrade；`reuse_suggestion_event` 同法验证 |
| `python scripts/ci/quality_ratchet.py` | 0 | **QUALITY_RATCHET=PASS**（ruff/mypy increased_keys 均为 0） |
| `pytest`（B3 四个测试文件 + 迁移/路由守卫） | 0 | 见下方分项 |
| **`pytest -q`（全量，与 CI 后端 required 同命令）** | 0 | **2885 passed, 52 skipped, 1 xfailed, 0 failed**（12:13） |

### 前端

| 命令 | 退出码 | 摘要 |
|------|:------:|------|
| `npm ci` | 0 | 850 packages（无新增依赖） |
| `npm run typecheck` | 0 | `tsc -b` 无错误 |
| `npm run lint` | 0 | `eslint . --max-warnings=0` 无告警 |
| `npx vitest run --maxWorkers=2` | 0 | **167 文件 / 732 例全绿** |
| `npm run build` | 0 | `✓ built in 8.71s` |

> 本机全量 vitest 直接跑会 JS heap OOM（B2 QA 报告 D4 已记录），故沿用 `--maxWorkers=2`。
> 这是环境限制，不是代码问题；CI runner 内存更大。

## 全量结果

```
python -m pytest -q -p no:cacheprovider
→ 2885 passed, 52 skipped, 1 xfailed, 0 failed in 733.70s (12:13)   exit 0
```

比 B2 的 2839 例多 46 例（本批新增 46 条回归：B3-1 13 + B3-2 9 + B3-3 13 + B3-4 11）。
本批也顺带验证了 B2 落地的 `conftest.py` `NO_PROXY` 修复在后续批次持续生效（无回环代理导致的假失败）。

## 逐条件验证

### B3-1: ImpactEdge 模型 + 迁移 ✅ PASS
**变更**: `app/models/impact_edge.py`、`app/models/__init__.py`、`alembic/versions/20260925_*`、`impact_graph_service.upsert_edge`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 迁移单头 / 可逆 | ✅ | from-base 建表 9 列；downgrade 落表；再 upgrade |
| kind ∈ {changed,covers,depends} | ✅ | 非法 kind 与空 ref 均被拒 |
| 幂等 upsert | ✅ | 同键更新而非重复；`(project,source,target,kind,version)` 唯一约束兜底（绕过服务直插 ORM 也会被 DB 挡住） |
| 与 InteractionEdge 分工 | ✅ | 模块/类 docstring 写明"交互拓扑 vs 影响图"，并有断言守着 |

### B3-2: 关联构建（需求变更 → 模块 → 用例） ✅ PASS（真实数据度量 → C260-1）
**变更**: `impact_graph_service.build_edges/module_coverage`、`scripts/backfill_impact_edges.py`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 三类边来源正确 | ✅ | changed ← `RequirementModule.change_type`（new/modified）；depends ← `parent_module_id`；covers ← `TestCase.requirement_module_id`（优先）或 module 名称回退 |
| 重复构建幂等 | ✅ | 二次构建 `created=0/updated=2`，总行数不变（否则图会随执行次数膨胀、覆盖率失真） |
| 覆盖率口径 | ✅ | 合成数据 10 模块覆盖 9 → `coverage_rate == 0.9` 且 `>= 0.9`（含恰好 90% 边界）；空包返回 0 不除零 |
| 回填脚本可用 | ✅ | 库未迁移时给出可读提示而非堆栈（首次冒烟抛 SQLAlchemy 堆栈，已修） |
| **真实体育资产上的 ≥90%** | ❌ | 本机 worktree 库是空的、无体育资产 → **C260-1**，不拿合成数据冒充 |

### B3-3: 「改了 X 要跑哪些」+ 未覆盖缺口 ✅ PASS
**变更**: `impact_query_service.py`、`app/api/v1/impact.py`、router、seed 权限点
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 一次查询给出四段结论 | ✅ | 受影响模块（含 depends 上游：改"赛事"带出"直播"）→ 用例分组（功能/接口/UI）→ 最近执行 → 缺口 |
| 每条结论可点回 | ✅ | 每条带 `case:` / `plan:` / `module:` 引用（前端渲染为链接） |
| **查询次数不随规模增长** | ✅ | SQL 计数断言：用例 3→33、模块 1→26，查询条数**完全不变**（Design P3-2 承诺落地为可执行校验） |
| 最近执行取"更近的一次" | ✅ | 两条 plan_case（2 天前 fail / 1 天前 pass）→ 取 pass |
| 无数据不伪装 | ✅ | 版本不存在返回可读 `reason` 而非空对象 |
| 权限点独立 | ✅ | `impact:view`（tester 默认）/ `impact:manage`（管理员），不复用 `uitest:*` |

### B3-4: 复用建议命中率 ✅ PASS
**变更**: `reuse_suggestion_event` 模型 + 迁移、`reuse_metrics_service.py`、`version_task.py` 两个端点
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 埋点可统计 | ✅ | suggested/adopted/rejected → hit_rate；4 建议 2 采纳 = 0.5（含 50% 边界） |
| 重复点击不撑大分母 | ✅ | 唯一约束 + 幂等；3 次记录只 1 行 |
| 无数据不误判 | ✅ | `suggested=0 → meets_50pct=None`（既不说达标也不说未达标） |
| 低于阈值如实上报 | ✅ | 0.25 → `meets_50pct=False` |
| **既有契约不变** | ✅ | `get_reuse_suggestions` 签名与 `GET knowledge/reuse` 返回原样（断言守住）——B12 与前端依赖它 |

### B3-5: 知识中心只读视图收敛 ✅ PASS
**变更**: `pages/knowledge/index.tsx`、`components/ImpactTab.tsx`、`api/impact.ts`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| tester 页签 ≤3 | ✅ | 恰好 3：影响面/项目知识/检索；`NORMAL_TAB_LIMIT=3` + 断言防回涨 |
| 代码与自身注释一致 | ✅ | 原 docblock 写 3、代码实为 5（漂移）；现已一致 |
| 影响面前端视图（B3-3 交付物） | ✅ | 输入模块 → 四段结论；每条带可点回引用；四态完整 |
| 空态/无执行记录不误导 | ✅ | 空态给原因；无执行记录写明"还没有执行记录"，不显示为通过 |
| 管理页签仍可达 | ✅ | 平台研发/版本记录/复用建议/概览/知识源/AI 审核台/图谱/实体/迭代/Wiki/差异/Skills 对维护者仍可见 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| D1 | P3 | 回填脚本在库未迁移时抛 SQLAlchemy 堆栈而非可读结论（脚本的用途就是给人看结论） | 首次冒烟输出 | ✅ 已修（输出"请先 alembic upgrade head"） |
| D2 | P3 | `module_names` 局部变量未使用（F841，我自己引入） | `ruff --select F,E9` | ✅ 已删 |
| D3 | P3 | mypy `assignment`：跨两个循环复用同一变量名 `plan_case`，导致 `dict.get()` 的 Optional 返回值与已推断类型冲突 | ratchet 报 `impact_query_service.py:131` | ✅ 改用 `latest_plan_case` 并注释原因 |
| D4 | P3 | 全量 vitest 在本机 JS heap OOM（环境限制，非代码问题） | `FATAL ERROR: JavaScript heap out of memory` | ✅ `--maxWorkers=2` 复跑全绿（沿用 B2 记录解法） |

无未修复缺陷。D3 说明一点：我第一版按"猜"加了类型标注但没修掉（错误在另一行），**直接对文件跑 mypy 拿到行号**才定位准——比继续猜快。

## bug-guard「未关闭已知风险」表核对（每批必答三问）

**1) 本批是否新增了清单中的任一项？** 否。
- 本批以「读既有数据 + 写新边表/事件表」为主，未新增"用户输入 → 出网/落盘/执行代码"路径。
- 新表写入均走服务层校验（kind/decision/ref 合法性），并有 DB 唯一约束兜底。

**2) 本批是否修复/关闭了其中任一项？** 本批清单内无对应项（S1–S6 已在 B1/B2 处理完）。
- **但避免了一次"复发"**：B3-4 若按 backlog 字面从零实现复用建议，会立刻形成第二份实现——正是 S1（守卫两份）/S5（密钥两套）的同一失败模式。开工前侦察发现 B11/B12 已存在，遂改为**只补埋点**，并在 PRD §3 写成非目标。

**3) 本批新增的「外部输入 → 出网 / 落盘 / 执行代码」路径，是否都过了对应铁律？** 是（且本批基本没有此类新路径）：
| 路径 | 铁律 | 校验 |
|------|------|------|
| `POST /impact/rebuild` 触发的关联构建 | 写库必须幂等、不得因重复执行膨胀 | 唯一约束 + 幂等断言 + dry_run 不写库 |
| 复用建议决策埋点 | 重复写不得改变事实 | 唯一约束 + 幂等断言 |
| 影响面查询（只读） | 不得 N+1 | SQL 计数断言（规模增长查询数不变） |
| 控制面职责边界 | 不跑浏览器/不跑模型/不存被测凭据 | 本批**零新增**执行或推理路径（纯登记·聚合·检索） |

## CI 分层核对

本 PR 改动 `test-platform-v2/backend/**` + `test-platform-v2/frontend/**` + `work-logs/**` + `C-CONDITIONS.md`
→ 前后端 required 都会实跑，**不存在跳过**。QA 不依赖 job 名称推断质量：上表门禁均在本机 worktree 实跑并记录退出码。

## 发布建议

状态：**READY**（B3-1…B3-5 全绿；1 条度量项按实登记为 C 条件）
必修复：0　建议修复：0

**行为变更提示（需随发布说明）**：
1. 新增两个数据库迁移（`impact_edge`、`reuse_suggestion_event`），部署需 `alembic upgrade head`；
2. 知识中心 tester 页签由 5 收敛为 **3**（影响面/项目知识/检索），默认落在「影响面」；平台研发移入专家区；
3. 新增权限点 `impact:view`（tester 默认）/ `impact:manage`（管理员）。

## 复盘卡（Batch 75 起强制）

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 20h / ~16h | 0/0/0/4 | 2 | 工具链（mypy 变量名复用）+ 需求（backlog 字面与既有实现冲突） | 开工前先跑一遍"这段是不是已经有了"的侦察（本批正是靠它避免了第二份复用建议实现）；改类型前先对文件跑 mypy 拿到行号再改 |

**技能使用**: `cameltv-bug-guard` → 三问与"同一能力存两份"复发风险核对（非测试证据）；`cameltv-agent-team` → 批次档位与工件骨架（非测试证据）。
