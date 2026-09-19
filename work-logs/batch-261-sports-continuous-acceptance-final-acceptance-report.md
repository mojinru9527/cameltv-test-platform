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
| 3 | 8 条试点用例真实跑通且证据可查 | ⚠️ **部分达成** | 真实 httpx + 真 Chromium 跑通 5+3；目标为**本地替身**（Test5 不可达 → C258-1） |
| 4 | 断线不丢任务 | ✅ **达成** | Batch 258 §B1-4（租约回收 + attempt 递增） |
| 5 | 恶意 URL / 恶意 spec 全被拒 | ✅ **达成** | Batch 258 §B1-1/B1-2 + Batch 259 §B2-2 |
| 6 | 「改了 X 要跑哪些」可用 | ✅ **达成** | Batch 260 §B3-3（API + 前端视图；试点规模时延实测中位 4.0ms « 2000ms） |
| 7 | 体育连续 3 个版本达成 SLO | ❌ **未达成**（需环境） | Batch 261 交付判定内核 + 演练驱动；真实数字 → C261-1/C258-1/C260-1 |
| 8 | 生产盘水位可控 | ❓ **未能由我验证** | 需生产访问；B0-1 已在方案中记录完成（79%→73%），B0-2 告警固化仍待办 |
| 9 | 备份可恢复 | ❓ **未能由我验证** | 需生产访问与 `docs/ops/restore-drill.md` 演练；B0-3 待办 |

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

### ③ 8 条试点用例真实跑通且证据可查 ⚠️ 部分达成
**怎么验**：平台上打开执行记录 → 下载证据。
**实测**：5 条接口用例经**真 httpx**、3 条 Web 用例经**真 Chromium** 执行；证据上传后逐文件 sha256 与 manifest 对账，再逐个下载复核一致；失败用例留存请求回放与截图（`neg-api.request.json`/`neg-web.png`）。
Batch 261 追加证据包校验：**改一字节即判定 tampered，且该证据不再满足必需证据**（API + 前端显红）。
**证据**：`scripts/node/drill_b1_e2e.py` 25/25；`tests/test_batch261_evidence_bundle.py` 17 例。
**未达成部分**：目标系统是**本地替身**，不是 Test5 体育环境——`camel-api-gateway05.svc.elelive.cn` 解析为 `192.168.50.170` 但 TCP 80 不通（需 VPN）→ `C258-1`。**未伪造** Test5 结论。

### ④ 断线不丢任务 ✅
**怎么验**：执行中杀掉节点 → 任务回 pending → 重启节点继续。
**实测**：租约过期自动回收为 `pending` 且 `attempt+1`；再认领同一任务 `attempt=2`。演练中以压缩租约（3s，生产默认 300s，同一代码路径）实测回收与再认领。
**证据**：`tests/test_batch258_execution_job_protocol.py` 18 例（含 `test_claim_then_lose_then_reclaim_over_http`）；演练项「失去心跳后任务回到 pending」「节点恢复后可再认领」。

### ⑤ 恶意 URL / 恶意 spec 全被拒 ✅
**怎么验**：用 5 个恶意 URL + 1 个恶意 spec 复现。
**实测**：5 类恶意 URL 全部被拒（`127.0.0.1` / `169.254.169.254` / 内网域名 / 重定向劫持 / 超大响应），且断言**拒绝发生在出网之前**；伪装域 `pingcode.attacker.tld` 收不到任何 Header；含 `execSync` 的 spec 在**起进程之前**被拒并给出含行号的可读原因。
**证据**：`tests/test_url_guard.py` 19 例、`tests/test_batch258_requirement_source_guard.py` 10 例、`tests/test_batch258_token_whitelist.py` 12 例、`tests/test_batch259_spec_guard.py` 20 例。

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

### ⑧ 生产盘水位可控 ❓ 未能由我验证
**怎么验**：`df -h` < 80% 且 85% 阈值能触发告警。
**现状**：B0-1（生产盘回收）在 09 方案中已记录完成（**79% → 73%**，释放约 3.2G）；**B0-2（85% 告警固化）仍为待办**。
我没有生产主机访问权限，因此**无法给出实测** `df -h` 与告警触发证据。这一条与第 9 条同属 B0 运维项，不在 B1–B4 的代码交付范围内。

### ⑨ 备份可恢复 ❓ 未能由我验证
**怎么验**：按 `docs/ops/restore-drill.md` 复演一次。
**现状**：B0-3（备份恢复演练）为**待办**；`docs/ops/restore-drill.md` 是否已存在需你确认。同上，需生产访问，我无法代为验证。

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
