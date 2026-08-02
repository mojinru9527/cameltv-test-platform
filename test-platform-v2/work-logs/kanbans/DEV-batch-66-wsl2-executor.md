# Dev Kanban — Batch 66 WSL2 Executor

## 项目信息

| 字段 | 值 |
|------|-----|
| 分支 | feature/batch-66-wsl2-executor |
| Base | origin/main at 993a9e6 |
| Worktree | F:/CamelTv-worktrees/codex-batch-66-wsl2-executor |
| Workflow / executor | agent-team / codex |
| Ports | frontend 5202; backend 8032 |
| 创建 | 2026-08-02 |

## 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 六部门工件 | ✅ | ✅ | ✅ | ✅ | ⏳ | 需求与范围锁定 |
| 2 | 安装脚本 + README | ✅ | ✅ | ✅ | ✅ | ⏳ | bash -n 通过；零 Secret |
| 3 | 前置条件登记（窗口/WSL2） | ✅ | ✅ | ✅ | ✅ | ⏳ | 1.1/1.5 ✅ |
| 4 | QA 门禁 + Leader 判决 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | 待用户 push 授权 |

## 当前位置

```
Batch 66 — Test5 验收执行器搭建（窗口 2026-08-03 11:00–18:00）
├── 已完成: 安装脚本；README（V1–V5 登记表）；1.1/1.5 登记；六部门工件
├── 🔄 进行中: QA 门禁与 Leader 判决 → 用户 push 授权
├── ⏳ 窗口前: 安装 Ubuntu 发行版（wsl --install -d Ubuntu）并运行脚本
└── ⏳ 2026-08-03 11:00–18:00: V1–V5 实测并登记（V2/V3 需 Test5 内网）
```

## 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| Ubuntu 发行版 | P1 | 本机仅 docker-desktop 发行版，需安装 Ubuntu | 用户/窗口前 | 2026-08-02 |
| Test5 内网信息 | P1 | V2/V3 需内网 IP/域名可达 | Test5 owner | 2026-08-02 |
| OpenVPN 凭据 | P1 | 凭据仅存本地，脚本交互读取 | 用户 | 2026-08-02 |

## 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| 安装脚本 | scripts/executor/wsl2-executor-setup.sh | ✅ |
| README | scripts/executor/README.md | ✅ |
| 登记 | docs/production-delivery/外部前置条件清单.md（1.1/1.5） | ✅ |
| PRD/PM/Design/QA/Leader | test-platform-v2/work-logs/batch-66-*.md | ✅ |
