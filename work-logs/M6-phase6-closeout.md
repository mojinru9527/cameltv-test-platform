# M6（Phase 6：加固 + 纵向验收 + Asset-map + Ops）收口报告

> **日期**：2026-11-12 · **范围**：TA-033 → TA-035（4 批）
> **结论**：M6 全部任务完成并合入 main；生产 `20261123` 已上线（112 表）。

## 1. 批次

| 批次 | TA | 内容 | PR |
|------|----|------|----|
| batch-315 | TA-033 | Reliability + Security Hardening（强杀恢复/幂等账本/RBAC 审计） | #544 |
| batch-316 | TA-034 | CamelTv Sports 纵向验收（TC-AIQE-001..010 + 造 Bug→修复） | #545 |
| batch-317 | TA-034.2 | Asset-map 接入（页面地图/24 准则/覆盖率三指标/EvidenceBundle） | #546 |
| batch-318 | TA-035 | 文档 / Ops / Rollback（版本锁 + 升级/回滚脚本） | #547 |

## 2. 数据模型

- `mutation_ledger`（迁移 `20261123`）；
- 生产迁移链：`20261122 → 20261123`，表数 111 → **112**。

## 3. 测试与质量

- 后端全量：**1642 passed / 43 skipped**；
- 前端全量：**560 passed**；
- ratchet PASS；版本锁 SelfTest PASS。

## 4. 生产部署

| 项 | 结果 |
|----|------|
| 备份 | `pre-m6-20261112-131900.dump`（176MB，sha256 `17142354…`） |
| 镜像 | `cameltv-tp-backend:release-m6-20261112` → `:main`；回滚 `prev-m6` |
| 迁移 | `20261122 → 20261123_ta033_mutation_ledger` |
| 表 | 111 → **112**（mutation_ledger） |
| 健康 | health=200；imports OK（sports cases=10） |
| 磁盘 | 82% |

## 5. 遗留（不阻塞 M7）

| 项 | 说明 |
|----|------|
| 真实浏览器纵向执行 | Sports executor 由节点注入；场景契约已固化 |
| Ops 空环境实机验证 | 文档 + 脚本已就绪，需独立空机器按文档跑 |
| Asset-map 前端渲染 | 数据契约已就绪，页面地图 UI 后续接 |
| 版本锁 CI 校验 | 脚本可 self-test，workflow 接入另批 |

## 6. 下一步

M7：按 §19 后续任务（TA-036+）。
