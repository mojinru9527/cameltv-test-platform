# Batch 72 — Design Spec（最终优化与决策材料）

> **Design (🎨)** | Date: 2026-08-04

## 1. C71-1 实测方法

- 复用 batch-69 实测口径：R1-USER-REQ（147 FP）→ extract → confirm → generate（use_extraction）。
- 计时：`POST /requirements/{id}/generate` 耗时 vs batch-69 串行 682s。
- 记录 functional_cases 数（batch-69 = 331）与 warning。

## 2. C71-2 模板编辑

- 现有编辑对话框已含标题/描述 input；确认提交保存后 `onChanged` 刷新列表。
- 补充：行内编辑入口复用现有「编辑」按钮；无新组件。

## 3. C70-1 Playground 评估

- 核对：`playground.py` compile/execute 端点；batch-66 执行器登记（V1~V5）；C22-C2/C3 状态。
- 结论标准：runner 有真实「编译+执行+截图/Trace」证据 → 开放入口；否则维持 API-only。

## 4. C68-4 决策材料

- 选项 A：保持 `cameltv-test-platform1.vercel.app`（零成本，立即可用）。
- 选项 B：自定义域名 + Cloudflare（品牌化，需 DNS/证书/费用）。
- 选项 C：仅内网/测试域（现状，不公开）。
- 推荐：A 起步（演练已 200），B 在正式对外发布时评估。
