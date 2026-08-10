# Batch 135 — 蓝湖登录入口补到创建表单 PRD-lite
> **Product (🟦)** | Date: 2026-08-10 | Status: Approved

mode: light
豁免理由: 仅修复"登录入口只在失败详情页出现"的展示可达性，复用 Batch 133 的 LanhuReloginDialog 与已有 API，无新接口/新配置/新依赖。

## 1. 问题陈述
用户填写蓝湖需求地址（需求证据采集 / 蓝湖证据包创建）时找不到登录入口——Batch 133 的"蓝湖登录/更新Cookie"只在任务失败（会话失效/418）后的详情页出现，创建表单没有入口，体验断裂。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 创建表单可达性 | 无入口 | 证据创建表单（LanhuEvidenceDialog）与需求证据面板（EvidenceTaskPanel）均有"蓝湖登录/更新Cookie"入口 | 本批验收 |
| 回归 | - | 前端 443 全量、typecheck/build 无新增失败 | 本批验收 |

## 3. 非目标与 C 条件
- 不新增后端接口（复用 Batch 133 的 /lanhu-evidence/cookie 与 /login）。
- 不改任务失败详情页已有入口；C 条件维持（C134-1 已关闭；无新增）。

## 4. 用户故事与验收标准
- As 测试平台用户, I want 在填写蓝湖地址时就能看到登录/更新 Cookie 入口, so that 会话过期时可先登录再采集。
  - Given 打开证据创建表单或需求证据面板 / When 查看 / Then 可见"蓝湖登录/更新Cookie"按钮，点击弹出粘贴 Cookie / 账号密码登录对话框（Batch 133 已具备）。

## 5. 技术考量
- 复用 LanhuReloginDialog（pages/lanhu-evidence/components），在 LanhuEvidenceDialog 与 EvidenceTaskPanel 挂载。
- 纯前端展示可达性改动，无数据/接口变化。
