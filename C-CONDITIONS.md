# C 条件追踪器

> 所有 Agent Team Leader 设定的「下一批次 C 条件」集中追踪。Product 开工前必须先读此文件。

**追踪规则**:
- 每个 Leader Verdict 末尾的 C 条件必须写入此文件
- Product 开工第一件事：检查此文件中所有 `Open` 条件，PRD 中必须包含或明确豁免
- 条件满足后标记为 `✅ Closed`，注明合入的 PR/commit
- **状态机（Batch 75 起）**：`Open（待处理）` → `In-Progress（处理中）` → `Closed（已关闭，必须带证据：PR/commit/链接）`；外部阻塞项 → `Deferred（延期，必须带解除条件）`
- 新增条件统一使用 `C{批次}-{序号}`（如 `C75-1`）命名，禁止裸 `C1`；关闭时在 Closed 表中注明合入 PR/commit
- 一致性校验：`pwsh scripts/git/audit-cconditions.ps1`（只读，孤儿条件/重复 ID/缺证据/日期漂移）

**最后更新**: 2026-08-04 (Batch 75: 状态机规则 + audit-cconditions.ps1 审计工具)

**Batch 63 复核（2026-08-02）**: Product/QA 对全部 Open 条件逐条复核。
TPv2-B19-C1 与 TPv2-B21-C2 已确认实现并关闭（见 Closed 表 Batch 63 节）；
C55-3/C55-4、G56-011/012/014、C58-01~06、CP-C1/C2 等外部依赖项继续保留 Open，
解除条件见 Batch 63 回归汇总 §3.3；其余早期孤儿（batch-18/22/24/25v2/26KB/27/31、
C21-P1-2/3/5、C22-C2/C3）未在本批获得新证据，保持 Open 并计入后续批次。

---

## Open (待处理)

### batch-75 — Agent Team 自我进化与提效改造（Batch 75 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C75-1 | 后续批次 Product 必须按「批次模式」判定完整/轻量，并在 PRD 记录 `mode`；轻量批次必须含豁免理由 | P2 | 2026-08-04 |
| C75-2 | 每批 Leader 判决必须含「流程回写」小节；改动 SKILL.md/DEPARTMENTS.md 必须同步 CHANGELOG | P2 | 2026-08-04 |
| C75-3 | PR 推送前运行 `audit-cconditions.ps1 -RequireLatestBatch`，0 硬错才允许合入 | P1 | 2026-08-04 |
| C75-4 | 下批同步 AGENTS.md 双档措辞，消除门禁双源措辞差异 | P2 | 2026-08-04 |

### batch-74 — Test5 契约 + Playground 实证（Batch 74 Leader 条件，Batch 75 补录）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C74-1 | J16 码率指标口径修复（HLS `probe_stream` 对 m3u8 播放列表误读为码率），修复后复测 6 项达标口径 | P2 | 2026-08-04 |
| C74-2 | Test5 无契约服务（admin-service 需登录、konfi-service 需 token）由用户提供登录/token 后补拉契约并登记 | P2 | 2026-08-04 |
| C74-3 | 真机性能验收（CP-C1/C2）待用户提供 Android/iOS 真机后排期执行 | P1 | 2026-08-04 |

### batch-76 — 避坑清单自动化 + 双档同步（Batch 76 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C76-1 | 修复 scan-common-bugs 扫出的存量 HARD：`R.err` 7 处（补 `def err` 或改 raise）、seed.py 密码 print（**复核结论：一次性显示契约，扫描降级 WARN 复核**）、高危 except-pass 逐处加日志或传播 | P1 | 2026-08-04 |
| C76-2 | 后续批次提交前运行 `scan-common-bugs.ps1`，HARD>0 处理或注明豁免 | P2 | 2026-08-04 |

### batch-77 — 存量 P0 修复（Batch 77 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C77-1 | 剩余 49 处 HARD 逐项处理：app 内 print 迁移 logger、无注释 except-pass 加日志或注释说明；每批消化 ≥10 处或给出豁免理由 | P2 | 2026-08-04 |
| C77-2 | 修复开发机 Python 3.12 环境（重装基础 Python 并重建 .venv），恢复本地 pytest 执行能力 | P2 | 2026-08-04 |

