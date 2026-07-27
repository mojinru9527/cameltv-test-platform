# DEV 测试平台 Test5、音视频、RAG 与通知实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 当前会话未提供 executing-plans skill，按本计划逐项实施并在每项后运行验证。

**Goal:** 让 DEV 部门像普通用户一样从测试平台 Web 前端完成测试5环境配置、蓝湖需求采集、音视频专项记录、RAG 检索、通知配置和六组 API 资产导入/增改查验证。

**Architecture:** 保留现有 FastAPI + React 分层。音视频专项以 ffprobe 真实流探测和人工/外部采集结果录入两条路径组成，不生成模拟指标；统计由后端统一计算。通知中心增加通用任务生命周期事件，并由专项/API/UI/计划执行入口发出。RAG 使用本地 fastembed 模型，知识切片回填后验证向量与混合检索。所有账号通过环境变量管理页加密保存，测试动作从 DEV Web 发起。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic、React 18、TypeScript、Playwright、ffprobe、fastembed/ONNX、pytest、Vitest。

---

## Task 1：建立音视频专项真实测量模型和统计服务

**Files:**
- Modify: `test-platform-v2/backend/app/models/av_check.py`
- Modify: `test-platform-v2/backend/app/schemas/av_check.py`
- Modify: `test-platform-v2/backend/app/services/av_check_service.py`
- Modify: `test-platform-v2/backend/app/api/v1/av_check.py`
- Create: `test-platform-v2/backend/alembic/versions/<revision>_add_av_measurements.py`
- Create: `test-platform-v2/backend/tests/test_av_measurements.py`

**Implementation:**
- 新增测量记录表，保存指标类型、场景、采集方法、网络/设备、样本值、阈值、比较方向、备注和统计结果。
- 支持视频延迟、连麦延迟、音画同步、帧率、首帧耗时五类模板。
- 后端使用真实样本计算 mean/median/min/max/stddev/p95 和是否达标；拒绝空样本、NaN、非法阈值和未知指标。
- 提供模板列表、记录新增/查询/删除接口；现有 ffprobe 指标继续保留。

**Verification:**
- `pytest backend/tests/test_av_measurements.py -q`
- 正向：12 个样本统计正确；反向：空样本/非法类型返回 422 或 400。

## Task 2：在 Web 前端提供音视频文档化执行界面

**Files:**
- Modify: `test-platform-v2/frontend/src/api/avcheck.ts`
- Modify: `test-platform-v2/frontend/src/types/index.ts`
- Modify: `test-platform-v2/frontend/src/pages/special/index.tsx`
- Create: `test-platform-v2/frontend/src/pages/special/__tests__/SpecialMeasurements.test.tsx`

**Implementation:**
- 新建任务时选择“流地址自动探测”或“采集结果录入”。
- 详情页展示历史总结中的五类模板、测试前置条件、样本输入、阈值、采集方法、环境和设备信息。
- 保存后展示平均值、P95、最大/最小值、标准差和达标结论，不展示随机值。
- 表单包含必填、数值和边界校验，并保留删除确认。

**Verification:**
- `npm test -- --run src/pages/special/__tests__/SpecialMeasurements.test.tsx`
- `npm run build`

## Task 3：补齐任务开始、结束和测试结果通知

**Files:**
- Modify: `test-platform-v2/backend/app/services/notify_service.py`
- Modify: `test-platform-v2/backend/app/api/v1/notify.py`
- Modify: `test-platform-v2/backend/app/api/v1/av_check.py`
- Modify: `test-platform-v2/backend/app/services/api_task_worker.py`
- Modify: `test-platform-v2/backend/app/services/ui_test_service.py`
- Modify: `test-platform-v2/backend/app/services/test_plan_service.py`
- Modify: `test-platform-v2/frontend/src/pages/notify/index.tsx`
- Create: `test-platform-v2/backend/tests/test_task_lifecycle_notifications.py`

**Implementation:**
- 新增 `task_started`、`task_finished`、`test_result` 三个可订阅事件和统一模板。
- 关键任务启动/结束时使用独立数据库会话发送，写入通知日志，不阻塞测试执行。
- Webhook 密钥和 SMTP 密码不写入页面或日志；测试发送支持指定生命周期测试消息。
- 未获得真实 Webhook/SMTP 与收件人前，Web 中建立禁用的 DEV 配置模板，不向外部发送。

**Verification:**
- `pytest backend/tests/test_task_lifecycle_notifications.py -q`
- 使用本地 Webhook 接收器验证三类事件的请求体和通知日志。

## Task 4：恢复完整 RAG 向量能力

**Files:**
- Verify: `test-platform-v2/backend/requirements.txt`
- Modify only if needed: `test-platform-v2/backend/.env.example`
- Add test if missing: `test-platform-v2/backend/tests/test_rag_runtime.py`

**Implementation:**
- 在实际后端虚拟环境安装 requirements 中的 fastembed。
- 预加载 `BAAI/bge-small-zh-v1.5`，确认输出维度与配置一致。
- 重启后端，通过 DEV Web 执行“重新向量化”，核对健康状态、向量切片数和混合检索结果。
- 如果模型源无法访问，记录所需模型镜像/缓存目录授权，禁止把关键词降级误报为完整 RAG。

**Verification:**
- 后端运行时 `embedding_service.available()` 为 true。
- Web 健康检查显示 embedding 可用，vector/hybrid 检索均返回相关知识切片。

## Task 5：通过 DEV Web 配置测试5和蓝湖运营后台需求

**Files:**
- Create temporary browser script under `F:/tmp/` only for execution evidence.

**Implementation:**
- 登录 DEV，创建“CamelTv 体育测试5环境”，保存项目地址、六个 API 文档基址以及加密账号变量。
- 蓝湖用户端复用已成功证据任务；创建运营后台单页证据任务，启用截图、OCR、Word/JSON、需求/知识库导入。
- 从环境管理页完成增改查验证，并保留审计日志。

**Verification:**
- Web 环境列表可见测试5且敏感变量掩码显示。
- 运营后台证据任务成功，资产、需求和知识源可在 Web 查看。

## Task 6：导入六组 API 并执行安全增改查闭环

**Files:**
- Create: `tests/api/test5/README.md`
- Create: `tests/api/test5/<service>-crud-cases.md`（按团队接口用例标准）

**Implementation:**
- 对每个 Knife4j 地址解析 `/swagger-resources` 和实际 OpenAPI JSON 地址。
- 通过 DEV Web 逐个预览和确认导入，按服务归类资产并生成正向/反向接口用例。
- 优先在测试5创建带 `codex-dev-<timestamp>` 前缀的临时数据，执行 create→query→update→query，若有安全删除接口则清理。
- 禁止调用支付扣款、转账、封禁、批量删除、生产发布等非普通 CRUD 副作用接口。

**Verification:**
- 六个服务均有导入批次和知识源；记录成功/失败/阻塞数量。
- 每个执行过的写操作均可查询验证，临时数据可清理则清理。

## Task 7：DEV Web 全流程回归与交付

**Files:**
- Create: `test-platform-v2/docs/DEV-Test5-使用与授权清单.md`

**Implementation:**
- 从 Web 完成环境、需求、知识库、API、UI、音视频、通知、计划、报告和审计页面检查。
- 输出 Webhook/SMTP 可直接填写的配置清单；仅把缺失的真实地址、邮箱、API 令牌列为授权项。
- 汇总证据编号、执行结果和遗留限制。

**Verification:**
- 后端相关 pytest、前端 Vitest/build 全部通过。
- Playwright 可见浏览器回归核心页面，并保存关键截图/运行记录。
