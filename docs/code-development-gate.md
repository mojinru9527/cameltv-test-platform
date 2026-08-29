---
title: "测试平台 代码开发校验门禁（减少返工）"
owner: "qa-team"
last_reviewed: "2026-08-07"
status: "active"
expires: "2027-01-07"
tags: ["gate", "clean-code", "gherkin", "qa-management", "engineering", "ci", "rework"]
related: ["engineering-standards.md", "testing-strategy.md", "common-pitfalls.md", "../test-platform-v2/docs/clean-code-standards.md", "../tests/clean-code/README.md", "../AGENTS.md", "adr/README.md"]
---

# 测试平台 代码开发校验门禁（减少返工）

> 一句话目标：**让「不合格的代码」在本地/PR 早期就被拦下，而不是等回归/生产才返工。**
> 本文档把 **GitHub Clean Code 项目** 提炼出的前端/后端代码标准、**Uncle Bob《Clean Code》** 编程思维、**Gherkin（行为）验收**、以及 **QA 管理条件**，整合成一套**分层的开发校验门禁**，与平台现已运行的 CI 门禁和 git 审计脚本无缝接续。

---

## 0. 为什么需要一套「门禁」——返工从哪来

测试平台的返工主要来自 5 类问题，每一类都能被一道**更早的闸门**截住：

| 返工来源 | 典型表现 | 事后成本 | 应被哪道门禁拦下 |
|---------|---------|---------|----------------|
| 1. 坏味道 / 命名混乱 | 变量名 `data/temp/tmp`、函数 200 行 | 阅读/排障成本高，改动处处踩雷 | **G1 代码体检（静态+约定）** |
| 2. 结构依赖倒挂 | Router 里写 SQL、Store 里发请求 | 契约变更连锁爆破 | **G2 分层与依赖** |
| 3. 行为不符合验收 | 功能「能跑」但不是 QA 要的 | 回归重写用例、重测 | **G3 行为验收（Gherkin）** |
| 4. 测试覆盖不足 | 只有正面用例、无边界/负面 | 缺陷漏网到生产 | **G4 测试与质量管理** |
| 5. 凭据/环境泄漏 | 硬编码 `SECRET_KEY`、`password` | 安全事故 + 全量返工 | **G0 提交卫生** |

> 设计原则：**Fail Fast（尽早失败）。** 能在 `git commit` 前挡住的，绝不留到 `git push`；能在 PR 挡住的，绝不留到 merge；能在 merge 挡住的，绝不留到回归。越早的门禁成本越低。

---

## 1. 门禁总览：5 道闸（G0 → G4）

```
G0 提交卫生    →  提交前，已存在于 scan-common-bugs.ps1 的 HARD 规则 + 凭据扫描
G1 代码体检    →  本地/PR，ruff/tsc/lint + 命名·函数·错误·注释约定（Clean Code）
G2 分层与依赖  →  本地/PR，单向分层 + 路由禁 ORM + Store 不调 API + 队列原语
G3 行为验收    →  PR，Gherkin（Given/When/Then）验收 + 正负用例 + FIRST
G4 测试与质量  →  CI 汇总，pytest/Vitest + 覆盖边界/异常 + 状态词表/删除语义
```

每道闸输出两个结果：**Block（必须改，强制）** 或 **Warn（需人工复核，建议）**。任一 `[强制]` 在 G0–G2 未过 → Block PR；`[建议]` 未过 → 记入 PR 评审说明，不阻断但需给出是否延期理由。

| 闸门 | 时机 | 工具（已存在） | 强制门槛 | 对应规范 |
|------|------|--------------|---------|---------|
| **G0 提交卫生** | pre-`commit` | `scripts/git/scan-common-bugs.ps1`（HARD）+ git hooks | 无调试遗留、无硬编码密钥、无备份/DB/IDE 文件 | `engineering-standards.md` §5、`AGENTS.md` §3.5 |
| **G1 代码体检** | pre-`push` / CI | `ruff check --select F821`、`npm run typecheck`、`npm run lint`、`npm run build` + Clean Code 约定 | 无未定义符号、类型通过、无 `any` 滥用、命名/函数/注释合规 | Clean Code 规范 §3/§4/§9 |
| **G2 分层与依赖** | pre-`push` / CI | `test_route_layer_orm_ban.py`、`test_route_inventory.py` + Code Review | 分层单向、路由禁 ORM、Store 不调 API、队列走原语 | Clean Code 规范 §6 |
| **G3 行为验收** | PR（Review） | `tests/clean-code/*.feature`（Gherkin）+ 代码评审 | 关键行为有 Given/When/Then、正负用例齐、断言可验证 | Clean Code 规范 §8、`tests/test-case-standards` |
| **G4 测试与质量** | CI（merge） | `pytest`、`npm test`、PostgreSQL concurrency、Alembic 单头 | 全量回归通过、状态词表规范、删除语义统一 | `AGENTS.md` §3、`backend/CLAUDE.md` |

