# Batch 227 — PM Plan

> PM | Date: 2026-09-03 | Mode: full | Executor: Codex

## Task 1：接入信息契约

**范围**：为 BusinessOnboarding 增加 `version`、`requirement_text`，补单头 Alembic migration，并让 Step 2 创建需求文档、正确绑定 VersionTask。

**验收**：16.0.0 独立落库；需求正文进入 `requirement_document`；旧调用仍有安全默认值；迁移单头与 revision 长度通过。

## Task 2：聚合就绪检查

**范围**：新增 `GET /api/v1/onboarding/readiness`，单次返回 AI 最近真实健康态、Temporal 配置态、在线 Runtime Worker 数量，以及 baseline/durable 两种就绪结论。

**验收**：AI unknown/error 不算 ready；失联 Worker 先标记 offline；Temporal/Worker 标记 `managed_by=platform`；接口不启动任何进程、不发重复外部请求。

## Task 3：接入页重组

**范围**：把页面整理为“你需要填写”“平台自动检查”“接入进度”“历史记录”四个清晰区块；补永久 Label、加载/错误/重试、提交中状态和响应式布局。

**验收**：六项缺一不可；管理员配置入口明确；B15 与耐久运行口径分离；桌面/平板/手机无溢出；页面加载每类 GET 仅一次。

## Task 4：自动化与交付证据

**范围**：后端服务/API/迁移测试，前端组件测试，双端硬门禁，浏览器真实路径与三视口截图，QA/Leader 工件。

**验收**：相关测试、全量测试、typecheck/build/F821/Alembic/dev-gate 有退出码；浏览器控制台无错误；Leader 在用户总确认、required checks 和最终审计后才能 APPROVED。

## 依赖与顺序

Task 1 → Task 2 → Task 3 → Task 4。预计 5 小时。任何真实 AI、OpenAPI、被测环境或 Runtime 外部失败都保留 BLOCKED，不用 mock 作为业务通过证据。
