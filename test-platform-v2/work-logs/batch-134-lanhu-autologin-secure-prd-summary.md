# Batch 134 — 蓝湖自动登录与安全清理 PRD
> **Product (🟦)** | Date: 2026-08-10 | Status: Approved

mode: full（完整批次）
判定理由: 在 lanhu-mcp 子模块新增 `lanhu_login` 自动登录能力属新行为/新接口（子模块指针变更）。

## 1. 问题陈述
Batch 133 提供了"蓝湖重新登录"入口，但自动登录依赖 lanhu-mcp 提供 `lanhu_login`，而 pinned 子模块缺失该函数 → 用户账号密码登录实际走不到。此外 lanhu-mcp 本地工作区 `extract_doc.py` 存在硬编码明文蓝湖密码（安全债，C134-1）。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| lanhu_login 钩子 | 缺失 | lanhu-mcp 提供 `lanhu_login(username,password)` 与 `_save_cached_cookie`，后端 runtime.login 可调用 | 本批验收 |
| 无凭据行为 | - | 未配置凭据时返回空串不抛异常，回退"粘贴 Cookie" | 本批验收 |
| 安全 | 明文密码 | 跟踪代码无新增硬编码凭据；extract_doc.py 本地硬编码改为环境变量 | 本批验收 |
| 子模块指针 | c9f4a43 | 指向含 lanhu_login 的新提交并可被 CI 拉取 | 本批验收 |
| 回归 | - | 后端 F821/导入/相关 pytest、前端 440 全量无新增失败 | 本批验收 |

## 3. 非目标与 C 条件
- **关闭 C133-1**（Batch 133 已交付 418 识别 + 登录入口），**新增 C134-1**（本批执行）。
- 不保证绕过蓝湖验证码/风控：自动登录尽力而为，失败回退粘贴 Cookie。
- 不引入前端改动（前端入口 Batch 133 已就位）；不改生产数据。

## 4. 用户故事与验收标准
- As 测试平台用户, I want 在"账号密码登录"提交后真正完成蓝湖登录, so that 会话过期后可自动重试。
  - Given 后端调用 `runtime.login(username, password)` / When 蓝湖 SSO 可登录 / Then 返回新 Cookie 并保存。
  - Given 未配置凭据或登录失败（验证码/风控）/ Then 返回空串/明确提示，前端回退粘贴 Cookie。
- As 仓库维护者, I want 无硬编码明文凭据, so that 不泄露账号密码。
  - Given 代码扫描 / Then 跟踪代码无明文密码；本地 extract_doc.py 改为环境变量。

## 5. 技术考量
- lanhu-mcp（子模块）：新增模块级 `lanhu_login(username="", password="")`（Playwright 无头 SSO：填账号→勾选协议→登录→等待 /web/→取 Cookie 拼 header；失败返回空串）；`_save_cached_cookie` 落 DATA_DIR/lanhu_cookie.txt。凭据可传参或走 LANHU_USERNAME/LANHU_PASSWORD 环境变量。
- 后端：`_load_lanhu_runtime` 已预留 login/save_cookie 钩子，无需改动即可接上；验证签名兼容（无参调用回退环境变量）。
- 子模块指针：父仓库 pin 到新提交并推送子模块 main/分支，确保 CI 可拉取。
- 风险：蓝湖 SSO 结构变化/验证码 → 函数返回空串走兜底；Playwright 浏览器需在部署环境可用（guard 捕获）。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批（test） | 内部 | 钩子可用性单测 + 后端门禁全绿 |
| 生产 | 用户 | 真实蓝湖链接在会话过期后经账号密码登录成功重试（依赖 SSO 无验证码） |

## 7. 技能使用
- `cameltv-agent-team`：批次门禁与工件。
- `cameltv-bug-guard`：异常吞错/外部依赖；无硬编码密钥。
- `vision`：生产截图核对（如需）。
