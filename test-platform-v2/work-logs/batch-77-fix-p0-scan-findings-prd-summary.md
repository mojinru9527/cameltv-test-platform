# Batch 77 — PRD Summary（C76-1 存量 P0 修复）

> **Product (🟦)** | Date: 2026-08-04 | Status: Approved

## 1. 问题陈述

`scan-common-bugs.ps1`（Batch 76 落地）首扫暴露仓库存量 HARD 67 处，其中 Batch 37 审计已点名的两个 P0 仍在：

1. **P0-01 `R.err()` 无定义**：`schemas/common.py` 的 R 只有 `ok()`，而 `test_case.py` 有 7 处 `R.err(code=..., msg=...)` 调用，一旦触发错误分支将抛 `AttributeError` → 500，而非业务错误码。
2. **P0-02 seed.py 明文打印密码（复核结论：契约非漏洞）**：`print(f"[seed] 测试用户自动生成密码：{tester_pwd}")` 曾被视为泄露；但 `tests/test_seed_credentials.py` 已强制"生成凭据一次性显示"契约（admin 走 WARNING 日志、tester 走 stdout，且二次运行零输出）。**本批修正 = 扫描将 seed.py print 降级为 WARN 复核，不再按 HARD 拦截。**
3. **高危静默吞异常**：Batch 37 点名的 open_api.py（通知失败 2 处 + Playwright 线程启动失败 1 处）、api_task_worker.py（任务标记失败、DB 关闭失败 2 处）、playwright_executor.py（产物文件列表失败 1 处）共 6 处 `except Exception: pass`，故障不可见。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量 |
|------|------|------|------|
| R.err | 无定义（7 调用会崩溃） | 定义 + 3 条单测 | pytest（CI）|
| seed 密码 | print 明文 | 保持一次性显示契约（单测强制）；扫描 WARN 复核 | scan 复扫 + 单测 |
| 6 处吞异常 | pass 静默 | logger 记录 | scan 复扫 |
| scan HARD | 67 | 显著下降且 R.err 清零 | scan 复扫 |
| ruff F821 | — | 全绿 | ruff |

## 3. 非目标（本次不做）

- **不修复全部 49 处剩余 HARD**（app 内 print、无注释 except-pass 等）：逐项复核登记为 C77-1，避免范围蔓延。
- **不重构 R 调用为 raise APIException**：本次最小变更 = 补 `err()`（与 R.ok 同构），保持 7 个调用点不动。
- **不处理 C74-1/2/3**（外部依赖验收项）：继续豁免。

## 4. 用户故事 + 验收标准

- As 平台用户, I want 查询不存在/参数错误时返回业务错误码而非 500, so that 前端能正确提示。
  - 验收：Given 用例不存在 / When 调用相关接口 / Then 返回 `{code:404,...}` 而非 AttributeError；R.err 单测通过。
- As 运维, I want 自动生成密码不进日志, so that 凭据不泄露。
  - 验收：Given seed 创建测试用户 / When 查看 stdout / Then 无明文密码；scan 复扫 seed.py 0 命中。
- As 排障者, I want 静默异常有日志, so that 通知/线程/产物失败可追踪。
  - 验收：Given 6 处场景 / When 异常触发 / Then logger 有记录；scan 复扫 6 处 0 HARD。

## 5. 技术考量

- `err()` 实现对齐 Batch 37 建议：`@classmethod def err(cls, code=1, msg="error") -> "R[T]"`。
- seed/open_api 无 logger → 补 `logging` 模块级 logger；api_task_worker/playwright_executor 已有 logger 直接复用。
- scan 工具同步细化：**带注释的 except-pass 视为有意为之降级 WARN**，避免误伤 `pass  # 邮件不是必需的` 类代码。
