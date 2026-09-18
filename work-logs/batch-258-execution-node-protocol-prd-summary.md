# Batch 258 — PRD Summary

> **Product (🟦)** | Date: 2026-09-18 | Status: Review
> **批次档位**: 完整批次（六件）

## 0. 批次模式判定（Product 第 1 步）

```text
mode: full
判定依据: 命中触发器 ×4 —— 新接口（ExecutionJob claim/heartbeat/report）、
          数据模型变更（execution_jobs 表 + Alembic 迁移）、
          执行链路变更（本地节点认领/执行/回收）、权限模型变更（节点令牌作用域）
豁免记录: 无（完整批次不允许豁免）
```

对应 `docs/agent-team/pipeline-modes.md` §1 与 `docs/platform-refactor/10-landing-plan-task-backlog.md` §1.3。
`09-platform-landing-plan.md` §6 曾把 B1 标为「轻量」；该标注与同文件 D4（执行链路/数据模型变更强制完整）
及本仓 pipeline-modes 触发器冲突，**以触发器为准**，B1 按完整批次执行。

## 1. 问题陈述

2026-09-18 全量审计基线（`work-logs/reviews/2026-09-18-code-audit-baseline.md`）在两版代码对比后确认：
**8 条问题跨 98 个提交、15 个批次原样存在**——不是某次实现的疏忽，而是流水线里没有任何角色负责核对它们。
其中 3 条（S1 SSRF、S2 令牌外发、S3 `shell=True`）落在「用户输入 → 出网 / 执行命令」这条链上，
而这条链目前**没有任何边界**：

| 事实（`main@e1ae5587` 实测） | 后果 |
|---|---|
| `requirement_source_service._request()` 只判 scheme，`follow_redirects=True`，无响应体上限 | 需求 URL 可打内网/云元数据，响应入库后可回读 = 数据外带 |
| 同文件 `classify_url()` 用 `"pingcode" in host` 子串判定，命中即带 `Bearer` 令牌 | `pingcode.attacker.tld` 直接收割企业 Token |
| `lanhu_evidence/local_ocr_provider.py:74` 用 `subprocess(..., shell=True)` 拼 `{image}` | 路径含空格/元数据字符时命令变形 |
| 平台无「执行协议」：控制面按 ADR-0026 不得跑浏览器/模型，但也没有本地节点可认领的任务模型 | 「控制面不执行」只停留在文档承诺，没有可运行载体 |

同时 `app/core/outbound_policy.py` **已经实现**了私网拒绝、重定向二次校验与响应上限，并有 3 条回归测试，
但需求抓取与发布包导入两个调用点**绕过它**——这是「同一能力存两份、脆弱的那份在被用」的典型流程性遗漏。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 恶意 URL 被拒率 | 0/5（无守卫） | 5/5 被拒且有单测 | 本批 |
| `rg "shell=True" app/` 命中数 | 1 | 0 | 本批 |
| 令牌可外发域名 | 任意含 `pingcode` 子串的主机 | 仅配置白名单根域 | 本批 |
| 用户可控 URL 出网点数 | 2（需求抓取 / 发布包导入） | 全部经统一守卫，0 绕过 | 本批 |
| `cameltv-node up` 可用性 | 不存在 | 一条命令注册+心跳+认领 | 本批（B1-5） |

## 3. 非目标（本次不做）

- **不合并** `ExecutionJob` 与 `AiJob`。方案 §3.2 明确两者并列，合并会重蹈 Batch 240–255 清理过的「双执行栈」。
- **不动老队列**：`ui_test_service` / `api_task_worker` 冻结不扩展（§4 硬约束 2），本批不修不改不删。
- **不做真机**（iOS/Android）：09 §0 D2 已明确本轮不排期。
- **不在控制面引入任何浏览器/模型执行**：本地执行能力只以节点协议 + CLI 形式提供（§4 硬约束 1）。
- **不做执行沙箱容器化**：属 B2-1，本批只交付协议与节点骨架。

## 4. 用户故事 + 验收标准

- As a 测试工程师, I want 需求地址 / 发布包导入里的 URL 被统一守卫拦截, so that 我不会因为填了一个内网地址就把内网数据带出来。
  验收：Given 5 个恶意 URL（`127.0.0.1` / `169.254.169.254` / 内网域名 / 重定向跳转 / 大响应），
  When 走需求抓取与发布包导入, Then 全部被拒且错误可读，单测通过。

- As a 安全负责人, I want 企业令牌只发给白名单域名, so that 仿冒域名 `pingcode.attacker.tld` 收不到任何 Header。
  验收：Given 白名单配置, When 请求 `pingcode.attacker.tld`, Then 不带 `Authorization`（分类回落 generic），
  且白名单域名行为不变。

- As a 运维, I want OCR 命令不再经 shell 拼字符串, so that 含空格/分号的图片路径不会让命令变形。
  验收：Given 默认与自定义 `lanhu_ocr_command`, When 图片路径含空格与 `;`, Then 识别正常且 `rg "shell=True" app/` 为空。

- As a 测试工程师, I want 本地节点一条命令就能认领任务, so that 执行不再依赖云端 4C4G 单机。
  验收：Given `cameltv-node up`, When 节点连接, Then 注册+心跳+认领循环可用；断网 30s 后任务回 pending 并可再认领。

- As a 版本负责人, I want 平台能看到节点在线/离线与队列长度, so that 「点了没反应」不再是常态。
  验收：Given 无节点, When 打开页面, Then 明确提示未连接 + 一键启动指引；节点上线 10s 内状态刷新。

## 5. 技术考量

- **B1-1 是收敛而非新造**：`outbound_policy.py` 的 `resolve_addresses` / `validate_outbound_url` / `safe_get_text`
  已是可用件，B1-1 把纯 URL 断言抽为 `app/core/url_guard.py::assert_public_url()` 作为唯一入口，
  `outbound_policy` 反向依赖它，避免「同一策略两份实现」再次漂移。
- **凭据白名单必须配置化**：真实 PingCode 存在自建域名，因此白名单支持「根域 + 其子域」匹配，默认含厂商根域，
  可用环境变量覆盖；分类不再看子串，令牌只随分类为 provider 的请求发出（结构上保证 H3）。
- **执行协议沿用既有 claim/heartbeat 语义**（`AiJob.status/locked_at/heartbeat_at` 已验证），
  `ExecutionJob` 并列新增，避免改 `AiJob` 语义引发存量回归。
- **已知风险**：B1-7 的 8 条试点用例依赖 Test5 内网 + VPN，控制面不得持有其凭据（H3），
  证据需在本地节点侧产出——本轮若环境不可达，将如实记录为 Deferred 而非伪造通过。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批合入 main | 平台研发 | required checks 全绿 + Leader APPROVED |
| 随发布火车 `release/vX.Y.Z` 上 test | 测试团队 | 迁移单头 + 冒烟通过 |
| B2 起接沙箱 | 试点测试人员 | B2-1 沙箱回归通过后放开 |

## 7. 技能使用

- `cameltv-bug-guard` → 开工前对照「⚠️ 未关闭的已知风险」表逐条定位，确认 S1/S2/S3 证据位置与审计基线一致；
  发现 S1 的能力件（`outbound_policy`）已存在却被绕过，据此把 B1-1 改为收敛方案（非测试证据）。
- `cameltv-agent-team` → 批次模式判定与六部门工件骨架（非测试证据）。
