# Batch 79 — PRD Summary（C77-1 存量 HARD 清零）

> **Product (🟦)** | Date: 2026-08-04 | Status: Approved

## 1. 问题陈述

Batch 76 落地的 `scan-common-bugs.ps1` 暴露仓库存量 HARD 67 处；经 Batch 77/78 修复与扫描规则细化后剩余 **41 处 HARD**：

1. **15 处 print 调试遗留**：`main.py`（安全校验/同步注册 4 处）、`ai_service.py`（截断告警 2 处）、`lanhu_provider.py`（提取过程日志 9 处）——违反 AGENTS.md"无 print"自检，且日志无法分级/检索。
2. **26 处无注释静默吞异常**：api/v1 9 处、services 15 处、backend/scripts 2 处——故障不可见，排障靠猜。
3. **扫描工具缺陷**：多行 except-pass 的注释检测取错换行位置，导致带注释的有意兜底（如 auth.py"邮件不是必需的"）仍误报 HARD。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量 |
|------|------|------|------|
| scan HARD | 41 | **0** | scan 复扫 |
| print 遗留 | 15 | 0 | scan 复扫 |
| 无注释吞异常 | 26 | 0（全部加日志或注释） | scan 复扫 |
| ruff F821 | — | 全绿 | ruff |
| 本地 pytest | 环境已恢复 | 全量通过（CI 同口径） | 本地 .venv 执行 |
| 扫描注释误报 | 5 处 | 0（降级 WARN） | scan 复扫 |

## 3. 非目标（本次不做）

- **不处理 231 处 WARN**（脚本 print、硬编码密钥模式、envelope 断言、注释吞异常）：登记 C79-1 后续分批消化。
- **不改 API 行为/契约**：日志与注释变更不影响返回体。
- **不处理 C74-1/2/3**（外部依赖验收项）：继续豁免。

## 4. 用户故事 + 验收标准

- As 排障者, I want 应用日志替代 print 且吞异常可追踪, so that 故障定位不再靠猜。
  - 验收：Given scan 全量 / When 运行 / Then HARD=0；每个原 print 位点有 logger 分级输出。
- As 开发者, I want 带注释的 except-pass 不被误报 HARD, so that 有意兜底代码不被门禁卡住。
  - 验收：Given 多行 except-pass 带注释 / When scan / Then 归入 WARN。

## 5. 技术考量

- 8 个无 logger 文件补 `logging` + 模块级 logger；已带 logger 的文件直接使用。
- 日志内容带上下文（id/名称/原因），不输出敏感信息。
- backend/scripts 两个脚本用行内注释（`pass  # 原因`）说明意图，满足扫描 WARN 分级。
