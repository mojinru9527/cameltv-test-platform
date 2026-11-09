# Batch 277b-4 — QA Report

> **部门**：🔍 QA · **日期**：2026-11-09

## 1. 验收

| 项 | 结果 | 证据 |
|----|:----:|------|
| 默认开关 | ✅ | `settings.control_plane_browser_enabled = True` |
| XHR 采集降级 | ✅ | `APIException 503` + "控制面浏览器已禁用" |
| `/uitest` local 降级 | ✅ | run failed + 可读错误 |
| `playwright_executor` 降级 | ✅ | run failed，不启动 subprocess |
| 蓝湖截图降级 | ✅ | `CaptureResult.error`，不裸抛 |
| Playground 降级 | ✅ | `APIException 503` |
| Dockerfile | ✅ | `playwright install` 0 命中；ENV 两项存在 |
| 单测 | ✅ | 7/7（+ 12 条契约回归） |
| 镜像 inspect | ⏳ | 构建被 github/npm 网络与子模块阻塞 |

## 2. 风险

| 风险 | 说明 | 缓解 |
|------|------|------|
| 部署后蓝湖截图/XHR/Playground 不可用 | 显式 503/error，不是静默失败 | UI 文案提示；后续迁移批次 |
| 镜像未本地构建 | 只做了静态校验 | 发布窗口内构建 + `docker run find` 验证 |
| 生产 DB 104 表 DROP | 部署触发 | 已获用户同意 + 备份就绪 |

## 3. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 0.5 人日 / 实际 ≈ 40min |
| 缺陷 | 0 |
| 返工 | 1（Dockerfile ENV 出现两处，需同时替换） |
| 根因 | 多 stage Dockerfile 的重复 ENV 块 |

## 4. 判定

代码侧通过；P0-4 evidence 需镜像构建 + 真机复验后补齐。
