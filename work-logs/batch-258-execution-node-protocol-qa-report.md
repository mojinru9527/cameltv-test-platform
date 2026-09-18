# Batch 258 — QA 报告

> **QA (🔍)** | Date: 2026-09-18 | Verdict: **PASS（附 1 条 C 条件）**
> 批次档位：完整批次（六件）。范围：`docs/platform-refactor/10-...backlog.md` §2 的 B1-1…B1-7。

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 7（B1-1…B1-7） | 6 | 0 | 1（B1-7 真实 Test5 部分 → C258-1） |

## 可执行门禁（命令 / 退出码 / 日志摘要）

### 后端

| 命令 | 退出码 | 摘要 |
|------|:------:|------|
| `python -m ruff check app/ --select F821` | 0 | All checks passed! |
| `python -c "import app.main"` | 0 | import OK |
| `python -m alembic heads` | 0 | `20260924_batch258_execution_payload (head)` —— 单头 |
| `alembic upgrade head`（独立临时 SQLite，从 base） | 0 | 20 列建表成功，`alembic_version=20260924_...` |
| `alembic downgrade -1` ×2 | 0 | `execution_jobs dropped = True`，version 回到 `20260922_ai_agent_token` |
| `pytest tests/test_batch258_* tests/test_url_guard.py tests/test_batch167_requirement_source.py tests/test_lanhu_ocr_merge.py tests/test_ai_local_agent_flow.py tests/test_playground_security.py tests/test_aitde_rbac_permissions.py` | 0 | **94 passed**（本批域） |
| `pytest tests/aitde/v39/test_migration_single_head.py tests/test_migration_revision_ids.py tests/test_alembic_runbook.py` | 0 | 11 passed |
| `pwsh scripts/git/scan-common-bugs.ps1` | 0 | HARD **0**；WARN 332（全部为存量，非本批引入） |

### 前端

| 命令 | 退出码 | 摘要 |
|------|:------:|------|
| `npm ci` | 0 | 850 packages（无新增依赖） |
| `npm run typecheck` | 0 | `tsc -b` 无错误 |
| `npm run lint` | 0 | `eslint . --max-warnings=0` 无告警 |
| `npm test` | 0 | **165 文件 / 721 例全绿**（含本批新增 12 例） |
| `npm run build` | 0 | `✓ built in 11.28s` |

### 端到端演练（B1-7）

`python scripts/node/drill_b1_e2e.py` → **25/25 PASS**，退出码 0，完整转录见
[batch-258-execution-node-protocol-b1-drill-transcript.txt](batch-258-execution-node-protocol-b1-drill-transcript.txt)。

链路里每一环都是真的：真 Alembic 迁移建库 → 真 uvicorn → 真登录/seed → 真节点令牌 →
真 `cameltv-node up --once` 子进程 → 真 httpx（5 接口）+ 真 Chromium（3 Web，截图落盘）→
真证据上传对账 → 真下载逐文件 sha256 校验 → 真失联回收与再认领 →
**真失败用例**（故意断言的失败 API/Web 各 1 条，验证失败未被伪造成通过且留存回放/截图证据）。

## 逐条件验证

### B1-1: 统一出网守卫 + 两个调用点接入 ✅ PASS
**变更**: `app/core/url_guard.py`（新增）、`app/core/outbound_policy.py`、`app/services/requirement_source_service.py`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 5 类恶意 URL 全拒 | ✅ | `127.0.0.1` / `169.254.169.254` / 内网域名 / 重定向劫持 / 超大响应 |
| 守卫前零出网 | ✅ | 用 `httpx.MockTransport` 记录：拒绝路径 `visited == []` |
| 收敛而非新增第二套 | ✅ | `outbound_policy.validate_outbound_url` 委托 `assert_public_url`，既有测试零改动通过 |
| 正常链路不回归 | ✅ | HTML 抓取、相对重定向、鉴权 Header 透传均有断言 |

### B1-2: 凭据白名单 ✅ PASS
**变更**: `app/core/config.py`、`requirement_source_service.classify_url`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| `pingcode.attacker.tld` 收不到 Header | ✅ | 分类回落 `generic`，请求无 `Authorization` |
| 伪装域全拒 | ✅ | `notpingcode.com` / `pingcode.com.attacker.tld` / `atlassian.attacker.tld` |
| 显式 kind 走私被拒 | ✅ | 复核域名白名单，不符即拒且零出网 |
| 自建实例可用 | ✅ | 配置追加根域后分类正确 |