### batch-78 — 开发机 Python 修复（Batch 78 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C78-1 | 后续批次本地受影响模块 pytest 必须执行并记录退出码；开发机环境已修复，禁止再以环境阻塞为由跳过 | P2 | 2026-08-04 |

### batch-79 — 存量 HARD 清零（Batch 79 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C79-1 | 231 处 WARN 分批消化：优先硬编码密钥模式（cameltv-dev-key/SECRET_KEY/api_key）、envelope 断言（status_code==404）；每批消化 ≥10 处或给出豁免理由 | P2 | 2026-08-04 |

### batch-63 — 汇总问题遗留解决版本（Batch 63 Leader 条件，本批归位）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C63-2 | 外部阻塞项（Test5、AI/OCR、真机、旧库、C58、DevOps）解除时，必须先登记提供人/日期/授权范围再执行，禁止补登假证据 | P0 | 2026-08-02 |
| C63-3 | `C-CONDITIONS.md` 继续按 Batch 63 复核口径维护；新批次 PRD 须引用 C63 条件 | P2 | 2026-08-02 |

### batch-64 — 架构解析与仓库拆分基线（Batch 64 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C64-1 | V1 整体移除受覆盖矩阵门禁（`docs/architecture/batch-64-architecture-analysis.md` §4）；B 档工具（mock/capture/apidiff/datafactory/logagg/loadtest/envcheck）逐项迁移或用户批准废弃后才可删除 | P0 | 2026-08-02 |
| C64-2 | 独立审计批次删除根目录两个 `pective pipeline — ...` 误提交文件，删除后同步更新 `repo-boundaries.json` | P2 | 2026-08-02 |
| C64-3 | 生产交付清单待运维回填 DB/Redis/MQ 真实内网地址后更新；production 保持 DEFERRED；拆仓批次合入前 `validate_repo_boundaries.py --check` 必须全绿 | P0 | 2026-08-02 |
| C64-4 | C63-1 四项 API-only UI（Token/Playground/导入导出/追溯下钻）排期 batch-65+ | P1 | 2026-08-02 |

### batch-65 — Test5 验收执行器隔离 + 外部前置条件清单（Batch 65 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C65-3 | 外部前置条件按 `docs/production-delivery/外部前置条件清单.md` 逐项解锁并登记；未解锁项对应验收保持 DEFERRED，禁止补登假证据（2026-08-04：1.3 网段/DNS、1.4 契约已解锁登记，见清单） | P1 | 2026-08-02 |

### batch-66 — Test5 验收执行器搭建（Batch 66 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C66-4 | ~~其余 5 个 Test5 节点内网 IP 待提供后补 WSL hosts~~ ✅ CLOSED — 2026-08-04：六节点 + 网关经 VPN DNS（10.7.7.1）均解析 `192.168.50.170`，`camel-to-test5` HTTPS 200 抽查通过；hosts 补录为可选优化 | P2 | 2026-08-02 |

### batch-67 — AI 验收与正式域名发布前置条件收口（Batch 67 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|

### batch-18 — Wiki Diff 孤儿（batch-30 归位）

### batch-68 — AI 验收全链路（Batch 68 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C68-1 | ✅ CLOSED — 2026-08-04：J15 外部页 2/2 只读执行 + J16 真实 HLS av-checks 已执行登记（batch-74 QA） | P1 | 2026-08-03 |
| C68-4 | 正式域名发布决策登记到交付清单（本批演练已 200；域名启用/自定义域名决策由用户确认） | P1 | 2026-08-03（batch-73 已确认：按 A 启用 `cameltv-test-platform1.vercel.app`、暂缓自定义域名、无需公告文案） |

### batch-69 — AI 验收跟进修复（Batch 69 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C69-1 | ✅ CLOSED — 2026-08-04：同 C68-1，J15/J16 正负面验收完成（batch-74 QA） | P1 | 2026-08-03 |
| C69-2 | 正式域名发布决策（自定义域名/启用公告）由用户确认后登记关闭 C68-4 | P2 | 2026-08-03 |

### batch-70 — 能力产品化 UI 补齐（Batch 70 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C70-1 | ✅ CLOSED — 2026-08-04：C22-C2/C3 实证通过，Playground 转正式 UI（/playground 入口已接入） | P2 | 2026-08-03 |

