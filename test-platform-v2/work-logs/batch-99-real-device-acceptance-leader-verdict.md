# Batch 99 — Leader Verdict（真机性能验收）

> **Leader (🎯)** | Date: 2026-08-05 | Decision: **APPROVED**

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | 轻量批次（mode: light），范围=C84-2 复测 + iOS 端到端尝试，无蔓延 |
| 实现质量 | PASS | fps 采集缺陷修复自包含；图层选择与解析有单测 |
| 证据 | PASS | 8 个真实采样点 + 报告 + 截图 + UI dump；启动 314ms |
| 诚实性 | PASS | iOS 阻塞如实登记（缺 Apple 驱动）；jank>0 记录为数据观察，不伪造通过 |
| 门禁 | PASS | 8/8 单测、契约回归、ruff/audit/boundary/保鲜全绿 |
| 风险 | 低 | 后端改动仅 perf 采集器；iOS 待外部驱动 |

## 关键决策（已批准）

1. C84-2 关闭：Android 滚动场景 fps 真实采样达标（mean 59.38 / max 117）。
2. B99-P1 修复：采集器自实现 Android fps/jank（规避 SoloX Android 14 缺陷）。
3. iOS：CP-C2/C84-1 保持 Open，阻塞原因（Apple Mobile Device 驱动缺失）登记为解除条件。
4. jank 阈值语义（≤0）对真实滚动过严 → 转产品决策，不阻塞本批。

## 抽检通过

- ✅ `test_perf_fps_parser.py` 8/8（含 Android14 头行回归、图层选择）
- ✅ `test_perf_collector_contract.py` + `test_perf_api.py` 无回归
- ✅ 证据 JSON：fps/cpu/memory/jank/startup 全量可复核
- ✅ audit-cconditions 0 硬错；boundary PASS

## 判决

**APPROVED**：进入一次总确认 → push → Draft PR → required checks → 合入 main。

## 下一批次 Leader 条件

- 不新增 C 条件。CP-C2/C84-1：用户安装 Apple Mobile Device 驱动（iTunes/Apple Devices）或提供 macOS 宿主后执行 iOS 端到端。
- C96-1：C27 四项验证（staging/本地全栈）待数据与性能测量。
- C95-1/C74-2：Test5 环境恢复后补拉契约。
- 产品决策项：perftest jank 报告阈值口径（≤0 vs 分位数）待评估。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| SoloX 2.9.3 Android 14 fps 解析缺陷 | 自实现 SurfaceFlinger 解析 + 图层选择，8 单测 | `perf_collector_service.py` |
| SurfaceFlinger 图层候选含 InputSink/ActivityRecord 壳层 | 排除规则 + 有帧数据优先遍历 | `_select_fps_layers` |
| iOS 在 Windows 缺 Apple 驱动 | 登记阻塞原因与解除条件 | C-CONDITIONS CP-C2/C84-1 |
| 验收脚本依赖平台 API 手工驱动 | 固化为可复用采集脚本 | `scripts/executor/run-real-device-acceptance.py` |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 0.5d / 实际 0.5d | 1(外部)/1/0/1 | 2 | 技术债+外部依赖 | 先做单点采样冒烟（图层/参数），再全链路 |

**技能使用**：`cameltv-agent-team`
