# P0–P2 收口报告（batch-329 / 330 / 331 + 332）

> **日期**：2026-11-12 · **生产**：`release-m9-20261112`（112 表，head 20261123，health 200）

## 1. 已完成

| 批次 | 范围 | 交付 |
|------|------|------|
| batch-329 | P0 | NodeRun→ExecutionJob 桥接（幂等）；条件边 success/failure/always；Artifact 30 天 GC（Local/MinIO delete）；Dogfood M1–M8 339 passed 留档；TC-AIQE E2E 入口（env-gated） |
| batch-330 | P1 | Console 管理 API：质量门禁、噪音规则 CRUD/续期、GC、Profile 列表；路由 323→330 |
| batch-331 | P2 | MCP HTTP adapter（写审批头）；Appium/minium/pywinauto/paho 探针 |
| batch-332 | 收口 | 回滚演练（M8↔M9 双健康）、版本锁、生产验证 |

## 2. 生产与演练

- 发布：`release-m9-20261112`（P0 代码），无迁移；备份 `pre-m9-20261112-204047.dump`（sha256 `f6e73f41…`）。
- **回滚演练**：`release-m8 ↔ release-m9` 双向切换，两次 health=200，head 保持 `20261123`；最终恢复 `release-m9`，backend healthy。
- 版本锁：commit `bb94584af`，tag `release-m9-20261112`。

## 3. 未闭环（环境/前端依赖）

| 项 | 状态 | 原因 |
|----|:----:|------|
| 真实 TC-AIQE-001..010 | 未执行 | 需隔离 Test 环境地址/账号（E2E 入口已就绪，不配即 skip） |
| 真 Dogfood（AIQE 测 AIQE） | 未执行 | 需可用 AIQE 实例/账号；当前为 pytest 子集留档 |
| Console 页面/菜单/RBAC | 未做 | 需前端批次（API 已就绪） |
| 第二项目 future-wayu 实机 | 未做 | 需真实项目环境 |
| 真实设备/minium/UIA/MQTT | 未做 | 仅契约 + 探针 |
| 全量镜像重建 + digest | 未做 | 仍为 delta 镜像链 |
| 三端 Skill 截图 | 未做 | 需真实客户端 |

## 4. 结论

P0–P2 的**代码/API/契约层**已全部落地并发布；**验收/前端/真实环境层**仍需按上表补齐。
AIQE 整体按代码约 90%，按“对外可用”验收约 80%。
