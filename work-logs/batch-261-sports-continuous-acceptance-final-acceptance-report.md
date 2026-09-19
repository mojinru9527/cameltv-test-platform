# 落地方案最终验收报告（B1→B4 全部批次）

> **交付方**: Codex（Agent Team 六部门流水线） | **验收方**: 用户 | Date: 2026-09-19
> **验收清单来源**: `docs/platform-refactor/10-landing-plan-task-backlog.md` §5 的 9 条
> **汇总范围**: Batch 258（B1）/ 259（B2）/ 260（B3）/ 261（B4）

## 0. 批次交付一览

| 批次 | 范围 | PR | 合入 commit | 后端全量 | 前端全量 | 状态 |
|------|------|----|------------|---------|---------|------|
| Batch 258 | B1 出网/凭据收口 + ExecutionJob 协议 + 本地节点 | #477 | `2ced1baf` | 2839 passed / 0 failed | 165 文件 721 例 | ✅ 已合入 |
| Batch 259 | B2 执行沙箱 + 菜单收敛 | #478 | `573f5c12` | 2839 → 0 failed | 165 文件 722 例 | ✅ 已合入 |
| Batch 260 | B3 知识主线 | #479 | `3788c66d` | 2885 passed / 0 failed | 167 文件 732 例 | ✅ 已合入 |
| Batch 261 | B4 体育连续验收 | 本批 PR | 待合入 | 见本批 QA | 168 文件 737 例 | ⏳ 待总确认 |

**三条审计硬线（S1–S6）现状**：S1（SSRF）、S2（令牌外发）、S3（`shell=True`）、S4（对象存储路径）、S5（双密钥派生）**已关闭**；
S6（dry-run 当沙箱 / 无凭据沙箱）**部分关闭**——表述纠正 + 危险 API 静态拦截 + 进程内可达面收敛已落地，内核级隔离属部署层（`C259-2`）。

## 1. 验收结果总表

| # | 验收项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | 菜单只剩 4 个入口 + 专家区 | ✅ **达成** | Batch 259 §B2-6 + Batch 260 §B3-5 |
| 2 | 本地节点一条命令可用 | ✅ **达成** | Batch 258 §B1-5/B1-7（真实子进程 + 认领 + 上报） |
| 3 | 8 条试点用例真实跑通且证据可查 | ✅ **达成（真机外）** | 2026-09-19 起在**真实 Test5** 跑通 5 接口（含信封码断言）+ 3 Web（截图 SHA256 互不相同）；此前为本地替身 → 详见 §2 第 ③ 条 |
| 4 | 断线不丢任务 | ✅ **达成** | Batch 258 §B1-4（租约回收 + attempt 递增） |
| 5 | 恶意 URL / 恶意 spec 全被拒 | ✅ **达成** | Batch 258 §B1-1/B1-2 + Batch 259 §B2-2 |
| 6 | 「改了 X 要跑哪些」可用 | ✅ **达成** | Batch 260 §B3-3（API + 前端视图；试点规模时延实测中位 4.0ms « 2000ms） |
| 7 | 体育连续 3 个版本达成 SLO | ❌ **未达成**（需环境） | Batch 261 交付判定内核 + 演练驱动；真实数字 → C261-1/C258-1/C260-1 |
| 8 | 生产盘水位可控 | ⚠️ **一半达成** | `df -h` 实测 **73% < 80% ✅**；但 **85% 告警不存在 ❌**（Batch 262 实测） |
| 9 | 备份可恢复 | ✅ **达成** | Batch 262 真实演练通过（67M dump → 临时库 → 抽查 137,642 行执行记录 → 删库，**20 秒**）；手册已补 `docs/ops/restore-drill.md` |

## 2. 逐条验收（怎么验 + 实测 + 证据）

