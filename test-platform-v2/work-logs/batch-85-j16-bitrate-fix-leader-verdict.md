# Batch 85 — Leader Verdict（J16 码率指标口径修复 + HLS 复测）

> **Leader (🎯)** | Date: 2026-08-04 | Decision: APPROVED

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | 轻量修复批（mode: light 已记录），仅 C74-1 范围 + 同口径的流可用性比较方向 |
| 证据 | PASS | 单测 7 条 + 平台 av-checks 复测 6/6（修复前 4/6 基线引用 batch-74） |
| 诚实性 | PASS | HLS 分段不可达时如实报 unavailable；签名 URL 脱敏 |
| 门禁 | PASS | ruff / 后端全量回归（见 QA）/ scan HARD 0 / audit-cconditions 0 硬错 |
| 风险 | 低 | 1 个服务函数 + 比较函数 + 测试；无前端/无新依赖 |

## 抽检通过

- ✅ `_extract_bitrate` 流 bit_rate 优先 / HLS 禁止 format 兜底 / 非 HLS format 兜底
- ✅ `_measure_hls_bitrate` 分段大小×时长实测（单测验证签名串继承）
- ✅ `_compare_metric` 流可用性 >= 修正
- ✅ 真实 HLS 复测 6/6：码率 2026.68 kbps、流可用性 100 均 PASS

## 判决

**APPROVED**：C74-1 关闭；进入一次总确认 → push → Draft PR → checks → 合入。

## 下一批次 Leader 条件

无新增 C 条件（C74-1 关闭即本批目标达成；C74-2 / CP-C2 / C84-2 等外部项维持原状态）。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| HLS `format.bit_rate` 是播放列表值，媒体码率需按分段实测 | 修复 `_extract_bitrate` + 新增 `_measure_hls_bitrate` | `backend/app/services/ffmpeg_service.py` |
| `_compare_metric` 白名单缺「流可用性」导致 score 100 误判 FAIL | 修复 + 单测 | 同上 + `tests/test_ffmpeg_service.py` |
| 指标口径缺陷批量暴露风险 | 复盘卡「下次避免」固化 | QA 复盘卡（无需改 SKILL） |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 2.5h / 实际 1.5h | 0/0/1/1 | 0 | 技术债 | 新指标先定义单位/比较方向并附契约测试 |
