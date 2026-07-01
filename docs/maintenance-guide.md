---
title: "CamelTv 知识库持续运营指南"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["maintenance", "operations", "knowledge-base", "governance"]
related: ["document-standards.md", "adr/README.md", "repo-map.md", "business-glossary.md"]
---

# CamelTv 知识库持续运营指南

> 本文档定义 CamelTv 项目知识库（CLAUDE.md + ADR + Memory + docs/）的持续运营机制。
> 目标：知识保鲜、熵减、AI 协作效率最大化。

---

## 1. 运营节奏

### 1.1 季度文档审核日（每季度一次）

**时间**：每季度最后一个周五下午（3 月 / 6 月 / 9 月 / 12 月）

**参与人**：Tech Lead + 各模块 owner

**议程**：

| # | 事项 | 耗时 | 说明 |
|---|------|------|------|
| 1 | 运行 `scripts/check_doc_freshness.py` | 5 min | 自动扫描所有文档的保鲜状态 |
| 2 | 处理过期文档 | 15 min | 更新 `last_reviewed` 和 `expires`，废弃无效文档 |
| 3 | ADR 状态审查 | 15 min | 检查已采纳 ADR 是否仍有效，废弃/替代的 ADR 更新状态 |
| 4 | Memory 条目审查 | 10 min | 清理过时的 memory，合并重复条目 |
| 5 | 常见陷阱更新 | 10 min | 汇总本季度新发现的重复性陷阱 |
| 6 | 知识缺口识别 | 15 min | 讨论缺少哪些文档/知识，分配编写任务 |

**产出物**：
- 更新后的文档（last_reviewed 刷新）
- 过时文档的 deprecated/archived 标记
- 「知识缺口待办」列表（追加到改进 Backlog）

### 1.2 月度自动化检查

每月 1 日 CI 自动运行 `scripts/check_doc_freshness.py --ci`：
- 有过期文档 → CI 失败，通知 owner
- 有即将过期文档（≤30 天）→ CI 警告
- 有待归档的 deprecated 文档（>3 个月）→ 提醒

### 1.3 事件驱动更新

以下事件发生时，**必须**同步更新对应文档：

| 事件 | 需更新内容 | 负责人 |
|------|-----------|--------|
| 重大架构变更 | 相关 ADR 状态更新（可能新增 ADR） | Tech Lead |
| 新增/废弃模块 | CLAUDE.md 模块矩阵 + repo-map.md | 模块 owner |
| 技术栈升级 | Memory `tech-stack-registry.md` + 相关 CLAUDE.md | 执行者 |
| 新常见陷阱发现 | `docs/common-pitfalls.md` + Memory `common-pitfalls.md` | 发现者 |
| 新业务术语引入 | `docs/business-glossary.md` | PM / QA |
| PR Merge | PR 模板自检清单中的文档更新项 | PR 作者 |
| 环境变更（URL/端口/账号） | Memory `env-urls.md` + 相关 README | 运维 |
| CI/CD 流程变更 | Memory `ci-cd-flow.md` + `deploy/CLAUDE.md` | DevOps |

---

## 2. ADR 生命周期管理

### 2.1 状态流转

```
proposed → accepted → superseded → deprecated
                ↓
            deprecated (直接废弃，无需被替代)
```

### 2.2 操作指南

**新增 ADR：**
1. 复制 `docs/adr/template.md`
2. 按 `NNNN-{slug}.md` 命名（取最大 NNNN + 1）
3. 填入标题、背景、决策、后果、弃选方案
4. 更新 `docs/adr/README.md` 索引
5. 在相关 CLAUDE.md 中添加关联

**废弃 ADR：**
1. 将 `## 状态` 改为 `❌ 已废弃（被 ADR-XXXX 替代）` 或 `📦 已弃用`
2. 在后果章节末尾添加废弃原因
3. 更新 `docs/adr/README.md` 索引中的状态标记

**审查要点（季度）：**
- 是否有 ADR 的决策前提已经改变？
- 是否有 ADR 的弃选方案现在变得更合适？
- 是否有新的决策需要 ADR 记录？

---

## 3. Memory 系统维护

### 3.1 Memory 生命周期

```
创建 → 活跃 → 合并/更新 → 归档/删除
```

### 3.2 AI 自动评估（每次对话结束时）

