# Batch 258 — PM Plan

> **PM (🟨)** | Date: 2026-09-18
> 对应 PRD: [batch-258-execution-node-protocol-prd-summary.md](batch-258-execution-node-protocol-prd-summary.md)

## 规格摘要

**原始需求**: `docs/platform-refactor/10-landing-plan-task-backlog.md` §2「B1」表 B1-1…B1-7；
硬约束取 §4，安全硬线取 `09-platform-landing-plan.md` §4.1。
**目标时间**: B1 原计划 W1–W2（8 周计划的前两周）。
**范围纪律**: 只做 B1 表内任务；B2（沙箱/菜单收敛）、B3（知识主线）、B4（3 版本验收）不在本批。

## 开发任务

### [ ] Task 1: 统一出网守卫 `assert_public_url()`（B1-1）
**描述**: 把 `app/core/outbound_policy.py` 中已验证的私网/回环/链路本地拒绝、重定向二次校验、
响应体上限抽为纯断言模块 `app/core/url_guard.py`，导出 `assert_public_url()` 作为用户可控 URL 出网的唯一入口；
`outbound_policy` 改为依赖 `url_guard`，保持既有行为与 3 条既有测试不变。
**验收标准**:
- `app/core/url_guard.py` 存在且导出 `assert_public_url(url)` 与 `assert_public_url_after_redirect(base, location)`
- 5 个恶意 URL（`127.0.0.1` / `169.254.169.254` / 内网域名 / 重定向跳转 / 大响应）全部被拒
- `outbound_policy.validate_outbound_url` 行为不变，`tests/test_outbound_policy.py` 3 条仍绿
**涉及文件**: `app/core/url_guard.py`（新增）、`app/core/outbound_policy.py`、`tests/test_url_guard.py`（新增）
**参考**: PRD §1 §2；bug-guard「出网 / 执行 / 凭据安全」第 1 条；审计基线 S1

### [ ] Task 2: 需求抓取与发布包导入接入守卫（B1-1 调用点）
**描述**: `requirement_source_service._request()` 出网前调用 `assert_public_url()`；
`follow_redirects=True` 改为逐跳手动跟随并对每一跳目标二次校验（含相对 `Location`）；
响应体加硬上限（`settings.outbound_max_response_bytes`，默认 10MB，可配 5MB）。
两个调用点（`requirement_docs.py` 需求 URL 导入、`release_bundles_core.py` 发布包导入）都经 `fetch_url_content()`，改一处即覆盖两处。
**验收标准**:
- 内网/回环/链路本地 URL 被拒并返回可读错误（`kind="guard"`）
- 302 跳转到 `127.0.0.1` 被拒
- 超过上限的响应被拒
**涉及文件**: `app/services/requirement_source_service.py`、`tests/test_batch258_requirement_source_guard.py`（新增）
**参考**: PRD §4；backlog B1-1 DoD

### [ ] Task 3: 令牌域名白名单（B1-2）
**描述**: `classify_url()` 改为配置化根域白名单匹配（根域及其子域），默认 `lanhuapp.com` / `pingcode.com` / `atlassian.net`，
支持环境变量覆盖（自建实例场景）；非白名单主机一律回落 `generic`，因此不携带任何凭据 Header；
并在发请求前断言解析 IP 为公网地址。
**验收标准**:
- `pingcode.attacker.tld` → `classify_url` 返回 `generic`，请求不含 `Authorization`
- `x.pingcode.com` → `pingcode`，携带 `Authorization`
- 自建域名经配置加入白名单后分类正确
**涉及文件**: `app/core/config.py`、`app/services/requirement_source_service.py`、`tests/test_batch258_token_whitelist.py`（新增）
**参考**: PRD §4；审计基线 S2；H3

### [ ] Task 4: OCR 去 `shell=True`（B1-3）
**描述**: `LocalCommandOcrProvider.recognize()` 改为 `shlex.split` 参数数组 + `shell=False`；
模板插值用哨兵占位再回填（**禁止先插值后 split**，否则含空格路径会被切成多个 argv）。
**验收标准**:
- `rg "shell=True" app/` 为空
- 图片路径含空格、含分号时命令仍为单一路径参数
- 默认模板（内置 rapidocr CLI）与自定义模板均可解析
**涉及文件**: `app/services/lanhu_evidence/local_ocr_provider.py`、`tests/test_batch258_ocr_command.py`（新增）
**参考**: PRD §4；审计基线 S3；bug-guard 第 3 条

### [ ] Task 5: `ExecutionJob` 协议 + 迁移（B1-4）
**描述**: 新增 `ExecutionJob` / `JobLease` 模型与 Alembic 迁移（单头）；实现 claim / heartbeat / report /
stale 回收 API，权限点独立（不复用 `uitest:trigger`）；跨项目不可认领。
**验收标准**: 认领→心跳→上报→超时回收全链路测试通过；跨项目认领返回 404
**涉及文件**: `app/models/execution_job.py`、`alembic/versions/*`、`app/api/v1/execution_jobs.py`、`app/services/execution_job_service.py`、`tests/test_batch258_execution_job_protocol.py`
**参考**: PRD §5；方案 §3.2；bug-guard「加列迁移前先搜是否已存在」

### [ ] Task 6: `cameltv-node` CLI（B1-5）
**描述**: `scripts/node/` 提供 `up`（注册+心跳+认领循环）、`run-api`、`run-web`、`upload`；README 说明一键用法。
**验收标准**: `cameltv-node up` 一条命令可用；断网 30s 后任务回 pending 并可再认领
**涉及文件**: `scripts/node/**`
**参考**: backlog B1-5 DoD

### [ ] Task 7: 平台侧节点状态（B1-6）
**描述**: 首页/版本任务页显示节点在线/离线、队列长度、一键启动指引。
**验收标准**: 无节点时明确提示；节点上线后 10s 内刷新；异步 effect 带 cleanup；TabsContent 条件渲染
**涉及文件**: `frontend/src/pages/**`、`frontend/src/api/**`
**参考**: bug-guard React 四条铁律

### [ ] Task 8: B1 端到端证据（B1-7）
**描述**: 5 条接口 + 3 条 Web 用例经本地节点真实执行，证据可下载。
**验收标准**: 8/8 执行成功、证据可下载、失败用例有截图/请求回放
**风险**: 依赖 Test5 内网 + VPN 可达性；不可达时按 Deferred 记录，不伪造通过
**参考**: PRD §5「已知风险」

## 质量要求

- [ ] 响应式（Desktop + Tablet）  - [ ] OpenAPI 同步  - [ ] 单元测试覆盖
- [ ] 无障碍（ARIA/键盘）  - [ ] 无 console 报错/告警
- [ ] 提交前 `pwsh scripts/git/dev-gate.ps1`：G0–G2 无 HARD/类型/守卫失败
- [ ] 每切片只 `git add` 本切片文件，禁止夹带
