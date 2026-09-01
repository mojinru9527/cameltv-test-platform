# CamelTv 测试平台 V4.0 AI 新功能 — 生产环境黑盒测试报告

> 测试对象：测试平台 V4.0（AITDE Legacy Cutover + Enterprise Stable）新上线 AI 功能
> 测试环境：**生产测试环境** `https://swiftbugs.cn`（后端 v2.3.0，main head `e56f6715`）
> 测试输入：**CamelTv 体育平台 16.0.0 需求**（篮球多体育项目适配，蓝湖 16.0.0 更新日志）
> 测试方式：黑盒 —— 真实 Chromium（Playwright 1.61.1）以 `sportsadmin` 登录，从前端 UI 操作
> 项目上下文：`CamelTv 体育平台`（proj#1）
> 执行时间：2026-09-01 21:22 – 22:10
> 证据目录：`work-logs/evidence/v40-ai-blackbox-16.0.0/`

---

## 一、结论

| 项 | 结果 |
|---|---|
| V4.0 AITDE 主链路（Mission→Contract→Scenario→Run）能否在前端使用 | ❌ **完全不可用** |
| 16.0.0 需求能否跑通 AI 用例生成 | ❌ **失败**（AI Key 401） |
| 可达 AI 能力（需求拆分 / DSH 生成） | ❌ 功能拆分失效；DSH 可提交但执行失败 |
| 总体判定 | **NEEDS WORK — 不具备验收条件** |

**一句话**：V4.0 的 AI 功能在生产环境**前端 100% 不可达**（14/14 路由为「未开放」占位），
且平台当前配置的 DeepSeek API Key 已 **401 失效**，导致现存所有 AI 能力同时不可用。
两个问题相互独立，需分别修复。

---

## 二、缺陷清单

### P0-1　V4.0 AITDE 全部功能在生产前端不可用（菜单可见但页面全是占位）

**现象**：侧边栏「更多功能」中可见并可点击「智能测试任务」「Durable Runtime」，
点进去全部显示 **「AITDE V3 未开放 — 需启用 AITDE V3 功能开关后开放」**。

**路由矩阵实测（14/14 全部 FEATURE_FLAG_OFF）**：

| 路由 | 页面 | 结果 |
|---|---|---|
| `/missions`、`/missions/new` | 智能测试任务 | 未开放 |
| `/ai-suggestions` | AI 建议收件箱 | 未开放 |
| `/healing` | 愈合评审 | 未开放 |
| `/flaky` | Flaky 分析 | 未开放 |
| `/executions` | 执行中心 | 未开放 |
| `/data-sources`、`/fixtures` | 数据源 / Fixture | 未开放 |
| `/production/evidence`、`/journeys`、`/templates` | 生产证据链 | 未开放 |
| `/admin/ai-evaluations` | AI 模型评估 | 未开放 |
| `/admin/masking` | 脱敏配置 | 未开放 |
| `/admin/workers` | Durable Runtime | 未开放 |

**后端其实是通的**（同一账号、同一 `X-Project-Id: 1`）：

```
GET /api/v2/missions             200 {"code":0,"data":{"total":0,...}}
GET /api/v2/flaky                200 {"code":0,"data":[]}
GET /api/v2/data-sources         200 {"code":0,"data":[]}
GET /api/v2/production/journeys  200 {"code":0,"data":[]}
GET /api/v2/workers              200 {"code":0,"data":{"items":[]}}
```

**根因**（前端构建变量无传递通道）：

- `frontend/src/config/aitde.ts`：`AITDE_V3_ENABLED = import.meta.env.VITE_AITDE_V3_ENABLED === 'true'` —— **构建期常量**
- `frontend/Dockerfile`：只声明 `ARG VITE_ICP_NUMBER`
- `deploy/docker-compose.yml` frontend `build.args`：只传 `VITE_ICP_NUMBER`
- ⇒ `VITE_AITDE_V3_ENABLED` **从未被传入构建**，前端恒为 `false`；线上 bundle `index-CLmrsH0j.js` 中三元已折叠成占位分支
- 后端 `AITDE_V3_ENABLED` 已为 true（`menu_service.py:49` 未隐藏菜单 + `/api/v2` 可用）→ **前后端开关不一致**