AI 编码助手在每次对话结束时，应自问以下问题并决定是否写入 Memory：

1. **本次对话产生了哪些非代码约定？**
   - 用户偏好（如"以后用这种方式处理"）
   - 新发现的架构约束
   - 工作流改进

2. **本次对话发现了哪些值得记录的模式？**
   - 重复出现的问题
   - 新的最佳实践
   - 需要注意的陷阱

3. **哪些信息在下次对话中 AI 会想知道？**
   - 当前工作状态和上下文
   - 未完成的任务
   - 等待的决策

**写入原则**：
- ✅ 只写代码/文档中没有的 **非显性知识**
- ✅ 每条 Memory 有明确的 Why 和 How to apply
- ✅ 跨会话有用的信息
- ❌ 不写可从 git/代码/CLAUDE.md 直接获取的信息
- ❌ 不写临时性、一次性信息

### 3.3 Memory 清理（季度）

- 检查是否有重复条目 → 合并
- 检查是否有过期信息 → 删除或标记
- 检查 `[[wikilink]]` 引用是否仍然有效
- 更新 `MEMORY.md` 索引

---

## 4. 文档保鲜自动化

### 4.1 CI 集成

在 `.github/workflows/` 中添加文档保鲜检查（建议添加）：

```yaml
name: 文档保鲜检查
on:
  schedule:
    - cron: '7 1 1 * *'   # 每月 1 日 01:07 UTC
  workflow_dispatch:

jobs:
  doc-freshness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install pyyaml
      - run: python scripts/check_doc_freshness.py --ci
```

### 4.2 手动检查

```bash
# 全面检查
python scripts/check_doc_freshness.py

# 修复建议
python scripts/check_doc_freshness.py --fix

# JSON 输出（用于仪表盘/监控）
python scripts/check_doc_freshness.py --json
```

---

## 5. 知识库健康指标

### 5.1 核心指标

| 指标 | 目标 | 测量方式 |
|------|------|---------|
| 文档保鲜率 | > 90% | `check_doc_freshness.py` 的 ok/total |
| 过期文档数 | 0 | `check_doc_freshness.py` |
| ADR 覆盖关键决策 | 100% | 季度审查时人工评估 |
| CLAUDE.md 与实际一致 | 100% | PR Review 时检查 |
| 新成员上手时间 | < 1 天 | 新成员反馈 |

### 5.2 季度健康评分卡

```
知识库健康评分 = (保鲜率 × 0.4) + (ADR 覆盖率 × 0.3) + (文档完整度 × 0.3)
```

- 🟢 健康：> 80%
- 🟡 需关注：60%–80%
- 🔴 需治理：< 60%

---

## 6. 角色与职责

| 角色 | 职责 |
|------|------|
| **Tech Lead** | ADR 审批、季度审核主持、架构文档最终责任人 |
| **Backend Team** | `backend/CLAUDE.md`、`backend/README.md`、后端相关 ADR |
| **Frontend Team** | `frontend/CLAUDE.md`、`frontend/README.md`、前端相关 ADR |
| **QA Team** | `tests/CLAUDE.md`、测试标准文档、测试用例模板、术语表 |
| **DevOps** | `deploy/CLAUDE.md`、CI/CD 文档、环境文档 |
| **全体** | 文档保鲜（更新 last_reviewed）、PR 自检清单、常见陷阱追加 |

---

## 7. 附录

### 7.1 文档类型 → 审核周期速查

| 文档类型 | 默认 expires（月） | 审核人 |
|----------|-------------------|--------|
| CLAUDE.md | 6 | owner |
| ADR | 12 | Tech Lead |
| README | 6 | owner |
| PRD | 与产品版本绑定 | PM |
| Runbook/运维文档 | 3 | 运维 |
| 设计方案 | 项目结束即 deprecated | 作者 |
| Memory | 季度审查 | 全体 |

### 7.2 快速链接

- [文档标准](document-standards.md)：Frontmatter 规范和命名约定
- [ADR 索引](adr/README.md)：所有架构决策记录
- [仓库地图](repo-map.md)：仓库导航
- [业务术语表](business-glossary.md)：统一术语定义
- [常见陷阱](common-pitfalls.md)：已知问题和排查
- [改进 Backlog](../test-platform-v2/docs/改进任务backlog.md)：待领任务
