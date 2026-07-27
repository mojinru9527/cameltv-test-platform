# 体育测试5六服务增改查测试用例

更新时间：2026-07-15

## 1. 范围与执行约束

- 测试入口：CamelTv 测试平台 Web 前端「接口测试」。
- 环境：`CamelTv 体育测试5环境`，基础地址 `http://192.168.50.170`。
- 请求头：`Host: ${TEST5_GATEWAY_HOST}`；需要用户鉴权的接口增加 `accesstoken: ${TEST5_ACCESS_TOKEN}`。
- `TEST5_ACCESS_TOKEN` 在平台环境变量中加密保存，文档、截图和报告不得出现明文。
- 六份 OpenAPI 已导入 892 个接口资产并生成 1323 条候选 API 用例：camel 190/312、live 45/85、payment 26/36、studio 418/595、konfi 51/65、account 162/230（接口数/用例数）。候选用例不等于执行授权，必须先按安全范围筛选。
- 本轮只执行新增、修改、查询。禁止执行 DELETE、支付扣款、退款、转账、封禁、发布、推流和批量数据变更。
- 新增和修改只选择可唯一命名、影响面低的 Live APP 配置；Payment 仅做只读查询。

## 2. 已执行用例

| 用例编号 | 接口 | 用例标题 | 重要程度 | 请求方式/URL | 请求参数（输入） | 预期结果（状态码+返回校验） | 执行结果 | 实际结果 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T5-LIVE-001 | APP 查询 | 查询不存在的名称 | P1 | GET `/live-platform/app/getByName` | `name=codex-dev-...-missing` | HTTP 200；业务状态 200；`data` 为空 | 通过 | HTTP 200、业务 200、空数据 |
| T5-LIVE-002 | APP 新增 | 新增唯一名称的测试 APP | P0 | POST `/live-platform/app/add` | 唯一 `name`；随机 `secretKey` | HTTP 200；业务状态 200；`data=true` | 通过 | 新增成功；密钥未写入文档或截图 |
| T5-LIVE-003 | APP 查询 | 查询并取得新增记录 ID | P0 | GET `/live-platform/app/getByName` | 新增步骤的 `name` | HTTP 200；业务状态 200；返回 `id` 和相同名称 | 通过 | 返回 ID `34779` |
| T5-LIVE-004 | APP 修改 | 修改名称和密钥 | P0 | POST `/live-platform/app/update` | `id=34779`；名称增加 `-updated`；新随机密钥 | HTTP 200；业务状态 200；`data=true` | 通过 | 修改成功 |
| T5-LIVE-005 | APP 查询 | 复查修改结果 | P0 | GET `/live-platform/app/getByName` | `name=codex-dev-20260715-874390-updated` | HTTP 200；ID 不变；名称为修改后值 | 通过 | ID、名称均符合预期 |
| T5-CAMEL-001 | 热门搜索 | 查询热门搜索配置 | P0 | POST `/camel-service/ee/search/hot` | 无业务写入参数 | HTTP 200；业务状态 200；返回数据字段 | 通过 | HTTP 200、业务 200、有数据 |
| T5-PAY-001 | 商品查询 | 按 USD 查询支付商品 | P0 | GET `/payment-service/ee/client/web/query` | `currency=USD` | HTTP 200；业务状态 200；返回数据字段；无扣款 | 通过 | HTTP 200、业务 200、有数据 |
| T5-STUDIO-001 | 剪辑分组 | 分页查询剪辑分组 | P0 | GET `/studio-service/clip/group/list` | `page=1&size=5` | HTTP 200；`code=0`；`success=true` | 通过 | HTTP 200、code 0、success=true |
| T5-ACCOUNT-001 | 商品列表 | 分页查询账号服务商品 | P0 | GET `/account-service/ee/goods/list` | `page=1&size=5`；有效 Web token | HTTP 200；业务状态 200；返回数据字段 | 通过 | HTTP 200、业务 200、有数据 |
| T5-ACCOUNT-002 | 用户信息 | 查询当前登录用户信息 | P0 | GET `/account-service/ee/client/userInfo` | `userId=${TEST5_USER_ID}`；有效 Web token | HTTP 200；业务状态 200；返回当前用户数据 | 通过 | HTTP 200、用户数据可读 |
| T5-KONFI-001 | 公共配置 | 查询直播关注配置 | P0 | POST `/konfi-service/web/getDataById` | JSON 字符串 `"sport_live_follow_conf"` | HTTP 200；业务状态 200；返回配置数据 | 失败 | 体育站点和测试平台均为 HTTP 200、业务 400：`Something goes wrong` |
| T5-KONFI-002 | 后台表单 | 普通 Web token 访问后台表单模板 | P1 | POST `/konfi-service/form/getFormTemList` | 普通体育 Web `accesstoken` | 应拒绝越权访问并返回明确鉴权错误 | 通过 | HTTP 200、业务 103：`token无效`；确认后台权限隔离生效 |

