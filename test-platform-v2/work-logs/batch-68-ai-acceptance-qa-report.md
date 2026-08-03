# Batch 68 — QA 报告（AI 验收全链路 + 正式域名发布演练）

> **QA (🔍)** | Date: 2026-08-03 | 状态: 🔄 进行中（Slice 1/2 部分证据已出；Slice 2~5 执行中）

## 测试总览

| 条件 | 通过 | 失败 | 阻塞/待执行 |
|:----:|:----:|:----:|:-----------:|
| Slice 1 环境 + C67-3 | 5 | 0 | 0 |
| J05 需求导入 + AI 提取 | 2 | 0 | 0 |
| J06 证据包全量闭环 | 106 页 | 0 | 全量采集+OCR+导入需求/知识/Wiki；N 路径 failed 可观察 |
| J07 AI 链路（P/N） | 6 | 0 | RAG/Wiki/Agent/差异对比真实 AI；截断失败正确拒绝（N） |
| J01 登录限流（N 路径） | 1 | 0 | 10 次/15 分钟触发 429 |
| J08 用例导入 | 50 | 0 | 真实 R1 用例 xlsx 导入 50/50 |
| J09 计划/执行 | 8 | 1 | 计划 1；7 过 1 败；幂等/状态持久验证 |
| J12 缺陷链 | 2 | 0 | 缺陷创建 + 合法流转；非法流转被拒 |
| J13 追溯矩阵 | 3 | 0 | coverage/trace/case/requirement 同源可钻取 |
| J10 报告链路 | 3 | 0 | 创建/详情/导出 xlsx |
| J03 RBAC 隔离 | 2 | 0 | 双项目/角色/跨项目 403 |
| J19 横向一致性 | 2 | 0 | API/DB 计数一致、分页一致 |
| Slice 5~6（发布演练登记/QA 终稿/PR） | 0 | 0 | 执行中 |

## 可执行门禁（命令、退出码、结果）

| # | 门禁 | 命令/方式 | 结果 |
|---|------|-----------|------|
| G1 | 后端启动 | `uvicorn app.main:app --port 8035`（batch-68 venv） | PASS：`GET /api/v1/open/health` → 200 `{status:ok, version:2.3.0}` |
| G2 | 前端启动 | `vite --port 5205` | PASS：`GET http://127.0.0.1:5205/login` → 200，title=CamelTv 测试平台 |
| G3 | AI Key 连通性 | `GET {AI_API_BASE_URL}/models`（batch-68 backend/.env Key，不回显） | PASS：HTTP 200（deepseek-v4-flash / deepseek-v4-pro） |
| G4 | OCR 依赖 | `F:/CamelTv/test-platform/.venv` 安装 paddleocr+paddlepaddle | PASS：`import paddle / paddleocr` 均成功（模型首跑下载数百 MB，Slice 2 触发） |
| G5 | lanhu-mcp 子模块 | `git submodule update --init lanhu-mcp` | PASS：c9f4a43（v1.5.0-238-gc9f4a43），`.env` Cookie 已就位（gitignored） |
| G6 | 后端硬门禁 | `ruff check app --select F821` | PASS：All checks passed |
| G7 | 前端硬门禁 | `npm run typecheck && npm run build` | PASS：tsc 0 错误；build 8.86s 成功 |

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

## 已出证据（Slice 2 部分）

### J05 — 需求文档导入 + 真实 AI 特征提取
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| R1 文档上传解析 | ✅ | `POST /requirements/upload`：用户端原型-需求分析.md（id=1）、运营后台-需求分析.md（id=2），parse_status=parsed |
| AI 特征提取 | ✅ | `POST /{doc}/extract` → DeepSeek 结构化模块/功能点/问题/建议；GET 回读确认 |
| 提取确认 | ✅ | doc1：8 模块 / 147 功能点；doc2：9 模块 / 106 功能点（`extraction/confirm` code=0） |

### J07 — AI 失败路径（N，可重试不产生假数据）
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| AI 生成用例截断 | ✅ 正确拒绝 | `POST /requirements/1/generate` 两次均返回 code=400「AI 返回的 JSON 格式异常」；原始响应保存至 `%TEMP%/ai_response_failed_*.json`（32KB 截断），未产生任何假用例 |

### J01 — 登录限流（N）
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 登录频率限制 | ✅ | 同一 IP 10 次/15 分钟触发 `HTTP 429`（连续 5 次验证），防暴力破解生效 |

### J06 — 证据包采集（进行中，部分证据）
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 任务创建/执行 | ✅ | job#1 状态 running（stage=capturing），total_pages=106，heartbeat 正常 |
| 页面采集 + OCR | ✅（部分） | 截至记录时 17 页 capture_status/ocr_status 均 success；已见「更新日志」「广告位系统」「银钻系统」「银钻预测玩法」等真实页面 OCR 文本 |
| 页面树/资产 | ✅ | Axure 资源下载约 65MB（4663+ 文件），docId=e6b5ce1e… 可追溯 |