**影响**：V4.0 宣称上线，但用户端零可用；且菜单可见 → 点击 → 死胡同，属于最差的失败形态。

**建议**：
1. `frontend/Dockerfile` 增加 `ARG/ENV VITE_AITDE_V3_ENABLED`，`docker-compose.yml` frontend `build.args` 透传，与后端 `AITDE_V3_ENABLED` 同源；
2. 加一条部署后冒烟断言：后端开关为 true 时 `/missions` 必须渲染真实页面；
3. 兜底：占位页文案应说明「如何开启 / 联系谁」，而不是只写"需启用开关"。

**证据**：`step4-route-matrix.json`、`screenshots/20-route-_missions.png`、`screenshots/10-智能测试任务-列表.png`

---

### P0-2　生产 AI 提供方 API Key 已 401 失效，所有 AI 能力同时不可用

**现象**：平台各处均显示 AI「已配置 / 可用」，但任何真实 AI 调用都失败。

**三条独立链路同时复现**：

| 链路 | 结果 |
|---|---|
| AI 配置 →「测试连通性」 | `{"ok":false,"error":"HTTPStatusError: Client error '401 Authorization Required' for url 'https://api.deepseek.com/chat/completions'"}` |
| 需求文档 →「AI 生成」（task `ai-bcfa505b2c`） | `status: failed` |
| DSH 任务 #12（16.0.0 功能用例生成） | `status: failed`，error：`AI 提供方 API Key 无效或已过期（401）——请到「AI 配置」更新密钥（提供方：DeepSeek 官方）` |

**但平台状态显示全部正常**：

- `GET /api/v1/ai-config/resolve` → `{"configured": true, "provider": {"name":"DeepSeek 官方","model":"deepseek-v4-flash"}}`
- AI 配置页顶部：「AITDE 当前生效模型 deepseek-v4-flash」
- DSH 任务页顶部：「DSH 可用　AI: DeepSeek 官方 / deepseek-v4-flash」

**建议**：
1. 立即更新 proj#1 的 DeepSeek API Key；
2. `resolve` 的 `configured` 语义应区分「已填写」与「可用」，或增加 `healthy` 字段（可缓存最近一次 test-connection 结果）；
3. AI 入口（需求 AI 生成 / DSH 新建任务）在 Key 不健康时应前置提示，而不是让用户提交后失败。

**证据**：`step12-model-discovery.json`、`ai-task-detail.json`、`dsh-task-12.json`、`screenshots/120-测试连通性-toast.png`

---

### P1-3　需求文档「功能拆分」按钮完全失效，且提示无意义

**复现**：需求文档页 → 16.0.0 文档行 →「功能拆分」

```
GET /api/v1/requirements/14/extraction  →  HTTP 404
Body: {"code":404,"msg":"功能拆分结果","data":null}
Toast: 「功能拆分结果」          ← 用户看到的全部信息
结果: 文档状态仍为「已解析」，未发起任何拆分，无弹窗
```

**根因**（前端 404 降级逻辑失效 + 前后端契约不一致）：

`frontend/src/api/requirement.ts` `getOrCreateExtraction`：

```ts
const code = (error as { code?: number }).code          // axios 错误自带字符串 code，如 'ERR_BAD_REQUEST'
  ?? (error as { response?: { data?: { code?: number } } }).response?.data?.code
if (code === 404) return extractFeatures(documentId, signal)
throw error
```

- axios 错误对象**恒有** `code`（字符串），`??` 因此提前短路，永远读不到 envelope 的 `404`
- ⇒ `code === 404` 恒为 false ⇒ **永不回落到 `extractFeatures`（真正发起拆分）**
- 代码注释写「本仓约定：查不到返回 **HTTP 200 + envelope code=404**」，但后端实际返回 **HTTP 404** → 契约不一致

**附带问题**：错误 `msg` 用了资源名「功能拆分结果」而非错误描述，toast 直出后完全不可理解。

