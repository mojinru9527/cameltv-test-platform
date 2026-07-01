---
title: "CamelTv 业务术语表"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["glossary", "terminology", "reference", "onboarding"]
related: ["CLAUDE.md", "docs/repo-map.md", "tests/test-case-standards/测试用例标准.md"]
---

# CamelTv 业务术语表

> 本文档是 CamelTv 体育平台测试生态系统的权威业务术语定义。所有项目文档、测试用例、需求规格中使用的术语以本文为准。
>
> 用途：新人 onboarding 第一站、需求评审对齐语言、AI 协作时的上下文锚点。

---

## 1. 产品与系统

| 术语 | 英文 | 说明 | 适用场景 |
|------|------|------|---------|
| CamelTv 体育平台 | CamelTv Sports Platform | 体育内容与服务的一体化平台，包含用户端和运营后台两个主要子系统 | 项目总称、架构文档 |
| 用户端 | User-facing App | 面向终端用户的体育内容消费产品（用户侧功能），版本号以蓝湖「更新日志」页产品手写为准 | 需求分析、功能测试 |
| 运营后台 | Admin Console / Operations Backend | 面向内部运营人员的管理系统（管理员侧功能），版本号以蓝湖「更新日志」页产品手写为准 | 需求分析、功能测试、权限测试 |
| 测试平台 v2 | Test Platform v2 | 主力测试管理平台，FastAPI + React 18 前后端分离架构，覆盖需求到报告的完整闭环 | 日常测试管理、CI/CD 集成 |
| 测试平台 v1 | Test Platform v1 (Legacy) | 旧版单体测试平台，含 10 件 CLI 工具套件，处于维护模式 | CLI 工具使用、旧版维护 |
| 蓝湖 | Lanhu | 第三方产品设计协作平台，承载 Axure 原型和设计稿 | 需求提取、原型分析、设计稿参数提取 |

## 2. 核心测试概念

| 术语 | 英文 | 说明 | 适用场景 |
|------|------|------|---------|
| 测试用例 | Test Case (TC) | 描述测试前置条件、步骤、预期结果的最小测试单元。命名格式 `TC-{模块}-{编号}.md` | 用例设计、用例库管理、执行 |
| 测试计划 | Test Plan | 组织多轮测试执行的容器，关联用例集合、指定执行者和时间窗口 | 版本测试规划、回归测试组织 |
| 测试执行 | Test Execution | 对测试计划中的用例逐一执行并记录结果的过程，结果类型包括 pass/fail/skip/block | 执行记录、进度跟踪 |
| 缺陷 | Defect / Bug | 测试执行中发现的与预期不符的问题，遵循 6 状态状态机（新建→确认中→已确认→修复中→已修复→关闭） | 缺陷管理、质量追溯 |
| 需求 | Requirement | 产品功能的规格描述，由蓝湖原型提取或手工创建，AI 可基于需求生成用例 | 需求管理、用例生成、追溯矩阵 |
| AI 生成用例 | AI-Generated Test Case | 通过 DeepSeek LLM 分析需求文档自动生成的测试用例，支持两段式生成和反向评审 | 快速生成用例、需求评审 |
| 质量追溯矩阵 | Traceability Matrix | 建立「需求→用例→执行→缺陷」全链路双向追溯关系，支持项目覆盖率和单用例追溯 | 质量度量、版本发布评审 |
| 域树 / 模块树 | Domain Tree / Module Tree | 测试用例的分类体系，按业务域和功能模块组织成树形结构 | 用例组织、批量操作 |

## 3. 测试类型

| 术语 | 英文 | 说明 | 适用场景 |
|------|------|------|---------|
| 功能测试 | Functional Testing | 验证产品功能是否符合需求规格的测试，以手动执行为主、AI 辅助生成用例 | 每个版本的必测项 |
| API 测试 | API Testing | 针对后端接口的自动化测试，Swagger 优先 + UI 捕获补充策略，基于 Playwright TypeScript | 接口回归、CI 流水线 |
| UI 自动化测试 | UI Automation Testing | 基于 Playwright + TypeScript 的浏览器端自动化，当前覆盖 6 个模块（home/list/detail/pay/refund/bonus） | P0 用例自动化覆盖 |
| 音视频质量测试 | Audio/Video Quality Testing | 针对体育直播/点播音视频质量的专项检测，包括码率、延迟、卡顿率等指标 | 直播质量保障、赛事重保 |
| 性能测试 | Performance Testing | 验证系统在高并发/大数据量下的表现，部分使用 locust 执行 | 大版本发布前、赛事高峰前 |
| 冒烟测试 | Smoke Test | 最小集的快速验证，确保核心功能可用，通常由 CI 定时触发 | CI/CD 部署后、每日自动执行 |
| 回归测试 | Regression Testing | 验证新代码变更未破坏已有功能的测试，main 分支合并后全量执行 | 版本发布前、合并到 main 后 |

