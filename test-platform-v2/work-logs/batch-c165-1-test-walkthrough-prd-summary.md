# Batch c165-1-test-walkthrough — PRD Summary（PRD-lite）
> **Product (🟦)** | Date: 2026-08-13 | Status: Approved
> **mode: light**
> **豁免理由**: 本批为 Batch 165 已合入代码的 test 环境部署后验收 + 证据回写，不引入新行为/新接口/新配置/新依赖；按 SKILL.md「轻量批次」执行。
> **非目标**: 不做 C165-2 四入口收敛；不做 Playground 勾选用例（完整批次 batch-166）；不改任何前后端业务代码。

## 1. 问题陈述
Batch 165 Leader 设定 C165-1（P2）：test 环境部署后，需按 6 项清单做走查验收并截图留证：
①菜单/命令面板/访客目录无专项测试、性能监控；②知识中心 12 tab 在 1024/1280 可切换且不裁切；③接口资产 899 条时第 1 页 20 行；④接口用例可编辑参数/断言；⑤UI 自动化「用例/脚本」页签可用；⑥测试计划环境选择入口（含 API/UI 自动化用例时显示）+ 纯人工计划执行提示。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| C165-1 六项走查 | 未验收 | 6/6 PASS | 2026-08-13 test 环境 |
| 证据落盘 | 无 | 截图 + 结果 JSON 入 work-logs/evidence | 合入前 |

## 3. 非目标（本次不做）
- 不关闭 C165-2（四入口收敛，另起批次）。
- 不修改平台源码；本批只写验收工件与 C-CONDITIONS 状态。

## 4. 用户故事 + 验收标准
- As 测试负责人, I want C165-1 六项部署后走查完成, so that Batch 165 的隐藏/分页/编辑/环境选择修复被确认在 test 环境生效。
- 验收：Given test 环境已部署 Batch 165 / When 按 6 项清单逐项走查 / Then 每项有截图或 DOM 结果佐证且结论为 PASS。

## 5. 技术考量
- 生产既有 899 接口资产的 admin 项目无可用凭据；采用 test 环境注册测试账号自建项目，并导入 test5-contracts 7 份真实 OpenAPI 契约（account-service 162、api-gateway-service 17、camel-mimo 34、camel-service 197、live-platform 45、payment-service 26、studio-service 418，合计 899 端点），等价复现第 3 项分页场景。
- 前端走查经 Vercel test 入口 `https://cameltv-test-platform1.vercel.app`，后端 API 为 Railway `https://test-platform.up.railway.app`。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本地工件提交 | Agent Team | QA/Leader 通过 + C-CONDITIONS 关闭 C165-1 |
| 合入 main | 全队 | required checks 全绿 |

## 7. 技能使用
- cameltv-agent-team → 轻量批次三件套（PRD-lite + QA + Leader）+ 看板。
- playwright-skill → test 环境浏览器走查、截图、DOM 结果 JSON。
- vision → 关键截图人工复核（侧边栏/接口资产/知识 tab）。
