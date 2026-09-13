# Batch 236 — 本地 AI Runtime 与 Shadow Mode（Phase 2）
> **Product (🟦)** | Date: 2026-09-13 | Status: Approved

## 1. 问题陈述

Batch 235 已落地精确缓存和 Phase 0 基线，但还没有独立本地推理运行时，也没有机制验证本地模型与当前云端模型在同一批真实 Prompt 上的质量差异。直接切换 local-first 会让未经验证的本地模型影响用户结果。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 本地 runtime 可配置 | 无 | 独立 OpenAI-compatible endpoint/model/key 配置 | 本批 QA |
| Shadow 默认安全 | 无 | 默认关闭；主链路返回值不依赖本地结果 | 单元测试 |
| 对比可追溯 | 无 | 记录模型、输入 hash、JSON 合法性、延迟、usage、输出 hash | API 测试 |
| 主链路可用性 | 云端成功 | 本地 shadow 失败不影响主结果 | 单元测试 |
| 样本控制 | 无 | 支持 0–1 采样率 | 单元测试 |

## 3. 非目标

- 不把模型权重打进 API 镜像。
- 不切换主链路到本地模型；local-first routing 属于 Phase 3。
- 不做前端可视化；Phase 2 先提供 API 与持久化证据。
- 不关闭 C235-1；本批实现 C235-1 的 runtime 与 Shadow 部分。
- 不引入 CUDA/Torch 依赖；本地模型由外部 runtime 提供 OpenAI-compatible API。

## 4. 用户故事与验收标准

- As a AI 平台管理员, I want 配置独立本地 runtime, so that 本地模型不依赖项目默认 Provider。
  验收：Given 本地 runtime 开启 / When 读取 runtime status / Then 返回 base URL、model、enabled，且不返回 Key。
- As a AI 质量负责人, I want 云端结果和本地结果后台对比, so that 切换前有真实质量证据。
  验收：Given Shadow 开启 / When 主模型成功 / Then 后台调用本地模型并写入对比记录；主响应不变。
- As a 运维人员, I want 本地失败不影响主链路, so that Shadow 探索不会造成线上故障。
  验收：Given 本地 endpoint 超时 / When 主模型成功 / Then 用户仍收到云端结果，shadow 记录为 failed。
- As a 安全负责人, I want shadow 默认关闭并按比例采样, so that 不产生不可控的本地成本和数据暴露。
  验收：Given 采样率 0 / When Runtime 开启 / Then 不提交 shadow 任务。

## 5. 技术考量

- 复用 Batch 235 的 `ai_client` 传输和 `AiOperation` usage 口径。
- 本地 runtime 使用独立配置和独立 `AiProvider` 风格的配置对象。
- Shadow 使用后台线程与独立 DB Session；不持有请求 Session。
- 新增 `ai_shadow_run` 表，保存结构化对比，不保存 API Key。
- 本地模型权重、Ollama/llama.cpp/vLLM 进程不在应用镜像内。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| Phase 2 | 管理员/QA | Shadow 默认关闭、开启后记录对比、主链不回归 |
| Phase 3 | 后续批次 | local-first routing、云端兜底、UI 可视化 |

## 7. 技能使用

`cameltv-agent-team` → 六部门工件；`cameltv-bug-guard` → 线程、Session、迁移与 AI 调用边界。
