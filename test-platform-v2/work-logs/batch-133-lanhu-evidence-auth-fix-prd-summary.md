# Batch 133 — 蓝湖证据采集会话失效与失败状态修复 PRD
> **Product (🟦)** | Date: 2026-08-10 | Status: Approved

mode: full（完整批次）
判定理由: 新增"蓝湖重新登录"接口与凭据处理属新行为/新接口；同时修复 418 会话失效被吞、失败误报"已完成"。

## 1. 问题陈述
用户在"需求文档新建证据采集"与"蓝湖证据包上传采集"提交蓝湖链接时报错：
`Client error '418 Unknown' for url 'https://lanhuapp.com/api/project/image?pid=...&image_id=...'`，界面却提示"已完成"。

根因（已定位）：
1. **418 = 蓝湖会话失效**：`lanhu_mcp_server.get_document_info`（lanhu-mcp 子模块）构造 `/api/project/image?pid=&image_id=` 并 `raise_for_status()`；Cookie 来自 `LANHU_COOKIE` 环境变量，过期/失效即 418。当前 `auth_error_types` 不含 418，`runtime.login` 也不存在，因此不触发任何刷新/明确报错。
2. **失败误报"已完成"**：证据任务把 `stage` 置为 `done`，前端 `stageLabel('done')='已完成'` 作为主状态展示；即使任务状态是 failed/success_with_warnings，用户看到的却是"已完成"，错误原因不展示。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 418 识别 | 原样报 418 | 识别为"蓝湖会话失效"，返回可读原因并触发刷新/重试 | 本批验收 |
| 自动重试 | 无 | 用户重新登录拿到新 Cookie 后自动重试原链接，成功拿到内容 | 本批验收 |
| 失败状态 | "已完成"掩盖 | 任务真正失败时主状态显示"失败"并展示 error_message；success_with_warnings 明确"成功(有告警)" | 本批验收 |
| 凭据安全 | 明文配置 | 密码仅用于登录换 Cookie；不落明文（Cookie 加密或仅存内存/环境） | 本批验收 |
| 回归 | - | 后端 F821/导入/相关 pytest、前端 typecheck/build/相关 vitest 无新增失败 | 本批验收 |

## 3. 非目标与 C 条件
- 不改 lanhu-mcp 子模块（登录编排放后端 lanhu_provider，Cookie 回填现有 `LANHU_COOKIE`/运行时 cookie 参数）。
- 不承诺绕过蓝湖风控（验证码等）；登录失败回退"粘贴 Cookie/管理员更新"。
- 纳入：C87-1（共享 lanhu 提取/证据链路行为一致）、C104-5（编辑工具落点）；豁免：其余 Open 条件与本批无关。

## 4. 用户故事与验收标准
- As 测试平台用户, I want 蓝湖会话过期时能自己重新登录并自动重试, so that 我不再卡在 418 和虚假"已完成"。
  - Given 提交的蓝湖链接返回 418 / When 采集执行 / Then 任务状态为"失败"，错误信息含"蓝湖会话失效/已过期"与重新登录入口。
  - Given 用户填写蓝湖账号密码并提交 / When 登录成功 / Then 新 Cookie 保存并自动重试原链接，重试成功后证据内容正常。
  - Given 蓝湖登录被风控拦截 / When 提交 / Then 明确提示并支持粘贴 Cookie 兜底。
- As 测试平台用户, I want 失败任务不被显示为已完成, so that 我能知道真实结果。
  - Given 任务 status=failed / When 查看任务 / Then 主状态显示"失败"（而非"已完成"），并展示 error_message。

## 5. 技术考量
- 后端：lanhu_provider 增加 418/401/403 → `LanhuAuthError`（或等价的会话失效异常）分类；新增 `POST /lanhu-evidence/login`（账号密码 → 调蓝湖登录换取 Cookie → 加密/受保护存储 → 返回脱敏结果）；`get_lanhu_pages_for_evidence`/`_extract_lanhu_content` 在会话失效时触发一次 Cookie 刷新重试；失败返回明确错误。
- 前端：LanhuEvidenceJobDrawer/列表主状态不再用 stage 冒充结果（`stage=done` 仅作阶段，主状态以 status 为准），失败展示 error_message + "蓝湖重新登录"按钮。
- 安全：密码不落库（仅登录换取 Cookie）；Cookie 存受保护位置（环境/加密字段），前端不回显。
- 风险：蓝湖登录接口可能需验证码 → 预留"粘贴 Cookie"兜底；不触碰 lanhu-mcp 子模块，避免子模块指针变更。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批（test） | 内部 | 418 识别 + 登录重试 + 状态修复在 test 验证 |
| 生产 | 用户 | 真实蓝湖链接在会话过期后经重新登录成功采集 |

## 7. 技能使用
- `cameltv-agent-team`：批次门禁与工件。
- `cameltv-bug-guard`：外部依赖异常分类（httpx 超时/418 处理顺序）、不吞错误。
- `cameltv-ui-conventions`：失败状态展示（danger Badge + 错误信息 + 重试入口）。
- `vision`：生产截图核对（418 报错与"已完成"误报）。
