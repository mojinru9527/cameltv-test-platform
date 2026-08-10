# Batch 134 — Design Spec
> **Design (🎨)** | Date: 2026-08-10 | Status: 就绪

## 0. 技术体系确认
lanhu-mcp 使用 Playwright(async_api) + FastMCP + httpx；后端 lanhu_provider 通过 runtime 钩子对接。

## 1. 组件规格表
| 组件 | 说明 | 交互 |
|------|------|------|
| lanhu_login(username, password) | 模块级 async 函数，Playwright 无头 SSO | 凭据缺失/失败返回空串；不抛异常 |
| _save_cached_cookie(cookie) | 落 DATA_DIR/lanhu_cookie.txt | 空串不写；幂等 |
| 后端登录入口（Batch 133） | POST /lanhu-evidence/login | 已就位，本批使 runtime.login 真正可用 |

## 2. 状态设计
- 凭据缺失 → 返回空串 → 后端提示"自动登录不可用，请粘贴 Cookie"
- SSO 验证码/风控/超时 → 返回空串 → 回退粘贴 Cookie
- 登录成功 → 返回 Cookie → 保存 → 自动重试

## 3. 设计 QA
- P2-1 无头浏览器可用性：Playwright 需安装 chromium；guard 捕获缺失，返回空串走兜底。
- P2-2 凭据来源：显式参数优先，环境变量回退；不落明文。

## 4. 设计签核
结论：通过（无 P1 阻断项）。