### ① 菜单只剩 4 个入口 + 专家区 ✅
**怎么验**：tester 登录后数一级导航；跑导航断言。
**实测**：`MAIN_ROW_DEFS` = 4 行（我的待办 / 版本验收 / 结果与缺陷 / 知识库），新增 `PRIMARY_ENTRY_LIMIT=4` 常量与「任何角色/菜单集合下 mainRows ≤4」断言；「资产与更多」更名**专家区**（二级 + 权限门禁，不占一级额度）。
知识中心 tester 页签同时由 5 收敛为 **3**（影响面/项目知识/检索），并有「恰好 3」断言。
**证据**：`frontend/src/layouts/nav-config.test.ts`、`frontend/src/pages/knowledge/__tests__/KnowledgeTabs.test.tsx`；`npx vitest run --maxWorkers=2` → 168 文件 737 例全绿。
**浏览器层证据（本机实跑）**：`npm run test:a11y:ci`（Playwright + Chromium，与 CI 同命令）→ **28 passed（39.4s）**，覆盖 login/a11y 基线、batch61 键盘·响应式·axe 基线（多路由 × desktop/tablet/mobile）、batch245 认证首页视觉。
**如实说明（残余缺口）**：本仓 Playwright 套件**没有**"数一级导航数量"的断言；`≤4` 落在 vitest 模型层（`PRIMARY_ENTRY_LIMIT` 与「恰好 3」断言，随 CI 前端 required 运行）。若要求**浏览器层**数导航项，需要一个带后端会话的 E2E job，本批未新增——不把模型断言表述成浏览器 E2E。

### ② 本地节点一条命令可用 ✅
**怎么验**：`cameltv-node up` → 平台显示在线 → 认领任务。
**实测**：Batch 258 的端到端演练**真起节点子进程**执行 `up --once`，完成注册→认领→执行→上传证据→上报；平台侧 `NodeStatusCard` 显示在线/队列/心跳超时。
**证据**：`scripts/node/drill_b1_e2e.py` 转录（`work-logs/batch-258-...-b1-drill-transcript.txt`，19→25 项 PASS）；`tests/test_batch258_node_cli.py` 28 例。
**诚实说明**：演练期间修掉两个真 bug（心跳线程覆盖 `threading.Thread._stop` 导致退出码 1；被测系统请求被系统代理接管返回 502）。
**推送前复跑（2026-09-19，main @ `334748bf`）**：同一脚本重跑 → **通过 25/25**（与 Batch 258 转录逐项一致），存档 `work-logs/evidence/batch-262/b1-drill-replay-20260919.txt`。

### ③ 8 条试点用例真实跑通且证据可查 ⚠️ 部分达成
**怎么验**：平台上打开执行记录 → 下载证据。
**实测**：5 条接口用例经**真 httpx**、3 条 Web 用例经**真 Chromium** 执行；证据上传后逐文件 sha256 与 manifest 对账，再逐个下载复核一致；失败用例留存请求回放与截图（`neg-api.request.json`/`neg-web.png`）。
Batch 261 追加证据包校验：**改一字节即判定 tampered，且该证据不再满足必需证据**（API + 前端显红）。
**证据**：`scripts/node/drill_b1_e2e.py` 25/25；`tests/test_batch261_evidence_bundle.py` 17 例。
**未达成部分（历史）**：B1–B4 交付时目标系统是**本地替身**，不是 Test5 体育环境——`camel-api-gateway05.svc.elelive.cn` 解析为 `192.168.50.170` 但 TCP 80 不通（需 VPN）→ `C258-1`。**当时未伪造** Test5 结论。

**2026-09-19 更新：③ 条在真实 Test5 上达成（真机外）**

Test5 入口已恢复且口径纠正（网关按 `/<service>/` 路由 → 体育 API 基址 `http://camel-api-gateway05.svc.elelive.cn/camel-service`）。用**可执行 payload**（`request{method,url}`+`assertions[]` / `steps[{action,...}]`）在平台+节点上实跑 8 条：

| 任务 | 用例 | 结果 | 证据 |
|---|---|---|---|
| API job **12** | `/ee/version/version`（$.data 含『打包时间』）· `/ee/stream_stats/quality` · `/ee/sports_live/list_faceoff` · `/ee/sports_live/living_group_match` · `/ee/sports_live/player/hot-players` | **5/5 passed**，evidence_files 11 | 请求/响应回放 + manifest；断言含 HTTP 200 **与信封码 `$.status`=200** |
| Web job **11** | 直播站首页主标题 · 直播站导航含 `Camel Live` · 篮球站首页主标题 | **3/3 passed**，evidence_files 7 | 截图 967912B / 1089762B / 451633B，**SHA256 互不相同**（真实渲染） |

对照与勘误：job **10** 用随机 GET 端点只过 3/5，两条失败是 **HTTP 200 但信封码 400**（缺参数）——按其仓库约定属正确判定；另需说明，Batch 265 早期曾把 driver 产生的「Web 30/30」当通过，复核后确认那是**空过**（`steps=[]`、30 张截图逐字节相同），该说法已作废并登记 `C265-3`。

