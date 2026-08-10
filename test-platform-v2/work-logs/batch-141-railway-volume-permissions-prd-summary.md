# Batch 141 — Railway 卷权限报错加固 PRD-lite
> **Product (🟦)** | Date: 2026-08-10 | Status: Approved

mode: light
豁免理由: 修复性加固（可操作报错提示 + 启动时目录权限修正），无新行为/新接口/新配置/新依赖。

## 1. 问题陈述
1. Railway 加持久卷挂载 `/app/storage` 后，后端启动报
   `[storage] Lanhu evidence storage init failed: [Errno 13] Permission denied: '/app/storage/lanhu-evidence'`。
2. 根因：Railway 卷默认以 root 挂载，镜像以非 root 用户 cameltv（UID 10001）运行，非 root 进程无法在卷下建目录。
3. 现状：代码只打 `init failed: Permission denied`，无任何可操作提示，运维容易再次踩坑。
4. 期望：报错信息给出明确修复指引（RAILWAY_RUN_UID=0 或 chown）；启动时尽量将目录权限放宽到 755。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 报错可操作 | 仅 errno | 提示 Railway Variables 设 RAILWAY_RUN_UID=0 或 chown 10001:10001 | 本批验收 |
| 目录权限 | 镜像默认 | 启动时 chmod 755（尽力而为，不阻断） | 本批验收 |
| 回归 | - | 后端全量 pytest 无新增失败 | 本批验收 |

## 3. 非目标与 C 条件
- 不改变部署方式：加卷与 RAILWAY_RUN_UID=0 仍是 Railway 控制台部署项（C140-1 由 Batch 140 交付方案）。
- 不引入对象存储迁移；不改变证据写入/读取逻辑，仅启动期加固。

## 4. 用户故事与验收标准
- As 运维, I want 卷权限失败时有明确指引, so that 我知道在 Railway 设 RAILWAY_RUN_UID=0 即可恢复落盘。
  - Given 卷以 root 挂载且容器非 root / When 后端启动 / Then 日志提示"Railway 后端服务 Variables 设置 RAILWAY_RUN_UID=0 并重新部署；或 chown -R 10001:10001 /app/storage"。
- As 平台, I want 启动时自动放宽存储目录权限, so that 降权/非 root 场景更少踩 Permission denied。
  - Given 目录可写 / When 启动 / Then mkdir 后尽力 chmod 755（失败静默，不阻断启动）。