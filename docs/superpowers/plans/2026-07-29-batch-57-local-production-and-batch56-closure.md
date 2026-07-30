# Batch 57 Local/Production 与 Batch 56 遗留闭环计划

> **For agentic workers:** 按任务顺序实施；外部输入未提供时只标记
> `BLOCKED`，不得构造通过证据。

**Goal:** 测试平台自身只保留 local 与 production 两种固定身份；当前运行
local，production 在服务器采购后再绑定真实 URL 与数据库。修复所有仓库内
可复现的 Batch 56 遗留，并为外部环境阻断建立可执行、可复核的输入清单和
证据闭环。

**Architecture:** local 固定使用 `http://localhost:5173` 与隔离 SQLite；
production 当前只保留模板、独立 Compose project 和 PostgreSQL 安全契约，
服务器采购后才创建受 Git 忽略的真实 profile。启动器只接受
`local|production`，页面 `/environment` 仍管理被测系统的
dev/test/staging/prod 地址和变量，不切换测试平台自身数据库。

**Provisioning decision (2026-07-29):** production 服务器尚未采购，缺少真实
URL 不计为 Batch 57 缺陷；真实部署验收移入基础设施就绪后的独立批次。

**Boundary:** 外部业务系统的 503、鉴权、登录会话、VPN、ELK、真机、AI/OCR、
蓝湖和旧库问题，只有在对应服务、授权或数据进入本任务范围后才能修复或复测。
缺少输入时保留 `BLOCKED`，不以本地 Mock 或静态检查替代。

---

## Task 1：将三实例运行拓扑收敛为两实例

**Files:**

- Delete: `test-platform-v2/config/runtime/test.env.example`
- Modify: `test-platform-v2/config/runtime/local.env.example`
- Modify: `test-platform-v2/config/runtime/production.env.example`
- Modify: `test-platform-v2/scripts/start-platform-environment.ps1`
- Modify: `test-platform-v2/backend/tests/test_runtime_environment_profiles.py`
- Modify: `test-platform-v2/backend/.env.example`
- Modify: `test-platform-v2/frontend/.env.example`
- Modify: `test-platform-v2/README.md`
- Modify: `test-platform-v2/deploy/README.md`

- [x] 测试先改为只读取 `local`、`production`，断言模板目录不存在第三个
  runtime profile。
- [x] 启动器的 `ValidateSet` 只允许 `local`、`production`；生产实例仍要求
  HTTPS、PostgreSQL、secure cookie、无占位符和显式确认。
- [x] 删除 test runtime 模板和所有“测试平台自身三环境”操作说明。
- [x] 保留 `/environment` 的被测系统多环境能力，并在文档中明确两者边界。
- [x] 运行 profile/Compose 定向测试和 PowerShell 语法检查。

## Task 2：修复环境管理跨项目隔离风险

**Files:**

- Modify: `test-platform-v2/backend/app/api/v1/environment.py`
- Modify: `test-platform-v2/backend/app/services/environment_service.py`
- Modify/Create: `test-platform-v2/backend/tests/test_environment.py`

- [x] 先补跨项目读取、更新、删除、变量读取/更新/删除和 resolve 的失败用例。
- [x] 所有环境操作使用 `project_id + environment_id` 联合归属校验。
- [x] 所有变量操作同时校验变量属于该环境且该环境属于当前项目。
- [x] 跨项目 resolve 不得返回密文、明文或变量存在性细节。
- [x] 运行环境模块聚焦测试与后端 F821 门禁。

## Task 3：补齐 Batch 56 交付物与一致性

**Files:**

- Create: `test-platform-v2/work-logs/batch-56-production-acceptance-issue-register.md`
- Create: `test-platform-v2/work-logs/batch-56-production-acceptance-leader-verdict.md`
- Create: `test-platform-v2/work-logs/evidence/batch-56-production-acceptance/README.md`
- Modify: `C-CONDITIONS.md`
- Modify: `docs/work-logs/batch-56-production-acceptance-execution-matrix.md`
- Modify: `docs/superpowers/plans/2026-07-29-batch-56-full-platform-production-acceptance.md`
- Modify: `test-platform-v2/work-logs/batch-56-production-acceptance-qa-report.md`
- Modify: `test-platform-v2/work-logs/batch-57-environment-targets-and-batch56-acceptance.md`