**当前判定**：③ 条**达成（真机外）**——5 接口 + 3 Web 真实跑通、证据可下载；真机（APP 侧）不在此条范围。证据：`work-logs/evidence/batch-265/pilot-8cases-real-test5-20260919.json`。

### ④ 断线不丢任务 ✅
**怎么验**：执行中杀掉节点 → 任务回 pending → 重启节点继续。
**实测**：租约过期自动回收为 `pending` 且 `attempt+1`；再认领同一任务 `attempt=2`。演练中以压缩租约（3s，生产默认 300s，同一代码路径）实测回收与再认领。
**证据**：`tests/test_batch258_execution_job_protocol.py` 18 例（含 `test_claim_then_lose_then_reclaim_over_http`）；演练项「失去心跳后任务回到 pending」「节点恢复后可再认领」。

### ⑤ 恶意 URL / 恶意 spec 全被拒 ✅
**怎么验**：用 5 个恶意 URL + 1 个恶意 spec 复现。
**实测**：5 类恶意 URL 全部被拒（`127.0.0.1` / `169.254.169.254` / 内网域名 / 重定向劫持 / 超大响应），且断言**拒绝发生在出网之前**；伪装域 `pingcode.attacker.tld` 收不到任何 Header；含 `execSync` 的 spec 在**起进程之前**被拒并给出含行号的可读原因。
**证据**：`tests/test_url_guard.py` **17** 例（勘误见附录 A）、`tests/test_batch258_requirement_source_guard.py` 10 例、`tests/test_batch258_token_whitelist.py` 12 例、`tests/test_batch259_spec_guard.py` 20 例。

### ⑥ 「改了 X 要跑哪些」可用 ✅
**怎么验**：平台输入变更模块 → 得到用例集 + 最近结果 + 缺口。
**实测**：`GET /api/v1/impact/what-to-run` 一次返回「受影响模块（含 depends 上游）→ 用例分组（功能/接口/UI）→ 最近一次执行结果 → 未覆盖缺口」，每条带可点回引用；前端 `ImpactTab` 四态完整。
**证据**：`tests/test_batch260_impact_query.py` 13 例（含两条 **SQL 计数断言**：用例 3→33、模块 1→26 时查询条数不变，即防 N+1）；`frontend/src/pages/knowledge/__tests__/ImpactTab.test.tsx`。
**时延实测（本机，试用规模合成数据）**：50 个模块 + 80 条用例（50 接口 + 30 Web）+ 90 条关联边上执行该查询，
5 次取中位：**min 3.8ms / 中位 4.0ms / max 7.4ms**（DoD 阈值 2000ms），返回 受影响模块 50 / 命中用例 80 / 最近执行 80 / 缺口 0。
**方法**：临时内存库建表 → 灌入上述规模的模块/用例/关联边与 plan_case 结果 → `impact_query_service.what_to_run` 计时 5 次；数据为**合成但规模与试点一致**，不使用生产数据。
**诚实边界**：这是"试点规模下不慢"的证据，不是生产数据上的时延 SLA；生产数据下的复测并入 `C261-1`。确定性守卫仍是 `test_batch260_impact_query.py` 的**查询条数不随规模增长**断言。

### ⑦ 体育连续 3 个版本达成 SLO ❌ 未达成（需环境）
**怎么验**：看版本记录：≤1 人日/版本、证据完整率 100%、复用命中 ≥50%。
**现状**：判定内核与演练驱动已交付并**可单测**（11 例），驱动的前置检查在本机实测**如实报 not_ready 并 exit 4**，列出具体缺哪一环（数据集/指纹/节点/被测系统）。
**为什么未达成**：Test5 需 VPN（`C258-1`）、库内无体育资产（`C260-1`）。**我不会用本地替身冒充体育 3 版本验收。**
**怎么跑到达成**：在接 VPN 的机器上依次执行
```bash
python scripts/build_pilot_baseline.py --project-id <N> --environment-id <E> \
    --module-prefix 体育 --account-slot <槽位名> --out baseline.json
python scripts/drill_three_versions.py --project-id <N> --environment-id <E> \
    --account-slot <槽位名> --base-url <平台> --target-url <Test5 网关> \
    --node-token <节点令牌> --versions 3 --person-hours-per-version <人工审核小时> \
    --reuse-suggested <带出数> --reuse-adopted <采纳数> --out drill-report.json
```
把 `baseline.json` 与 `drill-report.json` 回贴，我据此完成第 7 条的最终判定。

