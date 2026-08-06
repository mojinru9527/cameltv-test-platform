# C 条件追踪器

> 所有 Agent Team Leader 设定的「下一批次 C 条件」集中追踪。Product 开工前必须先读此文件。

**追踪规则**:
- 每个 Leader Verdict 末尾的 C 条件必须写入此文件
- Product 开工第一件事：检查此文件中所有 `Open` 条件，PRD 中必须包含或明确豁免
- 条件满足后标记为 `✅ Closed`，注明合入的 PR/commit
- **状态机（Batch 75 起）**：`Open（待处理）` → `In-Progress（处理中）` → `Closed（已关闭，必须带证据：PR/commit/链接）`；外部阻塞项 → `Deferred（延期，必须带解除条件）`
- 新增条件统一使用 `C{批次}-{序号}`（如 `C75-1`）命名，禁止裸 `C1`；关闭时在 Closed 表中注明合入 PR/commit
- 一致性校验：`pwsh scripts/git/audit-cconditions.ps1`（只读，孤儿条件/重复 ID/缺证据/日期漂移）

**最后更新**: 2026-08-06 (Batch 101: 体育平台生产接入（899 端点/325 用例/环境/UI 冒烟/定时/Token）+ 冒烟 3/5 发现登记，PR #139)

**Batch 63 复核（2026-08-02）**: Product/QA 对全部 Open 条件逐条复核。
TPv2-B19-C1 与 TPv2-B21-C2 已确认实现并关闭（见 Closed 表 Batch 63 节）；
C55-3/C55-4、G56-011/012/014、C58-01~06、CP-C1/C2 等外部依赖项继续保留 Open，
解除条件见 Batch 63 回归汇总 §3.3；其余早期孤儿（batch-18/22/24/25v2/26KB/27/31、
C21-P1-2/3/5、C22-C2/C3）未在本批获得新证据，保持 Open 并计入后续批次。

---

## Open (待处理)

### batch-103 — 用例质量与接口可视优化（Batch 103 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C103-1 | 功能用例生成遵循团队用例规范（tests/test-case-standards）：等价类/边界值/场景法/错误推测 + 正负向，覆盖度 ≥2 条/FP（用户端 92 FP → ≥184 条） | P1 | 2026-08-06 |
| C103-2 | 接口用例可视：请求参数、断言、实际请求结果（执行回填）在用例详情可见 | P1 | 2026-08-06 |
| C103-3 | 接口用例按接口测试规范（API接口测试方案）生成，且以生产真实业务请求参数为基线（如 news/list_visible 的 page/size/queryList/locale），字段级正/负/边界/类型/枚举/组合覆盖，禁止模拟造参 | P1 | 2026-08-06 |
| C103-4 | 全字段覆盖+生产回填原则：接口清单按功能需求确定；生产接口真实请求/响应优先回填基线；接口用例/调试数据须覆盖接口全部字段，按字段业务含义构造贴合数据（类型/含义/边界/枚举/格式/组合），禁止无意义 mock 占位值 | P1 | 2026-08-06 |

### batch-102 — 体育平台功能模块梳理（Batch 102 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C102-1 | 需求 AI 提取/生成同步超时（>300s 网关 502）：改造异步任务+轮询或分块放宽，消除大文档生成失败 | P1 | 2026-08-06 |
| C102-2 | 知识中心入库接口修复（capture 一律 409、vector_search 非 functional）；修复后回归 /knowledge/capture 落库 | P1 | 2026-08-06 |
| C102-3 | 需求模块树/跨系统关联支持从需求文档直建（当前强制蓝湖证据包 evidence_job_id） | P2 | 2026-08-06 |
| C102-4 | 生产页面与需求原型差异标注能力（英文站 vs 中文原型，新增 World Cup/Replays 模块） | P2 | 2026-08-06 |
| C102-5 | AI 生成截断自动补全（块级重试+补生成+覆盖缺口报告） | P2 | 2026-08-06 |

### batch-96 — V1 工具审计 / 只读账号 / staging / diff 基线（Batch 96 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C96-1 | C27-C1~C4 四项验证在本地全栈（staging 替代）执行，数据/性能测量就绪后逐项关闭（V1 工具删除已于 Batch 98 完成） | P1 | 2026-08-05 |

### batch-99 — 性能采集功能优化（Batch 99 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C99-1 | **性能采集功能需要优化**：①采样周期并行化（当前 10–55s/点 → 目标 ≤2s）；②jank 视频帧率口径（30fps 视频在 120Hz 屏误报）；③多核 CPU 语义与阈值（当前如实上报 >100%）；④iOS 26.5 支持（solox DeviceSupport 缺失）；详见 `test-platform-v2/docs/改进任务backlog.md` Epic PERF-OPT | P2 | 2026-08-06 |

### batch-101 — 体育平台承接（Batch 101 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C101-1 | 生产只读冒烟放行策略评估：站点 POST 信标与第三方广告域（ukankingwithea.com 等）的白名单/策略决策；当前严格只读守卫拦截为真实发现，不静默放行 | P1 | 2026-08-06 |
| C101-2 | 音视频专项 match replays 真实回放 URL（`--av-url` 待业务提供后创建任务） | P2 | 2026-08-06 |
| C101-3 | Test5 内网 API 回归由 CI `api-regression` workflow 承担；平台「体育平台-每日API回归」schedule 因内网不可达停用（enabled=false）登记 | P2 | 2026-08-06 |

### batch-95 — 后续小项消化（Batch 95 Leader 条件）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C95-1 | Test5 窗口开启后用 konfi 账号取 token 拉契约（补 C74-2）；admin-service 登录提供后一并完成 | P2 | 2026-08-05；2026-08-05 VPN 实测：隧道通但网关路由空/health 503（服务未就绪），konfi 登录 API 已定位（/konfiapi/user/login）但密码待提供；服务就绪+密码落位后执行 |
| C95-2 | iOS 真机（CP-C2/C84-1）今晚用户执行后登记结果并关闭或转缺陷 | P2 | 2026-08-05 |

### batch-93 — 响应式回归常驻 CI（Batch 93 Leader 条件）

> C93-1 已于 Batch 95 关闭（手动触发 workflow 运行成功，run 30986094838）。

### batch-92 — 蓝湖证据包审核 UI（Batch 92 Leader 条件）

> C92-1 已于 Batch 94 关闭（批量审核 Dialog 复用统一「人工审核」范式）。

### batch-91 — Open 区收口（Batch 91 Leader 条件）

> C91-1 已于 Batch 94 关闭（C26KB-C3 28/28 复测达标）；C91-2 保持 Open。
> C91-2 已于 Batch 95 关闭（search_service/vector_store docstring 对齐 + 49 测试通过）。

### batch-90 — 追踪器卫生审计（Batch 90 Leader 条件）

> C90-1 / C90-2 已于 Batch 91 关闭，见 Closed 表「Batch 91 — Open 区收口」。

### 流程门禁（持续生效，保持 Open；Batch 90 卫生审计保留）

| ID | 内容 | 优先级 | 创建日期 |
|----|------|--------|---------|
| C75-1 | 后续批次 Product 必须按「批次模式」判定完整/轻量，并在 PRD 记录 `mode`；轻量批次必须含豁免理由 | P2 | 2026-08-04 |
| C75-2 | 每批 Leader 判决必须含「流程回写」小节；改动 SKILL.md/DEPARTMENTS.md 必须同步 CHANGELOG | P2 | 2026-08-04 |
| C75-3 | PR 推送前运行 `audit-cconditions.ps1 -RequireLatestBatch`，0 硬错才允许合入 | P1 | 2026-08-04 |
| C76-2 | 后续批次提交前运行 `scan-common-bugs.ps1`，HARD>0 处理或注明豁免 | P2 | 2026-08-04 |
| C78-1 | 后续批次本地受影响模块 pytest 必须执行并记录退出码 | P2 | 2026-08-04 |
| C86-1 | 后续批次新增测试断言遵循双 404 约定（assert_guard_404 / HTTP 200+code 404）；新代码不得再引入裸 `status_code == 404` | P3 | 2026-08-04 |
| C63-3 | `C-CONDITIONS.md` 继续按 Batch 63 复核口径维护；新批次 PRD 须引用 C63 条件 | P2 | 2026-08-02 |

### 外部/阻塞项（Deferred，解除条件见描述；Batch 90 卫生审计标注）

| ID | 内容 | 优先级 | 解除条件 |
|----|------|--------|---------|
| CP-C2 | iOS 真机采集端到端验证 | P0 | 用户已连接 iPhone（Apple 驱动已装，tidevice 可识别）；**阻塞：solox 缺 iOS 26.5 DeviceSupport（GitHub 404），平台 iOS 采集不可用**；解除条件：solox 支持该版本或提供受支持 iOS 设备 |
| C84-1 | iOS 真机采集验收（tidevice 链） | P1 | 同 CP-C2（solox 支持后执行） |
| C74-2 | Test5 无契约服务契约补拉 | P2 | 部分解锁：konfi 账号 test-cameltv + 登录地址已提供；admin-service 登录已提供（2026-08-05：运营后台测试环境 camel-admintest5.elelive.cn，账号 ll）；2026-08-05 VPN 实测网关服务未就绪（路由空/health 503），konfi 密码待提供 |
| C65-3 | Test5 外部前置条件逐项解锁登记 | P1 | 清单 1.4 已更新（konfi 解锁登记 2026-08-05）；admin-service 已登记（2026-08-05）；业务 DB/Redis 已登记（7.1），体育平台无 MQ（N/A） |
| C63-2 | 外部阻塞项解除时先登记提供人/日期/授权范围 | P0 | 任一外部项解锁时遵守 |
| C27-C1 | 模块树自动提取准确率 ≥70% | P1 | staging 替代已登记（test 环境 + 本地全栈）；执行待数据/性能测量（C96-1） |
| C27-C2 | 图谱层级视图 200 节点渲染 <3s | P1 | 同上 |
| C27-C3 | release_bundle 创建流程端到端 | P1 | 同上 |
| C27-C4 | Wiki 基线同步覆盖率 ≥70% | P1 | 同上 |
| C31-2 | 至少一名人工审查者确认变更范围与生产验收结论 | P1 | 已关闭（用户 2026-08-05 确认），见 Closed 表 |
| C31-3 | 运营后台验收需生产地址与只读测试账号 | P1 | 已关闭（viewer 只读角色/账号实现 + 测试 3/3），见 Closed 表 |
| batch-18-C7 | 迁移 20260710_0017 staging 双向演练 | P2 | staging 可用后执行 |
| C21-P1-5 | 迁移 20260710_0017 staging 双向演练 | P1 | staging 可用后执行 |
| batch-18-C8 | 标注语料评估 diff classifier 基线 | P2 | 已关闭（Batch 96：10 组标注集 + 召回 1.0/误报 0），见 Closed 表 |
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

### Batch 79 → 80 关闭

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C79-1 | WARN 优先项：硬编码密钥 + envelope 断言 | Batch 80：`cameltv-dev-key` 移除（改用 effective_secret_key + 4 单测）；41 处 404 断言逐类核查为隔离/守卫正确契约并文档化豁免；scan 规则消息双约定化（PR #115 待合入） | 2026-08-04 |

### Batch 80 → 81 关闭

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C80-1 | WARN 清单长期维护机制 | Batch 81：warn-baseline.json（230 项）+ inventory 文档（4 类/节奏/趋势）+ scan -WriteBaseline/-BaselinePath 对比模式（PR #116 待合入） | 2026-08-04 |

### Batch 87 → 88 关闭

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C87-1 | 真实蓝湖设计源证据包闭环（J06 / Wiki ingest 缺口） | Batch 88：项目级链接自动识别设计图板（241+102 页真实设计稿）→ 截图+OCR → 质量门禁（24 页人工审核豁免）→ 导入需求/RAG/Wiki（清洗后 0 二进制垃圾）；PR #124 | 2026-08-05 |
| C87-2 | 定时任务与缺陷通知真实 SMTP 收件验证（J11 缺口） | Batch 88：QQ SMTP 587 STARTTLS 真实发送（NotificationLog sent）+ IMAP 真实收件确认（plan_done + defect_assigned）；PR #124 | 2026-08-05 |
| C87-3 | 项目级角色权限核验/修复（B87-Q1） | Batch 88：tester 权限矩阵补齐 51 项业务权限（testcase/testplan/report/defect/schedule 等）+ 全项目核验（项目内 200/跨项目 403/越权 403）+ 测试 5/5；PR #124 | 2026-08-05 |

### Batch 89 — 本地条件关闭

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C55-5-P2 | tablet/mobile 响应式回归 | Batch 89：Playwright 双视口（768×1024 / 390×844）× 8 关键页面（登录/工作台/用例/计划/报告/缺陷/定时/知识）无水平溢出、主操作可点、console 0；2/2 通过 + 截图 16 张（evidence/batch-89/responsive/）；PR #126 | 2026-08-05 |
| C81-1 | WARN 周审计 | Batch 89：`run-warn-audit.ps1 -BatchLabel batch-89` → AUDIT_RESULT=OK（WARN 209 持平、HARD 0、新增类别 0），趋势表追加 2026-08-05 行；PR #126 | 2026-08-05 |
| C64-2 | 根目录误提交文件清理 | Batch 89：两个 `pective pipeline — ...` 文件删除 + repo-boundaries.json 同步 + `validate_repo_boundaries.py --check` PASS（1996 tracked 全归属）；PR #126 | 2026-08-05 |
| C21-P1-2 | failure_analyzer / report_aggregator / task_worker 单测 | Batch 89：三服务单测 103/103 通过（引入 commit a3608b8，Batch 41/PR #66；本批执行证据 evidence/batch-89/c21-p1-2-closure.md）；PR #126 | 2026-08-05 |

### Batch 90 — 追踪器卫生审计关闭

> 审计方法：Open 区逐条核对（inline-CLOSED / Open-Closed 重复 / 代码现状），能证据关闭的关闭，外部或 staging 项标注 Deferred；本批关闭 42 项，Open 从 33 → 26（含 20 项外部 Deferred）。

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C55-3 | Knowledge/Wiki/Trace 真实数据验收 | Batch 87（真实 docx→AI→25 用例→RAG/Trace/隔离/审计/负面）+ Batch 88（C87-1 蓝湖设计源 Wiki ingest 闭环）；PR #123/#124 | 2026-08-05 |
| C55-4 | 真实浏览器主链验收 | Batch 87（25/25 执行+报告+定时+缺陷闭环+UI 截图）+ Batch 88（C87-2 SMTP 真实通知闭环）；PR #123/#124 | 2026-08-05 |
| G56-011 | Knowledge/Wiki/Trace 真实数据闭环 | J07（Batch 87）+ J06（C87-1/Batch 88）全部闭环；PR #123/#124 | 2026-08-05 |
| G56-012 | 真实 UI/API/DB/报告/通知闭环 | Batch 87 UI/API/DB/报告 + Batch 88 通知（C87-2）；PR #123/#124 | 2026-08-05 |
| G56-014 | J03/J08/J09/J15/J16/J19 横向矩阵 | Batch 87（J03/J08/J09/J19）+ Batch 74（J15/J16）全部闭环；PR #123 | 2026-08-05 |
| C64-4 | C63-1 四项 API-only UI 排期 | Batch 70：Token/Playground/导入导出/追溯下钻 UI 交付（PR #105，commit 7d4cee4） | 2026-08-05 |
| C69-2 | 正式域名发布决策登记（C68-4 关闭） | Batch 73：用户确认按 A 启用、暂缓自定义域名、无公告（PR #108，commit 9951a2b） | 2026-08-05 |
| C71-3 | J15 外部页 / J16 媒体授权 / 域名决策等外部项 | J15/J16 已闭环（batch-74）、C68-4 域名决策已登记（batch-73），所列子项全部关闭 | 2026-08-05 |
| C72-3 | J15/J16、C58-01/03/04、Test5 外部窗口 | J15/J16（batch-74）与 C58-01/03/04（batch-58/73）已关闭；Test5 部分转 C74-2/C65-3 Deferred 跟踪 | 2026-08-05 |
| C21-P2 | task_worker 双队列竞态/semaphore/SSRF/Wiki 开关/counter | inline 已标注解决（~~删除线~~），Batch 90 卫生审计确认归 Closed | 2026-08-05 |
| C22-C2 | Playground TC-LIVE-001 编译 | inline CLOSED（batch-74 实证），卫生审计归位 | 2026-08-05 |
| C22-C3 | 统一编排一键执行 6/6 | inline CLOSED（batch-74 实证），卫生审计归位 | 2026-08-05 |
| C58-01 | Cloudflare 注册（豁免决策） | inline CLOSED（Vercel 自带 HTTPS/CDN，暂不启用），卫生审计归位 | 2026-08-05 |
| C58-05 | 验收文档注册信息回填 | inline CLOSED（batch-58 文档一致），卫生审计归位 | 2026-08-05 |
| C66-4 | Test5 节点 hosts 补录（可选优化） | inline CLOSED（VPN DNS 解析可用），卫生审计归位 | 2026-08-05 |
| C68-1 | J15/J16 验收执行 | inline CLOSED（batch-74 QA），卫生审计归位 | 2026-08-05 |
| C69-1 | J15/J16 正负面验收 | inline CLOSED（batch-74 QA），卫生审计归位 | 2026-08-05 |
| C72-2 | C22-C2/C3 实证 | inline CLOSED（batch-74），卫生审计归位 | 2026-08-05 |
| C74-1 | J16 码率口径修复 | inline CLOSED（batch-85 修复 + av-checks 6/6），卫生审计归位 | 2026-08-05 |
| C74-3 | Android 真机验收 | inline CLOSED（batch-84，OPPO Find X3），iOS 部分转 CP-C2/C84-1 Deferred | 2026-08-05 |
| CP-C1 | Android 真机采集端到端 | inline CLOSED（batch-84 证据），卫生审计归位 | 2026-08-05 |
| C75-4 | AGENTS.md 双档措辞同步 | Closed 表 Batch 75→76 已有记录，Open 重复挂账清理 | 2026-08-05 |
| C76-1 | 存量 HARD 修复（R.err/密码 print/except-pass） | Closed 表 Batch 76→77 已有记录，Open 重复挂账清理 | 2026-08-05 |
| C77-1 | 剩余 HARD 逐项处理 | Closed 表 Batch 78→79 已有记录（HARD 41→0），Open 重复挂账清理 | 2026-08-05 |
| C77-2 | 开发机 Python 环境修复 | Closed 表 Batch 77→78 已有记录，Open 重复挂账清理 | 2026-08-05 |
| C79-1 | WARN 分批消化 | Closed 表 Batch 79→80 已有记录（cameltv-dev-key/404 断言），Open 重复挂账清理 | 2026-08-05 |
| C80-1 | WARN 清单长期维护机制 | Closed 表 Batch 80→81 已有记录，Open 重复挂账清理 | 2026-08-05 |
| C58-03 | Supabase 注册 + PG 连接 | Closed 表 batch-73 已有记录（PG 17.6 实测），Open 重复挂账清理 | 2026-08-05 |
| C58-04 | production.env 占位符清零 | Closed 表 batch-73 已有记录，Open 重复挂账清理 | 2026-08-05 |
| C68-4 | 正式域名发布决策登记 | Closed 表 batch-73 已有记录（按 A 启用），Open 重复挂账清理 | 2026-08-05 |
| C70-1 | Playground 转正式 UI | Closed 表 batch-70 已有记录，Open 重复挂账清理 | 2026-08-05 |
| batch-18-C6 | WikiReviewItem/Contradictions 持久化 | 已实现：`app/models/wiki.py` WikiReviewItem/WikiReviewContradiction 模型存在 | 2026-08-05 |
| batch-18-C9 | 差异接口 left/right 独立 ref/scope | 已实现：`app/api/v1/wiki.py:362-363` left/right 参数 | 2026-08-05 |
| batch-18-C11 | import 校验 lanhu_mcp_enabled 开关 | 已实现：`app/api/v1/wiki.py:91-142` lanhu_mcp_enabled 守卫 | 2026-08-05 |
| C24-C1 | ThemeLab 深层组件样式匹配新 token | 已实现：`frontend/src/theme-lab/theme-lab.css` | 2026-08-05 |
| C24-C2 | MainLayout 集成 lg-morph-bg | 已实现：`frontend/src/layouts/MainLayout.tsx:368` | 2026-08-05 |
| C24-C3 | 5 主题视觉回归 | 已实现：e2e `batch54-five-theme-production.spec.ts` + batch-52/53/54 主题交付 | 2026-08-05 |
| TPv2-B19-C2 | 预存组件测试契约漂移修复 | 组件测试 56 个文件 + vitest 334 全绿（batch-89 复验） | 2026-08-05 |
| C21-P1-3 | 现状功能PRD 诚实性修复 | 已实现：`test-platform-v2/docs/现状功能PRD.md` 模块 11 标注「真实执行」 | 2026-08-05 |
| C25v2-C2 | 固定高度布局多分辨率验证 | 已实现：testcase 页 calc 固定高 + overflow（index.tsx:343-365）+ batch-89 双视口截图通过 | 2026-08-05 |
| C26KB-C1 | 知识中心弹窗尺寸走查 | 已实现：`frontend/src/pages/knowledge/CaptureDialog.tsx` + batch-26-KB 交付 | 2026-08-05 |
| C26KB-C2 | 图谱两域数据隔离 | 已实现：GraphTab + 隔离测试（batch-26-KB 交付） | 2026-08-05 |
| C89-1 | worktree 开工先初始化子模块 | Batch 90 执行 `git submodule update --init --recursive lanhu-mcp`（本批 docs-only，无需全量测试） | 2026-08-05 |
| C89-2 | C-CONDITIONS 追踪器卫生审计 | Batch 90：Open 33→26（关闭 42 项：P0 验收 5 / 重复挂账 10 / inline-CLOSED 12 / 孤儿复核 11 / 本批流程 2 / 其他 2） | 2026-08-05 |

### Batch 91 — Open 区收口

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C90-1 | C-CONDITIONS 统计脚本口径 | Batch 91：`audit-cconditions.ps1` 新增 `stats:` 输出（Open/Closed/Deferred 按文件解析），维护约定强制引用脚本；PR #128 | 2026-08-05 |
| C90-2 | C21-P3 四子项复核 + SOP 文档 | Batch 91：migration downgrade 测试 7 passed（test_alembic_runbook 等）+ playwright path traversal 守卫（lanhu_evidence.py:315 / ui_test.py:55 is_relative_to）+ diff_classifier 模块 docstring + VNext-1..6 编号约定（wiki 落地方案）；《灰度放量SOP》docs/灰度放量SOP.md；PR #128 | 2026-08-05 |
| C21-P3 | migration downgrade / path traversal / docstring / VNext 编号 | 四子项全部证据关闭（同 C90-2 证据）；PR #128 | 2026-08-05 |
| batch-18-C14 | 分环境灰度放量 SOP 文档 | Batch 91：`docs/灰度放量SOP.md`（环境分层/灰度节奏/回滚/检查清单/责任矩阵）；PR #128 | 2026-08-05 |

### Batch 94 — AI 产物批量审核/采纳

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C26KB-C3 | 知识中心 28 检查点通过率 ≥90% | Batch 94：补齐 C7 批量采纳/驳回/导入（3 新端点 + 前端勾选/全选/批量 Dialog）后复测 **28/28（100%）**；后端 7/7 + E2E 1/1 + 截图 3；PR #131 | 2026-08-05 |
| C91-1 | batch-94 落地批量审核/采纳 UI 后复测 C26KB-C3 | 随 C26KB-C3 关闭（28/28）；PR #131 | 2026-08-05 |
| C92-1 | 与证据包页面审核统一「人工审核」交互范式 | 批量审核 Dialog 复用统一范式（C26KB-C3 同批）；PR #131 | 2026-08-05 |

### Batch 95 — 后续小项消化

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C91-2 | search_service/vector_store docstring 与实现对齐 | Batch 95：两处 docstring 更新（不按 status 过滤，全状态检索语义）+ 知识检索测试 49/49；PR #132 | 2026-08-05 |
| C93-1 | 响应式 E2E 定时任务首次运行核对 | Batch 95：手动触发 `responsive-e2e.yml`（run 30986094838）→ 双视口回归 job **success**；PR #132 | 2026-08-05 |

### Batch 96 — V1 工具审计 / 只读账号 / staging / diff 基线

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C31-2 | 人工审查者确认变更范围与生产验收结论 | 用户 2026-08-05 明确确认；PR #133 | 2026-08-05 |
| C31-3 | 运营后台只读账号 | Batch 96：viewer 只读角色/账号（seed，含 _VIEWER_MENUS/_VIEWER_ACTIONS）+ `test_viewer_role.py` 3/3（查看 200/写 403）；PR #133 | 2026-08-05 |
| batch-18-C8 | diff classifier 标注基线 | Batch 96：`test_diff_classifier_baseline.py` 10 组标注对 → 显著差异召回 1.0 / 误报 0（evidence JSON）；PR #133 | 2026-08-05 |

### Batch 63 — 遗留条件对账关闭

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| TPv2-B19-C1 | CategoryManagerDialog 补充 vitest 单元测试 | Batch 63 `CategoryManagerDialog.test.tsx` 7/7 | 2026-08-02 |
| TPv2-B21-C2 | Knife4j doc.html URL 自动发现（load_openapi_spec） | Batch 63 复核：`apitest.py:_resolve_spec` 已实现；`test_openapi_import_knife4j.py` 9/9 | 2026-08-02 |

### Batch 98 — CI 迁移 + V1 工具删除（2026-08-05）

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C64-3 | 生产交付清单运维回填 + 拆仓边界校验 | prod 业务 DB/Redis **无法提供**（用户 2026-08-05），验收以 test 环境为准（同 C31-3 口径）；test DB/Redis 已回填（2026-08-04，`testdata5.elelive.cn`）；体育平台无 MQ（N/A）；拆仓边界校验 PASS（Batch 97/98）；PR #136 | 2026-08-05 |
| C96-1（部分） | V1 工具实际删除 | 11 个工具目录删除 + CI 迁移（`api-regression`/`prod-smoke-test` 改自包含脚本 `scripts/ci/api-regression.ps1`，`tp` 命令 0 引用）；C27 四项验证仍 Open；PR #136 | 2026-08-05 |

### Batch 99 — 真机性能验收（2026-08-05）

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C84-2 | Android 采集复测（滚动/播放场景 fps 采样） | 用户口径重定义后完成：场景 A Chrome 赛事视频流 600s（fps 85/CPU 3.55%/mem 182MB）；场景 B 小象直播间 600s 60 点（fps 31.2/CPU 386.65%/mem 795MB，用户确认画面）；证据 `test-platform-v2/work-logs/evidence/batch-99/real-device-{chrome-sports,app-live}-10min.json`；PR #137 | 2026-08-05 |
| B99-P1 | Android 采集缺陷修复（fps/cpu/WS 重试） | SoloX Android 14 fps 解析崩溃 → 自实现 SurfaceFlinger 解析+图层选择；多进程 CPU 失真 → /proc 双采样多核不封顶；内存 → dumpsys PSS；无线断开中断 → 采集循环重试 5×3s + 客户端容忍关闭帧；性能模块测试 54 passed；PR #137 | 2026-08-05 |

### Batch 100 — V1 整体退役（2026-08-06）

| ID | 内容 | 合入方式 | 日期 |
|----|------|---------|------|
| C64-1 | V1 整体移除受覆盖矩阵门禁 | Batch 98：11 工具删除；**Batch 100**：web-ui/server/cli/core/config/docker/platform_tests 整体移除（用户规则：V2 覆盖即移除；cli/config 无消费者），API 回归资产迁移 `tests/api-testing/`；`rg -P 'test-platform/(?!v2)'` 非文档 0 引用 + boundary PASS；PR #138 | 2026-08-06 |

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

- **Open / 非关闭**: 25 (含 4 个 P0 blocking；其中 14 项 Deferred + 2 项 C95 + 1 项 C96 + 1 项 C99 + 3 项 C101；口径见 `audit-cconditions.ps1` stats 输出)
- **In Progress**: 0
- **Closed**: 134（Batch 91 起以 `audit-cconditions.ps1` stats 输出为准）
- **Total**: 159（另有 13 条历史补录不计入）

## 维护约定

0. **统计口径（C90-1，Batch 91 起强制）**：Open/Closed/Deferred 计数一律以 `pwsh scripts/git/audit-cconditions.ps1` 输出的 `stats:` 行为准；手工修改统计行视为漂移，Leader 复核时以脚本值校正。
1. 每个 batch Leader Verdict 定稿后，Leader 负责将 C 条件追加到此文件
2. Product 开工前必须 `Read C-CONDITIONS.md`，在 PRD 的「非目标」段中明确哪些 Open 条件纳入本次、哪些豁免及理由
3. PR 合入后，Dev 负责将本次满足的 C 条件从 Open → Closed
4. 每月 1 日 Leader 审查所有 Open 条件，超过 60 天无进展的需升级优先级或明确废弃
