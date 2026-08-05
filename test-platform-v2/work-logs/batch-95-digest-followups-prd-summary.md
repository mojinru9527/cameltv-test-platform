# Batch 95 — PRD-lite（后续小项消化 + Test5 解锁登记）

> **Product (🟦)** | Date: 2026-08-05 | Status: Review

```markdown
mode: light
豁免理由: 纯文档对齐（docstring）+ CI 验证 + 外部解锁登记，无新接口/配置/依赖/前端改动；
按 pipeline-modes.md 判定轻量批次（PRD-lite + QA + Leader + 看板）。
非目标: 不改检索行为；不引入新功能；契约拉取待 Test5 VPN 窗口。
```

## 1. 问题陈述

三条可本地消化的收尾项：
- **C91-2**：search_service/vector_store docstring 仍写「仅 status=active」，与实现（全状态检索）不符，误导维护者；
- **C93-1**：响应式 CI 定时任务需核验首次运行（可手动触发验证，不必等明天）；
- **C74-2/C65-3**：用户已提供 konfi-service 登录，需按 C63-2 登记解锁；契约拉取需 Test5 VPN 窗口。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| C91-2 | docstring 过时 | 两处对齐 + 知识检索测试全绿 |
| C93-1 | 未核验 | 手动触发 workflow → job success |
| C74-2/C65-3 | 未登记 | 清单 1.4 + C-CONDITIONS 登记 konfi 解锁；契约拉取待 VPN |
| 门禁 | — | audit 0 硬错；无生产代码行为变更 |

## 3. 用户故事 + 验收标准

- As a **维护者**, I want 文档与实现一致，so that 不误解检索语义（C91-2）。
- As a **验收负责人**, I want 定时任务首次运行核验，so that C93-1 关闭有据。

## 4. 技术考量

- C91-2：仅 docstring 文案；keyword/vector 查询体不动，跑 49 项知识检索测试确认无回归。
- C93-1：`gh workflow run responsive-e2e.yml` 手动触发，核对 job 结论。
- C74-2：konfi 凭据仅登记存放位置（WSL 本地，不入库），契约拉取排入 Test5 窗口。
