# Batch 84 — QA 报告（真机性能验收：CP-C1 Android 端到端采集）

> **QA (🔍)** | Date: 2026-08-04 | Verdict: PASS（有条件）

## 测试总览

| Slice | 通过 | 失败 | 阻塞 |
|:------|:----:|:----:|:----:|
| 1 环境（adb + SoloX + venv） | 1 | 0 | 0 |
| 2 设备识别 + App 包名发现 | 1 | 0 | 0 |
| 3 采集会话 E2E（WS 采样 + 报告 + 启动耗时） | 1 | 0 | 0 |
| 4 缺陷修复（SoloX 设备解析） | 1 | 0 | 0 |

## 可执行门禁

| # | 门禁 | 方式 | 结果 |
|---|------|------|------|
| G1 | ruff F821 | `ruff check app --select F821` | PASS（exit 0） |
| G2 | perf 模块 pytest | `pytest tests/test_perf_collector_contract.py tests/test_perf_api.py` | PASS：44 passed |
| G3 | 后端全量 pytest | `.venv python -m pytest` | 本批执行并记录（见下方） |
| G4 | scan-common-bugs | `scan-common-bugs.ps1` | 执行并记录 HARD（见下方） |
| G5 | 前端 | 本批无前端改动（CI 按 backend 域分类） | 不适用（注明） |

## CP-C1 — Android 真机采集端到端（证据驱动）

| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 设备识别 | ✅ | `GET /perf-sessions/devices` → OPPO Find X3（PEDM00 / Android 14 / online） |
| App 包名发现 | ✅ | adb `pm list packages -3` → `com.camelrn`（v3.4.5.30，Camel RN 应用，启动 Activity `.MainActivity`） |
| 采集会话 | ✅ | `PERF-20260804-002`：start → WebSocket 实时推流 → stop（session_end: user_stop, 3 samples, 16s） |
| 实时指标 | ✅ 真实 | cpu `appCpuRate 0.68%` / memory `293MB` / fps `0`（静态页，如实记录）/ battery `98%, 32.7°C` / network `send 2.04 recv 0.87 KB/s` |
| 报告 | ✅ | `GET /perf-sessions/2/report` → 4 项统计：cpu mean 0.65 PASS、memory mean 294.85 PASS、fps 0 FAIL（静态页观察）、jank 0 PASS |
| 启动耗时 | ✅ | `am start -W` → TotalTime **307ms**（真实冷启动） |
| 持久化 | ✅ | 3 个 timeseries 数据点入库（`/metrics` 返回 3 points） |

证据文件：`test-platform-v2/work-logs/evidence/batch-84/real-device-collection.json`（设备、会话、samples、report、startup 全量）。

## 缺陷与遗留

| # | 级别 | 内容 | 处理 |
|---|:----:|------|------|
| B84-Q1 | P1 | `perf_collector_service.get_connected_devices` 对 SoloX `getDevices()` 返回的字符串 `"dcd8891f(PEDM00)"` 调用 `.get()` → AttributeError → 设备列表恒为空 | 已修复（解析字符串/字典两种形态）+ 2 条契约测试 |
| B84-Q2 | P3 | 采样窗口内 App 处于静态页，fps=0 属数据观察非缺陷；采集时建议带滚动/播放场景复测 | 登记 C84-2 |
| B84-Q3 | P0(外部) | CP-C2 iOS 采集需 iPhone + tidevice/iTunes，用户未提供 | 保持 Open，登记 C84-1 |

## CI 分层核对

- 变更范围：`test-platform-v2/backend/**` + `docs/**` + `C-CONDITIONS.md` → CI 分类为后端域（前端重型回归预计跳过）；本地后端全量回归记录退出码。
- 未引入新依赖到 requirements（solox 仅本地 venv 安装，既有 `perf_collector_service` 运行时依赖）。

## 引用基线

无（本批为新的真机验收类型，无既有基线可引用；验收证据库建议后续批次复用本批 `real-device-collection.json` 作为 Android 真机采集基线）。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h / 实际 2.5h | 0/1/0/1 | 0 | 技术债 | 真机验收前先用 collector 冒烟设备发现，避免 E2E 中途才发现解析缺陷 |
