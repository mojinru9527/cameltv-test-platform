# Batch 134 — PM Plan
> **PM (🟨)** | Date: 2026-08-10

## 规格摘要
**原始需求**: lanhu-mcp 提供可用 `lanhu_login` 自动登录（C134-1），清理明文密码，父仓库更新子模块指针。

## 开发任务
### [ ] Task 1: lanhu-mcp 新增 lanhu_login + _save_cached_cookie
**描述**: 在 `lanhu_mcp_server.py` 末尾（`if __name__` 前）新增模块级 `lanhu_login`（Playwright SSO，凭据可传参或环境变量，失败返回空串）与 `_save_cached_cookie`（落 DATA_DIR/lanhu_cookie.txt）。
**验收标准**: py_compile 通过；无凭据返回空串；函数可被 `getattr(module,"lanhu_login",None)` 获取。
**涉及文件**: `lanhu-mcp/lanhu_mcp_server.py`
### [ ] Task 2: 子模块提交与指针更新
**描述**: lanhu-mcp 内提交并推送（分支 + main），父仓库 `git add lanhu-mcp` 更新指针。
**验收标准**: 指针指向含 lanhu_login 的新 SHA；CI 可拉取。
### [ ] Task 3: 后端钩子测试 + extract_doc 明文密码清理
**描述**: 新增 `tests/test_lanhu_login_hook.py`（导入优先/源码回退）；本地 `extract_doc.py` 明文密码改环境变量（未跟踪文件，仅本地卫生）。
**验收标准**: 测试通过；代码扫描无新增明文凭据。
### [ ] Task 4: C-CONDITIONS 追踪更新
**描述**: 关闭 C133-1，新增 C134-1。
**验收标准**: audit-cconditions 通过。

## 质量要求
- [ ] 后端 `ruff check app --select F821`、相关 pytest 全过
- [ ] 无新增硬编码密钥；无 console/print 调试遗留
- [ ] 子模块指针可被 CI 拉取（已验证推送）
