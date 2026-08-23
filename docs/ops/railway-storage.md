# Railway 持久卷：蓝湖证据截图/导出存储

> Batch 140 / C140-1 — 解决"资产文件缺失 404"：Railway 每次部署重建容器文件系统，
> `/app/storage`（蓝湖证据截图、Word/JSON 导出）默认是**临时目录**，部署重建后旧文件被清空，
> 数据库资产记录仍在 → 下载报 `{"code":404,"msg":"资产文件缺失"}`。

## 症状
- 已采集任务的"查看截图"显示"截图文件已失效"或 `资产文件缺失`。
- 数据库里资产记录存在，但文件不在。

## 解法：给后端服务挂 Railway 持久卷，挂载点 `/app/storage`

### 方式 A：Railway 控制台（推荐）
> ⚠️ **Volumes 不在 Settings 里**（Settings 只有 Config-as-code 等）。Config-as-code
> 文件（railway.json/toml）**不能声明卷**，卷只能通过控制台或 CLI 创建。

1. 打开 Railway 项目 → 点击**后端服务**（服务卡片）。
2. 服务详情页顶部标签 `Deployments / Variables / Volumes / Metrics / Logs / Settings` → 点 **Volumes**。
   - 若找不到 Volumes 标签：在项目画布**右键后端服务 → Create Volume / Attach Volume**，或按 **⌘K** 命令面板输入 `volume` 创建。
3. **Add Volume** → Mount path 填：`/app/storage`（容量默认即可）。
4. 确认后 Railway 会自动重新部署（加卷会重启容器）；之后截图写入持久卷，不再随重建丢失。

### 方式 B：Railway CLI
```bash
railway link                       # 选择项目/服务
railway volume add --mount-path /app/storage
railway up                         # 重新部署
```

## 验证
1. 创建一个蓝湖采集任务（可勾选"仅最新版本"）→ 等成功 → 打开"查看截图"应正常显示。
2. 触发一次**强制重新部署**（Deployments → Redeploy）。
3. 再次打开同一任务"查看截图"→ 截图仍可显示 → 持久化生效。
4. （可选）`railway ssh` 后端，检查 `ls /app/storage/lanhu-evidence` 有历史任务目录。

## 说明
- **已丢失的旧截图无法找回**（部署前没有持久卷）；加卷后**新采集**会持久保留。
- **权限报错**（`[storage] ... Permission denied: '/app/storage/lanhu-evidence'`）：Railway 卷以 root
  挂载，而镜像以非 root 用户（cameltv，UID 10001）运行，非 root 进程无法在卷下建目录。
  在服务 **Variables** 添加 `RAILWAY_RUN_UID=0` 并重新部署；或先以 root 执行
  `chown -R 10001:10001 /app/storage`。
- **重复提示 Permission denied 但服务仍启动**：该报错是 warning 不阻断启动，但证据落盘会失败；
  务必按上条处理后再采集。
- 后端启动日志会打印存储落点（`[storage] Lanhu evidence storage base: ...`），便于确认卷已挂到该路径。
- 若后续截图量大，可评估迁移到对象存储（S3/Supabase Storage），本卷方案为当前最小改动。

## Batch 162 / C161-1 — 蓝湖 Cookie 持久化

- `DATA_DIR=/app/storage/lanhu-data`（持久卷内）：蓝湖 Cookie（`lanhu_cookie.txt`）与采集缓存跨部署保留。
- 自动登录需在 Railway Variables 配置 `LANHU_USERNAME` / `LANHU_PASSWORD`（蓝湖账号）；或通过平台「蓝湖登录/更新Cookie」粘贴 Cookie（写入持久卷）。

## 磁盘写满事故复盘（2026-08-20）— 新建 DSH 任务报 ENOSPC

**症状**：新建 DSH 任务报 `[Errno 28] No space left on device: '/app/storage/dsh-sessions/workspaces/ws-xxx'`。
**根因**：`/app/storage` 持久卷默认容量极小（实测 434M），被 UI 测试产物（`ui-runs/`，单批可超 300M）
+ DSH 工作区 + 蓝湖证据累积写满。`dsh-sessions` 与 `ui-runs` 此前**均无自动清理机制**。

### 应急恢复（SSH 进容器清理）

```bash
# Railway 控制台 → 后端服务 → ⋯ → Shell；或 Railway CLI：
railway ssh

# 看谁占空间
df -h /app/storage
du -sh /app/storage/* | sort -h

# 删 7 天前的旧 UI 运行产物目录与 DSH 工作区（mtime 判断，运行中的任务不受影响）
find /app/storage/ui-runs -maxdepth 1 -type d -regextype posix-extended -regex '.*/[0-9]+' -mtime +7 -exec rm -rf {} +
find /app/storage/dsh-sessions/workspaces -maxdepth 1 -type d -name 'ws-*' -mtime +7 -exec rm -rf {} +
```

### 根治一：扩容 Railway 卷（控制台，推荐）

> Railway **卷只支持扩容、不支持缩容**；Volumes 不在 Settings 里（Settings 只有
> Config-as-code，且 config-as-code **不能声明卷**），必须走控制台或 CLI。

1. Railway 项目 → 点后端服务卡片 → 顶部标签 **Volumes**（找不到则项目画布右键服务 → Create Volume / Attach Volume）。
2. 找到挂载点 `/app/storage` 的卷 → **Increase size**。
3. 建议至少 **5GB**（当前默认 434M 过小；UI 测试产物一次批量回归即可数百 MB）。
4. 确认后 Railway 会自动重新部署（卷数据保留，不丢失）。

### 根治二：保留期自动清理（平台内置，Batch fix 起）

- 后端每日定时（默认 02:30 Asia/Shanghai）按 **mtime** 清理超过保留期的旧产物：
  - `ui-runs/<纯数字运行id>/`（UI 测试截图/录像，最大占用源）
  - `dsh-sessions/workspaces/ws-*`（DSH 任务隔离工作区）
  - `dsh-sessions/*.jsonl*`（DSH 会话日志）
  - `plan-sync/`（计划执行逐用例产物）与蓝湖证据**默认不在**清理范围；
    若需要清理 plan-sync，显式设 `STORAGE_RETENTION_INCLUDE_PLAN_SYNC=true`
- Railway Variables 配置（生产启用）：
  ```
  STORAGE_RETENTION_ENABLED=true
  STORAGE_RETENTION_DAYS=7
  ```
- 容器日志轮转已内置（deploy/docker-compose.yml：json-file max-size 50m / max-file 3），
  防止容器 stdout 写满宿主磁盘；宿主机定期 `docker image prune -a` 清理废弃镜像。
- 补充建议：磁盘使用率告警（卷 >80% 告警），避免再次被动应急。
- DSH 任务失败提示已做可读化映射（`dsh_task_service._friendly_error`）：
  `HTTP_422 Model Not Exist` → 提示核对 AI 配置模型名；`RATE_LIMIT quota` → 提示充值/换提供方；
  `401` → 提示更新密钥；未命中保持原文。
- 若任务仍报 `HTTP_422: Model Not Exist`，见 Dockerfile 中多提供方补丁说明
  （node 模式 profile 已内置 llm-pi-ai `platform` 路由，读 `DSH_MODEL`/`DEEPSEEK_BASE_URL` env，
  任意 OpenAI 兼容端点按项目接入不同模型；部署后验证 `dsh --profile headless --dump-config`
  的 `llm-pi-ai.providers.platform` 含 `process.env.DEEPSEEK_BASE_URL`）。
