# Batch 99 — Leader Verdict（真机性能验收：安卓双视频场景）

> **Leader (🎯)** | Date: 2026-08-05 | Decision: **APPROVED**

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | 轻量批次（mode: light），按用户口径重定义为双视频场景（Chrome 赛事 / 小象直播间 各 10 分钟） |
| 实现质量 | PASS | 采集器三处缺陷修复（fps 解析 / cpu 多核 / WS 断线重试）均带单测与实测 |
| 证据 | PASS | 场景 A：11 点 600s；场景 B：60 点 600s + 用户画面确认 + 截图；门禁 54 passed |
| 诚实性 | PASS | 小象高负载（CPU 386%/内存 795MB）如实上报不掩盖；iOS 阻塞原因（solox 缺 DeviceSupport）如实登记 |
| 门禁 | PASS | ruff/audit/boundary/保鲜全绿 |
| 风险 | 低 | 后端改动仅 perftest 采集器；iOS 待外部支持 |

## 关键决策（已批准）

1. C84-2 关闭：安卓双视频场景（Chrome 赛事流 fps 85 / 小象直播间 fps 31.2）各 10 分钟真实采样完成。
2. B99-P1 系列修复合入：fps（Android 14 SurfaceFlinger 解析）、cpu（/proc 多核不封顶）、内存（dumpsys PSS）、WS 断线重试。
3. iOS（CP-C2/C84-1）保持 Open：solox 无 iOS 26.5 DeviceSupport（GitHub 404），平台 iOS 采集不可用；解除条件登记。
4. jank 视频口径、采样周期并行化转后续优化（B99-Q2/Q4）；小象直播间高负载为真实被测问题（B99-Q5），转业务侧跟进。

## 抽检通过

- ✅ 场景 A/B 证据 JSON 可复核（fps/cpu/mem/jank 全量）
- ✅ `test_perf_fps_parser.py` 10 项 + 契约/API 回归，54 passed
- ✅ audit-cconditions 0 硬错；boundary PASS

## 判决

**APPROVED**：进入一次总确认 → push → Draft PR → required checks → 合入 main。

## 下一批次 Leader 条件

- **C99-1（P2，已登记）**：**性能采集功能需要优化**——①采样周期并行化（当前 10–55s/点 → 目标 ≤2s）；②jank 视频帧率口径；③多核 CPU 语义与阈值；④iOS 26.5 支持（solox DeviceSupport）。详见 `test-platform-v2/docs/改进任务backlog.md` Epic PERF-OPT。
- CP-C2/C84-1：solox 支持 iOS 26.5（或提供受支持版本 iPhone）后执行 iOS 双场景。
- C96-1：C27 四项验证（staging/本地全栈）待数据与性能测量。
- B99-Q5：小象直播间高负载（CPU 386%/内存 795MB）真实发现，转业务侧跟进。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 滚动压测不等于视频观看验收 | 按用户口径重定义为双视频场景，滚动数据仅辅助 | PRD/QA Batch 99 |
| 站点广告遮罩拦截自动化点击 | 视频场景采用「用户手动确认画面 + 平台自动采样」 | 验收脚本 manual 模式 |
| 无线 adb 瞬时断开中断会话 | 采集循环重试 5×3s + 客户端容忍关闭帧 | perf_ws.py + 采集脚本 |
| 多核 CPU 被 100% 封顶低估 | 去掉封顶，如实上报多核总和（top 实测印证） | perf_collector_service.py |
| solox iOS 缺新版 DeviceSupport | 登记阻塞原因与解除条件 | C-CONDITIONS CP-C2/C84-1 |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 1d+ | 1(外部)/1/0/3 | 4 | 外部依赖+工具链 | 视频验收先视觉确认；采集先加固断线；CPU 多核不封顶 |

**技能使用**：`cameltv-agent-team`