## 4. 优先级体系

| 级别 | 英文 | 说明 | 执行策略 |
|------|------|------|---------|
| P0 | Priority 0 - Critical | 核心必测用例，每个版本必须通过 | 自动化优先覆盖、CI 阻塞项 |
| P1 | Priority 1 - High | 常用功能，高频使用场景 | 自动化优先覆盖、版本必测 |
| P2 | Priority 2 - Medium | 一般功能，中低频使用 | 回归时覆盖 |
| P3 | Priority 3 - Low | 次要功能、边界场景 | 大版本全量时覆盖 |

## 5. 角色与权限

| 术语 | 英文 | 说明 | 适用场景 |
|------|------|------|---------|
| 管理员 | Admin | 系统超级管理员，拥有所有权限点和全局数据范围 | 系统配置、用户管理、权限分配 |
| 项目经理 | Project Manager (PM) | 负责项目级管理，拥有所管理项目的数据范围 | 需求管理、计划制定、进度跟踪 |
| 测试执行者 | Tester | 执行测试用例、提交缺陷的一线测试人员 | 用例执行、缺陷提交、测试记录 |
| 开发者 | Developer | 负责修复缺陷和实现功能的开发人员 | 缺陷修复、功能开发、代码审查 |
| RBAC | Role-Based Access Control | 基于角色的访问控制，三级数据范围（global/project/self）+ 权限点精细化授权 | 权限系统设计 |
| 权限点 | Permission Point | RBAC 的最小授权单元，每个 API 操作对应一个权限点 | 权限配置、API 开发 |
| JWT | JSON Web Token | 无状态认证令牌，包含用户身份和过期时间 | 前端认证、API 鉴权 |

## 6. 版本管理

| 术语 | 英文 | 说明 | 适用场景 |
|------|------|------|---------|
| 用户端版本号 | Client Version | 以蓝湖「更新日志」页产品手写版本号为准，当前为 14.1.0 | 需求规格说明、测试版本标识 |
| 运营后台版本号 | Admin Console Version | 以蓝湖「更新日志」页产品手写版本号为准，当前为 8.2.0 | 需求规格说明、测试版本标识 |
| 版本号来源 | Version Source | 版本号一律以蓝湖产品手写为准，不使用系统自动编号 | 版本管理约定 |
| Alembic 迁移版本 | Alembic Migration Revision | 数据库 schema 的变更版本标识，用于追踪和管理数据库变更历史 | 数据库迁移、升级 |

## 7. 蓝湖与设计集成

| 术语 | 英文 | 说明 | 适用场景 |
|------|------|------|---------|
| 蓝湖 | Lanhu | 第三方产品设计协作平台（lanhuapp.com），用于管理 Axure 原型和设计稿 | 需求分析、原型查看 |
| 原型设计 | Prototype Design / Axure | 在蓝湖中管理的产品交互原型，是需求提取的主要来源 | 需求提取、用例设计参考 |
| MCP | Model Context Protocol | AI 模型上下文协议，蓝湖 MCP 服务器通过该协议将设计稿内容暴露给 AI 编码助手 | AI 工具连接、上下文注入 |
| 蓝湖 MCP 服务器 | Lanhu MCP Server | 基于 FastMCP + Playwright Chromium 的本地服务，桥接蓝湖原型数据与 AI 编码助手（Claude Code、Cursor 等） | 需求分析、设计稿参数提取 |
| Cookie 认证 | Cookie Authentication | 蓝湖登录态的认证凭证，MCP 服务器需要有效 Cookie 才能访问蓝湖内容 | MCP 配置、Cookie 管理 |
| CDP | Chrome DevTools Protocol | Chrome/Edge 浏览器的远程调试协议，MCP 通过 CDP 端口 9222 与浏览器通信 | MCP 运行、浏览器自动化 |
| 版本缓存 | Version Cache | 基于蓝湖 versionId 的增量缓存机制，避免重复拉取未变更的设计内容 | 提取效率优化 |
| 需求文档提取 | Requirement Document Extraction | 自动从 Axure 原型下载和解析页面、资源和交互信息，生成结构化需求文档 | 需求管理、AI 用例生成 |