### ⑧ 生产盘水位可控 ⚠️ 一半达成（Batch 262 实测）
**怎么验**：`df -h` < 80% 且 85% 阈值能触发告警。
**实测（2026-09-19，生产主机 `111.230.155.116`）**：
```
df -h /          →  /dev/vda2  40G  28G used  11G avail  73%     ← 达标（< 80%）
容器健康          →  postgres Up 12 days / backend·frontend·runner·ai-gateway·aitde-worker Up 37h 全部 healthy
crontab -l        →  仅腾讯云 stargate + 系统任务（e2scrub_all/sgagenttask/sysstat/yunjing）
```
**结论**：水位达标（73%），但**「85% 阈值能触发告警」不成立**——生产上没有任何磁盘水位告警。
与方案 B0-2「磁盘与容量告警固化：待办」一致，本次给出了生产侧直接证据（此前只是文档状态）。
**推送前复核（同日 13:25，只读）**：`df -h /` = **74%**（同一天两次读数差 1 个百分点，属容器日志增长），仍在 80% 阈值内；`crontab -l` 依旧无任何水位告警 → 结论不变。

### ⑨ 备份可恢复 ✅ 达成（Batch 262 真实演练）
**怎么验**：按 `docs/ops/restore-drill.md` 复演一次。
**实测（2026-09-19）**：取最新 dump `cameltv-prod-20260917-145752.dump`（67M）→ 建临时库 → `pg_restore`（stdin 灌入）→ 抽查 → DROP 临时库：
```
public 表数 = 197 ｜ alembic 版本 = 20260922_ai_agent_token
test_execution 行数 = 137642
最近 3 条执行记录 = 137650/137649/137648 | failed | 2026-09-17 04:00:00
临时库已 DROP ｜ 演练耗时 = 20 秒（DoD 要求 2h 内）
```
**补充说明**：`docs/ops/restore-drill.md` 此前**不存在**（B0-3 交付物缺失），当时的演练是临时脚本；本批已补写该手册（含步骤、证据、判定与失败处置），使第 ⑨ 条今后可以"照文档复演"。
**演练同时暴露的两个运维缺口**见 `docs/ops/restore-drill.md` §4：生产库落后主干（B1/B3 迁移未上生产）、备份节奏不满足"每日"。
**推送前独立复演（同日 13:28，逐字执行手册 §2 命令块）**：`pg_restore_exit=0` / `tables=197` / `alembic=20260922_ai_agent_token` / `test_execution=137642` / 同样 3 条执行记录 / `elapsed_seconds=20` / 临时库 `drop_exit=0` —— 与首次演练**逐项一致**，即"照文档复演"这句话现在成立（转录见 `docs/ops/restore-drill.md` §3.1）。

## 3. 未决条件（C 条件）汇总

| ID | 优先级 | 内容 | 解除条件 |
|----|:------:|------|---------|
| `C258-1` | P1 | B1-7 体育试点 8 条用例在 **Test5** 真实跑通 | 在接 VPN 的机器上 `cameltv-node up` 跑 5 接口 + 3 Web 并留存可下载证据 |
| `C258-2` | P2 | 节点侧凭据隔离 | ✅ 已由 Batch 259（B2-1）关闭 |
| `C259-1` | P2 | B2-6 的「被隐藏页面可经**搜索**直达」 | 新增全局搜索/命令面板（新接口 → 完整批次） |
| `C259-2` | P1 | 内核级无凭据沙箱容器 | 节点侧 runner 以非 root 容器运行并给出实测证据 |
| `C260-1` | P2 | B3-2 体育模块关联覆盖率 ≥90%（真实度量） | 目标环境跑 `backfill_impact_edges.py` 并回贴数字 |
| `C261-1` | P1 | **本批新增**：B4-3/4/5 真实 3 版本 SLO 数据 | 执行 §2 第 7 条的两条命令并回贴 `baseline.json` / `drill-report.json` |

## 4. 需要你验收的结论

1. **第 1、2、4、5、6 条**：判定为达成，证据为可复现命令 + 测试集合（上表逐条给出）。
2. **第 3 条**：判定为**部分达成**——链路真实跑通，但目标系统是本地替身；体育真机验收是 `C258-1`。
3. **第 7 条**：判定为**未达成**——需环境跑演练；我已交付判定内核与驱动，且驱动在环境不足时**如实失败**而非降级为替身。
4. **第 8、9 条**：**不在 B1–B4 代码交付范围**（属 B0 运维项），且需生产访问；我没有实测证据，故不给结论。

