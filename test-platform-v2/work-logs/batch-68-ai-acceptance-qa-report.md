# Batch 68 — QA 报告（AI 验收全链路 + 正式域名发布演练）

> **QA (🔍)** | Date: 2026-08-03 | 状态: 🔄 进行中（Slice 1 已出证据；Slice 2~5 执行中）

## 测试总览

| 条件 | 通过 | 失败 | 阻塞/待执行 |
|:----:|:----:|:----:|:-----------:|
| Slice 1 环境 + C67-3 | 5 | 0 | 0 |
| Slice 2~5（J06/J07/J13/G56-012/014/发布演练） | 0 | 0 | 执行中 |

## 可执行门禁（命令、退出码、结果）

| # | 门禁 | 命令/方式 | 结果 |
|---|------|-----------|------|
| G1 | 后端启动 | `uvicorn app.main:app --port 8035`（batch-68 venv） | PASS：`GET /api/v1/open/health` → 200 `{status:ok, version:2.3.0}` |
| G2 | 前端启动 | `vite --port 5205` | PASS：`GET http://127.0.0.1:5205/login` → 200，title=CamelTv 测试平台 |
| G3 | AI Key 连通性 | `GET {AI_API_BASE_URL}/models`（batch-68 backend/.env Key，不回显） | PASS：HTTP 200（deepseek-v4-flash / deepseek-v4-pro） |
| G4 | OCR 依赖 | `F:/CamelTv/test-platform/.venv` 安装 paddleocr+paddlepaddle | PASS：`import paddle / paddleocr` 均成功（模型首跑下载数百 MB，Slice 2 触发） |
| G5 | lanhu-mcp 子模块 | `git submodule update --init lanhu-mcp` | PASS：c9f4a43（v1.5.0-238-gc9f4a43），`.env` Cookie 已就位（gitignored） |

## C67-3 — 蓝湖 Cookie 有效期实测（本批关闭）

| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| Cookie 存在性 | ✅ | lanhu-mcp/.env `LANHU_COOKIE` 非空（len≈1100，不回显） |
| 鉴权实测 | ✅ | `GET https://lanhuapp.com/api/project/multi_info?project_id=cc8cfbd5…&team_id=6324825d…&doc_info=1`（Cookie 头）→ **HTTP 200**，业务码 `00000`，返回真实项目信息与账号（已脱敏） |
| 结论 | ✅ | Cookie 运行期有效 → C67-3 关闭（已登记 C-CONDITIONS） |

## 待执行（Slice 2~5）

- J06：lanhu-evidence job 采集 → OCR → `jobs/{id}/import` → 需求追溯闭环（P/N）
- J07：知识摄取/检索/Wiki/Agent 真实 AI（无 fallback）
- J13 + G56-012/014：trace 同源钻取、UI 主链、横向矩阵、报告/通知正负面
- 正式域名发布演练：Vercel/Railway 生产全链路

> 每个 PASS 将在执行时补齐 HTTP/JSON/DB/截图/日志证据；缺授权项（J15 外部页/J16 媒体）登记 DEFERRED（C63-2）。
