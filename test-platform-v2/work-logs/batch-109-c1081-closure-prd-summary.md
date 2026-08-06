# Batch 109 — PRD-lite（C108-1 生产复验登记关闭）

> **Product (🟦)** | Date: 2026-08-06 | Status: Review

```markdown
mode: light
豁免理由: 纯证据/纯文档批次——仅登记 Railway 已开启 KNOWLEDGE_INGEST_ENABLED 后的生产 API
capture 复验结果并关闭 C108-1，不引入新行为/新接口/新配置（pipeline-modes.md §2 轻量判定）。
非目标: 任何代码改动；新功能/新接口/新配置；C107-2/C103-5/6 等遗留项（沿用）。
```

## 1. 问题陈述

C108-1（Batch 108 Leader 条件）：Railway 部署环境增加 `KNOWLEDGE_INGEST_ENABLED=true` 后，
需复验生产 API capture 的错误语义并登记交付清单。用户已于 2026-08-06 在 Railway 配置完成。

## 2. 成功指标

| 指标 | 结果 |
|------|------|
| 生产 capture 唯一内容 | code=0 + id + status=captured（复验通过） |
| 生产 capture 重复内容 | code=409「内容重复」（复验通过） |
| 知识中心可见性 | sources API total=7，新增复验记录可见 |
| 交付清单登记 | `生产环境交付清单.md` 记录开关与复验结果 |
| C108-1 关闭 | C-CONDITIONS Open → Closed 带证据 |

## 3. 验收标准

Given Railway 已配置 KNOWLEDGE_INGEST_ENABLED=true，When 调用生产 capture，
Then 唯一内容返回 200+id、重复内容返回 409，且交付清单与 C-CONDITIONS 同步登记。
