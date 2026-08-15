# Batch 185 — PM 计划：性能采集优化（C99-1 ①②③）

> 配套 PRD/Design：`batch-185-perf-collector-optimize-{prd-summary,design-spec}.md`

## 任务清单

| # | 任务 | 验收标准 | 执行 |
|---|------|---------|------|
| T0 | 工件 PRD/PM/Design/看板 | 四件落库、mode:full | 主代理 ✅ |
| T1 | 五指标并行采样（ThreadPoolExecutor + 降级） | 单点≈max 非求和；单指标失败不影响整体 | 主代理 ✅ |
| T2 | jank 内容感知口径（中位基线 + 2×下限兜底 + <4帧回退） | 30fps/120Hz 不误报；UI 抖动仍检出；旧规则回归 | 主代理 ✅ |
| T3 | PERF_CPU_REPORT_MODE 配置 + per_core 归一 + 核数探测 | raw 默认兼容；per_core=÷核数 | 主代理 ✅ |
| T4 | 测试（fps 新场景 4 例 + c99 并行/CPU 6 例）+ iOS collectX 语义修复 | 66 例 perf 测试全绿 | 主代理 ✅ |
| T5 | 全量回归 + 门禁 | pytest 无新增失败；ruff F821 | 主代理 |
| T6 | QA/Leader 工件 + C99-1 ①②③ 关闭（④ 保持 Open） | 工件齐全 | 主代理 |
| T7 | 总确认 → push → Draft PR → audit → 合入 | required checks 全绿 | 主代理 |

## 风险提示

- 并行采集 adb 并发：ThreadPoolExecutor 上限=指标数；失败降级保持。
- jank 口径变化：<4 帧窗口回退旧规则保证小样本行为一致。
