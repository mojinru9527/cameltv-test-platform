# V4.0 AI 生产黑盒缺陷修复报告

> 分支：`fix/v40-ai-blackbox-remediation`（从 `origin/main` = `e56f6715` 切出，独立 worktree）
> 输入：`work-logs/v40-ai-blackbox-16.0.0-qa-report.md`（生产黑盒测试，15 项缺陷）
> 执行器：DeepSeek Harness（direct 工作流）
> 日期：2026-09-01

---

## 一、修复总览

| 编号 | 问题 | 状态 | 修复方式 |
|---|---|---|---|
| P0-1 | V4.0 全部路由在生产前端不可达（14/14 未开放） | ✅ | 开关改为**运行时读后端**，根除前后端不一致 |
| P0-2 | AI Key 401 但全平台显示「可用」 | ✅ | 新增健康态登记 + `resolve` 暴露 `health` |
| P1-3 | 「功能拆分」按钮完全失效 | ✅ | 修复 `??` 短路 + 抑制预期路径的错误 toast |
| P1-4 | AI 失败误归因为 JSON 错误 + 路径泄露 | ✅ | 统一错误归因模块 + 前端展示真实原因 |
| P1-5 | 「用 DSH 生成」只带标题不带正文 | ✅ | 深链改传 `docId`，异步拉取正文预填 |
| P2-6 | 无 AI 健康状态展示 | ✅ | AI 配置页三态徽标（连通正常/不可用/未验证） |
| P2-7 | 连通性错误是原始 Python 异常串 | ✅ | 可执行中文提示 + 「更新密钥」动作 |
| P2-8 | 使用指引与实际状态矛盾 | ✅ | 改写为「后端为准、前端自动跟随」 |
| P2-9 | V4.0 入口折叠在最底部 | ✅ | `menu:missions` 升入一级平铺区 |
| P2-10 | 命令面板搜不到 V4.0 | ✅ | 补 AITDE 分组 + keywords 别名 + 关闭 cmdk 二次过滤 |
| P2-11 | DSH 向导不预选提供方、置灰无原因 | ✅ | providers 异步到达后补预选 + 置灰原因提示 |
| P2-12 | 「用 DSH 生成」上下文丢失 | ✅ | 随 P1-5 一并解决（正文随深链带入） |
| P3-13 | 图标按钮无 aria-label | ✅ | 三个操作按钮补 `aria-label` |
| P3-14 | 工作台统计口径自相矛盾 | ✅ | 区分「条用例」与「执行次数」 |
| P3-15 | 占位页文案与版本号不符、无指引 | ✅ | 新占位组件含三态与可执行指引 |

**15/15 全部修复。**（P0-2 的「更换生产 Key」属运维动作，代码侧已让失效状态**立即可见**。）

---

## 二、关键修复详解

### P0-1　开关从构建期常量改为运行时跟随后端（根治）

**原缺陷链**：
```
frontend/src/config/aitde.ts   AITDE_V3_ENABLED = import.meta.env.VITE_AITDE_V3_ENABLED === 'true'
frontend/Dockerfile            只声明 ARG VITE_ICP_NUMBER
deploy/docker-compose.yml      frontend build.args 只传 VITE_ICP_NUMBER
⇒ 该变量没有任何传递通道，前端恒为 false；后端开着也没用
```

**修复**（不是补一个构建参数了事，而是消除双事实源）：
- 后端 `GET /api/v2/health` 本就**不受特性门控**且公开返回 `aitde_v3_enabled`——直接作为唯一事实源。
- `config/aitde.ts` 重写为运行时解析（会话内缓存、并发去重），三态：`enabled / disabled / unknown`；
  后端不可达时是 `unknown`，**不静默当作关闭**。
- 新增 `components/AitdeGate.tsx` 统一门控，router 中 **23 处**三元判断全部替换。
- 构建变量降级为**可选覆盖**，并把 `ARG/ENV` 与 compose `build.args` 补齐（文档化的旋钮仍然存在）。

**效果**：改后端 `AITDE_V3_ENABLED` 并重启即可生效，**无需重建前端**；前后端不可能再不一致。

### P1-3　`getOrCreateExtraction` 的 `??` 短路

```ts
// 旧：axios 错误恒带字符串 code（'ERR_BAD_REQUEST'），?? 提前短路，
//     永远读不到 envelope 的 404 → 降级到 extractFeatures 的分支从未执行
const code = (error as { code?: number }).code ?? error.response?.data?.code

// 新：只接受数值型业务码，兼容 HTTP200+code / HTTP404+body / 裸 status
export function readEnvelopeCode(error: unknown): number | undefined
```
同时给该 GET 加 `suppressErrorToast`——「首次无拆分结果」是预期路径，
不该把 envelope 的 `msg`（资源名「功能拆分结果」）当错误弹给用户。

### P1-4　错误归因统一

新增 `backend/app/services/ai_errors.py`：
- `classify_ai_error` → `unauthorized/forbidden/quota/rate_limited/not_found/timeout/unreachable/bad_response/unconfigured`
- `humanize_ai_error` → 可执行中文提示，并**剥离服务端本地路径**（`/tmp/...`、`C:\...` → `<服务端日志>`）
- `AiHealthRegistry` → 进程内按项目登记最近一次真实调用结果

`_call_ai_api` 现在返回 `error_kind`；上层只有在 `error_kind == BAD_RESPONSE` 时才说
「不是合法 JSON」，其余直接透传可执行提示。原始响应仍落盘，但**只写日志、不进用户消息**。

---

## 三、新增回归测试

