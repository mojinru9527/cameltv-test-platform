# 测试用例索引

> 平台自身验收用例索引。业务系统用例由使用方按 `test-case-standards/` 标准自行沉淀。

---

## 一、测试平台验收用例

| 批次 | 用例文件 | P0 数 | P1 数 | P2 数 | 执行/证据要求 |
| --- | --- | ---: | ---: | ---: | --- |
| Batch 47 | [functional/BATCH47-测试平台需求服务-生产级验收.md](functional/BATCH47-测试平台需求服务-生产级验收.md) | 28 | 20 | 0 | 已执行基线；实际、状态、缺陷和浏览器/命令证据 |
| Batch 48 | [functional/BATCH48-测试平台需求服务-生产级复测.md](functional/BATCH48-测试平台需求服务-生产级复测.md) | 28 | 20 | 0 | 保留 B47 ID；已执行 48 通过、0 失败、0 阻塞；A01～A12 全部通过，结论 `READY` |
| Batch 55 | [functional/BATCH55-测试平台验收收尾.md](functional/BATCH55-测试平台验收收尾.md) | — | — | — | 平台验收收尾资产 |

## 二、平台功能点矩阵

| 资产 | 说明 |
| --- | --- |
| [batch-63-function-point-matrix.md](batch-63-function-point-matrix.md) | 全功能点正负面资产矩阵（认证安全、项目隔离与 RBAC 等），与 `test-platform-v2/work-logs/batch-63-*` 对应 |

---

> 生产验收用例必须符合 [生产级模块验收规则](../test-case-standards/生产级模块验收规则.md) 的证据字段与 READY / CONDITIONAL / NEEDS WORK 判定。