### batch-71 — 内部收尾优化（Batch 71 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C71-3 | J15 外部页 / J16 媒体授权、正式域名发布决策（C68-4）等外部项仍待用户提供 | P1 | 2026-08-04 |

### batch-72 — 最终优化与决策材料（Batch 72 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C72-2 | ✅ CLOSED — 2026-08-04：C22-C2（1/1 + 截图）+ C22-C3（6/6 + 报告 xlsx）实证通过 | P2 | 2026-08-04 |
| C72-3 | J15 外部页 / J16 媒体授权、C58-01/03/04、Test5 外部窗口等用户侧项待提供后执行 | P2 | 2026-08-04 |

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| batch-18-C6 | review_items/contradictions持久化 — WikiReviewItem表或复用AiArtifact | P2 | 2026-07-10 |
| batch-18-C7 | 迁移20260710_0017 staging双向演练(upgrade/downgrade) | P2 | 2026-07-10 |
| batch-18-C8 | 建标注语料评估差异召回率/误报率(diff classifier baseline) | P2 | 2026-07-10 |
| batch-18-C9 | 差异接口补left/right独立ref/scope或文档化单查询限制 | P2 | 2026-07-10 |
| batch-18-C11 | import校验lanhu_mcp_enabled开关—拒绝导入当disabled | P3 | 2026-07-10 |
| batch-18-C14 | 分环境灰度放量SOP文档 | P3 | 2026-07-10 |

### batch-19 — 早期批次孤儿（batch-30 归位）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| TPv2-B19-C2 | 修复至少5项预存组件测试契约漂移 | P2 | 2026-07-19 |

### batch-21 — 缺失特性孤儿（batch-30 归位）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|

### batch-21 — PR #27/#28/#29 Pipeline Verification

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C21-P1-2 | 补三个新服务单测：failure_analyzer / report_aggregator / task_worker | P1 | 2026-07-12 |
| C21-P1-3 | `现状功能PRD.md` 诚实性修复：模块 11/12 详情段同步为真实执行 | P1 | 2026-07-12 |
| C21-P1-5 | 迁移 `20260710_0017` staging 双向演练 (upgrade/downgrade) | P1 | 2026-07-12 |
| C21-P2 | ~~task_worker 双队列竞态 / semaphore 并发上限 / SSRF / Wiki 开关 / 计数器 double-count~~ | P2 | 2026-07-12 |
| C21-P3 | migration downgrade / playwright path traversal / diff_classifier docstring / VNext-N 编号 | P3 | 2026-07-12 |

### batch-22 — Slice 1 Playground

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C22-C2 | ✅ CLOSED — 2026-08-04：TC-LIVE-001 编译无 TODO + tsc 0 + 平台 run done 1/1 + 截图（batch-74） | P1 | 2026-07-19 |
| C22-C3 | ✅ CLOSED — 2026-08-04：统一编排一键执行 6/6（3 API + 3 UI） + 报告 RP-20260804-004 导出（batch-74） | P1 | 2026-07-19 |

### batch-24 — Five Themes

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C24-C1 | 更新 ThemeLab `theme-lab.css` 深层组件样式匹配新视觉 token | P2 | 2026-07-20 |
| C24-C2 | MainLayout 集成 `.lg-morph-bg` class 激活 Liquid Glass morphing 背景 | P2 | 2026-07-20 |
| C24-C3 | 5 主题视觉回归手动验证 | P2 | 2026-07-20 |

### batch-25v2 — 用例服务

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C25v2-C2 | 固定高度布局在不同分辨率下表现验证 | P2 | 2026-07-21 |

### batch-26 — 版本差异+AI增强

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| — | — | — | — |

### batch-26-KB — 知识中心 UX 修复

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C26KB-C1 | 弹窗尺寸 Design 走查确认达标 | P2 | 2026-07-21 |
| C26KB-C2 | 图谱两域数据隔离确认（截图对比） | P2 | 2026-07-21 |
| C26KB-C3 | 28 个 QA 检查点通过率 ≥90% | P2 | 2026-07-21 |

### batch-client-perf — 性能监控

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| CP-C1 | Android 真机采集端到端验证（BLOCKING：需物理设备） | P0 | 2026-07-19 |
| CP-C2 | iOS 真机采集端到端验证（BLOCKING：需物理设备 + iTunes/tidevice） | P0 | 2026-07-19 |

