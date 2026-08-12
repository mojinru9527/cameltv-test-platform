# Batch 160 — 需求「功能拆分」404 热修（PRD-lite）

> **Product (🟦)** | Date: 2026-08-12 | Status: Approved | Mode: light

mode: light
豁免理由: 纯前端契约 Bug 修复，无后端/接口/依赖变更，紧急热修。
非目标: 不改后端 404 语义（本仓约定 envelope code=404 + HTTP 200）。

## 1. 问题陈述
提取成功的需求文档点击「功能拆分」报 `{"code":404,"msg":"功能拆分结果","data":null}`，无法进入拆分。
- 根因：后端查不到拆分结果返回 **HTTP 200 + envelope code=404**（本仓约定），但前端 `getOrCreateExtraction` 用 `error.response?.status === 404` 判断；且 axios 拦截器把业务错误转成普通 `Error(message)` 丢失 code → 前端永远走不到“创建拆分”回退，直接报错。

## 2. 修复
- `client.ts`：业务错误（code!=0）的 Error 对象附加 `code` 字段。
- `requirement.ts` `getOrCreateExtraction`：按 `error.code ?? error.response?.data?.code === 404` 回退调用 `POST /extract` 创建拆分。

## 3. 验收标准
- GET /extraction 返回 envelope code=404 时，自动创建拆分（POST /extract）并打开审核弹窗。
- 其它错误（403/500/网络）不创建、原样报错。
- 回归测试：拦截器 code 附加 + getOrCreateExtraction 三种分支。

## 4. 技能使用
- cameltv-bug-guard（envelope 码 vs HTTP 码：查不到 → R(code=404)+HTTP 200）
