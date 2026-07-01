---
title: "ADR-0007: DeepSeek LLM 驱动 AI 用例生成"
owner: "tech-lead"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["adr", "ai", "llm", "deepseek", "test-case-generation"]
related: ["0001-use-python-fastapi-monostack.md", "0004-jwt-bcrypt-rbac-auth.md"]
---

# ADR-0007: 采用 DeepSeek LLM 驱动 AI 测试用例生成

## 状态

✅ 已采纳

## 日期

2026-03

## 背景

测试平台 v2 的核心差异化能力之一是「AI 原生」——从需求文档自动生成测试用例，降低人工编写成本。需要决定：

1. 使用哪个大语言模型（LLM）
2. 如何设计 AI 调用架构使其可替换
3. 如何保证生成用例的质量

## 决策

采用 **DeepSeek Chat API** 作为 LLM 后端，通过 OpenAI 兼容协议接入：

- **模型**：`deepseek-chat`（后续可升级为 `deepseek-v3` 等）
- **接入方式**：OpenAI 兼容 API（`/v1/chat/completions`），通过 `AI_API_BASE_URL` 配置
- **架构**：在 `ai_service.py` 中抽象 LLM 调用，上层不感知模型提供商
- **生成策略**：两段式生成（先生成用例骨架 → 再反向评审补全），提升质量
- **配置外置**：`AI_API_KEY` 通过环境变量注入，无硬编码

### AI 调用在系统中的角色

| 功能 | 调用方式 | 说明 |
|------|---------|------|
| 需求 → 用例生成 | `ai_service.generate_cases(requirement)` | 核心链路，两段式 |
| 反向评审 | `ai_service.review_cases(cases)` | 对 AI 生成结果自检 |
| 参数可调 | `AI_TEMPERATURE=0.3` | 低温度保证输出稳定性 |

## 后果

### 正面影响

- ✅ 降低用例编写成本 — 需求文档导入后自动生成初版用例
- ✅ 模型可替换 — OpenAI 兼容协议意味着可切换到任何兼容 API（Qwen、GLM 等）
- ✅ 低温度 + 两段式策略保证输出质量
- ✅ API Key 外置，不污染代码仓库

### 负面影响 / 权衡

- ⚠️ DeepSeek API 依赖外部网络 — 服务中断时 AI 功能不可用（降级为手动）
- ⚠️ 生成用例仍需人工审核 — AI 不是银弹，`review_status` 字段支持审核流程
- ⚠️ Token 消耗成本 — 长需求文档可能触发大量 token 消耗
- ⚠️ 模型输出格式不稳定 — 需要 `ai_service.py` 中的解析容错逻辑

## 弃选方案

### 方案 A: OpenAI GPT-4o

- 优点：模型能力强，生态成熟
- 缺点：成本高，国内网络访问不稳定
- 放弃原因：DeepSeek 性价比更优，中文能力相当

### 方案 B: 本地部署开源模型（如 Llama/Qwen）

- 优点：数据不出网，无 API 费用
- 缺点：需要 GPU 服务器，运维成本高，模型能力弱于云端
- 放弃原因：团队无 GPU 运维能力，ROI 低

### 方案 C: 纯规则/模板生成（无 AI）

- 优点：稳定可控，无外部依赖
- 缺点：只能生成骨架，无法理解需求语义
- 放弃原因：无法实现「AI 原生」产品定位

## 关联

- 实现：[app/services/ai_service.py](../../test-platform-v2/backend/app/services/ai_service.py)
- 配置：[app/core/config.py](../../test-platform-v2/backend/app/core/config.py) (AI 相关配置项)
- 需求模块：[app/api/v1/requirement.py](../../test-platform-v2/backend/app/api/v1/requirement.py)
- 用例审核：[ADR-0009 (待定)](../adr/) — 用例审核流