---

## 2. GitHub Clean Code 参考来源（研发基线）

> 以下仓库是「把 Clean Code 落到工程」的公认范本，我们**借鉴其约定**，翻译成测试平台前端/后端的可执行规则。技术栈不同，但原则通用。

| 来源 | 语言/场景 | 我们吸收的规则 |
|------|----------|--------------|
| [ryanmcdermott/clean-code-javascript](https://github.com/ryanmcdermott/clean-code-javascript) | JS/TS | 变量须自解释、函数小而单一、用映射替代 if/else、布尔前缀 `is/has/can`、`any` 禁用 → 用于 **G1/Clean Code 规范 §3–§4** |
| [uncle-bob-clean-code-skill（istari）](https://github.com/Contrast-Security-OSS/istari/blob/main/uncle-bob-clean-code-skill.md) | 工程化 skill | 把 Clean Code「可执行化」：命名、函数、错误、测试 → 用于 **G1/G4 条目落入 AI 生成门禁（规范 §7）** |
| [hhy5277/clean-code（《Clean Code》读书笔记）](https://github.com/hhy5277/clean-code) | 笔记 | SOLID、SRP/OCP/DIP、函数抽象层级、错误处理用异常 → 用于 **G2/G3 分层与错误** |
| [PEP 8 / PEP 257](https://github.com/SENATOROVAI/python-open-source-standards-course) | Python | snake_case、docstring 用 `"""` 说明职责 → 用于 **G1 后端命名/注释** |
| [sickn33/agentic-awesome-skills/clean-code](https://github.com/sickn33/agentic-awesome-skills/blob/main/skills/clean-code/SKILL.md) | AI 协作 | 规范要能被 Agent 照读 + 可执行自检 → 用于 **G3/规范 §7（AI 生成代码适配）** |
| [off-grid-mobile/CLAUDE.md](https://github.com/WildMeOrg/off-grid-mobile/blob/main/CLAUDE.md) | 仓库级规范文件 | 把约定写成 AI 可直接遵守的 CLAUDE.md → 用于 **本文档落到 `CLAUDE.md` 索引** |

**吸收结论**：一流开源项目的共同点是——**规范围绕「分层、命名、函数、错误、测试」五件事**，并且**把约定写成「可读、可审、可自动检查」的形态**。测试平台作为质量标杆，应做到更进一步：**把约定写成 Gherkin 验收 + 门禁**。

---

## 3. G1 代码体检：原则 → 规则 → 门禁映射

每条 Clean Code 原则拆成「规则 → 强制级别 → 检查方式」。

### 3.1 命名（Clean Code 第 2 章）

| 原则 | 规则 | 级别 | 门禁（落到 G1） |
|------|------|------|----------------|
| 意图命名 | 变量/函数名表达用途，不用 `data/temp/tmp/obj` | 强制 | 评审 Gherkin `01-naming`；后台可用正则扫描常见坏名 |
| 布尔前缀 | `is_/has_/can_/should_` | 强制 | 评审 + `is_deleted` 约定 |
| 术语统一 | 用例/计划/执行/缺陷/需求 各一词 | 强制 | 评审 Gherkin `01-naming` |
| 免 `any` | 前端禁 `any` 逃生舱 | 强制 | `tsc` + 评审 Gherkin `01-naming` |
| PEP 8 | 后端 snake_case/PascalCase/UPPER | 强制 | 评审 + `ruff`（E 系列） |

### 3.2 函数（Clean Code 第 3 章）

| 原则 | 规则 | 级别 | 门禁 |
|------|------|------|------|
| 小函数 | 单函数 ≤ 30 行 | 建议 | 评审 Gherkin `02-functions` |
| SRP | 一函数一事，路由只做校验/调用/响应 | 强制 | `test_route_layer_orm_ban` + 评审 `04-layering` |
| SLAP | 高层不写原生 SQL | 强制 | 评审 `02-functions` |
| 禁魔法数字 | 提为常量/settings | 强制 | 评审 `02-functions` |
| 事务收敛 | `with transaction(db):` | 建议 | 评审 `02-functions` |

### 3.3 错误处理（Clean Code 第 7 章）

| 原则 | 规则 | 级别 | 门禁 |
|------|------|------|------|
| 用异常 | 抛 `APIException`，不散落 `return {code...}` | 强制 | 评审 `03-error-handling` |
| 预期失败显式化 | `not_found()`/`forbidden()`/领域异常 | 强制 | 评审 `03-error-handling` |
| 禁裸 except | 禁止 `except: pass` | 强制 | `scan-common-bugs.ps1`（已有 HARD 规则） |
| 前端统一解包 | 拆 envelope + 401 统一登出 | 强制 | 评审 `03-error-handling` |
| AbortError 放行 | 取消不 toast | 强制 | 评审 `03-error-handling` |

> **关键差异**：命名/函数/错误的「语义」规则难以完全自动化，因此 G1 的**语义部分靠评审 + Gherkin**，**机械部分靠 lint/静态扫描**。正是「机械部分进 CI、语义部分进评审」，才让门禁既快又稳。

---

## 4. G3 行为验收：Gherkin 作为「行为门禁」

> 引用仓库：**Gherkin 的「行为即验收」本意**来自 BDD 社区；这里把其用作**行为级验收门禁**——每个关键行为写成 `Given/When/Then`，评审/QA 用它核对「代码是否真的做到」。

### 4.1 结构与复用

- 已有套件：[`tests/clean-code/`](../tests/clean-code/README.md)（8 个 `.feature`，70 个场景），覆盖命名/函数/错误/分层/测试/注释/AI 生成/交付。**本文档不重写，直接复用为 G3 的验收清单。**
- 每条 `Scenario` 的 `Then` 就是「验收点」；`[强制]` 条目的 `Then` 在 PR 评审中必须有证据。

### 4.2 Gherkin 如何拦截「行为不对」的返工

以「前端接口请求规范」为例：

```gherkin
Feature: 前端 API 请求规范
  Scenario: 组件加载时接口只请求一次
    Given 一个在 React 页面中使用 useApi 拉取列表的组件
    When 页面在 StrictMode 下挂载
    Then 每个 GET 只发出 1 次有效请求
    And 卸载时请求被 AbortController 取消
```

- 若开发者写出**没有 cleanup 的 effect**，该 `Then` 失败 → 在 PR 即被标识，避免「上线后才发现重复请求/内存泄漏」这类返工。

---

## 5. G4 测试与质量管理：QA 管理条件融入门禁

> 引用仓库：**QA 管理**（用例体系、P0–P3、正负覆盖、缺陷管理）来自 `tests/test-case-standards/`。门禁把 QA 条件变成「放行前提」，而不是事后补测。

### 5.1 放行前提（QA 条件门禁）

- [强制] **正负覆盖**：每个需求功能点 ≥ 1 正面 + ≥ 1 负面（`功能测试用例规范.md`）。
- [强制] **三要素**：功能用例 = 前置条件 + 操作步骤 + 预期结果（可验证）。
- [强制] **接口三要素**：入参校验 + 业务逻辑校验 + 返回值校验（`test-case-design` skill 必选）。
- [强制] **执行状态走规范词表**：`pending/running/passed/failed/skipped/cancelled/blocked`（`backend/CLAUDE.md`），读取侧用映射表。
- [强制] **删除语义唯一**：软删 = `is_deleted`，硬删 = 显式审计删除（`backend/CLAUDE.md`）。
- [建议] **测试遵循 FIRST**：Fast / Independent / Repeatable / Self-validating / Timely。

### 5.2 质量指标（放进 QA 报告，对齐 `AGENTS.md` §4）

| 指标 | 达标线 | 来源 |
|------|-------|------|
| 后端 F821 | 0 | `main-quality-gate.yml` |
| 前端 tsc | 0 error | `main-quality-gate.yml` |
| 全量 pytest / vitest | 无新增失败（基线需说明） | `AGENTS.md` §3.1 |
| 生产验收门禁 | A01–A12 全部取证 | `tests/test-case-standards/生产级模块验收规则.md` |

---

## 6. G2 分层与依赖：结构性门禁

- [强制] **后端单向分层**：Router → Service → Model；Router 禁 ORM（`test_route_layer_orm_ban.py`、`test_route_inventory.py` 已在线）。
- [强制] **前端依赖单向**：page → hooks → api → client；Store 不做 API 调用（`frontend/CLAUDE.md`）。
- [强制] **新队列走 `core/task_queue.py` 原语**（`atomic_claim*`/`reap_stale`），禁自研 SELECT→改→commit。
- [强制] **稳定的抽象放 `core/`**，易变业务放 `services/`（DIP）。

---

## 7. 落地与执行

### 7.1 本地门禁（推荐，可一键）

新增 [`scripts/git/dev-gate.ps1`](../scripts/git/dev-gate.ps1) —— 把 G0–G2 的**机械强制项**串成一条命令，在 `commit`/`push` 前跑：

```powershell
# 推荐：加为 pre-push hook
pwsh scripts/git/dev-gate.ps1 -RepositoryPath (Get-Location).Path
```

它按顺序执行并**聚合 HARD 结果**：

1. `scan-common-bugs.ps1`（G0 提交卫生：HARD + 凭据）
2. `ruff check app/ --select F821`（后端未定义符号）
3. `npm run typecheck` + `npm run lint`（前端类型/风格）
4. 后端守卫测试 `test_route_layer_orm_ban.py` + `test_route_inventory.py`（G2 分层）

> G3/G4 语义与全量部分交给 **CI（`main-quality-gate.yml`）** 与 **评审**，本地门禁只管「快、早、机械」的项，形成「本地先行、CI 兜底、评审终审」三层。

### 7.2 CI 门禁（已存在，无需新增工作流）

- `main-quality-gate.yml`：PR → main 按文件域跑后端 F821/导入/Alembic/PG + 全量 pytest，前端 typecheck/lint/test/build。
- `main-merge-smoke.yml`：merge 后轻量冒烟。
- `ai-delivery-policy.yml`：凭据/分支/CI 分类契约测试（阻断）。
- `audit-ai-pr.ps1` + `run-warn-audit.ps1`：本地/CI 的 AI PR 审计与 WARN 趋势。

---

## 8. 如何达成「减少返工」

| 门禁 | 拦截的返工 | 证据 |
|------|-----------|------|
| G0 提交卫生 | 无调试遗留、无硬编码密钥 → 免去安全整改 | `scan-common-bugs.ps1` |
| G1 代码体检 | 坏味道、命名/函数混乱 → 免去「读不懂再重写」 | ruff/tsc/lint + Gherkin 评审 |
| G2 分层依赖 | 结构倒挂 → 免去契约变更连锁爆破 | `test_route_layer_orm_ban.py` |
| G3 行为验收 | 行为不符验收 → 免去回归+重写用例 | `tests/clean-code/*.feature` |
| G4 测试质量 | 覆盖不足、状态词表错 → 免去缺陷漏到生产 | pytest/Vitest + QA 前提 |

**一句话总结**：把「评审靠人记」变成「门禁靠规则挡 + 人只审语义」，用确定性取代记忆，从源头压掉返工。

---

## 9. 关联资源

- **规范**：[测试平台 Clean Code 代码规范](../test-platform-v2/docs/clean-code-standards.md)（§3–§10 是 G1–G4 的细则）
- **Gherkin 套件**：[tests/clean-code/README.md](../tests/clean-code/README.md)（G3 验收清单 + 自动化接入建议）
- **交付红线**：[engineering-standards.md](engineering-standards.md)、[AGENTS.md](../AGENTS.md) §3
- **测试标准**：[tests/test-case-standards/](../tests/test-case-standards/)（QA 管理条件）
- **已有门禁**：[main-quality-gate.yml](../.github/workflows/main-quality-gate.yml)、`scripts/git/scan-common-bugs.ps1`