### B1-3: OCR 去 shell ✅ PASS
**变更**: `app/services/lanhu_evidence/local_ocr_provider.py`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| `rg "shell=True" app/` 为空 | ✅ | 并被一条测试固化为可执行校验 |
| 含空格/分号路径不变形 | ✅ | 哨兵 + `shlex.split`，路径始终单一 argv |
| **真实识别**（非仅命令构造） | ✅ | 真生成 PNG → 真 rapidocr 子进程，路径 `...\a b; c\shot 1;2.png`（同时含空格与分号）→ `status=success`，识别出 `CAMELTV NODE 258`；依赖缺失时 `importorskip` 跳过，不做模块级硬断言 |

### B1-4: ExecutionJob 协议 ✅ PASS
**变更**: `app/models/execution_job.py`、迁移 ×2、`app/services/execution_job_service.py`、`app/api/v1/execution_jobs.py`、`app/seed.py`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 认领→心跳→上报→回收全链路 | ✅ | 18 例，含 HTTP 端到端 |
| 跨项目不可认领 | ✅ | 令牌即项目作用域，结构上不成立 |
| 静态路径不被 `/{job_id}` 抢匹配 | ✅ | `/claim` 返回非 422 |
| 权限点独立 | ✅ | `execution:view` / `execution:manage`，不复用 `uitest:*` |
| 迁移单头 + 可离线/可逆 | ✅ | 见门禁表 |

### B1-5: cameltv-node CLI ✅ PASS
**变更**: `scripts/node/**`、`app/services/execution_evidence_store.py`、payload 迁移
| 检查项 | 结果 | 说明 |
|--------|------|------|
| `cameltv-node up` 一条命令可用 | ✅ | 演练中真实子进程执行，退出码 0 |
| 断网不丢任务 | ✅ | 失联后回 `pending`，再认领 `attempt=2` |
| 执行器不伪造成功 | ✅ | 依赖缺失/断言失败/上传对账不一致均如实失败 |
| 证据路径收敛 | ✅ | 文件名显式拒绝路径成分；下载 `is_relative_to` |

### B1-6: 平台侧节点状态 ✅ PASS
**变更**: `frontend/src/api/executionJobs.ts`、`components/execution/NodeStatusCard.tsx`、`pages/workbench/index.tsx`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 无节点时明确提示 | ✅ | 「本地节点未连接」+ 任务会排队的说明 + 启动命令 + 复制 |
| 10s 内刷新 | ✅ | 轮询 8s，且有 `NODE_STATUS_POLL_MS <= 10000` 的断言 |
| 四态完整 | ✅ | 骨架 / 错误可重试 / 未连接 / 在线（含心跳超时告警） |
| 副作用卫生 | ✅ | 两个 effect 均有 cleanup，卸载后不再轮询 |

