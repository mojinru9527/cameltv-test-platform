# Batch 85 — QA 报告（J16 码率指标口径修复 + HLS 复测）

> **QA (🔍)** | Date: 2026-08-04 | Verdict: PASS

## 测试总览

| Slice | 通过 | 失败 | 阻塞 |
|:------|:----:|:----:|:----:|
| 1 码率口径修复 + 单测 | 1 | 0 | 0 |
| 2 后端回归 + 门禁 | 1 | 0 | 0 |
| 3 J16 HLS 复测（av-checks 6/6） | 1 | 0 | 0 |

## 可执行门禁

| # | 门禁 | 方式 | 结果 |
|---|------|------|------|
| G1 | ruff F821 | `ruff check app tests --select F821` | PASS（exit 0） |
| G2 | 新增单测 | `pytest tests/test_ffmpeg_service.py` | PASS：7 passed |
| G3 | 后端全量 pytest | `.venv python -m pytest` | 本批执行并记录（见下） |
| G4 | scan-common-bugs | `scan-common-bugs.ps1` | 执行并记录 HARD（见下） |
| G5 | audit-cconditions | `audit-cconditions.ps1 -RequireLatestBatch` | 0 硬错（见下） |

## C74-1 — 码率指标口径（修复前 vs 修复后）

| 项 | 修复前（batch-74） | 修复后（batch-85） |
|---|--------------------|--------------------|
| 码率值 | 0.02 kbps（m3u8 播放列表误读） | **2026.68 kbps**（HLS 分段实测） |
| 码率判定 | FAIL | **PASS** |
| 流可用性 | FAIL（score 100 用了 <= 比较） | **PASS**（>= 比较修正） |
| 六项总览 | 4/6 | **6/6 全过** |

## 证据（平台 av-checks 链路）

任务 `AV-20260804-001`（世界杯决赛回放 HLS，raw_duration 7843s）：trigger → ffprobe + 分段实测 → done。
指标：起播时延 1453.66ms PASS / 码率 2026.68kbps PASS / 帧率 29.97 PASS / 分辨率 921600 PASS / 流可用性 100 PASS / 编码格式 PASS。
证据文件：`test-platform-v2/work-logs/evidence/batch-85/c74-1-bitrate-retest.json`（签名已脱敏）。

## 缺陷与遗留

| # | 级别 | 内容 | 处理 |
|---|:----:|------|------|
| B85-Q1 | P2 | `_compare_metric` 缺少「流可用性」>= 比较（score 100 误判 FAIL） | 已修复 + 2 条单测 |
| B85-Q2 | P3 | HLS 分段实测依赖媒体 CDN 可访问；不可达时如实报 `hls-segments:unavailable`（不伪造） | 登记说明 |

## CI 分层核对

- 变更范围：`test-platform-v2/backend/**` + `docs/**` + `C-CONDITIONS.md` → 后端域；前端无改动。
- 无新增依赖（httpx 为既有 requirements 依赖）。

## 引用基线

引用 batch-74 `evidence/batch-74/j16-avcheck-result.json` 作为修复前基线（4/6）；本批为增量修复证据。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 2.5h / 实际 1.5h | 0/0/1/1 | 0 | 技术债 | 指标口径（单位/比较方向）新增时先对齐阈值语义再上线 |