测试记录 `34779 / codex-dev-20260715-874390-updated` 按“禁止删除”约束保留在测试5环境，便于后续回归复用。

## 3. 待执行的通用负向与边界用例

| 用例编号 | 接口 | 用例标题 | 重要程度 | 请求方式/URL | 请求参数（输入） | 预期结果（状态码+返回校验） | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T5-AUTH-001 | 任一鉴权查询 | 缺少 accesstoken | P0 | 使用项目实际查询接口 | 不发送 `accesstoken` | 返回未登录/未授权；不得返回用户私有数据 | 鉴权负向 |
| T5-AUTH-002 | 任一鉴权查询 | 无效 accesstoken | P0 | 使用项目实际查询接口 | `accesstoken=invalid` | 返回明确鉴权失败；不得产生写入 | 鉴权负向 |
| T5-PAY-002 | 商品查询 | currency 为空 | P1 | GET `/payment-service/ee/client/web/query` | `currency=` | 返回参数错误或受控空结果；不得触发交易 | 入参边界 |
| T5-STUDIO-002 | 剪辑分组 | page 为 0 | P1 | GET `/studio-service/clip/group/list` | `page=0&size=5` | 返回参数错误或按文档默认分页；不得 5xx | 数值边界 |
| T5-LIVE-006 | APP 新增 | name 为空 | P0 | POST `/live-platform/app/add` | `name=`；有效测试密钥 | 返回参数校验失败；查询不得出现空名称记录 | 必填校验，执行前需确认不会生成脏数据 |
| T5-LIVE-007 | APP 修改 | id 不存在 | P1 | POST `/live-platform/app/update` | 不存在的正整数 ID | 返回记录不存在；不得修改其他记录 | 业务负向 |
| T5-KONFI-003 | 公共配置 | formKey 不存在 | P1 | POST `/konfi-service/web/getDataById` | 唯一不存在的字符串 | 返回受控空结果或明确业务错误；不得 5xx | 待 Konfi 基线接口恢复后执行 |

## 4. 复用于其他项目

复制平台环境并替换以下变量即可复用，不需要修改接口测试功能代码：

- `BASE_URL`：项目网关地址。
- `GATEWAY_HOST`：存在反向代理 Host 路由时填写。
- `ACCESS_TOKEN`、`USER_ID`：项目登录后得到的鉴权变量，敏感值使用加密存储。
- OpenAPI JSON/YAML 或文档地址：通过 Web「预览导入」确认后再导入。
- 用例标签：建议使用 `query-safe`、`create-isolated`、`update-isolated`、`forbidden-delete`、`forbidden-transaction` 区分可执行范围。

执行顺序固定为：负向查询不存在 → 新增唯一测试数据 → 查询并保存 ID → 修改 → 再次查询校验。若项目不允许遗留测试数据，应先单独取得删除授权，再安排清理任务。
