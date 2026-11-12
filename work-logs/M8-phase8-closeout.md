# M8（Phase 8：扩展 Driver / Device Broker / Domain Packs）收口报告

> **日期**：2026-11-12 · **范围**：TA-039 → TA-045（4 批，7 个扩展任务）
> **结论**：M8 全部扩展任务完成并合入 main；生产 `release-m8-20261112` 已上线（112 表，health 200）。

## 1. 批次

| 批次 | TA | 内容 | PR |
|------|----|------|----|
| batch-324 | TA-039 | Mobile Device Broker（Android 优先、能力匹配、iOS C84-1 门禁） | #553 |
| batch-325 | TA-040 | 小程序 Adapter（微信版本矩阵、minium/weapp-dev-mcp 回退） | #554 |
| batch-326 | TA-041+042 | Desktop Driver（Electron/UIA/AppleScript）+ IoT Driver（mqtt/http/serial、只读） | #555 |
| batch-327 | TA-043+044+045 | Domain Packs：E-commerce / SaaS / IoT | #556 |

## 2. 交付物

- `app/aiqe/services/device_broker.py`
- `app/aiqe/adapters/miniapp.py`
- `app/aiqe/adapters/desktop_driver.py` / `iot_driver.py`
- `app/aiqe/domain_packs.py`

无新增迁移（复用 `20261123`）。

## 3. 测试

- 后端全量：**1671 passed / 43 skipped**（M8 新增 24 条）；
- 前端：560 passed（M8 未改前端）；
- ratchet PASS。

## 4. 生产部署

| 项 | 结果 |
|----|------|
| 备份 | `pre-m8-20261112-200414.dump`（177MB，sha256 `035d9c35…`） |
| 镜像 | `cameltv-tp-backend:release-m8-20261112` → `:main`；回滚 `prev-m8` |
| 迁移 | 无（head 保持 `20261123_ta033_mutation_ledger`） |
| 表 | **112** |
| 健康 | health=200；imports OK（packs=ecommerce/iot/saas） |
| 磁盘 | 82% |

## 5. 遗留（真实设备/环境依赖）

| 项 | 说明 |
|----|------|
| 真实 Android 真机池 | Broker 状态机已固化，需接设备/Appium |
| iOS 真机 | C84-1 未解除，门禁保持拒绝 |
| 微信开发者工具/minium | Adapter 契约已固化，需实机执行器 |
| 桌面自动化 | UIA/AppleScript/Electron 执行器待接 |
| IoT 真实协议 | transport 注入点已备，需设备网关 |
| future-wayu 等业务接入 | Domain Pack 契约已固化 |

## 6. 下一步

M8 完成，V1.1+ 预留扩展全部收口。后续按业务优先级接入真实设备/项目（非代码批次）。