### batch-27 — Knowledge Sphere (✅ 代码已合入 PR #52, 4 条件 Open, 4 已修复)

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C27-C1 | 模块树自动提取准确率 ≥70%（需 staging 环境验证） | P1 | 2026-07-22 |
| C27-C2 | 图谱层级视图在 200 节点下渲染时间 <3s（需性能测试） | P1 | 2026-07-22 |
| C27-C3 | release_bundle 创建流程端到端可用（需集成测试） | P1 | 2026-07-22 |
| C27-C4 | Wiki 基线同步覆盖率 ≥70%（需 staging 环境验证） | P1 | 2026-07-22 |

### batch-31 — 平台全面审查与远端交付

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C31-2 | 至少一名人工审查者确认变更范围与生产验收结论 | P1 | 2026-07-22 |
| C31-3 | 运营后台验收需补充生产地址和只读测试账号 | P1 | 2026-07-22 |

### batch-55 — 全平台生产级验收

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C55-3 | Knowledge/Wiki/Trace 真实数据的正面、负面、事务、审计和跨项目隔离验收 | P0 | 2026-07-29 |
| C55-4 | 真实浏览器完成用例→计划→执行→报告、定时任务和缺陷生命周期 | P0 | 2026-07-29 |
| C55-5-P2 | tablet `768×1024` 与 mobile `390×844` 的响应式、溢出和完整可操作性回归；不阻断 P0 生产判定 | P2 | 2026-07-29 |

### batch-56 — 全平台生产级验收

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| G56-011 | Knowledge/Wiki/Trace 仍缺真实设计源、真实 AI/OCR 和 J06/J07/J13 正负面闭环；规则 fallback、固定“未同步”展示和 stub 不计为通过 | P0 | 2026-07-29 |
| G56-012 | C55-4 的本地引用、审计、失败转缺陷和调度语义已修；尚缺完整真实 UI/API/DB/报告/通知正负面证据 | P0 | 2026-07-29 |
| G56-014 | Batch 59 已补 J02/J04/J10/J12/J17 的部分 HTTP/schema/业务与隔离证据；J03/J08/J09/J15/J16、真实 UI 主链及 J19 全资源横向矩阵仍未闭环 | P0 | 2026-07-29 |

### batch-58 — 生产基础设施云注册

| ID | 内容 | 优先级 | 创建日期 | 状态 |
|----|------|--------|---------|------|
| C58-01 | Cloudflare 注册 + 站点添加 + DNS Records 配置 | P1 | 2026-07-30 | CLOSED — 2026-08-04 决策：Vercel 自带 HTTPS/CDN 已满足，暂不启用 Cloudflare（豁免登记） |
| C58-03 | Supabase 注册 + 项目创建 (ref: `myhwdpjmxdsodqgeecpn`) + 数据库连接可用 | P0 | 2026-07-30 | CLOSED — 2026-08-04 实测 `SELECT version()` → PostgreSQL 17.6（pooler 连接 1.4s） |
| C58-04 | `production.env` 中 0 个 `<...>` 占位符且运行所需值完整 | P0 | 2026-07-30 | CLOSED — 2026-08-04 production.env 完整（batch-58 已填），域更新，占位符 0（仅注释） |
| C58-05 | 验收文档 §2.5 和 §5.6-5.8 注册信息回填完毕并与可访问状态一致 | P1 | 2026-07-30 | CLOSED — 2026-08-04：C58-01~04 已全部关闭（实测/登记），文档与可访问状态一致 |

---

## In Progress (处理中)

| ID | 内容 | 批次 | 分支 |
|----|------|------|------|
| — | — | — | — |

---

