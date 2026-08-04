# Batch 76 — PRD Summary（避坑清单自动化 + AGENTS.md 双档同步）

> **Product (🟦)** | Date: 2026-08-04 | Status: Approved

mode: light
豁免理由: 本批为内部流程工具 + 文档同步（scan 脚本、AGENTS.md 措辞、技能引用），不引入产品行为/新接口/新配置/新依赖；按 SKILL.md「批次模式」判定为轻量批次，PM/Design 工件省略，QA/Leader/看板照常。

## 1. 问题陈述

1. **避坑清单停留在"读"的层面**：`cameltv-bug-guard` 的铁律靠执行者自觉对照，无法机器拦截。Batch 37 曾抓到 `R.err()` 崩溃、密码明文 print、静默吞异常等 P0/P1，均可自动化扫描。
2. **C75-4 待办**：Batch 75 双档流水线已写入 SKILL.md，但 AGENTS.md 仍是"一刀切"措辞，两个门禁事实源不一致。

## 2. 非目标（本次不做）

- **不实现完整 ruff/ESLint 插件**：先做独立扫描脚本，插件化留待后续评估。
- **不处理 C74-1/2/3**（J16 码率 / Test5 契约 / 真机性能）：外部依赖与业务验收，继续豁免。
- **不改前端/后端业务代码**：纯工具 + 文档。

## 3. 用户故事 + 验收标准

- As a Dev, I want 提交前一条命令扫出可自动化的避坑项, so that P0/P1 不依赖自觉。
  - 验收：Given `pwsh scripts/git/scan-common-bugs.ps1` / When 运行 / Then 输出 file:line 级命中；硬伤 >0 退出码 1。
- As a QA, I want 脚本自带自测, so that 规则变更不会悄悄失效。
  - 验收：Given `-SelfTest` / When 运行 / Then 临时夹具命中预期规则并退出 0。
- As 仓库维护者, I want AGENTS.md 与 SKILL.md 双档措辞一致, so that 门禁事实源无分歧。
  - 验收：Given AGENTS.md / When 阅读批次模式相关章节 / Then 与 SKILL.md「批次模式」一致并指向规范文档。

## 4. 成功指标

| 指标 | 目标 | 测量 |
|------|------|------|
| scan-common-bugs.ps1 | Parser 0 错 + SelfTest 全过 | QA 记录退出码 |
| 真实仓库扫描 | 输出完整命中清单，无脚本崩溃 | QA 记录 |
| C75-3 门禁 | audit-cconditions.ps1 exit 0 | push 前运行 |
| AGENTS.md 双档 | 与 pipeline-modes.md 一致 | 结构检查 |

## 5. 技术考量（Design 摘要，轻量批次内嵌）

`scan-common-bugs.ps1` 接口：

| 项 | 设计 |
|----|------|
| 参数 | `-RepositoryPath`（默认当前目录）、`-FailOnWarning`、`-SelfTest` |
| 规则集 | R.err 无定义 / 调试遗留 / 静默吞异常（Hard）；硬编码密钥 / 密码进日志 / envelope 断言（Warn） |
| 输出 | `file:line:col` 命中 + 摘要；只读 |
| 退出码 | 0=干净；1=硬伤；2=仅警告（-FailOnWarning 时 2→1） |