**建议**：
1. 判定改为 `const envelopeCode = error?.response?.data?.code ?? (typeof error?.code === 'number' ? error.code : undefined)`；
2. 统一后端「资源不存在」的返回形态（HTTP 200 + code=404，或统一 HTTP 404），并加契约测试；
3. 该请求应带 `suppressErrorToast`（属于预期的"首次无结果"），改由业务逻辑处理。

**证据**：`step7-requirement-ai-entries.json`、`step6-ai-split-generate.json`

---

### P1-4　需求「AI 生成」失败提示无诊断价值，且后端错误归因错误

**UI 只给一句**：`AI 生成失败，请稍后重试`（4 秒后消失，无任务号、无详情入口、无重试按钮）

**后端 `error` 字段实际内容**：

```
AI 返回的 JSON 格式异常，无法解析。
错误: Client error '401 Authorization Required' for url 'https://api.deepseek.com/chat/completions'
原始响应已保存至: /tmp/ai_response_failed_1788270304.json
请检查该文件中的 JSON 语法错误。
```

三个独立问题：

1. **归因错误**：401 鉴权失败被包装成「JSON 格式异常」，并引导用户「检查 JSON 语法错误」——把排查带向完全错误的方向；
2. **泄露服务器内部路径** `/tmp/ai_response_failed_*.json`，且用户无从访问；
3. **前端丢弃全部诊断信息**，只留一句通用文案。

**对照标准**：同一个 401，DSH 模块输出的是
`AI 提供方 API Key 无效或已过期（401）——请到「AI 配置」更新密钥（提供方：DeepSeek 官方）`
—— 正确范本已存在，需求模块未对齐。

**建议**：需求 AI 链路复用 DSH 的错误映射；异步任务失败时前端展示任务号 + 后端 error + 「去 AI 配置」跳转。

**证据**：`step8-ai-generate-network.json`、`ai-task-detail.json`、`step18-dsh-task-detail.json`

---

### P1-5　「用 DSH 生成」只带入文档标题，不带正文

从需求文档行点击「用 DSH 生成」后，向导第 1 步「需求文本」框内容为：

```
体育平台-16.0.0-需求规格说明书      ← 仅 19 字符，即文档标题
```

文档正文（约 3.5KB，含 FR-16-001 ~ FR-16-081 共 30+ 条需求）**未带入**。
若用户直接点下一步提交，AI 只能看到一个标题，产出必然无效。
本次测试是手动粘贴全文后才形成有效任务（DSH #12）。

**建议**：从需求文档发起时自动注入文档解析后的正文（超长时截断并提示）。

**证据**：`step11-dsh-wizard.json`（`prefilledLength: 19`）、`screenshots/70-DSH生成弹窗.png`

---

### P2 级问题

| # | 问题 | 说明 | 证据 |
|---|---|---|---|
| P2-6 | AI 健康状态未接入任何展示 | 平台有 `test-connection` 且能正确检出 401，但 `resolve` 只判「填没填」；AI 配置页/DSH 页/需求页在 Key 失效时仍显示「可用」 | step12 |
| P2-7 | 「测试连通性」提示是原始 Python 异常串 | toast 直出 `HTTPStatusError: Client error '401 Authorization Required' for url ... For more information check: https://developer.mozilla.org/...`，无中文可操作提示 | step14 |
| P2-8 | AI 配置页使用指引与实际状态矛盾 | 指引①写「需开启 aitde_v3_enabled=true，默认关闭」，但后端**已开启**，真正卡点是前端构建变量；用户照指引排查无解 | step10 |
| P2-9 | V4.0 入口可发现性差 | 「智能测试任务」「Durable Runtime」位于折叠的「更多功能」11 项中的第 10/11 位；旗舰新功能默认折叠且排最后 | step2 |
| P2-10 | 命令面板搜不到 V4.0 功能 | Ctrl+K 搜 `Mission`/`AI`/`场景`/`契约` 均 **0 结果**；搜「任务」只命中「定时任务」 | step2 |
| P2-11 | DSH 向导不预选默认 AI 提供方 | 项目已有 `is_default: true` 的提供方，向导仍为空；「下一步」置灰**且无任何原因说明**，用户不知为何点不动 | step15/16/17 |
| P2-12 | 「用 DSH 生成」跳离需求页 | 从需求文档行点击后跳转 `/dsh-tasks` 并在该页开向导，返回需重新定位文档 | screenshots/70 |