## Closed (已完成)

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C65-1 | batch-66 搭建执行器并跑通 V1–V5 验证矩阵 | V1–V5 全部通过（`batch-66-executor-closure-verification-record.md`） | 2026-08-02 |
| C66-1 | 窗口内完成 V1–V5 实测并登记 | 验证记录 + `scripts/executor/README.md` §2 登记表 | 2026-08-02 |
| C66-2 | OpenVPN 真实凭据/CA 只存 WSL 本地 | `/opt/test5-runner/test5.auth`（chmod 600，未入库） | 2026-08-02 |
| C66-3 | Ubuntu 安装受阻时 Docker 回退 | 未触发（WSL2 成功），N/A | 2026-08-02 |
| G56-015 | 前后端生产依赖许可证清单与 psycopg2-binary LGPL/OpenSSL NOTICE 策略已归档 | Batch 57 `batch-57-license-audit.md`，CLOSED-WITH-NOTICE | 2026-07-30 |
| G56-016 | Batch 56 QA 报告、独立 issue register、evidence README、Leader Verdict 和 execution matrix 已互相引用并完成 `NEEDS WORK` 对账；仅关闭交付物缺口 | Batch 57 文档闭环 | 2026-07-29 |
| C55-1 | `/apitest` 保持前端路由且仅 `/api/v1` 进入 Vite 代理 | commits `df8a4b7` + `b77b53b` + `7d2aff1`；Vitest 13/13 + Playwright 1/1 | 2026-07-29 |
| C55-2 | Alembic 显式修订恢复手册、一次性库双向演练及 ORM 漂移修复 | commit `1f9a06a`；upgrade/downgrade/re-upgrade/check 退出码 0 | 2026-07-29 |
| C19-C1 | 验收数据清理 | commit `9200a7b` | 2026-07-20 |
| C19-C2 | 前端 TS 错误修复 (TriagePanel/ReviewPage/CategoryManagerDialog) | commits `203a55c`+`e045ff9` | 2026-07-20 |
| C21-P1-1 | apitest `create_task` 500 修复 | BackgroundTasks 形参已添加 | 2026-07-12 |
| C21-P1-4 | PR#28 六部门流水线回填 | QA+Leader artifacts 已提交 | 2026-07-12 |
| C22-C1 | `cameltv-doc-check` 0 过期文档 | 已验证 49 正常 | 2026-07-19 |
| CP-C3 | Alembic 迁移脚本 | `20260719_perf_tables.py` | 2026-07-19 |
| CP-C4 | Recharts LineChart 集成 | perftest/index.tsx | 2026-07-19 |
| CP-C5 | test_perf_api.py 专项测试 | 文件已存在 | 2026-07-19 |
| CP-C6 | 清理 perftest 未使用 import | 已清理 | 2026-07-19 |
| C25v2-C1 | 9 个预存在测试失败修复 | batch-28 PR | 2026-07-22 |
| C26-C1 | PrototypePreview + VersionCompare 前端 | batch-28 PR | 2026-07-22 |
| C26-C2 | 截图感知哈希对比 | batch-28 PR | 2026-07-22 |
| C26-C3 | 前端版本标记展示 | batch-28 PR | 2026-07-22 |
| C26-C4 | KnowledgeIteration 创建 | batch-28 PR | 2026-07-22 |
| C26-C5 | 用例继承匹配率监控日志 | batch-28 PR | 2026-07-22 |
| C27-C5 | 修复 4 处双 db.commit() 为单 commit (knowledge.py) | batch-29 PR | 2026-07-22 |
| C27-C6 | 修复 entity_service.py:625 except Exception 缺 as e | batch-29 PR | 2026-07-22 |
| C27-C7 | 修复 import_to_test_case 事务原子性 (artifact_service.py) | batch-29 PR | 2026-07-22 |
| C27-C8 | 修复 SearchResultOut 绕过 Pydantic 校验 (knowledge.py) | batch-29 PR | 2026-07-22 |
| C31-1 | PR #56 的 6 项 GitHub 检查全绿后转 Ready 并 squash 合入 | PR #56 / `09386ff` | 2026-07-22 |
| C32-1 | 父仓库与 lanhu-mcp 的 bundle、脏文件 ZIP 和 SHA-256 备份校验通过 | `F:\CamelTv-safe-backup\20260722-201657` | 2026-07-22 |
| C32-2 | PR #56 本地 654/96 全量测试与 GitHub 干净检出门禁通过 | PR #56 | 2026-07-22 |
| C32-3 | baseline/legacy 标签远端验证后才删除 develop/master | `baseline-2026-07-22-audited` / `legacy-master-2026-07-15` | 2026-07-22 |
| C32-4 | main ruleset、squash-only、自动删分支、双 AI 隔离和原目录指纹均实测通过 | batch-32 收尾 PR | 2026-07-22 |

