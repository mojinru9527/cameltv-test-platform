# Batch 277b-4 — Leader Verdict

> **部门**：🎯 Leader · **日期**：2026-11-09

## 1. 判决

# ✅ APPROVED（控制面无浏览器开关）

**理由**：

- 四处控制面浏览器依赖全部**显式降级**：`/uitest` local、`playwright_executor`、XHR 采集、蓝湖截图、Playground；
- Dockerfile 删除两条 `playwright install`，镜像 ENV 默认 `CONTROL_PLANE_BROWSER_ENABLED=false` + `UITEST_EXECUTION_MODE=node`；
- 单测 7 + 12 全绿；本地 `/uitest` node E2E（277b-3）已通过；
- 默认配置仍是 `True`（源码/开发环境不受影响），只有镜像内默认关闭。

**边界**：P0-4 证据未写——镜像 `docker run` 验证与真实生产节点复验尚未完成。

## 2. 部署前必须

1. 在有网构建机/服务器完成镜像构建，`docker run` 内无 Chromium；
2. 真机节点 `--capabilities api web ui` 复验 `/uitest`；
3. 发布窗口执行（104 表 DROP 已获同意，备份 2026-11-09 已就绪）；
4. 补 `P0-4-control-plane-no-browser.json`（含镜像 digest + 无 Chromium 输出 + 节点 run id）。

## 3. 关联

- [PRD-lite](batch-277b-4-browserless-control-plane-prd-lite.md)
- [QA](batch-277b-4-browserless-control-plane-qa-report.md)
- [本地验证](p0-evidence/P0-4-browserless-local.md)