### J06 — 全量闭环（已成功）
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 全量采集 + OCR | ✅ | job#1 status=success：106/106 页 capture_status=ocr_status=success；`lanhu_ocr_block` 10833 块 |
| 证据包导入 | ✅ | `POST /jobs/1/import`（requirement/knowledge/wiki 全开）→ code=0；生成需求文档 #4「蓝湖证据包 e6b5ce1e…」（source_ref=蓝湖 URL）；knowledge 源 4→6、切片 134→136 |
| 追溯可回源 | ✅ | 每页含 doc_id/version_id/page_id 与 source_url（page_discovery 全序 106 页） |
| 失败路径（N） | ✅ | job#2（无效 URL）→ status=failed，error=「URL parsing failed: missing required param pid」，可观察可重试，无假数据 |

### J03 — RBAC 双项目隔离
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 项目 B 创建 | ✅ | `POST /projects` → id=2「Batch68 验收项目 B」 |
| 受限角色 | ✅ | `POST /system/roles` → id=3「验收只读角色」（data_scope=project，permission=testcase:list） |
| 测试用户 + 成员 | ✅ | `POST /system/users` → id=3；`PUT /users/3` 绑定角色；`POST /projects/2/members` 加入项目 B |
| P：项目内访问 | ✅ | viewer 登录后 `GET /projects`（X-Project-Id=2）→ 200 仅见项目 B；`GET /test-cases`（proj2）→ 200 |
| N：跨项目隔离 | ✅ | viewer `GET /test-cases`（X-Project-Id=1）→ **403 无权访问该项目** |

### J19 — 横向一致性
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 分页/总数 | ✅ | `GET /test-cases?page=1&page_size=10` → total=50、items=10，与 DB `COUNT(*)`=50 一致 |
| 覆盖矩阵一致性 | ✅ | coverage 的 total/in_plans/executed/passed/defects 与计划 stats 与缺陷表一致 |

### J08 — 真实用例导入（R1 资产）
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| Excel 导入 | ✅ | `POST /test-cases/import/excel`：50 条真实 R1 用例（BASELINE-用户端 25 + ADMIN-运营后台 25）→ imported 50/50；域分布 用户端 25 / 运营后台 25 |

### J09 — 测试计划与执行
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 计划创建/关联 | ✅ | `POST /test-plans` id=1；`POST /{id}/cases` added 50 |
| 自动执行语义 | ✅ | manual 用例 execute-all 返回 skip「需人工执行」，不伪造通过 |
| 人工执行 | ✅ | 8 条执行：7 pass + 1 fail（pcase 4「切换视频线路」），stats pass=7 fail=1 skip=42 |
| 重复触发 | ✅ | 第二次 execute-all 正常返回，未产生重复执行记录 |

### J12 — 缺陷管理链
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| Triage 分类 | ✅ | `POST /test-plans/1/triage` 将失败分类为 bug（置信度 0.9 + 建议动作） |
| 缺陷创建 | ✅ | `POST /defects` id=1（关联 case 4 / execution 104） |
| 合法流转 | ✅ | open → confirmed 成功 |
| 非法流转（N） | ✅ | confirmed → invalid 被拒：「不允许从已确认转为 invalid。允许: fixing, rejected」 |

### J13 — 追溯矩阵同源钻取
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 项目覆盖矩阵 | ✅ | total 50 / in_plans 50 / executed 50 / passed 7 / with_defects 1；coverage_rate 100%、execution_rate 100% |
| 用例追溯链 | ✅ | `/trace/case/4`：TC-LIVE-004 → 计划 1 → 执行 fail(104)/skip → 缺陷 1；`/trace/case/1`：pass 链完整 |
| 需求覆盖 | ✅ | `/trace/requirement/1`：25 用例、in_plans 25、passed 7、defects 1、coverage_rate 100%（source_doc_id 种子数据：用户端→doc1、运营后台→doc2，DB 直写并文档化） |
| 已知差异 | ⚠️ | 项目级 `requirements_with_cases` 走 requirement_module 关联，需 J06 导入后填充（per-doc 矩阵已 PASS） |

### J10 / G56-012 — 报告链路
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 报告创建 | ✅ | `POST /reports` id=1（基于计划 1 真实统计） |
| 报告详情 | ✅ | `GET /reports/1` 返回名称/计划关联 |
| 报告导出 | ✅ | `GET /reports/1/export` → 200 application/vnd.openxmlformats（xlsx 9.2KB） |

### J07 — 知识/RAG/Wiki/Agent 真实 AI 闭环
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| RAG 健康 | ✅ | `GET /knowledge/search/health`：rag_enabled、embedding BAAI/bge-small-zh-v1.5 available、vector_search_functional、embedding_coverage=1.0（134/134） |
| 知识源/切片 | ✅ | 4 源 / 134 切片 / 3 实体；含「蓝湖证据包 e6b5ce1e…」（J06 采集物实时入库） |
| 混合检索 | ✅ | `POST /knowledge/search`（query=直播间切换视频线路）命中真实切片（含「切换视频线路后偶发无画面」缺陷与「根目录/更新日志」证据页） |
| Wiki 页面 | ✅ | `GET /wiki/pages` 4 页（Wiki 索引 + 蓝湖证据包来源页） |
| Agent 运行 | ✅ | `POST /agents/run/requirement_analysis` → run#1 success，AI 产物#1：分析引用了真实缺陷（线路切换偶发无画面） |
| Wiki 差异对比 | ✅ | `POST /wiki/diff/tasks`（rag_vs_wiki）→ task success，8 条差异项 |
| 失败路径（N） | ✅ | `POST /requirements/1/generate` 两次截断 → 400 拒绝、保存原始响应、零假用例（可重试） |
