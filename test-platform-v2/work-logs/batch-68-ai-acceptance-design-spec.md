# Batch 68 — Design Spec（AI 验收全链路执行设计）

> **Design (🎨)** | Date: 2026-08-03

## 1. 环境拓扑（本地执行 + 生产演练）

| 组件 | 地址 | 说明 |
|------|------|------|
| 后端 FastAPI | `http://localhost:8035` | batch-68 sqlite（`data/platform-batch-68-ai-acceptance.db`），AUTO_CREATE_TABLES=true |
| 前端 Vite | `http://localhost:5205` | `npm run dev`，API 代理到 8035 |
| lanhu-mcp server | `http://localhost:8000` | 子模块 c9f4a43；`lanhu-mcp/.env` 含 Cookie（gitignored） |
| OCR venv | `F:/CamelTv/test-platform/.venv` | `pip install paddleocr paddlepaddle`；`LANHU_OCR_COMMAND` 指向 `backend/scripts/ocr_paddle.py` |
| 生产后端 | `https://test-platform.up.railway.app` | 正式域名演练 |
| 生产前端 | `https://cameltv-test-platform1.vercel.app` | 正式域名演练；`/api` 反代到 Railway |

## 2. 凭据与配置（均 gitignored，禁止入库）

- `test-platform-v2/backend/.env`：`AI_API_KEY`（DeepSeek，已实测 200）、`LANHU_USERNAME/PASSWORD`、`LANHU_MCP_ENABLED=true`、
  `LANHU_EVIDENCE_ENABLED=true`、`LANHU_OCR_PROVIDER=local`、`LANHU_OCR_COMMAND`（batch-68 路径）、`RAG/WIKI/KNOWLEDGE_*` 开启。
- `lanhu-mcp/.env`：`LANHU_COOKIE`（从主仓库 gitignored .env 复制，len≈1100）、`SERVER_PORT=8000`。
- 路径修正：`EMBEDDING_CACHE_DIR`、`LANHU_OCR_COMMAND`、`DATABASE_URL` 等指向 batch-68 worktree 绝对路径。

## 3. 执行链路

### Slice 1 — 环境就绪 + C67-3 Cookie 实测
1. 后端：`uvicorn app.main:app --port 8035`；验证 `GET /api/v1/open/health` 200 与 `GET /api/v1/requirements` 登录态。
2. 前端：`npm run dev -- --port 5205`；Playwright 打开 `/login` 截图。
3. lanhu-mcp：按 README 启动 server；用 Cookie 调蓝湖只读接口（用户端 + 运营后台各 ≥1 页）验证登录态。
   - P：返回 200 且页面结构可解析；N：Cookie 失效 → 401/302，登记 C67-3 为需重取并暂停 Slice 2。
4. 证据：lanhu-mcp 日志（HTTP 状态）、健康检查、截图。

### Slice 2 — J06 蓝湖证据包 → OCR → 需求导入闭环
1. `POST /api/v1/lanhu-evidence/jobs` 创建采集任务（R0-LANHU-USER + R0-LANHU-ADMIN 各 ≥1 条 URL，只读）。
2. 轮询 `GET /api/v1/lanhu-evidence/jobs/{id}` 与 `GET .../pages`：页面树、截图、OCR 文本、Job/Page ID。
3. `POST /api/v1/lanhu-evidence/jobs/{id}/import` 导入需求/RAG/Wiki；校验 `GET /api/v1/trace/requirement/{doc_id}` 追溯建立。
4. P/N 原子：附件失败（损坏/超时）→ `review`/`retry` 可见处理，不伪造成功；重复导入幂等。
5. 证据：任务 JSON、OCR 行输出、导入后 DB 计数、截图、证据包 SHA-256（对齐 G56-004）。

