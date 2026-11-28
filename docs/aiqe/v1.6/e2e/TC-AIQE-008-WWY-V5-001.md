# WWY-V5-001 缺陷详情（TC-AIQE-008 原始缺陷，当前 FAIL / OPEN）

> **状态：FAIL / OPEN（2026-11-27 复测仍失败，2026-11-28 复核未关闭）。**
> 该缺陷只能由它自己的正式 Defect Regression Run（固定 SHA + Mandatory Scope +
> Comparison Snapshot）关闭；`WWY-V5-006`（记住账号）是另一条用例，不得覆盖、替换或
> 关闭本缺陷（手册 §9.2 / FIX-008）。

## 基本信息
| 项 | 内容 |
|---|---|
| 缺陷编号 | `WWY-V5-001` |
| 对应用例 | `TC-ADM-06-N`（角色与菜单可见性：异常/禁止场景被正确拦截） |
| 模块 | 管理后台 / 门店-门店设备 |
| 严重程度 | 严重 |
| 账号 Secret | 运营账号：`FUTUREWAYU_TEST_USERNAME`（值由 CI Secret / Vault 注入，不写入仓库） |
| 日期 | 2026-11-27 |
| 当前状态 | **FAIL / OPEN** |

## 请求（运营账号）
```http
POST https://xinyuwadao.com/prod-api/system/device
Authorization: Bearer <运营账号 Token：运行时由 Secret 注入，不复述>
clientid: e5cd7e4891bf95d1d19206ce24a7b32e
Content-Type: application/json
Origin: https://xinyuwadao.com
Referer: https://xinyuwadao.com/

{}
```

## 实际结果
```http
HTTP/1.1 200
{"code":500,"msg":"设备类型不能为空","data":null}
```
- 鉴权已通过，请求进入参数校验；
- 未返回 403，说明运营没有被“新增设备”权限拦截；
- 空体校验失败，因此本次没有落库。

## 正常预期
1. 运营在“门店-门店设备”只看列表，**页面无「新增设备 / 编辑 / 删除」入口**；
2. 直调 `POST /prod-api/system/device`、`PUT /prod-api/system/device`、`DELETE /prod-api/system/device/{ids}` 均应返回 `code=403`（无权限），不得进入参数校验；
3. 不产生设备数据；`GET /system/device/list` 仍允许只读。

## 合法请求体（来自接口用例）
```json
{"deviceType": "API_TEST", "id": 1, "status": 1}
```
> 本次未用合法体执行，避免在生产创建设备；从空体返回 500 已证明权限拦截缺失。

## 影响
运营账号具备设备新增/删除的调用能力（只差通过参数校验），可越权创建设备或删除门店设备，属于权限越权。

## 建议修复
- 在 `POST/PUT/DELETE /system/device` 控制器入口增加 `@PreAuthorize("@ss.hasPermi('system:device:add|edit|remove')")` 或等价角色校验；
- 权限校验必须发生在 Bean Validation 之前，确保无权限直接 403；
- 前端按 `system:device:add` 等权限隐藏按钮；
- 增加回归：运营空体/合法体均 403，DB 设备数不变；管理员仍可新增。

## 关闭条件（FIX-008）

本缺陷当前没有正式回归证据，因此保持 FAIL / OPEN：

1. 用 `WWY-V5-001` 的原缺陷记录发起回归，**不创建替代缺陷**；
2. 提交固定的 `fixed_commit_sha`（40 位），服务端校验该 SHA 可读取；
3. 冻结 Mandatory Scope Snapshot，并确认其中每条 case 都有执行结果；
4. 走正式 Worker/Driver，产出 Assertion 与 Artifact；
5. 生成 Comparison Snapshot，证明修复前失败、修复后通过；
6. 带幂等键调用正式 Defect Regression API：

```powershell
python scripts/aiqe/per_tc/defect_regression_runner.py `
  --api-base <平台 API 基址> --project-id <项目 ID> --defect-id <WWY-V5-001 的缺陷主键> `
  --fixed-commit-sha <40 位修复提交> --scope-snapshot <scope-json> `
  --idempotency-key <唯一幂等键> --case-results <mandatory case 结果> `
  --output <回归结果 JSON>
```

缺任一参数、API 不可达、缺 mandatory case 结果或 Comparison Snapshot 时，Runner 输出
`BLOCKED` / `NOT_PROVEN` 并非零退出，不得写成 PASS。

## 2026-11-27 复测记录

- 复测：**仍失败**，`POST /prod-api/system/device` 空体返回 HTTP 200 + `code=500`；
- 未执行正式 Defect Regression Run（无固定 SHA、无 Mandatory Scope Snapshot、无 Comparison Snapshot）；
- 证据：`docs/aiqe/v1.6/e2e/TC-AIQE-008-Retest-20261127.md`。

## 与 `WWY-V5-006` 的关系

- `WWY-V5-006`（记住账号）是另一条已修复用例，只能单独记录、单独判定；
- 即使 `WWY-V5-006` 的点击复核通过，也不改变本缺陷的 FAIL / OPEN 状态；
- 把 `WWY-V5-006` 当作 `WWY-V5-001` 的替代证据属于手册 §0.1 明令禁止的“换用另一条已通过用例”。

## 与 V5.0 需求对比（关键冲突）

V5.0（2026-11-09）ADM-06 角色定义：

- 运营：款/组件/系列只读；**门店的店铺、门店设备可新增和修改**；导购业绩查看/导出；订单只读（不能备货/退款）；营销全部；社区全部；设置仅身份卡。
- 审核：款/组件/系列只读，可审核/上下架，订单可退款，店铺/活动优惠只读。
- 门店店员：只有门店-订单、门店-设备，且仅自己负责的自提点。
- 管理员/开发：设备全部操作。

权威问题表（2026-11-17，甲方 11-16 反馈）却要求：运营对门店设备**只读**、无新增入口、直调 POST/DELETE 返回 403。

结论：**两者冲突**。
- 若 V5.0 仍是需求基线：WWY-V5-001 的 403 预期不成立；运营 POST 设备返回 500 只是校验错误码问题（应 400，而非越权）。
- 若 11-16 反馈已正式变更 ADM-06：需先更新需求/变更记录，再按 403 修复。
- DELETE 在 V5 未授权给运营；当前对不存在 ID 返回 500，提示删除接口可能也缺少权限前置。

## 设备删除权限复测（2026-11-27）

- 店员账号（Secret `FUTUREWAYU_TEST_CLERK_USERNAME`）：DELETE /prod-api/system/device/0 -> code=403（符合矩阵）
- 运营账号（Secret `FUTUREWAYU_TEST_USERNAME`）：同一请求 -> code=500（未按 403 拦截）
- 运营 POST/PUT 设备在 V5 允许；空体 500 属校验错误码，不是越权。
- 结论：店员删除已正确 403；运营删除仍需按 403 修复。
