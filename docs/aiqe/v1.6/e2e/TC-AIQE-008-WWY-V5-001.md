# WWY-V5-001 缺陷详情（TC-AIQE-008 复测对象）

## 基本信息
| 项 | 内容 |
|---|---|
| 缺陷编号 | `WWY-V5-001` |
| 对应用例 | `TC-ADM-06-N`（角色与菜单可见性：异常/禁止场景被正确拦截） |
| 模块 | 管理后台 / 门店-门店设备 |
| 严重程度 | 严重 |
| 账号 | `tester-operator`（运营，密码 123456） |
| 日期 | 2026-11-27 |

## 请求（运营账号）
```http
POST https://xinyuwadao.com/prod-api/system/device
Authorization: Bearer <tester-operator token>
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

## 当前状态
- 2026-11-27 复测：**仍失败**，不能标记 TC-008 PASS。
- 证据：`docs/aiqe/v1.6/e2e/TC-AIQE-008-Retest-20261127.md`
