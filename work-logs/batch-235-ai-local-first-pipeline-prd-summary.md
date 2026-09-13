# Batch 235 — AI Local-First 基础（Phase 0 + Phase 1）
> **Product (🟦)** | Date: 2026-09-13 | Status: Approved

## 1. 问题陈述

AI 全链路当前已经统一到共享 `ai_client`，并能记录供应商 usage 与 prompt cache 命中 Token；但应用层仍缺少可控的精确响应缓存。相同项目、相同模型、相同 Prompt、相同输入重复调用时，双方只能依赖供应商的输入前缀缓存，输出仍会被重复生成，平台也无法回答“应用层节省了多少次模型调用”。

同时，Phase 0 没有一份可持续采集的基线：API 镜像中的 Node/DSH/Playwright/ffmpeg 依赖、本地 Embedding 状态、Provider 路由和缓存配置散落在代码与部署文件中，后续本地模型化和镜像拆分缺少统一观测口径。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 应用层精确缓存可观测率 | 无 | 命中/未命中/写入/绕过均可查询 | 本批 QA |
| 重复精确请求上游调用数 | 2 | 1（缓存开启且 namespace 明确时） | 单元测试 |
| 缓存跨项目隔离 | 无表 | 100% 按 project_id 隔离 | 单元测试 |
| 缓存安全默认 | N/A | 默认关闭，显式配置开启 | 配置与测试 |
| 缓存失效能力 | 无 | 可按项目/命名空间清理 | API 测试 |
| Phase 0 基线 | 分散 | 形成代码/部署/本地 Embedding 清单与采集结果 | 本批证据 |

## 3. 非目标（本次不做）

- 不接本地 LLM runtime，不引入 Ollama/llama.cpp/vLLM 依赖；属于 Phase 2。
- 不做 local-first/cloud-fallback/shadow routing；属于 Phase 2–3。
- 不拆 API/AI Worker/UI Runner 镜像；属于 Phase 4。
- 不改前端页面和交互。
- 不默认开启精确缓存，避免在模型/Prompt 版本治理未完成前复用陈旧输出。
- 不缓存 `finish_reason=length` 的截断响应。

## 4. 用户故事 + 验收标准

- As a 平台管理员, I want 查看精确缓存命中与条目统计, so that 我能判断重复生成带来的节省。
  验收：Given 已写入缓存 / When 调用统计接口 / Then 能看到命中次数、活跃条目、命名空间和 TTL。
- As a 测试工程师, I want 相同确定性 AI 请求复用已验证结果, so that 重复分析不再重复消耗模型。
  验收：Given 精确缓存开启且 namespace 相同 / When 两次提交完全相同的 system prompt、用户输入、模型与参数 / Then 上游只调用一次，第二次返回 `cache_status=hit`。
- As a 平台管理员, I want 按命名空间失效缓存, so that Prompt/Schema 升级后不会复用旧结果。
  验收：Given 某 namespace 有缓存 / When 清理该 namespace / Then 后续请求重新调用上游。
- As a 安全负责人, I want 缓存默认关闭并严格按项目隔离, so that 不会跨租户泄露 AI 输出。
  验收：Given 项目 A 写入缓存 / When 项目 B 使用相同输入 / Then 项目 B 不命中项目 A 的缓存。

## 5. 技术考量

- 复用现有 `ai_client.chat_completions_full` 作为唯一传输层，增加 opt-in 精确缓存，不新建第二套模型客户端。
- 缓存键必须包含 project_id、provider_id、model、namespace、system prompt hash、user input hash、json_mode、max_tokens、temperature。
- 缓存表保存结构化响应摘要与 usage，不保存 API Key、Secret、Header 或链式思考。
- 缓存读写失败不得阻断主 AI 调用。
- Phase 0 基线作为后续 Phase 2–4 的对照，不把“计划”冒充收益。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| Phase 0 | 研发/运维 | 基线清单与采集脚本可用 |
| Phase 1 | 平台管理员 | 缓存默认关闭、开启后重复调用可复用、统计/清理可用 |
| Phase 2–4 | 后续批次 | 本批只交付前置接口与证据，不宣称完成 |

## 7. 技能使用

`cameltv-agent-team` → 本批六部门工件与看板；`cameltv-bug-guard` → 迁移、路由、缓存与异步边界核查。
