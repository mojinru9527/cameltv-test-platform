# Batch 259 — PM Plan

> **PM (🟨)** | Date: 2026-09-18
> 对应 PRD: [batch-259-execution-sandbox-and-menu-prd-summary.md](batch-259-execution-sandbox-and-menu-prd-summary.md)

## 规格摘要

**原始需求**: `10-landing-plan-task-backlog.md` §2「B2」表 B2-1…B2-6。
**范围纪律**: 只做 B2 表内任务；B3（知识主线）、B4（3 版本验收）不在本批。

## 开发任务

### [ ] Task 1: 本地对象存储路径收敛（B2-4，关闭审计 S4）
**描述**: `LocalStorage._path` 由 `normpath(join(...))` 改为「resolve + 断言落在 base 内」，
读写删三个入口共用同一收敛函数；写法与 `lanhu_evidence_assets.py:86` 一致。
**验收标准**: `../../etc/passwd`、`..\\..\\windows\\win.ini`、绝对路径、符号链接逃逸全部被拒；正常 URI 不受影响。
**涉及文件**: `app/integrations/object_storage/local.py`、`tests/test_batch259_object_storage_containment.py`
**参考**: 审计 S4；bug-guard「文件路径拼接必须收敛」

### [ ] Task 2: 密钥派生统一 + 启动 fail-fast（B2-5，关闭审计 S5）
**描述**: `ai_config_service._fernet` 改为复用 `app/core/cipher.py`（不再自建 `sha256(secret_key)`）；
新增启动校验：无 SECRET_KEY 且库中已有密文 → 明确报错，而不是静默换一套密钥。
**验收标准**: `rg "sha256\(.*secret_key"` 只命中 `cipher.py`；两处加密/解密互认；无 SECRET_KEY + 有密文 → fail-fast。
**涉及文件**: `app/services/ai_config_service.py`、`app/core/cipher.py`、`app/main.py`、`tests/test_batch259_key_derivation_unification.py`
**参考**: 审计 S5

### [ ] Task 3: 纠正「dry-run = 沙箱」+ 计划路径不再跳过校验（B2-3，关闭审计 S6 的表述部分）
**描述**: 模块 docstring 与段注释不再把 dry-run 称作 sandbox，明确写「语法检查，不是安全边界」；
`test_plan_service._compile_ui_case` 不再传 `validate=False`。
**验收标准**: 全仓搜索无「dry-run/--dry-run」被称作 sandbox 的表述；计划执行路径无 `validate=False`；有断言固化。
**涉及文件**: `app/services/case_compiler_service.py`、`app/services/test_plan_service.py`、`tests/test_batch259_dryrun_not_sandbox.py`
**参考**: 审计 S6；PRD §4 最后一条

### [ ] Task 4: 危险 API 静态拦截（B2-2）
**描述**: 新增 `app/core/spec_guard.py::assert_spec_safe(code) -> list[str]`，拦截
`child_process`（含 `execSync`/`spawnSync`）、`fs` 写操作、`net`/`tls`、`process.env` 读取等危险 API；
在「生成代码 → 落盘 → 执行」链路上**执行前**统一调用，拒绝时给出可读原因（含命中行号）。
**验收标准**: 含 `execSync` 的 spec 在执行前被拒且原因可读；正常 spec 不受影响；拦截点覆盖 ui_test / playground / plan 三条执行路径。
**涉及文件**: `app/core/spec_guard.py`（新增）、`app/services/case_compiler_service.py`、`app/services/playwright_executor.py`、`app/services/playground_service.py`、测试
**参考**: 审计 S6；H1「危险 API 静态拦截」

### [ ] Task 5: 本地执行沙箱硬化（B2-1，H1）
**描述**: 在既有 `execution_sandbox.py`（环境白名单 + POSIX rlimit）之上补齐两项可达面收敛：
文件写入限制在临时工作区、出网按白名单（被测系统 + 平台 API），并在多 worker 下把该结论写成可执行校验。
**验收标准**: 沙箱内读 `.env`、连内网、写持久卷**必须失败**，且有回归用例（缺依赖时 skip 而不是伪造通过）。
**涉及文件**: `app/core/execution_sandbox.py`、`app/core/config.py`、测试
**参考**: H1；PRD §3「不做 OS 级容器」

### [ ] Task 6: 一级菜单收敛 4 入口 + 专家区（B2-6）
**描述**: `nav-config.ts` 收敛 tester 一级导航到 4 项 + 专家区；隐藏项走白名单，保证「权限 + 搜索」仍可达。
**验收标准**: 导航项 E2E 断言 ≤4；被隐藏页面仍可直达；a11y 不回归。
**涉及文件**: `frontend/src/layouts/nav-config.ts`、`MainNavRows.tsx`、相关测试
**参考**: `09` 方案 §2.1；`cameltv-ui-conventions`

## 质量要求

- [ ] 单元测试覆盖  - [ ] 无障碍（ARIA/键盘）  - [ ] 无 console 报错/告警
- [ ] 提交前 `pwsh scripts/git/dev-gate.ps1`：G0–G2 无 HARD/类型/守卫失败
- [ ] 每切片只 `git add` 本切片文件
- [ ] 新增路由/配置同步（路由基线 `tests/fixtures/route_inventory.json`）
