# Stage 1–5 执行就绪报告（Gate F）

## 当前生产拓扑（2026-11-27 只读核查）

| 组件 | 现状 |
|---|---|
| 前端容器 | `cameltv-tp-production-frontend-v16`，nginx，`127.0.0.1:8080` |
| 后端容器 | `cameltv-tp-production-backend-v16`，镜像 `cameltv-tp-backend:v16-api` |
| AIQE 后端 | `aiqe-v16-backend`，同镜像 |
| 入口 | 主机 Caddy（admin `127.0.0.1:2019`）反代 |
| 候选版本 | main `eb20b980`，**尚未构建/部署新镜像** |
| 流量切分 | 当前**没有 canary/权重上游**配置 |

## Stage 就绪度

| 阶段 | 就绪度 | 缺什么 |
|---|---|---|
| Stage 1 Shadow | ❌ | 候选镜像 + shadow 容器/端口 + 对比脚本；需不影响线上 |
| Stage 2 Dogfood | ✅ 可执行 | 内部账号已有；可记录 Run/Job/Assertion |
| Stage 3 小流量 5% | ❌ | Caddy/入口权重切换能力；监控基线 |
| Stage 4 扩量 50% | ❌ | 同上 + 6h 观察窗口 |
| Stage 5 GA | ❌ | 100% 切换 + 发布公告 + 独立验收签署 |

## 执行前置（必须确认）

1. **发布窗口**：Stage1 11-28、Stage2 11-29、Stage3 12-01、Stage4 12-03、Stage5 12-05（计划）；
2. **候选镜像 digest**：从 main 构建并记录；
3. **流量切换方式**：Caddy upstream 权重 / 维护窗口整机切换；
4. **回滚**：保留 `cameltv-tp-backend:v16-api` 旧镜像，切回命令；
5. **独立验收**：MoojinR 在生产证据 `independent_verification` 签字；
6. **监控基线**：错误率、P95、AIQE job 失败率、DB 连接数。

## 证据要求（每阶段）

- 发布/回滚命令与时间戳
- 镜像 digest、容器 ID
- 阶段 Run/Job/NodeRun/Assertion/Artifact ID
- 监控截图或 Prometheus 查询结果
- 观察窗口与结论

## 当前结论

Gate F **保持 NOT_PROVEN**。没有候选镜像与流量切换能力之前，不能把 stage 标记 PASS；代码/单元测试不能替代真实发布。
