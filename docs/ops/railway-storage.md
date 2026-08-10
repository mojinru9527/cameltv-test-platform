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
