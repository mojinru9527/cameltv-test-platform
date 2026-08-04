# cameltv-agent-team 技能变更日志

> 技能版本化唯一日志。凡修改 `SKILL.md` / `DEPARTMENTS.md` 必须在本文件追加一条。格式：日期 | 批次 | 变更摘要 | 动因。

## 2026-08-04 | Batch 75 | 双档流水线 + 自我进化 + 复盘卡 + 验收证据库

- **变更**：SKILL.md 增加「批次模式（完整/轻量）」「自我进化（流程回写 + CHANGELOG 强制）」「复盘卡」「验收证据库」四节；DEPARTMENTS.md 重构 Leader 模板为独立第 6 节、QA/Leader 模板加入复盘卡、Product 模板加入技能使用行与轻量批次判定。
- **动因**：审计发现 Batch 54–61 工件不完整且无豁免记录；SKILL.md 自 Batch 36/37 后 10 天无更新；无量化复盘指标；验收证据重复劳动。

## 2026-07-23 | Batch 36 | CI 范围门禁

- **变更**：SKILL.md 增加 CI 分层核对规则（完整 base/head diff 分类，未知/CI/部署必须双端全量）。
- **动因**：文档/工具类提交被误触发全量回归。

## 2026-07-23 | Batch 35 | 双用户确认

- **变更**：增加执行器双确认状态机（开工确认 + 完成确认）。
- **动因**：无法从客户端/进程推断实际执行器，防止身份伪造。

## 2026-07-22 | Batch 34 | 执行器身份模型

- **变更**：Agent Team 与 Executor 分离；文档不再把 Agent Team 当作实际 AI。
- **动因**：工作流与实际宿主混淆导致审计失败。

## 2026-07-22 | Batch 33 | AI Git 交付审计自动化

- **变更**：引入 `audit-ai-pr.ps1` / `verify-ai-worktree.ps1` 等脚本化门禁。
- **动因**：人工审计不可扩展，PR 门禁需要可执行校验。

## 2026-07-22 | Batch 31/32 | 单一 main 主干迁移

- **变更**：develop/main 双主干迁移为单一 main；新增多窗口 worktree 隔离与防冲突规则。
- **动因**：双主干导致文件丢失与合并回退（如 C-CONDITIONS 被覆盖）。

## 2026-07-22 | Batch 28 | C 条件追踪闭环

- **变更**：Leader 设定的 C 条件必须同步写入 `C-CONDITIONS.md`；Product 开工必须先读条件并在 PRD 中纳入或豁免。
- **动因**：26 个孤儿 C 条件无人跟踪。

## 2026-07-21 | Batch 26 | Agent Team RAG 集成

- **变更**：新增「KB 自动检索（RAG）」章节；部门执行前按模块检索历史缺陷/知识。
- **动因**：知识库建成后需接入开发/QA 流程，让第二大脑可查。

## 2026-07-20 | Batch 19 | 六部门流水线初建

- **变更**：创建 SKILL.md + DEPARTMENTS.md（Product→PM→Design→Dev→QA→Leader 六部门 + 工件模板 + Git 工作流）。
- **动因**：Batch 19 复盘要求 Agent Team 有标准化可追溯的交付流程。