| 文件 | 用例数 | 覆盖 |
|---|---|---|
| `backend/tests/test_ai_errors_and_health.py` | 17 | 401 归因、真实 httpx 异常、路径脱敏、健康态三态与项目隔离 |
| `frontend/src/__tests__/v40-blackbox-remediation.test.ts` | 18 | `readEnvelopeCode` 五种形态、命令面板别名/门控、开关三态与缓存去重 |

> 其中 2 个测试在编写时就抓到了我自己新代码的真实 bug：
> ① `classify_ai_error` 用未小写文本匹配小写字面量（「未配置 AI 提供方」永不命中）；
> ② 健康态登记直接访问 `cfg.provider_id`，遇到测试替身会把主流程打挂（已改 `getattr` 旁路安全）。

---

## 四、验证结果

### 自检门禁

| 项 | 结果 |
|---|---|
| 后端 `ruff check app/ --select F821` | ✅ All checks passed |
| 后端新增文件 `ruff check ai_errors.py` | ✅ All checks passed |
| 后端全量 `pytest tests/` | ✅ **2338 passed, 9 skipped, 1 xfailed, 0 failed** |
| 前端 `npm run typecheck` | ✅ 0 错误 |
| 前端 `npm run lint`（`--max-warnings=0`） | ✅ 0 |
| 前端全量 `npm test` | ✅ **130 文件 / 607 用例全通过** |
| 前端 `npm run build` | ✅ 通过 |
| `scan-common-bugs` | 2 HARD 均在 `requirement_service.py`（**未改动**，既有基线） |
| E501 | 我新增的行 **0 处**超长（28 项均为未触碰区域基线） |

> 首轮全量曾有 6 个后端失败：1 个是我的真实 bug（已修），5 个是该 worktree 未初始化
> `lanhu-mcp` 子模块所致；`git submodule update --init` 后全部通过。

### 端到端真实浏览器验证（本地后端 + 前端，`VITE_AITDE_V3_ENABLED` **未设置**）

| 场景 | 验证结果 |
|---|---|
| 后端 `AITDE_V3_ENABLED=true` → `/api/v2/health` 返回 `true` | 前端渲染**真实 Mission 列表页**（"新建 Mission"、表格、分页），不再是占位 |
| 同上，侧边栏 | 「智能测试任务」出现在**一级平铺区**，「更多功能」11→10 |
| 命令面板搜「Mission」 | 返回 `AITDE › 智能测试任务 /missions`（此前 0 结果） |
| 命令面板搜「契约」 | 返回智能测试任务（此前 0 结果） |
| 命令面板搜「AI」 | 返回 **11 条**（此前 0 结果） |
| 后端切 `AITDE_V3_ENABLED=false` 重启 | 前端**自动跟随**，渲染新占位页「AITDE 未开放」+ 可执行指引；菜单同步隐藏（10→9） |
| 生产构建产物 | `dist` 主 bundle 含 `/api/v2/health` 与 `aitde_v3_enabled`；旧硬编码占位串已消失 |

### 端到端真实浏览器验证（第二轮：P1-3 / P0-2 / P2-6 / P2-7 / P3-13）

> 证据：`work-logs/evidence/v40-ai-blackbox-16.0.0/fix-verification.json`、
> `fix-verification-sanitize.json`、`screenshots-fixverify/`

| 缺陷 | 断言 | 结果 |
|---|---|---|
| **P1-3** | 点「功能拆分」后必须继续发出 `POST /requirements/{id}/extract` | ✅ 实测请求序列：`GET .../extraction`(**404**) → **`POST .../extract`(200)** —— 旧实现永远走不到第二步 |
| **P1-3** | 不再弹无意义 toast「功能拆分结果」 | ✅ toast 为空；拆分真实产出 modules |
| **P2-7** | 提示不含原始 Python 异常类名 / MDN 链接 | ✅ `hasRawPythonClassName=false` |
| **P2-7** | 给出可执行中文提示 + 「更新密钥」动作 | ✅ 「AI 提供方 API Key 无效或已过期（401）——请到「AI 配置」更新密钥（提供方：…）」 |
| **P0-2/P2-6** | 刚保存未验证时显示「未验证」，不谎称「连通正常」 | ✅ `showsUnverified=true` / `falselyClaimsHealthy=false` |
| **P0-2/P2-6** | 连通失败后显示「不可用」+ 具体原因 | ✅ `resolve` 返回 `health.status=error`、`kind=unauthorized` |
| **P3-13** | 图标按钮有 aria-label | ✅ `测试连通性：本地验证-无效Key` |

> **本轮自查发现并修复的新问题**：脱敏正则过于宽泛，把端点 URL
> `https://api.deepseek.com/chat/completions` 一并抹成 `https:/<服务端日志>`，
> 使 detail 失去诊断价值。已改为「先占位保护 URL、再脱敏本地路径」，
> 并新增用例 `test_humanize_keeps_endpoint_url_intact` 固化；
> 复验确认 URL 完整保留、`/tmp/...` 仍被抹除。

---

## 五、部署注意事项

1. **本次修复后，生产只需把后端 `AITDE_V3_ENABLED=true` 保持开启即可**——前端会自动跟随，
   不需要为开关重建前端镜像。
2. `VITE_AITDE_V3_ENABLED` 保持**留空**（compose/.env.example 默认即留空）。显式填 `false`
   会覆盖后端开关；占位页会主动提示存在该覆盖。
3. **P0-2 仍需一次运维动作**：更新 proj#1 的 DeepSeek API Key。修复后 Key 失效时，
   AI 配置页会显示「不可用」红色徽标与具体原因，不会再伪装成「可用」。
