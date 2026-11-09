# Batch 277b-3 — Leader Verdict

> **部门**：🎯 Leader · **日期**：2026-11-09

## 1. 判决

# ✅ APPROVED（修复 + 本地 E2E）

**理由**：

- 4 个真实环境缺陷全部修复（路径 / spec 命名 / Windows 编码 / project 与 reporter），并补 `ui` capacity 文档；
- **真实 Chromium** 跑通节点 spec，本地 `/uitest` 全链路：`ExecutionJob(kind=ui)` → 节点执行 → 证据上传 → `UiTestRun.status=done`；
- 单测不再污染仓库；12/12 + ratchet 绿；
- 默认仍 `local`，生产零变化。

**边界**：P0-4 仍未闭环——控制面 Dockerfile 与蓝湖/XHR/Playground 浏览器依赖未处理。

## 2. 下一步（本地继续）

1. 决策三项浏览器依赖：迁节点 vs 控制面关闭并显式降级；
2. 本地构建无 Chromium 镜像 + `docker image inspect`；
3. 真机节点复验（可复用本次流程）；
4. 发布窗口：确认 104 表 DROP → 部署 → 证据。

## 3. 关联

- [PRD-lite](batch-277b-3-node-spec-runner-fix-prd-lite.md)
- [QA](batch-277b-3-node-spec-runner-fix-qa-report.md)
- [本地 E2E 证据](p0-evidence/P0-4-local-e2e.md)