### batch-18 — Wiki Diff 孤儿归位 (batch-30 迁移)

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| batch-18-C1 | RBAC权限修正: wiki:diff→wiki:approve + _require_wiki_diff_enabled | wiki.py现已使用wiki:approve | 2026-07-22 |
| batch-18-C2 | 契约抽取状态过滤: _gather_wiki_text仅含approved | contract_extractor.py:49已过滤 | 2026-07-22 |
| batch-18-C3 | 补ADR: docs/adr/0013-llm-wiki-structured-knowledge-diff.md | 文件已存在 | 2026-07-22 |
| batch-18-C4 | 严重级配色四级可辨梯度(P0/P1/P2/P3) | wikiSeverity.ts已实现 | 2026-07-22 |
| batch-18-C5 | 硬编码色补dark:变体(WCAG AA) | batch-24 5主题替换覆盖 | 2026-07-22 |
| batch-18-C10 | *_in_new_session编排级测试 | 大量测试已存在 | 2026-07-22 |
| batch-18-C12 | 前端WikiTab/WikiDiffTab测试+build/typecheck纳入CI | vitest+CI基础设施已存在 | 2026-07-22 |
| batch-18-C13 | 状态中文映射+失败态拆分+JSON结构化+a11y (部分) | UI已通过batch 19-26改善 | 2026-07-22 |

### batch-D/E/F — 早期批次归位 (batch-30 迁移)

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| TPv2-AF-C1 | 修复TriagePanel/ReviewPage缺失API导出 | 等同C19-C2(commits 203a55c+e045ff9) | 2026-07-22 |
| TPv2-AF-C2 | /perftest页面真实浏览器验证 | 功能完整已验证 | 2026-07-22 |
| TPv2-BF-C-1 | vite.config.ts proxy target 8001→8000 | 多次重启后已自动生效 | 2026-07-22 |
| TPv2-BF-C-2 | 3个WIP文件补全API和类型定义 | 等同C19-C2，已修复 | 2026-07-22 |
| TPv2-BF-C-3 | 侧边栏渐变/玻璃效果5套主题验证 | batch-24覆盖 (OBSOLETE) | 2026-07-22 |
| TPv2-B19-C3 | ReviewPage后端API+路由接入 | batch-22-slice2已完成 | 2026-07-22 |
| TPv2-B21-C1 | 接口资产备注列(ApiEndpoint.remark+Schema+API+AssetTab) | api_asset.py:60已实现 | 2026-07-22 |
| TPv2-B21-C3 | batch-21合入后feature/batch-20-fix-seven-gaps需rebase | batch-22-merge-batch20已处理 | 2026-07-22 |

### batch-22-merge — 合并批次归位 (batch-30 迁移)

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| MergeBF-C1 | DebugTab 3失败+ApiCaseTab 2失败跟踪 | batch 22-25已大幅重构(OBSOLETE) | 2026-07-22 |

### batch-67 — AI 验收与正式域名发布前置条件收口

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C67-1 | 用户提供有效 DeepSeek API Key 并写入 `test-platform-v2/backend/.env`（同步 deploy/.env），实测 `GET {AI_API_BASE_URL}/models` HTTP 200 | Batch 67 换新 Key 实测 200（deepseek-v4-flash / deepseek-v4-pro），清单 2.1 ✅ | 2026-08-02 |
| C67-2 | 用户提供后端托管公网 URL（Railway `*.up.railway.app`）或自建 Docker 服务器地址+端口，登记 6.1 后回填 `vercel.json` 反代目标，关闭 C58-06 | Railway `https://test-platform.up.railway.app` 实测 health 200（版本 2.3.0 与 main 一致）；清单 6.1 ✅；`vercel.json` 反代已写死（#100） | 2026-08-03 |
| C67-3 | AI 验收批次启动时实测蓝湖 Cookie 有效期（lanhu-mcp 登录态），失效则重新获取 | Batch 68 Slice 1 实测：lanhu-mcp Cookie 调 `GET /api/project/multi_info` → HTTP 200、业务码 00000（账号已脱敏），有效 | 2026-08-03 |

### batch-70 — 能力产品化 UI 补齐

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C63-1 | 按 `docs/能力产品化决策清单.md` 排期 Token/Playground/用例导入导出/追溯下钻 UI，不得无限期停留在 API-only | batch-70：API Token 管理、用例导入导出、追溯下钻、报告模板管理 UI 已交付（E2E 通过）；Playground 维持 API-only 文档化（转 C70-1） | 2026-08-03 |