### Slice 3 — J07 知识/RAG/Wiki/Agent 真实 AI 闭环
1. 知识摄取：`POST /api/v1/requirements/upload`（R1-USER-REQ/R1-ADMIN-REQ）→ `extract` → `extraction/confirm`；
   确认 `KNOWLEDGE_INGEST_ENABLED/RAG_ENABLED` 生效，摄取/切片任务完成。
2. 检索：`/api/v1/knowledge` 搜索命中真实来源；`EMBEDDING_HEALTH_REQUIRED=true` 时验证 fastembed 模型可用。
3. Wiki：`/api/v1/wiki` 生成/对比引用 J06 采集物，`WIKI_DIFF_ENABLED` 差异可追踪。
4. Agent：`POST /api/v1/agents/run/{agent_type}` 真实 DeepSeek 调用；`GET /agents/runs/{id}` 输出引用来源。
   - 无 fallback 证据：请求日志含 `api.deepseek.com` 200；失败路径（无 Key/超时）→ 可重试且不产出假结论。
5. 证据：摄取/检索/Wiki/Agent 响应 JSON、日志、DB 行、截图。

### Slice 4 — J13 追溯 + G56-012/014
1. 导入 `R1-TRACE-V14`（108 条）与 R1-USER/ADMIN-CASES → `GET /api/v1/trace/coverage`、`/trace/case/{id}`、
   `/trace/requirement/{doc_id}`：覆盖率与 DB 计数一致；断链/重复/跨项目不计数。
2. J09：`POST /api/v1/test-plans` → 关联用例 → `execute-all`/`auto-execute` → 非法重复触发被拒（幂等）、
   刷新状态持久；失败执行 → `POST /api/v1/test-plans/{id}/triage`。
3. J12：失败执行建缺陷 → 合法状态迁移（`POST /api/v1/defects/{id}/transition`）→ `sync-push/pull` 审计一致。
4. J10/G56-012：`POST /api/v1/reports` → `GET /{id}` → `export`；通知/门禁（`/{id}/gate/check`）正负面。
5. J03/J08/J19：两项目（R2-RBAC-PROJECT-AB）+ 三类身份；用例/脑图导入；列表/详情/写接口 count 与分页横向一致。
6. J15：真实浏览器 Playwright 跑 1 条 P0 用例（本平台页面）；外部页面无授权 → DEFERRED。J16 无媒体样本 → DEFERRED。

### Slice 5 — 正式域名发布演练
1. `GET https://cameltv-test-platform1.vercel.app/login`、`/`、`/api/v1/open/health` → 均 200。
2. `GET https://test-platform.up.railway.app/api/v1/open/health` → 200（版本 2.3.0）。
3. 核对 Railway `ALLOWED_ORIGINS` = `https://cameltv-test-platform1.vercel.app`（用户已在面板更新）。
4. 登记发布决策到 `docs/production-delivery/生产环境交付清单.md`。

## 4. 证据规范

- 每个 J 条件 P/N 各至少 1 条证据：HTTP 状态码 + 响应摘要 + DB 计数 + 截图（Playwright）/日志。
- 证据包文件记录 SHA-256 与采集时间；脱敏范围按 B4（不涉及用户信息）。
- 禁止：规则 fallback、固定“未同步”展示、stub 当 PASS；缺授权项登记 DEFERRED（C63-2）。

## 5. 风险与回退

| 风险 | 影响 | 回退 |
|------|------|------|
| 蓝湖 Cookie 过期 | Slice 2 阻塞 | 请用户重取 Cookie（C67-3），登记后重试 |
| PaddleOCR 安装/模型下载慢 | Slice 2 OCR 慢 | 提前后台安装；失败则 OCR 相关 J 项 DEFERRED 不伪证 |
| J16 媒体样本 / J15 外部页授权缺失 | J15/J16 无法闭环 | 对应行 DEFERRED，附授权需求说明 |
| DeepSeek 限流/超时 | Slice 3 Agent 慢 | 重试策略 + 明确失败可重试证据 |