### P3 级问题

| # | 问题 | 说明 |
|---|---|---|
| P3-13 | 「测试连通性」是纯图标按钮（lucide-zap），无文字、**无 aria-label**，仅有 title —— 可发现性与可访问性缺陷 |
| P3-14 | 工作台统计口径自相矛盾：「共 10614 条用例，执行通过 1584 条，执行失败 **34208 条**」——失败数是用例总数的 3.2 倍。实为「执行次数」（manual 26240 + api 11704）却表述为「条用例」 |
| P3-15 | 占位页写「AITDE **V3** 未开放」，与本次发布的 **V4.0** 版本号不一致；且未说明开启方式或责任人 |

---

## 三、16.0.0 需求跑通情况

| 步骤 | 结果 |
|---|---|
| 上传 16.0.0 需求规格说明书（Markdown） | ✅ 成功，需求文档 6 → 7（doc#14），状态「已解析」 |
| AI 功能拆分 | ❌ HTTP 404，未发起拆分（P1-3） |
| AI 生成用例 | ❌ 任务 `ai-bcfa505b2c` failed（P0-2 / P1-4） |
| 用 DSH 生成功能用例 | ⚠️ 任务 #12 提交成功，执行 2 秒后 failed（401） |
| 进入 V4.0 Mission 主链路做 16.0.0 验收 | ❌ 入口不可达（P0-1） |

**结论**：16.0.0 需求**无法**在生产环境跑通 V4.0 任一 AI 能力。

---

## 四、修复优先级建议

1. **P0-2 换 Key**（分钟级，解锁现有全部 AI 能力）
2. **P0-1 打通 `VITE_AITDE_V3_ENABLED` 构建链**（否则 V4.0 等于没上线）
3. **P1-3 / P1-4 / P1-5**（AI 主入口的可用性与可诊断性）
4. P2 批次：健康状态展示、错误文案、入口可发现性、向导默认值
5. P3 批次：可访问性、统计口径文案、版本号文案

---

## 五、验证方式与证据索引

**验证方式**：真实 Chromium（Playwright 1.61.1，headless，1600×1000，locale zh-CN）
以 `sportsadmin` 登录生产站点，全程采集 console error / pageerror / requestfailed /
所有 `/api/*` 请求响应（含 envelope `code≠0`）+ 全页截图；关键结论均以「UI 现象 + 网络证据 + 源码根因」三重固化。

| 证据文件 | 内容 |
|---|---|
| `step1-nav-recon.json` / `step2-menu-discoverability.json` | 导航与命令面板可发现性 |
| `step4-route-matrix.json` | **18 条路由可达性矩阵（V4.0 14/14 未开放）** |
| `step5-requirement-upload.json` | 16.0.0 需求上传 |
| `step6/step7-*.json` | 功能拆分 404 复现 |
| `step8-ai-generate-network.json` | AI 生成全量网络抓包 |
| `ai-task-detail.json` | 需求 AI 任务失败原文 |
| `step10/12/13/14-*.json` | AI 配置、测试连通性、401 证据 |
| `step11/15/16/17-*.json` | DSH 向导全过程 |
| `step18-dsh-task-detail.json` / `dsh-task-12.json` | DSH 任务失败详情（正确错误文案范本） |
| `dashboard-stats.json` | 工作台统计口径原始数据 |
| `screenshots/` | 50 张全页截图 |
| `体育平台-16.0.0-需求规格说明书.md` | 本次测试输入 |
| `_tmp_v40_bb/*.mjs` | 可复跑的黑盒脚本（18 步） |

**本次在生产留痕的数据**（供清理参考）：需求文档 `doc#14`、AI 任务 `ai-dcf45ebbc0` / `ai-bcfa505b2c`、DSH 任务 `#12`。