**如果你要我继续推进第 7/8/9 条**，请提供：Test5 VPN 可达的执行环境（第 7 条），以及生产主机的 `df -h` / 备份恢复演练授权（第 8、9 条）。拿到后我可以按上述命令跑完并回填本报告的对应结论。

## 附录 A. 引用证据逐份复跑（2026-09-19，推送 Batch 262 前）

本报告每个「N 例 / N 文件」都在主干（`334748bf`）上重跑核对一次，避免"报告数字与仓库实际不符"。

### A.1 后端（`test-platform-v2/backend`，`python -m pytest <file> -q`）

| 引用文件 | 报告原写 | 复跑实测 | 结论 |
|---|---:|---:|---|
| `tests/test_batch258_node_cli.py` | 28 | 28 passed (4.55s) | ✅ 一致 |
| `tests/test_batch258_execution_job_protocol.py` | 18 | 18 passed (5.05s) | ✅ 一致 |
| `tests/test_url_guard.py` | 19 | **17 passed (0.10s)**；`--collect-only` 亦为 17 | ❌ **已更正为 17** |
| `tests/test_batch258_requirement_source_guard.py` | 10 | 10 passed (0.10s) | ✅ 一致 |
| `tests/test_batch258_token_whitelist.py` | 12 | 12 passed (0.09s) | ✅ 一致 |
| `tests/test_batch259_spec_guard.py` | 20 | 20 passed (0.11s) | ✅ 一致 |
| `tests/test_batch260_impact_query.py` | 13 | 13 passed (4.13s；3 warnings) | ✅ 一致 |
| `tests/test_batch261_evidence_bundle.py` | 17 | 17 passed (2.83s) | ✅ 一致 |

**`test_url_guard.py` 勘误说明**：该文件自 Batch 258 引入（`2ced1baf`）后**未被任何后续提交改动**（`git log -- tests/test_url_guard.py` 仅一条），文件内 14 个 `def test_`，其中 1 处 `@pytest.mark.parametrize` 展开后共 **17** 例。原写的 19 例最初出自 Batch 258 QA 报告 S1 行的笔误；本报告按实测改正，Batch 258 QA 报告作为已合入批次的历史工件**不改写**，在此留痕。

### A.2 前端（`test-platform-v2/frontend`）

| 引用 | 报告原写 | 复跑实测 | 结论 |
|---|---|---|---|
| `npx vitest run --maxWorkers=2` | 168 文件 / 737 例 | **168 passed (168) / 737 passed (737)**，148.42s | ✅ 一致 |
| `npm run test:a11y:ci`（Chromium） | 28 passed（39.4s） | **28 passed（41.6s）** | ✅ 计数一致（耗时差为机器负载） |

> 复跑在 `wt-main` 工作区执行（= 本分支 base `334748bf`）。Batch 262 未改动任何前端文件，故与在本分支上跑等价。

### A.3 未复跑的引用（如实标注，不当作已验证）

| 引用 | 报告原写 | 状态 |
|---|---|---|
| `scripts/node/drill_b1_e2e.py` + `work-logs/batch-258-execution-node-protocol-b1-drill-transcript.txt` | 19→25 项 PASS | ✅ **已重跑（2026-09-19，main @ `334748bf`）**：`python scripts/node/drill_b1_e2e.py` → `通过 25/25`，与 Batch 258 转录逐项一致；本次以 UTF-8 输出（无 GBK 解码噪声），存档 `work-logs/evidence/batch-262/b1-drill-replay-20260919.txt` |
| `scripts/build_pilot_baseline.py` / `scripts/drill_three_versions.py` | 前置检查 not_ready、exit 4 | **未重跑**（需 Test5 环境）。其"环境不足即如实失败"的行为由 11 例单测覆盖 |
| 第 ⑥ 条时延实测（中位 4.0ms） | 试用规模合成数据 | **未复跑**（临时内存库 harness 未入库）。确定性对照项"查询条数不随规模增长"由 `tests/test_batch260_impact_query.py` 13 例覆盖并通过 |

### A.4 审计基线 S1–S5「已关闭」的代码级复核（2026-09-19）

本报告开头断言 S1–S5 已关闭、S6 部分关闭。该断言的证据此前分散在各批 QA 报告里，这里给出**当前代码上的复核**（基线定义见 `work-logs/reviews/2026-09-18-code-audit-baseline.md` §4）：