## 8. CI/CD 与部署

| 术语 | 英文 | 说明 | 适用场景 |
|------|------|------|---------|
| Jenkins Pipeline | Jenkins Pipeline | 主 CI/CD 流水线（Jenkinsfile），包含 11 个阶段：Checkout → Lint → Test（前后端）→ Build → Push → Deploy → Smoke → Quality Gate | 代码提交自动构建、部署 |
| GitHub Actions | GitHub Actions | GitHub 原生 CI/CD，包含两个定时工作流：api-regression（每日 API 回归）和 prod-smoke-test（每日生产冒烟） | 定时自动化测试 |
| 阶段 / Stage | Stage | CI/CD 流水线的执行阶段，每个阶段可包含多个步骤 | Pipeline 定义、执行监控 |
| Docker Compose | Docker Compose | 容器化部署编排工具，用于本地开发和测试环境的一键部署 | 环境部署、服务编排 |
| 环境 | Environment | 部署目标环境，分四级：localhost（本地）→ test（测试）→ staging（预发布）→ prod（生产） | 部署策略、测试分层 |
| 质量门禁 | Quality Gate | Pipeline 最后阶段的检查关卡，确认所有测试通过后才能继续 | CI/CD 流程 |

## 9. 技术架构术语

| 术语 | 英文 | 说明 | 适用场景 |
|------|------|------|---------|
| 前后端物理隔离 | Physical Frontend-Backend Separation | v2 的核心架构决策：frontend/ 和 backend/ 独立部署、独立 CI/CD，仅通过 REST API 通信 | 架构设计、部署策略 |
| SQLite WAL | SQLite Write-Ahead Logging | SQLite 的并发优化模式，支持并发读但写操作串行，是开发/测试环境的默认数据库模式 | 数据库配置、性能优化 |
| FastAPI | FastAPI | Python 异步 Web 框架，v2 后端的核心技术选型 | 后端开发 |
| shadcn/ui | shadcn/ui | 基于 Radix UI + Tailwind CSS 的 React 组件库，组件源码被复制到项目中而非通过 npm 安装 | 前端组件开发 |
| Zustand | Zustand | 轻量级 React 状态管理库，v2 前端的全局状态方案 | 前端状态管理 |
| Alembic | Alembic | SQLAlchemy 的数据库迁移工具，用于管理 schema 版本变更和数据库升级 | 数据库迁移 |
| APScheduler | Advanced Python Scheduler | Python 任务调度库，用于 v2 后端的定时任务执行 | 定时任务管理 |
| DeepSeek LLM | DeepSeek LLM | 驱动 AI 用例生成的大语言模型服务 | AI 用例生成 |
| RBAC | Role-Based Access Control | 基于角色的三级数据范围访问控制（global/project/self） | 权限系统 |

## 10. 环境与地址

| 术语 | 英文 | 说明 | 适用场景 |
|------|------|------|---------|
| localhost | Local Development | 本地开发环境，后端 `uvicorn` + 前端 `npm run dev` | 日常开发 |
| test | Test Environment | 测试环境，由 Jenkins 自动部署，main 分支 push 触发 | 集成测试、QA 验证 |
| staging | Staging Environment | 预发布环境，手动 docker compose 部署 | 发布前最终验证 |
| prod | Production Environment | 生产环境，手动触发部署，需 VPN 接入 | 线上服务 |
| VPN | Virtual Private Network | 生产环境访问所需的虚拟专用网络连接 | 生产环境接入 |

---

## 维护说明

- 本术语表为 **active** 状态文档，随项目演进持续更新
- 新增术语时按分类归入对应章节，必要时新增分类
- 术语定义变更需通知全团队并同步更新相关文档
- 过期术语标记删除线并在说明中注明废弃日期