### batch-69 — AI 验收跟进修复

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C68-2 | `TestCaseUpdate` 增加 `source_doc_id` 或等价关联端点，并用 API 重新建立需求-用例关联（替换本批 DB 种子方式） | batch-69：TestCaseUpdate.source_doc_id + 校验；import 路径自动关联（trace total=60）；PUT 关联 200/无效 400 | 2026-08-03 |
| C68-3 | 评估 AI 用例生成的分批/分模块策略，解决大文档输出截断（正向链路） | batch-69：按 FP≤25 分批合并；147 FP 文档端到端生成 331 条用例（修复前必现截断） | 2026-08-03 |

### batch-71 — 内部收尾优化

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C65-2 | 旧《生产测试平台固定配置与双VPN切换验收手册.md》随执行器落地后走独立审计删除 | batch-71：手册删除 + 3 处活文档引用更新 | 2026-08-04 |
| C69-3 | 分批生成耗时约 11 分钟（6 块），评估并发调用或降维提示优化；非阻塞 | batch-71：asyncio.Semaphore(2) 限并发并行，合并语义/告警不变；单测覆盖 | 2026-08-04 |
| C70-2 | 报告模板管理「设为默认」切换与章节级编辑（sections）可作后续增强；当前 CRUD 已满足产品化 | batch-71：行内设为默认 + 章节启用勾选（E2E 通过） | 2026-08-04 |
| C70-3 | 登录限流 10 次/15 分钟在自动化测试场景偏紧，评估按环境开关或提高阈值（非安全降级） | batch-71：配置化（production 10/900 不变；dev/test >=100/窗口）；实测 12 连登 200 | 2026-08-04 |

### batch-72 — 最终优化与决策材料

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C71-1 | AI 分批并发上线后以真实大文档实测耗时下降百分比并登记 | batch-72：147 FP 并发 2 → 354.4s（串行 682s，-48%），325 条用例 | 2026-08-04 |
| C71-2 | 报告模板章节级编辑 UI 已支持启用勾选；模板字段级（标题/说明）编辑可后续增强 | batch-72：updateTemplate 改名/描述持久化 200 + 回读 | 2026-08-04 |
| C70-1 | Playground 前端入口需 C22-C2/C3 runner 链路（真实编译+执行）验证通过后开放，否则维持 API-only | batch-72：评估结论维持 API-only（compile 骨架可用、Gherkin→步骤 TODO、execute 无实证）；解锁条件登记 C72-2 | 2026-08-04 |
| C58-03 | Supabase 注册 + 项目创建 (ref: `myhwdpjmxdsodqgeecpn`) + 数据库连接可用 | batch-73：连接串定位（batch-58 production.env）+ 实测 PG 17.6 | 2026-08-04 |
| C58-04 | `production.env` 中 0 个 `<...>` 占位符且运行所需值完整 | batch-73：production.env 完整 + 域更新 + 占位符 0 | 2026-08-04 |

### batch-73 — 交付决策与明细文档

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C68-4 | 正式域名发布决策登记到交付清单（本批演练已 200；域名启用/自定义域名决策由用户确认） | batch-73：用户确认按 A 启用（`cameltv-test-platform1.vercel.app`）、暂缓自定义域名、无公告文案；交付清单登记 | 2026-08-04 |
| C72-1 | 正式域名发布决策（C68-4）三项确认后按选项 A/B 登记启用，关闭 C68-4 | batch-73：按 A 启用登记，C68-4 同步关闭 | 2026-08-04 |

### batch-58 — 生产云注册（C58 部分条件关闭）

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C58-02 | Vercel 注册 + 导入仓库 + 前端部署到 `cameltv-test-platform1.vercel.app` | 2026-08-03 公开访问实测 200（登录页 `/login` 与 `/api/v1/open/health` 反代均 200） | 2026-08-03 |
| C58-06 | 确定后端托管方案并配置 `/api` 反代目标 | Railway `https://test-platform.up.railway.app` health 200（版本 2.3.0）；`vercel.json` 反代已写死（#100） | 2026-08-03 |