| 编号 | 基线问题（main@96cd5b6） | 当前代码证据 | 复核结论 |
|---|---|---|---|
| S1 | 用户可控 URL 出网无 SSRF 守卫（`requirement_source_service.py:80-90`） | 策略本体收敛到 `app/core/url_guard.py`；`_guard()` 在出网前调用（`:139`），重定向逐跳 `_guard_redirect`（`:161`）；`app/core/outbound_policy.py` 反向复用该模块（**不存在第二套 IP 判定**） | ✅ 关闭 |
| S2 | 令牌按"域名含关键字"外发（同文件 `:71-75`、`:128,145`） | `requirement_source_service.py:204`「目标域名不在信任白名单内，已拒绝发送凭据」——白名单判定发生在**拼 `Authorization` 之前**；`tests/test_batch258_token_whitelist.py` 12 例通过 | ✅ 关闭 |
| S3 | `subprocess(shell=True)` + `{image}` 未加引号（`lanhu_evidence/local_ocr_provider.py:62-74`） | 该 provider 现以 **argv 数组 + `shell=False`** 执行（`local_ocr_provider.py:94`），模板经哨兵分词后再插值；全仓 `test-platform-v2/backend/app` 下 `shell=True` / `os.system(` 命中数 = **0** | ✅ 关闭 |
| S4 | 本地对象存储路径未收敛到 base（`object_storage/local.py:24-26`） | `local.py:44-46` = 分段 → `resolve()` → `is_relative_to(base)` 兜底；`tests/test_batch259_object_storage_containment.py` = **16 passed, 1 skipped** | ✅ 关闭 |
| S5 | 密钥加密两套派生（`core/cipher.py:21` vs `ai_config_service.py:61-62`） | `ai_config_service.py:15` 直接复用 `core/cipher.py` 的 `encrypt_value/decrypt_value`，自派生实现已删除；另加「无 `SECRET_KEY` 但库中已有密文 → 启动即失败」兜底（`cipher.py:80-95`） | ✅ 关闭 |
| S6 | 把 `playwright --dry-run` 当沙箱（`case_compiler_service.py:290-345`、`validate=False`） | 表述纠正 + `tests/test_batch259_spec_guard.py` 20 例（危险 API 在**起进程之前**被拒）；**内核级无凭据沙箱仍属节点侧部署层 → `C259-2`（P1，Open）** | ⚠️ 部分关闭（与原文一致） |

**方法**：只读 grep + 源码阅读 + 上列测试实际执行。附带上表外的一项：`tests/test_outbound_policy.py` 3 例通过。

### A.5 审计基线 S7/S8 的复发核对与棘轮覆盖范围（2026-09-19）

审计基线把 S7（静默吞异常 + 异常链丢失）、S8（类级可变默认值）标为**未随 S1–S6 关闭**的项，并要求"把数量做成 CI 棘轮（只降不升）"。按落地方案约束 ④ 核对：

| 项 | 2026-09-18 基线 | 2026-09-19 实测（main @ `334748bf`） | 结论 |
|---|---:|---:|---|
| `S110` try-except-pass | 11 | **11** | 未复发 |
| `S112` try-except-continue | 7 | **7** | 未复发 |
| `B904` raise-without-from-inside-except | 32 | **32** | 未复发 |
| `RUF012` mutable-class-default | 18 | **18** | 未复发 |

命令：`python -m ruff check app --select S110,S112,B904,RUF012,RUF100 --statistics`（工作目录 `test-platform-v2/backend`）。即 **B1–B4 四个批次没有让 S7/S8 恶化**。

**棘轮覆盖范围核对（未处理则登记）**：`scripts/ci/quality_ratchet.py` 执行 `ruff check app/ --config pyproject.toml`，而 `pyproject.toml` 的 `select = [E, F, B, UP, RUF]` —— 因此 `B904`(B) 与 `RUF012`(RUF) 在棘轮内，**`S110/S112` 不在**（`S` 规则集未启用）。该缺口已登记 **`C262-4`（P2）**；现行兜底是 `scripts/git/scan-common-bugs.ps1` 把 `except: pass`（同行与换行两种写法）判为 **HARD**，本批实测 HARD 0。

N-1/N-2/N-3（前端 effect 无 cleanup、裸 `.catch(() => {})`、`noqa` 堆积）属前端静态债，**本批未测量**，保持基线原文状态，不计入本报告结论。
