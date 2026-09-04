# Batch 229 Worker Token Onboarding - Evidence Index

> Date: 2026-09-04 | Branch: `fix/batch-229-worker-token-onboarding`

本目录只保存本批增量证据。Runtime、System Token 和全局页头均在本批修改，旧截图不再作为这些页面的基线。Token 创建成功窗口不截图，Playwright 临时快照已删除，证据中不含明文 Token、密码或 Cookie。

| 证据 ID | 覆盖范围 | 类型 | 基线或增量 | 对应提交 | 结论 | 复用规则 |
|---------|----------|------|------------|----------|------|----------|
| E229-01 | Worker Token 鉴权、错误 scope、停用 Token | 后端回归 | 增量 | 本文件所在提交 + `593c3482` | PASS | Worker heartbeat 鉴权未改时可复用 |
| E229-02 | Runtime 入口、Token 深链、用途预选、一次性配置 | 浏览器黑盒 | 增量 | 本文件所在提交 + `973c15f6` | PASS | Runtime/System 页面未改时可复用 |
| E229-03 | Token 创建、停用、删除 | 浏览器请求清单 | 增量 | 本文件所在提交 | PASS | Token 生命周期契约未改时可复用 |
| E229-04 | 1440x900、768x1024、390x844 | 7 张截图 | 增量 | 本文件所在提交 | PASS | 页面、Shell 或主题未改时可复用 |
| E229-05 | 双端全量、构建、静态与迁移门禁 | 回归清单 | 增量 | 本文件所在提交 | PASS | 仅用于本批提交 |
| E229-06 | 空 Token 启动 fail-fast | 契约测试/环境清单 | 增量 | `4c51de58` | PARTIAL | Linux/Bash 实机复验后替换 |

## 文件

- `pc-usage-snapshots/runtime-worker-{1440x900,768x1024,390x844}.png`
- `pc-usage-snapshots/system-token-{1440x900,768x1024,390x844}.png`
- `pc-usage-snapshots/worker-token-form-390x844.png`
- `regression/test-results.md`
- `regression/browser-network.md`

## 边界

- 浏览器使用本地 FastAPI、SQLite 和 Vite 代理，所有业务请求均走真实前端，没有路由 mock。
- 本机 WSL 缺少 `/bin/bash`，Docker Desktop daemon 未运行，无法执行 Linux 启动脚本；已用启动器契约测试固定 fail-fast 顺序。
- 本批没有部署生产，也没有证明生产 Worker 已在线；体育主验收继续受 C227-2 外部条件约束。
