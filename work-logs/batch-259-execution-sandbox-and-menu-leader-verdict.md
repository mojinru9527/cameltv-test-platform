# Batch 259 — Leader Verdict

> **Leader (🎯)** | Date: 2026-09-19 | Decision: **有条件通过（2 条 C 条件）**
> 待用户一次总确认（推送 + Draft PR + required checks 通过后合入）后转 APPROVED。

## 评审摘要

| 维度 | 评分 | 备注 |
|------|:----:|------|
| 实现质量 | 良 | 逐切片 TDD；把"哪一层负责什么"写成可执行校验而非承诺 |
| 风险 | 低 | 审计 S4/S5 关闭、S6 部分关闭并明确剩余；无数据模型变更 |
| 覆盖 | 良 | 后端 85 例 + 前端 722 例；缺口是"搜索直达"与内核级隔离（已登记） |
| 流程合规 | 良 | 完整批次六件齐全；看板/复盘卡/流程回写齐备 |

## 关键决策（已批准）

1. **B2 按完整批次执行**：命中执行链路 + 权限/凭据模型 + 新配置 + 前端行为变更四个触发器。
2. **沙箱边界如实分层，不夸大**：进程内负责环境白名单与危险 API 静态拦截；内核级文件/网络隔离与非 root 归部署层。模块 docstring 必须声明这一点，且有断言守着这句话——与 B2-3 纠正「dry-run 不是沙箱」同一原则。
3. **出网白名单只留一份真源**：`execution_egress_allowlist` → `CAMELTV_EGRESS_ALLOWLIST`，避免"配置在平台、执行靠另一份清单"的双份漂移。
4. **静态拦截的规则按"不误伤"设计**：放行 `page.goto`/`page.request`/`waitForResponse` 与 `CAMELTV_*` 契约变量；否则守卫会被绕过或关掉——守卫越严越好是错觉，**能被用下去**才有价值。
5. **DoD 中不成立的部分登记而非绕过**：B2-6 的「可经搜索直达」当前平台无全局搜索 → C259-1；S6 的无凭据容器 → C259-2。
6. **导航改造保持"隐藏 ≠ 删除"**：历史 URL 与权限不变，每个可见菜单恰好出现一次（有断言 + 路由表核对）。

## 抽检通过

- ✅ `app/core/cipher.py:26-40` — 唯一密钥派生；`ai_config_service` 已改为复用（互认测试双向覆盖）。
- ✅ `app/core/cipher.py:60-96` — `assert_key_for_existing_ciphertext` 只在"无 SECRET_KEY 且有密文"时报错，无密文不误报。
- ✅ `app/integrations/object_storage/local.py:21-50` — 反斜杠归一 + `..` 段拒绝 + `is_relative_to` 兜底；注释解释了前导 `/` 是平台前缀。
- ✅ `app/core/spec_guard.py:1-20` — 模块 docstring 明确"静态检查不是沙箱"。
- ✅ `app/core/execution_sandbox.py:1-20` — 四层职责划分写明（进程内 vs 部署层）。
- ✅ `frontend/src/layouts/nav-config.ts:8-30` — 新 IA 与 `PRIMARY_ENTRY_LIMIT` 常量；注释给出事实源章节。
- ✅ `npx vitest run --maxWorkers=2` — 165 文件 / 722 例；`typecheck` / `lint` / `build` 退出码 0。
- ✅ `pytest` 本批域 — 85 passed, 1 skipped（skip 有明确环境原因，非静默跳过）。

## 判决

**有条件通过**：代码与工件达到合入标准，须满足下列条件且需用户一次总确认。

合入前置（不可跳过）：
1. 用户一次总确认（推送 `feature/batch-259-execution-sandbox-and-menu` + 创建 Draft PR + required checks 全绿后合入 main）。
2. `pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks` 通过。
3. `C-CONDITIONS.md` 记录 C259-1 / C259-2（含解除条件）。

## 下一批次 Leader 条件

- **C259-1（P2）**：B2-6 DoD 的「被隐藏页面仍可经**权限 + 搜索**访问」中，"搜索"一半不成立——平台当前没有全局搜索/命令面板（前端 `rg` 无命中）。本批已保证"隐藏 ≠ 删除"（路由与权限保留 + 断言）。**解除条件**：新增全局搜索/命令面板（属新接口/新行为 → 完整批次），覆盖全部授权菜单 code，并补"被收起页面可经搜索直达"的 E2E。
- **C259-2（P1）**：审计 S6 的"执行用户/LLM 产出的代码必须在**无凭据沙箱容器**内"仅部分关闭：表述纠正 + 危险 API 静态拦截已落地，进程内可达面已收敛；内核级文件/网络隔离与非 root 仍依赖部署层。**解除条件**：节点侧 runner 以非 root 容器运行（只读根 + 仅工作区可写 + 出网仅白名单），并给出"容器内读 `.env`/连内网/写持久卷全部失败"的实测证据。

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| 「字面量守卫被散文误伤」连续两次出现（B2-5 的注释写了被禁的 sha256 写法、B2-3 的注释写了被禁的实参写法） | 本批在测试注释中写明机制；**若第三次出现即升级为自动检查**（bug-guard 规则 3） | `work-logs/batch-259-...-qa-report.md` 缺陷 D1/D2 与三问第 1 问；暂不改 SKILL.md（改技能需同批 CHANGELOG） |
| 本机全量 `vitest` 触发 JS heap OOM，需 `--maxWorkers=2` 才能跑完 | 解法记入 QA 报告，供后续批次与 QA 部门复用 | `work-logs/batch-259-...-qa-report.md` 缺陷 D4 |
| 09 §2.1 的"4 入口 + 专家区"与 batch-212 的"5 入口"措辞不同，执行者需自行判断哪个是当前口径 | 本批以 09（更新的事实源）为准并记录理由 | 本判决「关键决策 1/6」；建议 B3 开工前把 01 §3.1 的"≤5 一级入口"同步为 ≤4，避免两份方案长期打架 |
| 组件文件名 `AssetsMoreGroup.tsx` 与用户可见名「专家区」不再一致（历史遗留） | 保留文件名以免扩大改动面，已在组件 docstring 注明；作为 B3 的低优先级整理项 | `frontend/src/layouts/AssetsMoreGroup.tsx:19-24` |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 22h / ~14h | 0/0/0/4 | 3 | 工具链（字面量守卫 vs 散文）+ 环境（内存） | 写字面量守卫时先约定注释改写表述；QA 跑前端全量默认加 `--maxWorkers=2` |

**技能使用**: `cameltv-bug-guard` → 三问与 S4/S5/S6 状态核对（非测试证据）；`cameltv-agent-team` → 六部门工件与门禁（非测试证据）。
