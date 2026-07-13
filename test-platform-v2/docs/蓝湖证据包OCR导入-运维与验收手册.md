# 蓝湖证据包 OCR 导入 —— 运维与验收手册

> 落地实现见 [plans/2026-07-13-lanhu-evidence-pack-ocr-implementation.md](superpowers/plans/2026-07-13-lanhu-evidence-pack-ocr-implementation.md)。
> 本手册面向运维与验收：如何开启、如何跑一次证据包、如何验收完整性。

## 1. 定位

蓝湖链接 → 全页面树发现 → 滚动/分段截图 → OCR → DOM/MCP 文本辅助 → OCR+DOM 合并 → 证据包
→ Word + JSON → 需求文档 / RAG / LLM-Wiki 导入。

- **证据包（DB + storage 文件）是系统真源**：保留页面树、原始蓝湖 URL、docId/versionId/pageId、
  每页一张或多张截图、每段 OCR 文本、DOM/MCP 文本、合并文本、质量指标、Word/JSON 路径、导入引用。
- **Word 是人审工件**，不是唯一真源。JSON / RAG / Wiki 以证据包元数据作为追溯源。
- 原 `lanhu-mcp` 文本导入保留为快速预览 / 降级路径；正式需求沉淀走证据包路径。

## 2. 开关与配置（backend `.env` / `app/core/config.py`）

```bash
LANHU_EVIDENCE_ENABLED=true          # 总开关，默认 false（采集+OCR 成本高）
LANHU_OCR_PROVIDER=mock              # mock（确定性演示/测试）| local（真实命令）
# 真实 OCR：
LANHU_OCR_PROVIDER=local
LANHU_OCR_COMMAND=python F:/CamelTv/test-platform-v2/backend/scripts/ocr_paddle.py {image}   # {image} 占位图片路径
LANHU_OCR_MIN_CONFIDENCE=0.60
# 采集：
LANHU_CAPTURE_VIEWPORT_WIDTH=1440
LANHU_CAPTURE_VIEWPORT_HEIGHT=1200
LANHU_CAPTURE_SCROLL_STEP_RATIO=0.85
LANHU_CAPTURE_MAX_SEGMENTS_PER_PAGE=30
LANHU_CAPTURE_WAIT_MS=600
```

OCR 命令须逐行输出 JSON：`{"text":"比赛推送","confidence":0.96,"bbox":[0,0,100,20]}`。
> 注意：PaddleOCR 原生 CLI **不**输出该逐行 JSON 格式，故仓库提供封装脚本
> [`backend/scripts/ocr_paddle.py`](../backend/scripts/ocr_paddle.py)（兼容 PaddleOCR 2.x/3.x）。
> 启用真实 OCR：`pip install paddleocr paddlepaddle`（首次运行自动下载模型，需联网），
> 再把 `.env` 的 `LANHU_OCR_PROVIDER` 改为 `local` 并启用 `LANHU_OCR_COMMAND`。

前置依赖：`playwright` + chromium（`python -m playwright install chromium`）、`python-docx`、
蓝湖登录态（`LANHU_COOKIE` 或 `LANHU_USERNAME`/`LANHU_PASSWORD` 自动登录）。

## 3. 权限（RBAC）

| 权限点 | 说明 | 默认角色 |
|--------|------|----------|
| `lanhu_evidence:view` | 查看证据包任务/页面/资产 | tester、admin |
| `lanhu_evidence:run` | 创建/重试/取消采集任务 | tester、admin |
| `lanhu_evidence:import` | 导入需求/RAG/Wiki | admin |

## 4. API 一览（`/api/v1/lanhu-evidence`）

```http
POST /jobs                 # 启动采集（异步后台，不阻塞请求）
GET  /jobs                 # 任务列表（项目级隔离）
GET  /jobs/{id}            # 任务详情（状态/阶段/计数/质量）
POST /jobs/{id}/cancel     # 协作式取消
POST /jobs/{id}/retry      # 重试
GET  /jobs/{id}/pages      # 页面列表
GET  /pages/{id}           # 页面详情
GET  /assets/{id}          # 下载资产（项目隔离 + 路径逃逸防护）
POST /jobs/{id}/import     # 导入需求/RAG/Wiki
```

## 5. 手工验收链路

1. 置 `LANHU_EVIDENCE_ENABLED=true`；先用 `LANHU_OCR_PROVIDER=mock` 跑通链路，再切 `local` 验真实 OCR。
2. 启动后端 `uvicorn app.main:app --reload` 与前端 `npm run dev`。
3. 「知识中心 → 导入蓝湖 → 使用证据包 OCR 导入」或「需求文档 → 蓝湖链接 → 证据包 OCR 导入（推荐）」，
   粘贴验收链接：
   ```
   https://lanhuapp.com/web/#/item/project/product?tid=6324825d-1614-4d73-bc4c-f05cdf0734c1&pid=cc8cfbd5-16d2-481f-828e-7eb424a91694&versionId=26af2885-b229-4971-881c-c9bda43492fd&docId=e6b5ce1e-0d25-4e22-a9e9-450283918b3b&docType=axure&pageId=2b4c4235b036420787d3e856b5d133d7&corpId=null
   ```
   勾选 capture_all_pages / include_word / include_json / import_to_*。
4. **完整性验收**（任务抽屉 + Word/JSON）：
   - `status` 为 `success` 或 `success_with_warnings`
   - `total_pages > 0` 且 `captured_pages == total_pages`
   - `word_path`、`json_path` 存在
   - 每页至少一张截图资产；可滚动页面 `segment_count > 1`
   - Word 章节数 == total_pages；JSON `pages` 长度 == total_pages
5. **导入验收**：
   - 需求文档由证据包 Word 生成（file_type=docx）
   - `KnowledgeSource.source_type=lanhu_evidence` 存在，chunk 为 `requirement_page` 页面粒度
   - `WikiRawSource.source_type=lanhu_evidence` 存在（`wiki_enabled=true` 时可触发 Wiki 编译）
   - 每个需求/chunk/Wiki 源可回溯 `evidence_job_id` + page_id + 截图资产

## 6. 已知边界

- 真实 Lanhu 采集需登录态与 chromium，CI/无头环境需预装浏览器与提供 Cookie。
- OCR provider 未配置时返回 `unavailable`（不算失败），合并步骤据此降级并在质量里标 `needs_review`。
- 任一页面缺截图或缺合并文本 → `complete=false`，任务落为 `success_with_warnings`。
