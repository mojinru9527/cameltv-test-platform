# M10 最终状态与环境交接清单（2026-11-13）

> **结论**：M10 的离线可执行项（349 学习 API/运营闭环、347 http 执行器）已完成并验证；
> **346 future-wayu、347 真机/UI runner、348 IoT 三项因外部环境缺失无法执行**，M10 不能正式收口。
> 本文给出可复跑的前置检查与最小交接清单。

## 1. 前置检查（Test 云主机实测）

```bash
python3 scripts/qa/m10_env_preflight.py
```

```json
{
  "status": "BLOCKED",
  "blocked_count": 4,
  "results": [
    {"id": "future_wayu", "status": "BLOCKED", "reason": "未配置 FUTURE_WAYU_BASE_URL / FUTURE_WAYU_USERNAME / FUTURE_WAYU_PASSWORD"},
    {"id": "android", "status": "BLOCKED", "reason": "未安装 adb，且未配置 APPIUM_URL"},
    {"id": "iot", "status": "BLOCKED", "reason": "未配置 MQTT_HOST / MQTT_PORT / MQTT_USERNAME"},
    {"id": "business_web", "status": "BLOCKED", "reason": "TCP 连接失败: timed out（DNS 指向内网地址 192.168.50.170）"}
  ]
}
```

本机（Windows）复跑结论相同。脚本退出码：0=全部 READY，2=存在 BLOCKED。

## 2. 最小交接清单（按批次）

### M10-346 future-wayu

| 项 | 形式 |
|----|------|
| 环境地址 | `FUTURE_WAYU_BASE_URL`（Test/预发，含协议） |
| 账号 | `FUTURE_WAYU_USERNAME` / `FUTURE_WAYU_PASSWORD`（建议专用只读+写测试账号） |
| 项目/租户 | 项目 ID、租户模型、可写测试数据范围 |
| 验收 | 需求→用例→执行→缺陷闭环 + 数据隔离（Domain Pack `ecommerce-pack` 已就绪） |

### M10-347 真机 / UI runner

| 项 | 形式 |
|----|------|
| Android | 一台已授权设备接在可执行环境（`adb devices` 可见）或 `APPIUM_URL` |
| iOS | 可选；无设备时按 `NO_DRIVER/BLOCKED`，不计通过 |
| 说明 | http/API 节点执行器已交付（batch-347）；本项只剩 UI/设备执行分支 |

### M10-348 IoT

| 项 | 形式 |
|----|------|
| Broker | `MQTT_HOST` / `MQTT_PORT` / `MQTT_USERNAME` / `MQTT_PASSWORD`（只读） |
| 设备 | 至少一个可发布遥测的模拟/真实设备 |
| 边界 | 只读守卫 + 写操作审批 |

### TC-004（M9-R2，与 347 同源）

| 项 | 形式 |
|----|------|
| 业务 Web | 内网 runner 节点，或 `camelive-g3-test5.elelive.cn` 公网测试入口/白名单 |

## 3. M10 批次最终状态

| 批次 | 状态 | 证据 |
|------|:----:|------|
| 346 | 🚫 BLOCKED（缺环境/账号） | 本文 §1/§2 |
| 347 | ⚠️ 部分完成（http 执行器已交付，设备待接） | `work-logs/aiqe/batch-347-real-dag-20261113.md` |
| 348 | 🚫 BLOCKED（缺 MQTT/设备） | 本文 §1/§2 |
| 349 | ✅ DONE | `work-logs/aiqe/batch-349-ops-loop-20261113.md` |
| 350 | ⏳ 条件收口（依赖 346-348） | `work-logs/M10-status-20261113.md` |

## 4. 复跑与验收

```bash
# 环境就绪后
python scripts/qa/m10_env_preflight.py     # 期望 exit 0
# 再按 work-logs/aiqe/M9-M10-plan-20261113.md 346-350 验收项执行
```

在 `m10_env_preflight.py` 返回 READY 之前，346/347(UI/设备)/348 的任何执行结果都应标记 BLOCKED，不得记为通过。
