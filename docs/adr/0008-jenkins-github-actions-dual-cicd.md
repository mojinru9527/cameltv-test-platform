---
title: "ADR-0008: Jenkins + GitHub Actions 双通道 CI/CD"
owner: "devops-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["adr", "ci-cd", "jenkins", "github-actions", "devops"]
related: ["0003-frontend-backend-physical-separation.md", "0001-use-python-fastapi-monostack.md"]
---

# ADR-0008: Jenkins + GitHub Actions 双通道 CI/CD

## 状态

✅ 已采纳

## 日期

2026-01

## 背景

CamelTv 测试平台需要 CI/CD 流水线支持以下场景：

1. **代码门禁**：PR 提交时自动运行 lint + 测试
2. **自动部署**：合并到 main 后自动部署到 test 环境
3. **定时回归**：每日 API 全量回归 + 生产冒烟
4. **手动部署**：staging / prod 环境手动触发部署
5. **内网访问**：部分服务（Elasticsearch、内部 API）仅内网可达

单一 CI/CD 系统无法同时满足「外网 PR 触发」(GitHub Actions 擅长) 和「内网部署」(Jenkins 擅长) 的需求。

## 决策

采用 **Jenkins + GitHub Actions 双通道**，各司其职：

### 职责划分

| 职责 | 系统 | 触发条件 | 原因 |
|------|------|---------|------|
| **PR 门禁** (lint/test) | GitHub Actions | PR 提交 | 与 GitHub 深度集成，反馈快 |
| **分支构建** (build 镜像) | Jenkins | push 到 main | 需访问内网 Docker Registry |
| **自动部署 test** | Jenkins | main 构建成功后 | 需访问内网服务器 |
| **手动部署 staging/prod** | Jenkins | 手动触发 | 需要审批链 + 参数化 |
| **11 阶段完整 Pipeline** | Jenkins | push + 定时 | 内网资源访问（ELK、DB） |
| **每日 API 回归** | GitHub Actions | 定时 02:03 UTC | 独立运行，无需内网 |
| **生产冒烟** | GitHub Actions | 定时 08:07 UTC | 外网可访问 prod API |

### 触发流

```
GitHub PR → GitHub Actions (lint + test)
GitHub push main → Webhook → Jenkins (build + deploy test + 全量 Pipeline)
GitHub Actions (定时) → API 回归 + 生产冒烟
手动 → Jenkins (deploy staging/prod)
```

## 后果

### 正面影响

- ✅ 覆盖全场景 — 外网 PR 门禁 + 内网部署都能满足
- ✅ GitHub Actions 免费额度覆盖 PR 门禁和定时回归
- ✅ Jenkins 11 阶段 Pipeline 覆盖从构建到报告的全链路
- ✅ 两个系统独立，一个故障不影响另一个

### 负面影响 / 权衡

- ⚠️ 两套 CI/CD 配置需同步维护（如 Python 版本、依赖变更）
- ⚠️ 新人需理解两个系统的分工
- ⚠️ Jenkins 需要单独的服务器/容器运维
- ⚠️ 两套系统的日志分散，排查跨系统问题需切换上下文

## 弃选方案

### 方案 A: 仅 GitHub Actions

- 优点：统一平台，配置简洁，与 GitHub 深度集成
- 缺点：无法访问内网资源（ELK、内部 API、Docker Registry）
- 放弃原因：测试平台的核心价值在于内网环境的端到端测试

### 方案 B: 仅 Jenkins

- 优点：统一平台，内网访问无限制
- 缺点：PR 门禁反馈不如 GitHub Actions 快，需自运维
- 放弃原因：GitHub Actions 的 PR Check Run 体验优于 Jenkins

### 方案 C: GitLab CI（迁移到 GitLab）

- 优点：单一平台覆盖所有场景
- 缺点：需要迁移整个仓库，GitLab Runner 需自运维
- 放弃原因：迁移成本高，GitHub 生态（Actions Marketplace）更丰富

## 关联

- Jenkinsfile：[根目录 Jenkinsfile](../../Jenkinsfile)
- Jenkins 本地环境：[deploy/jenkins/](../../deploy/jenkins/)
- GitHub Actions：[.github/workflows/](../../.github/workflows/)
- CI/CD 文档：[deploy/CLAUDE.md](../../deploy/CLAUDE.md)
