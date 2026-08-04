# Batch 79 — Design Spec（C77-1 存量 HARD 清零）

> **Design (🎨)** | Date: 2026-08-04 | Status: 就绪

## 0. 技术体系确认

后端 Python 3.12 + logging 标准库；无 API/契约变更。

## 1. 变更设计

| 组 | 文件 | 改动 |
|----|------|------|
| print→logger | main.py（4）、ai_service.py（2）、lanhu_provider.py（9） | `logger.warning/info(...)`，%s 占位，带上下文 |
| 补 logger | main / ai_service / lanhu_provider / apitest / ui_test / defect_service / playground_service / test_plan_service | `import logging` + 模块级 logger |
| 吞异常加日志 | open_api / perf_ws×2 / release_bundles×2 / requirement×2 / av_check / case_compiler / defect / agent_queue / change_detector / regression_predictor / playground×2 / playwright_executor / task_worker / test_plan×3 / wiki/sync | `logger.warning(...)` 带上下文 |
| 吞异常注释 | migrate_cases / migrate_knowledge_domain | `pass  # 原因` |
| 扫描修复 | scan-common-bugs.ps1 | 注释检测从匹配结束位置找行尾 |

## 2. 日志约定

- 解析失败类：`logger.warning("...解析失败，跳过/按空处理: %s", 上下文)`。
- 资源清理类：`logger.warning("...清理失败: %s", 路径)`。
- 后台/通知类：`logger.warning("...失败: %s", 名称/id)`。
- 过程信息类：`logger.info(...)`；告警类：`logger.warning(...)`。
- 不输出密码/Token；截断值（`id[:8]`）可输出。

## 3. 扫描规则修复

```text
修复前: $lineEnd = IndexOf("\n", $m.Index)            # 多行模式取到 except 行尾，注释在 pass 行 → 漏检
修复后: $lineEnd = IndexOf("\n", $m.Index + $m.Length) # 从匹配结束找行尾 → 覆盖 pass 行注释
```

## 4. 设计 QA 走查发现

### ⚪ P3-01 新 worktree 未初始化 lanhu-mcp 子模块
3 个 lanhu 契约测试因子模块缺失失败 → **建议**：QA 前 `git submodule update --init --recursive`，初始化后 3 个测试通过（环境问题，非代码回归）。

## 5. 设计签核

结论：通过（P3-01 为环境操作项，已处理）。
