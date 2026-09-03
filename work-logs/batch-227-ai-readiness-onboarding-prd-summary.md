---
title: "Batch 227 AI 全链路就绪向导 PRD"
owner: "qa-team"
last_reviewed: "2026-09-03"
status: "approved"
expires: "2027-03-03"
tags: ["batch-227", "onboarding", "readiness", "ai-e2e"]
---

# Batch 227 AI 全链路就绪向导 — PRD

> Product | Date: 2026-09-03 | Mode: full | Executor: Codex

## 1. 问题陈述

体育 16.0.0 最终验收证明平台不会伪造成功，但真实外部条件分散在新业务接入、AI 配置、环境管理和 Runtime 管理四处。普通测试人员不知道自己要填什么，也会误以为每次运行前需要手动启动 Temporal/Worker。当前接入记录还把 `service_key` 当成版本号，需求正文没有进入 AI 方案上下文，容易再次生成不可执行方案。

## 2. 成功指标

| 指标 | 当前 | 本批目标 |
|------|------|----------|
| 用户输入 | 4 个无标签字段，版本/需求缺失 | 6 个有标签字段，说明用途和示例 |
| 平台条件 | 分散在 3 个管理页 | 一个只读接口、一个页面集中展示 |
| 运行时认知 | 用户可能以为需手动启动 | 明示平台常驻管理，普通用户不操作 |
| 需求上下文 | 接入任务不绑定需求正文 | 需求正文绑定 VersionTask 并进入 AI 上下文 |
| 假就绪 | “已配置”可能被当成可用 | 未验证/失败 AI、未启用 Temporal、离线 Worker 均如实显示 |

## 3. 用户需要填写

1. 业务名称：面向人的中文名称。
2. 服务标识：网关或 OpenAPI 中稳定的 service key。
3. 本次版本：例如 `16.0.0`，独立于服务标识。
4. 需求内容：本版本要验收的完整正文或摘要。
5. OpenAPI 地址：平台后端可访问的 JSON/YAML 地址。
6. 被测服务地址：平台后端可直接访问的 Base URL。

鉴权密钥不允许粘贴进需求正文或普通文本框。需要登录态、内网 Runner 或专用凭据时，由管理员先在现有“环境管理/Runtime”中配置；本批只给出明确入口和阻塞说明，不宣称同步 B15 基线路径已经支持内网 Runner。

## 4. 平台自动管理

- AI 提供方：读取项目默认配置及最近一次真实连通性结果；`unknown/error` 不显示为就绪。
- Temporal：读取部署开关；它是长驻基础设施，不随某次任务临时启动。
- Runtime Worker：读取最近心跳并剔除失联节点；它由管理员/部署系统常驻维护。
- B15 同步基线不依赖 Temporal；AITDE 耐久执行需要 Temporal + 在线 Worker。页面必须把两种口径分开。

## 5. 用户故事与验收

- As a 测试人员, I want 在一个页面知道必须填写什么, so that 我不用理解平台内部架构。
  - Given 首次进入接入页 / When 查看表单 / Then 六项均有永久标签、用途说明和示例，缺项时按钮不可执行。
- As a 测试负责人, I want 看到真实就绪状态, so that 我不会把“配置过”误判为“可运行”。
  - Given AI 未验证或 Worker 离线 / When 页面加载 / Then 显示阻塞原因和对应处理入口，不显示绿色就绪。
- As a 平台管理员, I want 基础设施由部署管理, so that 普通任务不会擅自启动系统服务。
  - Given Temporal/Worker 未就绪 / When 普通用户查看 / Then 页面只提示管理员处理，不提供启动/停止按钮。
- As a 体育业务测试人员, I want 版本和需求进入任务, so that 16.0.0 AI 方案使用真实需求上下文。
  - Given 填写版本与需求并完成 OpenAPI 导入 / When 创建 VersionTask / Then task.version=`16.0.0` 且 requirement_doc_id 指向该需求正文。

## 6. 非目标与 C 条件

- 不在 Web 请求中启动 Docker、Temporal Server 或 Worker 进程。
- 不新增密钥明文存储，不把鉴权值写入 onboarding 表。
- 不在本批改造 VersionTask 的同步 HTTP 执行为内网 Runner 异步执行。
- 纳入 C225-1 的后续改进：直接呈现 Batch 226 暴露的 AI/OpenAPI/Runtime 解除条件；本批不以 UI 改造宣称体育 16.0.0 已放行。
- C-CONDITIONS.md 其余 Open 条件属于体育业务参数、旧文档归档、设备/生产闭包等独立专项，与本批就绪向导无直接依赖，明确豁免。

## 7. 小白走查

不阅读文档的 tester 应能在 3 分钟内回答：我需要填哪 6 项、哪些由平台自动管理、为什么现在不能开始、应该找谁处理。页面不得出现要求普通用户执行 shell、Docker 或 Temporal 命令的文案。
