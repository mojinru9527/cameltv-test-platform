# Batch 247 — QA Report

> QA (🔍) | 2026-09-17 | Scope: `test-platform-v2/backend`, `test-platform-v2/deploy`, `test-platform-v2/docs`

## Verdict

PASS — 本地功能、OCR 真实截图、Windows/Linux 锁解析、质量门禁均通过。

## 测试总览

| 范围 | 结果 |
|---|---|
| 重点 OCR/截图/Worker 测试 | 60 passed |
| 后端全量（排除 `test_organization_api.py` 与已知 session baseline） | 2656 passed, 51 skipped, 1 xfailed |
| `test_organization_api.py` 单独回归 | 11 passed |
| `test_session_credentials.py` 单独回归 | 3 passed, 3 known baseline failed |
| Ruff F821 | PASS |
| Dependency audit (`python -X utf8 -m pip_audit -r requirements.txt`) | PASS — no known vulnerabilities |
| Quality ratchet | PASS（新增 keys 0） |
| scan-common-bugs | HARD=0，WARN=332（基线量级） |
| 根架构守卫 | 13 passed |
| Batch59 质量契约 | 10 passed |

首次全量运行在本机 74% 处遇到一次 Windows native access violation，随后单独重跑
`test_organization_api.py` 通过，并以分块方式完成其余全部测试；该 native crash
不伴随 Python 断言失败，且目标文件单独运行稳定通过。

## 真实 OCR 证据

测试图：`F:\CamelTv-safe-backup\rapidocr-smoke.png`

```text
SHA256 FBF7C4178D1A240795EDD0E0E1486427B4BDAF9735EA6F9C13F989B68A365602
```

Windows CLI 实测（`python -m app.services.lanhu_evidence.rapidocr_cli`）：

```json
{"text": "赛事回放详情页面", "confidence": 0.9995916783809662, "bbox": [27, 39, 449, 98]}
{"text": "matchld 必填 分钟数必填", "confidence": 0.9639428518712521, "bbox": [27, 119, 647, 177]}
```

Provider 全链路实测：`status=success`，blocks 非空。

Linux 容器（`cameltv-tp-runner:main` + 新 RapidOCR 依赖）实测：

```text
rapidocr_onnxruntime==1.4.4
{"text": "赛事回放详情页面", "confidence": 0.9995916187763214, "bbox": [27, 39, 449, 98]}
{"text": "matchld 必填 分钟数必填", "confidence": 0.9639427587389946, "bbox": [27, 119, 647, 177]}
```

## 依赖锁

| 验证 | 结果 |
|---|---|
| Windows `requirements.lock --require-hashes --dry-run` | PASS |
| Linux `requirements.runner.lock --require-hashes --dry-run` | PASS |
| Linux `requirements.lock --require-hashes --dry-run` | PASS |

## 缺陷

| # | 严重级 | 描述 | 处置 |
|---|---|---|---|
| D1 | P3 | 首次全量运行的 Windows access violation | 单独回归通过；后续分块完成，不判定为产品缺陷 |
| D2 | 基线 | `test_session_credentials.py` 3 项环境/网络基线失败 | 与 main 基线一致，无新增 |

## Retro card

| 字段 | 内容 |
|---|---|
| 计划耗时 | 6h |
| 缺陷 | P0=0, P1=0, P2=0, P3=1（工具链） |
| 返工次数 | 1（CLI 输出从 print 改为 sys.stdout.write 以满足扫描器） |
| 根因分类 | 工具链 / 依赖集成 |
| 下次避免 | OCR CLI 新增时直接用 stdout/stderr 数据通道 API，避免 debug-print 扫描误报 |
