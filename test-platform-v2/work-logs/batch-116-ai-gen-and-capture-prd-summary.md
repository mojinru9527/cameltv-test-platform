# Batch 116 — PRD（AI 生成链路加固 + B10 平台采集集成）

> **Product (🟦)** | Date: 2026-08-07 | Status: Review

```markdown
mode: full
豁免理由: 无（含后端异步任务/API + 前端入口 + 采集集成，走完整六部门流水线）。
非目标:
- iOS 真机采集（CP-C2 外部）
- Test5 契约（C111-4 外部）
- internal-network runner（C111-1 外部）
- staging 全栈四项验证（C27-C1~C4 继续 Deferred）
- api.d.ts 全量重生成（C104-3/C105-3 继续 P2 跟踪）
```

## 1. 问题陈述

处理剩余可落地遗留（3 项）：

1. **C102-1（P1）**：需求 AI 提取/生成同步请求超时（>300s 网关 502，大文档失败）。
2. **C103-6（P2）**：AI 生成块级截断自动补全（截断块补生成 + 覆盖缺口报告）。
3. **C115-3（P3）**：B10 页面 XHR 采集仅脚本，缺平台 API/UI 集成（C103-5 平台工具）。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| C102-1 | 同步 300s 502 | 生成/提取走后台任务 + 状态轮询；大文档不 502 |
| C103-6 | 截断块补全不完整 | 截断块自动补生成 + 覆盖缺口报告（每批次） |
| C115-3 | 仅脚本采集 | 平台采集 API（页面列表→样本 JSON 落库）+ 最小前端入口 |

## 3. 用户故事 + 验收标准

- As a **需求承接人**, I want 大文档 AI 提取/生成不因网关超时而失败。
  - Given 大文档提交，When 生成，Then 后台任务运行 + 前端轮询进度，无 502。
- As a **QA**, I want 截断块自动补全 + 缺口报告，so that 用例覆盖无遗漏。
  - Given 截断发生，When 补生成，Then 缺口清单与补全结果落盘。
- As a **承接负责人**, I want 平台内发起页面 XHR 采集，so that 用例基线随时可采。
  - Given 页面列表，When 创建采集任务，Then 样本 JSON 落库并可见。

## 4. 技术考量

- **C102-1**：requirement 生成/提取改造为后台任务（复用 BackgroundTasks/线程 + 任务状态表或内存状态 + GET 状态轮询）；前端生成按钮轮询。
- **C103-6**：ai_service 已具备 chunk retry/truncated 检测；补齐「截断块补生成」（retry 上限内重试截断块）+「覆盖缺口报告」（生成结果 vs 提取功能点覆盖矩阵 JSON）。
- **C115-3**：backend 增加 `POST /uitest/capture`（页面列表 → 后台 playwright 采集 → 样本 JSON 存 evidence/DB）+ `GET /uitest/capture/{id}` 结果；最小前端入口（可选）。
- **技能**：`cameltv-bug-guard`（后台任务/API 避坑）、`playwright-cli`。

## 5. 范围

**纳入**：C102-1 异步化（后端+前端轮询）、C103-6 补全+缺口报告、C115-3 平台采集 API/UI。

## 6. 上线计划

| 阶段 | 内容 | 出口标准 |
|------|------|---------|
| S1 | 工件 + C102-1 异步生成 | 大文档不 502；状态轮询可用 |
| S2 | C103-6 截断补全 + 缺口报告 | 单测 + 证据 |
| S3 | C115-3 平台采集 API | 采集任务 + 样本落库证据 |
| S4 | QA/Leader + 一次总确认 | 工件齐全 + 审计 0 硬错 |

## 7. 技能使用

- `cameltv-agent-team` → 六部门流水线
- `cameltv-bug-guard` → 后台任务/API 避坑
- `playwright-cli` → 采集验证