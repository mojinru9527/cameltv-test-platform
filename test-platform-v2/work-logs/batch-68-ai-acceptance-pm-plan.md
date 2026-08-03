# Batch 68 — PM Plan（AI 验收全链路 + 正式域名发布演练）

> **PM (🟨)** | Date: 2026-08-03

## 规格摘要
按 PRD 完成 G56-011/012/014、C67-3 与正式域名发布演练；所有结论须真实执行证据（C63-2），缺授权项 DEFERRED。

## 开发任务

### [ ] Task 1: 环境就绪 + C67-3 蓝湖 Cookie 实测
**描述**: 初始化 lanhu-mcp 子模块（已 init）、复制 gitignored 凭据（backend/.env、lanhu-mcp/.env）、安装
backend venv + frontend npm ci + OCR venv（paddleocr+paddlepaddle）+ lanhu-mcp 依赖；启动 lanhu-mcp 并用 Cookie
访问蓝湖只读接口实测有效期。
**验收标准**: AI Key `GET /models` 200；lanhu-mcp 启动无鉴权错误；Cookie 实测有效（或失效则请用户重取，登记 C67-3）。
**涉及文件**: `test-platform-v2/backend/.env`、`lanhu-mcp/.env`（均 gitignored）、`lanhu-mcp/requirements.txt`
**参考**: PRD §5/§6；DevOps 手册；`test-platform-v2/docs/蓝湖证据包OCR导入-运维与验收手册.md`

### [ ] Task 2: J06 蓝湖证据包 → OCR → 需求导入闭环
**描述**: 通过 lanhu-mcp 从 R0-LANHU-USER/ADMIN 只读采集页面树/截图/文本，PaddleOCR 抽取，导入需求模块并建立
Job/Page ID 与需求追溯；执行 P/N 原子结果（附件失败→可观察人工处理，不伪造成功）。
**验收标准**: J06 P/N 全部 PASS；证据含来源、时间、SHA、脱敏记录（G56-004 口径）。
**涉及文件**: `test-platform-v2/backend/app/services/lanhu_evidence/**`、`app/services/external/lanhu_provider.py`、`scripts/ocr_paddle.py`
**参考**: PRD 成功指标；执行矩阵 J06 行；蓝湖证据包手册

### [ ] Task 3: J07 知识/RAG/Wiki/Agent 真实 AI 闭环
**描述**: 用 R1 需求文档 + J06 采集物做知识摄取/切片/检索，Wiki 生成与对比，Agent 任务执行；验证真实 DeepSeek
调用与输出来源、无 fallback；服务失败/无权限时不生成假结论且可重试。
**验收标准**: J07 P/N 全部 PASS；`R0-AI-LIVE` 无 fallback 证据（请求日志/响应引用来源）。
**涉及文件**: `test-platform-v2/backend/app/services/knowledge/**`、`wiki/**`、`agent/**`、`external_llm_wiki.py`
**参考**: PRD 成功指标；执行矩阵 J07 行

### [ ] Task 4: J13 质量追溯同源钻取
**描述**: 导入 R1-TRACE-V14（108 条），建立 需求→用例→计划/执行→缺陷/报告 同源链；覆盖率计算正确；断链/重复/
跨项目不计数且有明确状态。
**验收标准**: J13 P/N 全部 PASS；`/trace` 钻取与 DB 计数一致。
**涉及文件**: `test-platform-v2/backend/app/services/trace/**`、`app/api/v1/trace/**`
**参考**: PRD 成功指标；执行矩阵 J13 行

### [ ] Task 5: G56-012/014 剩余 J 条件 + UI 主链
**描述**: J03（RBAC 两项目三角色）、J08（用例/脑图）、J09（计划/执行/调度/幂等）、J15（真实浏览器 UI 自动化）、
J19（横向矩阵）真实正负面执行；报告与通知正负面证据（G56-012）。
**验收标准**: 对应 J 行 PASS；缺授权（J15 外部页/J16 媒体）登记 DEFERRED 不伪证。
**涉及文件**: `test-platform-v2/frontend/**`、`test-platform-v2/backend/app/api/v1/**`（按需只读验证，预计零代码改动）
**参考**: PRD §2/§3；执行矩阵 J03/J08/J09/J15/J16/J19 行

### [ ] Task 6: 正式域名发布演练
**描述**: 生产域名 `https://cameltv-test-platform1.vercel.app`（登录/首页/`/api` 反代/健康）与
`https://test-platform.up.railway.app/api/v1/open/health` 全链路实测；核对 ALLOWED_ORIGINS 与新域名一致；
登记发布决策（可用 / 需正式域名决策）。
**验收标准**: 全部 200 证据；`生产环境交付清单.md` 与 C-CONDITIONS 发布相关行更新。
**涉及文件**: `docs/production-delivery/生产环境交付清单.md`、`docs/外部阻塞项手动填写清单.md`

### [ ] Task 7: QA 报告 + Leader 判决 + 看板 + PR
**描述**: 汇总证据写 QA 报告、Leader 判决、更新 kanban，走 push 授权 → Draft PR → checks → 二次确认 → 合入。
**验收标准**: 六部门工件齐全；QA 全部门禁证据化；Leader 判决 APPROVED。
**涉及文件**: `test-platform-v2/work-logs/batch-68-ai-acceptance-{qa-report,leader-verdict}.md`、`kanbans/DEV-batch-68-ai-acceptance.md`

## 质量要求
- [ ] 硬门禁：后端 `ruff check app --select F821`、`pytest`（受影响模块）；前端 `npm run typecheck && npm run build`、Vitest 受影响模块
- [ ] 无调试遗留、无硬编码密钥；凭据只写 gitignored .env
- [ ] `git diff --check` 通过；每次 push 前按 AGENTS.md §2.4 展示摘要并获授权
- [ ] QA 每个 PASS 都有截图/日志/HTTP/DB 证据；缺证据的 J 项 DEFERRED（C63-2）
- [ ] KB 检索：编码/QA 前检索平台知识库相关模块历史缺陷（`platform_knowledge`/`defect_case`）
