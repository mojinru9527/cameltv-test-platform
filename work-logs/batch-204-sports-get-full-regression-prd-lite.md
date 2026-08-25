# Batch 204 — PRD-lite：体育接口服务只读 GET 全量回归

> **Product (🟦)** | Date: 2026-08-25 | Status: 执行完成（回归矩阵 + 1 项修复）| Executor: DeepSeek_Harness | 轻量批次

```markdown
mode: light
豁免理由: 本批为「验收/回归」类批次：对现有体育接口资产与接口用例做只读 GET 全量真实执行回归，无新行为、无新接口、无新配置、无新依赖、无 schema/迁移变更（含 1 项存量缺陷修复，属回归发现修复），符合 pipeline-modes.md 轻量批次判定。
非目标: 不做写操作（POST/PUT/DELETE/PATCH）回归；不做真实参数矩阵补全（4xx 类接口的逐参数正例补测另立批）；不归档/删除 camel-service-final、camel-test-confirm 资产（仅登记 C204-1 待确认）；不做慢接口超时调优（登记 C204-2）。
```

## 1. 问题陈述

camel-service 恢复（C203-2 关闭）后，用户要求对「现有的体育所有接口服务 + 下面接口用例」做**只读 GET 全量回归**，以得到平台引擎在真实 Test5 上的完整健康矩阵，并据此发现平台缺陷与资产/环境事实。

## 2. 范围与口径

| 维度 | 口径 |
|------|------|
| 对象 | 8 个体育服务全部 GET 接口资产 575 条（黑名单排除 52 条明确变更型 GET：`/clear`、`refresh*`、`sync*`、`reHandle*`、`close*`、`init_basic_info` 等）→ 实跑 **523** 条 |
| 对象 | 全部 GET 接口用例：库内 621 条，其中 605 条 `is_deleted=1`（软删除迁移数据，平台已不执行）→ 实际可执行 **10** 条（另 6 条为本会话 E2E 残留已清理） |
| 执行路径 | 平台引擎（`/apitest/api-execute` 与 `/test-cases/{id}/execute`），环境=API测试环境（Test5 网关），VPN 已连 |
| 分类 | PASS（2xx+业务码 200）/ PASS_UNVERIFIED（2xx 非 JSON 体）/ BUSINESS_ERR（2xx+业务码≠200，多为缺真实参数/前置）/ NEED_PARAMS（HTTP 4xx）/ NETWORK（超时/不可达）/ SERVER_ERR（5xx） |

## 3. 成功指标

- 全部只读 GET 资产 523 条执行完成并分类落矩阵（证据 JSON）
- 全部可执行 GET 用例执行完成并分类
- 平台缺陷：发现即修（本批已修 1 项），外部事实登记 C 条件
- 硬门禁：受影响后端 pytest + ruff F821 全绿；CI 全绿后合入

## 4. 执行结果摘要（详见 QA 报告）

- 端点 523：PASS 75 / PASS_UNVERIFIED 5 / BUSINESS_ERR 193 / NEED_PARAMS 232 / NETWORK 18 / SERVER_ERR 0
  - camel-service-final（115）+ camel-test-confirm（117）在 Test5 网关**无路由全 404** → C204-1
  - 18 条慢接口（list_competition/init_* 等）25s+ 超时 → C204-2
- 用例 10：修复前 0 可执行通过；修复后 `getById?id=1` 200+status=200 真实通过；5 条绑定 camel-test-confirm 的 article/match 用例 404（同 C204-1）；3 条负向用例断言口径（HTTP 4xx vs 网关信封 status=400）失配 → C204-3

## 5. 交付物

- 回归矩阵证据 JSON（QA 报告附件引用）
- 修复：`_case_execution_url` 经 `api_spec_ref` 回退解析服务前缀（存量用例 404 修复）+ 3 例单测
- 三件套（本 PRD-lite + QA + Leader）+ 看板 + C204-1/2/3
