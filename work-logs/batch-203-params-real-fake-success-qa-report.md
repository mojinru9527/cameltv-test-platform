# Batch 203 — QA 报告：参数真实化 + 假成功与状态一致性修复

> **QA (🟩)** | Date: 2026-08-24 | Verdict: **PASS** | Executor: DeepSeek_Harness | 轻量批次（A+B 修复）

## 1. 验证范围

| 域 | 分支/PR | 入口 |
|----|---------|------|
| A 组·参数真实化 | `fix/params-real-assertions` → **PR #313 → main `fea9c602`** | 导入→生成→调试→断言 全链路 |
| B 组·假成功与状态一致性 | `fix/fake-success-state-consistency` → **PR #314 → main `98a26f4b`** | B1–B14 逐项 |

对照组环境：本机后端 8067 + 前端 5237（复用 `backend/data/platform.db` 证据库：1272 接口资产/8 服务），Test5 VPN（OpenVPN，2026-08-24 用户重连后完成真实执行取证）；执行路径设 `NO_PROXY=*`（先清残留失效代理 127.0.0.1:7688）。

## 2. 结果总表

| 检查 | 命令 | 结果 |
|------|------|------|
| 后端 lint | `ruff check app --select F821`（A 改 5 文件 / B 全 app 独立复核） | ✅ 通过 |
| 后端受影响 pytest | A：`test_agroup_params_real` 17 + generation 16 + knife4j 9 + entrypoint parity/response structure/case real-sample/spec-checklist/assets 等 | ✅ 全绿 |
| 后端全量 | A：`pytest tests`（合并后状态）→ **1686 passed**；B：→ **1703 passed**（`-p no:cacheprovider` 规避本机 %TEMP% 死符号链接清理报错） | ✅ 仅 **5 例 lanhu-mcp 既有基线失败**（见 §3） |
| 前端全量 | `npx vitest run` → **118 文件 / 510 tests**（A 合并后复跑） | ✅ |
| 前端硬门禁 | `npm run typecheck` / `npm run build` | ✅ exit 0（build 9.5s） |
| CI 门禁 | PR #313 / #314：`主干全新检出质量门禁`（后端+前端全量）、`AI/Git 交付策略`、变更范围识别、Vercel | ✅ 双 PR 全绿（#313 run 32682489373 success；#314 run 32684272908 success，含修复后复跑） |

## 3. 基线失败与处置（非本批引入）

| 失败用例 | 性质 | 处置 |
|---------|------|------|
| `test_deploy_compose_contract::test_backend_build_context_contains_runner_and_root_lanhu_submodule` | lanhu-mcp 子模块内容/指针环境依赖 | 主仓库同批失败复现（3/5），登记 **C203-1** |
| `test_lanhu_login_hook::*` ×2 | 同上（pinned 依赖/hook 检查） | 同上 |
| `test_lanhu_provider::*` ×2 | 同上（runtime 依赖声明） | 同上 |

A 全量结论：**无新增失败**（与主基线失败集合一致）。

## 4. B 组首轮 CI 回归 → 修复闭环（重点记录）

PR #314 首轮 `主干全新检出质量门禁` 抓出 **8 例回归**（本地子集自检未覆盖）：

| 回归 | 根因 | 修复 |
|------|------|------|
| `test_batch48_requirement_acceptance` ×6 + `test_batch48_requirement_modules` ×1 | B12 认证审计新增 `auth.*` 审计行，旧测试断言「全量审计计数==0」 | 断言改为排除 `auth.%`（上传链路副作用语义保留；auth 审计为新契约） |
| `test_c55_4_lifecycle_contracts::test_defect_update_rejects_foreign_or_mismatched_references` | B5 对引用校验失败改抛 HTTP 400，违反仓库「业务拒绝=200+code=1」envelope 契约（batch59 过渡契约同款） | PUT 捕获 ValueError → `R.err(code=1, msg)`；自研 B5 单测同步改为 envelope 断言 |

修复后本地全量 1703 passed + CI 复跑 success。**教训**：Batch 3.1 自检「受影响模块」不足以覆盖审计计数类全局断言，CI 全量兜底有效。

## 5. 对照组证据（Black-box 同款，真实环境）

| 场景 | 修复前（QA §8 证据） | 修复后实测 | 结论 |
|------|------|------|------|
| home_match URL | `…/camel-service/sports-live-controller/ee/sports_live/home_match`（tags 污染+双拼） | `http://camel-api-gateway05.svc.elelive.cn/camel-test-confirm/ee/sports_live/home_match` | ✅ 与 §8.2 B-真 手工修正版同构 |
| getByName URL | `…/live-platform/APP管理/app/getByName`（module 乱码） | `…/live-platform/app/getByName` | ✅ module 不再混入 |
| 参数预填 | 空值/占位（§8.2 D） | `day`/`name` 必填预填；有 example 取真实值（单测锁 `20260615`）；无契约留空不造假 | ✅ |
| 默认断言 | 空（发送必「至少需要一个有效断言」） | 3 条（2xx + response_time），页面「断言规则 (3)」 | ✅ |
| **真实执行** | §8.2 C-真：200 + `data.id=34779` | 同款经平台执行：**HTTP 200 / 398.2ms / `{"status":200,"data":{"id":34779,"name":"codex-dev-20260715-874390-updated",…}}` 全部断言过** | ✅ 引擎真实；正确 URL+真参数→真实数据 |
| 不可达语义 | — | 网关不可达（首次执行 VPN 未连）→ 平台诚实报「ERR 请求超时 (30s)」 | ✅ 无假成功 |

取证方式：浏览器驱动平台 UI（登录 admin → 接口测试 → 资产筛选 → 详情/调试 → 断言编辑/参数行读取 `value` 属性 → 执行响应体），与 QA 报告 §8.2 同法。

## 6. 修复后关键断言口径（供 release 用例审计）

- 生成用例正向断言 = 2xx + `$.status`/`$.code` 业务码（有契约 example/default/enum 时 eq，否则 exists）+ 核心字段 exists；无响应契约结构时不虚构断言（保留 2xx）。
- release 门禁 `_assertion_contract_error` 业务码路径识别含 `.status`/`.resultCode`（网关 body.status 为业务码），approved 用例执行不再被误拦。
- 缺陷 PUT 状态机（open→confirmed→fixing→pending_review→closed/…）非法流转 → 200 + code=1 + 状态保持不变；合法流转维护 DefectTransition 历史与 resolved_at。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 2 轮会话（约 6h）/ 约 7h | 0/0/0/5（lanhu 基线，非本批引入） | 3（B 组 envelope 契约 1、审计断言 2、PS5.1 脚本绕过 1 次计入工具链） | 工具链（PS5.1 脚本 stderr 坑）+ 流程（自检范围未覆盖全量断言） | ①轻量批自检清单增加「全局审计/计数断言」扫描；②提交前本地跑一次 `pytest tests -q -p no:cacheprovider` 全量（含受影响域外文件）；③Windows 下 AI 脚本先预 fetch 或用 -q 参数绕过 stderr 中断 |

**证据目录**：本机对照组页面/响应截图存于 A worktree `backend/dev-8067.out.log`（执行记录）与聊天内取证（URL value / 响应 JSON 原文如上表）。