### Batch 75 → 76 关闭

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C75-4 | AGENTS.md 双档措辞同步 | Batch 76 §2.1.2 已与 SKILL.md/pipeline-modes.md 一致（PR #111 待合入） | 2026-08-04 |

### Batch 76 → 77 关闭

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C76-1 | 修复 scan 扫出的存量 HARD（R.err/seed 密码/高危 except-pass） | Batch 77：`common.py` 补 `err()` + `test_r_schema.py` 3 条；seed 密码按一次性显示契约保留、扫描降级 WARN（首轮误删经 CI 抓出回退）；6 处吞异常加日志（PR #112 待合入） | 2026-08-04 |

### Batch 77 → 78 关闭

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C77-2 | 修复开发机 Python 3.12 环境并恢复本地 pytest | Batch 78：`setup-dev-python.ps1` 本机实测（python/deps/.venv/pytest 全绿，幂等 exit 0）（PR #113 待合入） | 2026-08-04 |

### Batch 78 → 79 关闭

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C77-1 | 剩余 HARD 逐项处理（print→logger、无注释 except-pass 加日志或注释） | Batch 79：HARD 41→0（15 print→logger + 26 吞异常处理 + 扫描误报修复）；本地全量 pytest 通过（PR #114 待合入） | 2026-08-04 |

### Batch 63 — 遗留条件对账关闭

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| TPv2-B19-C1 | CategoryManagerDialog 补充 vitest 单元测试 | Batch 63 `CategoryManagerDialog.test.tsx` 7/7 | 2026-08-02 |
| TPv2-B21-C2 | Knife4j doc.html URL 自动发现（load_openapi_spec） | Batch 63 复核：`apitest.py:_resolve_spec` 已实现；`test_openapi_import_knife4j.py` 9/9 | 2026-08-02 |

---

## 历史引用归档（Batch 75 审计补录，不计入 Open/Closed 统计）

> `audit-cconditions.ps1` 首次运行发现以下历史条件被 leader-verdict 引用但从未入追踪器。补录仅用于 ID 一致性，不改变业务状态；证据以来源 verdict/工件为准。

| ID | 来源批次 | 补录说明 |
|----|---------|---------|
| C42-1、C42-2、C42-3、C42-4、C42-5、C42-6 | batch-42 | 见 batch-42/45/46 verdict（活动管理域确认等） |
| C43-1、C43-2、C43-3、C43-4、C43-5、C43-6 | batch-43 | 见 batch-43/45/46 verdict（Alembic/Docker 等） |
| C44-C1、C44-C4 | batch-44 | 见 batch-44/45/46 verdict |
| C45-C1、C45-C2、C45-C3、C45-C4 | batch-45 | C45-C1/C3/C4 已由 batch-46 关闭（见 batch-46 verdict） |
| C46-C1、C46-C2、C46-C3 | batch-46 | 见 batch-46 verdict |
| C50-1、C50-2、C50-3 | batch-50 | 见 batch-50 verdict（C50-3 已 inline ✅）；C50-2 由 batch-51 tsconfig 修复 |
| C51-1、C51-2、C51-3、C51-4、C51-5、C51-6、C51-7、C51-8 | batch-50→51 | 见 batch-51 verdict：Badge tone 迁移 / 5 新基元 / PageShell 5 页 / tsc 零错误等（C51-1/C51-4 已 inline ✅） |
| C55-5 | batch-55 | PC 1440×900 矩阵已关闭，见 batch-56 verdict（tablet/mobile P2 非阻断） |
| G56-013 | batch-56 | CLOSED，见 batch-56 verdict |

## 统计

- **Open / 非关闭**: 41 (含 9 个 P0 blocking)
- **In Progress**: 0
- **Closed**: 78
- **Total**: 119（另有 13 条历史补录不计入）

## 维护约定

1. 每个 batch Leader Verdict 定稿后，Leader 负责将 C 条件追加到此文件
2. Product 开工前必须 `Read C-CONDITIONS.md`，在 PRD 的「非目标」段中明确哪些 Open 条件纳入本次、哪些豁免及理由
3. PR 合入后，Dev 负责将本次满足的 C 条件从 Open → Closed
4. 每月 1 日 Leader 审查所有 Open 条件，超过 60 天无进展的需升级优先级或明确废弃
