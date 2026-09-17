# Batch 255 — 发布请求核对 + 容量回收（PRD-lite / QA / Leader 合并记录）

> **🔍 QA** | Date: 2026-09-18 | 分支：`fix/batch-255-release-reconcile-and-capacity`（base `81e84ac5`）
> 模式：**轻量批次**（发布脚本内部加固 + 容量开关）| 范围：`scripts/ops/**`、`C-CONDITIONS.md`、`work-logs/**`

```yaml
mode: light
豁免理由: |
  修复既有缺陷 + 给既有脚本加可选开关：不改接口/契约/依赖，不引入新用户可见行为；
  - C252-1 只改"请求失败后的判定逻辑"（新增独立模块 + 接入 publish/rollback 失败路径）
  - C252-2 只新增可选 -ReclaimPrevious（默认关闭，行为不变）
判定依据: docs/agent-team/pipeline-modes.md → 否。
```

## 1. 问题（2026-09-17 实测）

`release.ps1 -Publish release-20260917-0008` 时：客户端报
`API 失败: An error occurred while sending the request.` → 脚本 `throw "发布失败"`；
但服务端**完整成功**：6 容器重建 healthy、事件到 `PROD_OBSERVING`、随后 `/verify` 返回
`production verified`。同次上传后生产磁盘一度 **94%（2.7G 可用）**。

## 2. 交付

| 条件 | 交付 |
|------|------|
| C252-1 | 新增 `scripts/ops/release-reconcile.ps1`（`Resolve-DeploymentOutcome`：可注入查询/等待/日志，按意图区分成功/失败状态集）；`release.ps1` 的 publish 与 rollback 失败路径接入：请求中断后按 deployment id 核对状态，成功态则按成功报告并提示"请勿重发"，失败态才报错，不可达时明确交人工确认 |
| C252-2 | `release.ps1` 新增 `-ReclaimPrevious`：上传前删除**非本次 tag** 的历史 `release-*.tar` 并打印 df 前后对照；镜像保留（回滚锚点不依赖 tar），默认关闭、行为不变 |

## 3. 硬门禁与验证

| 门禁 | 命令 | 结果 |
|---|---|---|
| 核对逻辑单测（桩驱动，不触网） | `pwsh scripts/ops/test-release-reconcile.ps1` | **6/6 PASS**（中断但成功 / 服务端失败 / 不可达 / 仍在部署 / 查询抖动恢复 / 回滚意图） |
| `release.ps1` 语法 | PowerShell AST Parser | OK |
| `release-reconcile.ps1` 语法 | PowerShell AST Parser | OK |
| `-DryRun` 回归（默认路径未被破坏） | `pwsh scripts/ops/release.ps1 -Tag release-20260918-0099 -RuntimeMode split -ExecutionConfig … -DryRun` | 仍"未构建、未登记、未上传、未发布"，预览 manifest 正常写入 |
| 提交卫生 | `scan-common-bugs.ps1` | HARD 0（见批次提交） |

## 4. 未做 / 后续

- 本批**未**再跑一次真实发布验证"请求中断"分支（该分支需要网络恰好中断，无法人为复现）；
  逻辑已由桩测试覆盖 6 个分支，正常路径已确认不受影响（DryRun + 语法 + 上传/迁移/启停顺序未改）。
- `-ReclaimPrevious` 的真实验证留给下次发布；首次使用前建议先人工 `ls /opt/cameltv-release` 确认待删清单。

## 5. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1.5h / 实际约 1h | 0/0/0/0 | 0 | 工具链（客户端网络中断 + 磁盘容量） | 对"远程执行 + 客户端等待"的动作，失败判定必须查服务端状态；长流程动作前预留容量并自动回收 |