- [x] 将 B56-B01～B10 逐项登记优先级、状态、责任边界、输入、复测和关闭标准。
- [x] 将 G56-011/G56-012/G56-013/G56-014/G56-015/G56-016 与实际代码和交付物
  重新对账；G56-013 已由 B57-PC-01 的 11/11 PC P0 矩阵关闭，
  G56-011/G56-012/G56-014/G56-015 保持 OPEN，G56-016 只关闭交付物对账且
  不等于 A12 PASS。
- [x] 按用户最新口径将 C55-5/G56-013 的 P0 视口限定为 PC `1440×900`；
  tablet `768×1024` 与 mobile `390×844` 登记为 P2 非阻断项。
- [x] Leader Verdict 与 QA 报告保持同一机械结论：存在 P0/P1 阻断即
  `NEEDS WORK`。
- [x] 证据索引只登记可复现路径、命令、退出码、环境与脱敏状态。
- [x] C 条件不得把外部未执行项写成 CLOSED。

## Task 4：处理 Knowledge/Wiki/Trace 代码遗留

**Files to inspect first:**

- `test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx`
- `test-platform-v2/backend/app/services/version_differ.py`
- `test-platform-v2/backend/app/services/attachment_extractor.py`
- `test-platform-v2/backend/app/services/navigates_to_extractor.py`

- [x] 逐项确认固定“未同步”、AI diff fallback、附件 AI stub、多模态/DOM
  简化逻辑是否有现成真实 provider 契约。
- [x] 有仓库内真实数据源和 provider 契约的，补测试后实现；Wiki 同步覆盖率
  已改为读取最新 active 发布包真实 coverage。
- [x] 依赖真实 AI/OCR/设计源的，保持明确 unavailable 状态并归入
  B56-B05/B56-B09，不把规则 fallback 标成 AI 成功。
- [x] 更新 G56-011 状态及验收证据。

## Task 4.5：缩小 C55-4 本地生命周期缺口

- [x] 计划、执行、报告、调度、缺陷和通知配置的审计记录显式提交并以请求
  结束后 rollback 模拟验证持久化。
- [x] 缺陷创建/更新联合验证 case、execution 和 project 归属及一致性。
- [x] 为计划补齐失败分诊路由和可见 UI，一键缺陷草稿保留 case/execution。
- [x] 调度从“创建 pending 后误报完成”改为真实执行计划，并记录 completed/
  failed 终态。
- [x] 使用 DB running claim、APScheduler `max_instances=1` 和 coalesce 拒绝
  当前运行中的重复触发；完成通知只在整份计划无 pending 时发送。
- [x] 13 项生命周期专项测试和双端全量回归通过。
- [ ] G56-012 仍需真实 UI/API/DB/报告/通知的完整正负面旅程，不因单元/
  集成测试自动关闭。

## Task 5：逐项执行外部阻断复测

- [ ] B56-B01：获得节点 6 URL、网络边界和服务恢复确认后复测 503。
- [ ] B56-B02：获得六服务实时 OpenAPI URL 或带来源/SHA 的脱敏快照后复核。
- [ ] B56-B03：获得公开/受保护接口清单与最小权限账号/Token 后复测无效 Bearer。
- [ ] B56-B04：获得运营后台 URL、可登录账号和允许的只读动作后复测浏览器会话。
- [ ] B56-B05：获得 AI 与 OCR provider 配置后验证真实输出和无 fallback。
- [ ] B56-B06：获得设备代理/SoloX、授权设备和采样窗口后执行真机性能。
- [ ] B56-B07：获得 ELK URL、索引、只读凭据与 trace 时间窗后关联验证。
- [ ] B56-B08：获得脱敏旧 PostgreSQL 快照、版本、SHA 和基线后隔离恢复升级。
- [ ] B56-B09：获得精确设计源链接、只读授权或可追溯导出后重建证据包。
- [ ] B56-B10：获得生产 URL、vpn07 边界、只读账号和批准窗口后复测。

所有秘密只写入已忽略的本地 profile/secret 文件，不写聊天、Git、日志或截图。

## Task 6：完整回归与交付

- [x] 后端：F821、受影响模块 Pytest、全量 Pytest。
- [x] 前端：typecheck、受影响 Vitest、全量 Vitest、build。
- [x] 运行：local 启动/status/幂等复用，production profile 静态校验与
  Compose config。
- [x] 浏览器：`http://localhost:5173` 登录、工作台、console/network。
- [x] 安全：秘密、调试遗留、数据库、运行产物和提交范围扫描。
- [x] 更新 QA、issue register、evidence index 和 Leader Verdict；只按真实
  结果关闭条目。
- [ ] 本地提交后停止；push 前按 AGENTS.md 展示新范围并重新获取逐次授权。