### B1-7: 端到端证据 ⚠️ 部分（本地替身全绿；Test5 部分 → C258-1）
**交付**: `scripts/node/drill_b1_e2e.py` + 演练转录
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 5 接口 + 3 Web 真实跑通 | ✅ | 5/5 与 3/3，真 httpx + 真 Chromium |
| 证据可下载 | ✅ | 11 + 7 个文件，逐个 sha256 与 manifest 一致 |
| 失败用例有请求回放/截图 | ✅ | 失败阶段实测：`neg-api` 留下 `request.json`（含 method/url/headers/body）+ `response.json`（HTTP 500），`neg-web` 留下 `neg-web.png` + `console.json`；任务结论为 `failed`（`failed=1`）而**未被伪造成通过**，节点仍正常退出 0（失败是任务结论，不是节点崩溃） |
| 目标为体育 Test5 | ❌ | `camel-api-gateway05.svc.elelive.cn` → 192.168.50.170:80 **TCP 不通**（需 VPN）→ 登记 C258-1，**不伪造** |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| D1 | P1 | `HeartbeatThread` 用 `_stop` 覆盖 `threading.Thread` 内部方法，解释器收尾时调用 `Event` 对象 → `TypeError`；节点实际干完活却**退出码 1**（"一条命令可用"会被误判失败） | 演练首轮 FAIL 输出 | ✅ 已修（改名 `_stop_event`） |
| D2 | P1 | 被测系统请求未禁 `trust_env`，被 Windows/IE 全局代理（`127.0.0.1:7688`，未监听）接管 → HTTP 502；内网被测目标不应经全局代理 | 演练首轮 `HTTP 502 body=''` | ✅ 已修（SUT 客户端 `trust_env=False`） |
| D3 | P2 | `safe_file_name` 用 `Path(name).name`「剥掉」目录：POSIX 不把 `\` 当分隔符 → `..\evil.txt` 被原样接受（Linux 生产即目录穿越），且改名会让上传对账对不上 | `test_unsafe_file_names_are_rejected` 4 例 FAIL | ✅ 已修（显式拒绝路径成分） |
| D4 | P2 | 测试替身 `lambda host, port: {PUBLIC_IP}` 把 `127.0.0.1` 也伪装成公网 → 守卫生效却测不出来 | `test_redirect_to_loopback_is_rejected` FAIL | ✅ 已修（字面量 IP 保持原值） |
| D5 | P3 | `cameltv-node.cmd` 含中文注释，在 cmd.exe 部分代码页下被当作命令执行 | `'��命令开工...' is not recognized` | ✅ 已修（纯 ASCII + 注释说明原因） |

无未修复缺陷。P1 两条均为**演练（真实执行）**发现，静态检查与单测都没抓到——这正是"禁止静态代替执行"的价值。

## bug-guard「未关闭已知风险」表核对（每批必答三问）

**1) 本批是否新增了清单中的任一项？** 否。
- `ruff --select S110,S112,B904,RUF012` 未见本批新增（新增代码无静默吞异常、无 `raise ... from` 缺失、无类级可变默认值）。
- 新增的两条「用户输入 → 出网 / 落盘 / 执行代码」路径（证据文件落盘、被测系统出网）见第 3 问。

**2) 本批是否修复/关闭了其中任一项？** 是，关闭 3 条：

| 编号 | 风险 | 关闭证据 |
|------|------|---------|
| S1 | 用户可控 URL 出网无 SSRF 守卫 | commit `063bb3a2`；`tests/test_batch258_requirement_source_guard.py` 10 例 + `tests/test_url_guard.py` 19 例 |
| S2 | 令牌按域名子串外发 | commit `2adb3dab`；`tests/test_batch258_token_whitelist.py` 12 例 |
| S3 | OCR `shell=True` | commit `52ba41e6`；`tests/test_batch258_ocr_command.py` 9 例 + `app/` 全局扫描断言 |

仍开放（按计划归 B2，未在本批扩散）：S4 本地对象存储路径收敛、S5 双密钥派生、S6 dry-run 当沙箱。
Playground `uitest:code_execute` 回归未被触碰（`tests/test_playground_security.py` 绿）。

**3) 本批新增的「外部输入 → 出网 / 落盘 / 执行代码」路径，是否都过了对应铁律？** 是：

| 路径 | 铁律 | 校验 |
|------|------|------|
| 需求 URL / 发布包导入出网 | SSRF 守卫 + 白名单 + 响应上限 | 见 S1/S2 用例 |
| 执行载荷出网（节点 → 被测系统） | 出网不得被全局代理接管 | D2 修复 + 演练 5/5 接口实跑 |
| 证据文件落盘 | 路径拼接必须收敛 | 文件名显式拒绝路径成分 + 下载 `is_relative_to` + 3 类穿越用例 |
| 用户提供代码执行 | dry-run 不是安全边界 | **本批未新增该路径**；沙箱归属 B2-1 |

## CI 分层核对

本 PR 同时改动 `test-platform-v2/backend/**`、`test-platform-v2/frontend/**` 与 `scripts/node/**`
（后者不在分类器域内，按"未知/混合"保守处理），因此**前后端 required 都会实跑**，不存在跳过。
QA 不依赖 job 名称推断质量：上表所有门禁均在本机 worktree 实跑并记录退出码。

## 发布建议

状态：**READY**（B1-1…B1-6 全绿；B1-7 本地替身全绿，Test5 部分转 C258-1）
必修复：0　建议修复：0

## 复盘卡（Batch 75 起强制）

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 16h / 实际 ~21h | 0/2/2/1 | 3 | 需求不清（B1 与 B4-1 证据口径重叠）+ 环境（代理/VPN） | 批次开工前先跑一次"依赖与可达性探针"（VPN/浏览器/代理），把不可达项在 PRD 阶段就登记成 C 条件，而不是到 B1-7 才发现 |

**技能使用**: `cameltv-bug-guard` → 三问 + 未关闭风险表核对（非测试证据）；`cameltv-agent-team` → 批次档位与工件骨架（非测试证据）；`test-case-design` 未调用（本批以代码级回归为主，非用例设计任务）。
