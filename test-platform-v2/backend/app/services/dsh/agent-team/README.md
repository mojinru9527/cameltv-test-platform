# agent-team profile — AgentTeams 团队模式（Batch 191）

DSH 团队模式（`mode=team`）需要 `$DSH_HOME/profiles/agent-team` profile：
CLI `--profile agent-team` 从 `$DSH_HOME/profiles/<name>` 解析（`$DSH_HOME` 默认
`%USERPROFILE%\.dsh`，本机 `C:\Users\26029\.dsh`），**harness checkout 下没有
profiles 目录，不要安装到仓库**。

> 注意：`dsh_team_harness_path`（DSH_TEAM_HARNESS_PATH）配置的语义是 **DSH_HOME
> 覆盖**——非空时作为 `DSH_HOME` 环境变量注入 node 子进程，profile 从
> `{dsh_team_harness_path}/profiles/agent-team` 解析；它不是 bin.js 路径
> （那是 `dsh_harness_path`）。

## 安装（推荐方式 A）

```powershell
# 1. 确认 $DSH_HOME（Windows: %USERPROFILE%\.dsh）
dsh --version

# 2. 官方 CLI 命令：创建 profile 骨架 + pnpm 安装 + 写入 dsh.profile.bundles
dsh plugin --profile agent-team add @nanmicoder/dsh-agent-teams
```

## 安装（手工方式 B）

把本目录三个模板复制到 `$DSH_HOME/profiles/agent-team/` 后安装：

```powershell
$dst = "$env:USERPROFILE\.dsh\profiles\agent-team"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item package.json.template "$dst\package.json"
Copy-Item cordis.patch.yml.template "$dst\cordis.patch.yml"
Set-Content "$dst\cordis.yml" '[]'   # 根空，与 headless profile 一致
# pnpm-workspace.yaml（照 web/headless）：
Set-Content "$dst\pnpm-workspace.yaml" @"
packages:
  - .

nodeLinker: hoisted
autoInstallPeers: false

"@
cd $dst; pnpm install
```

## 安装自检（冒烟前置）

```powershell
dsh --profile agent-team --dump-config
```

应输出组合树且**包含 agent-teams 插件**，无「profile 不存在」错误。

## 平台侧配置（backend .env）

```ini
DSH_TEAM_PROFILE=agent-team
DSH_TEAM_TIMEOUT_SECONDS=1800
DSH_TEAM_POLL_SECONDS=3
# DSH_TEAM_HARNESS_PATH=   # 非空 = DSH_HOME 覆盖（见上）
```

python-sdk 运行时无需本 profile：平台自动使用内置
`app/services/dsh/team.cordis.yml`（minimal + agent-teams 插件行）；
可经 `DSH_TEAM_CORDIS_CONFIG` 覆盖为自定义组合文件。
