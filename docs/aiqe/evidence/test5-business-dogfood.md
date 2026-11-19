# Camel Test5 业务 Dogfood（登录 → 创建 → 校验 → 清理）

- 时间：2026-11-19
- 用户端：`https://camel-test5.elelive.cn`
- 运营后台：`https://camel-admintest5.elelive.cn`
- 结论：**PASS**，无残留

| 步骤 | 接口 | 结果 |
|---|---|---|
| 用户登录 | `POST /account-service/ee/client/demo/login` | 200，userId=11025728 |
| 管理员登录 | `POST /captcha/check` + `POST /login` | success（账号已脱敏） |
| 创建 | `POST /ee/sports_live/NewsKind/upsert` | 200，id=19，`AIQE_DOGFOOD_20261119_164512` |
| 校验 | `GET /ee/sports_live/NewsKind/detail?id=19` | 200，字段一致 |
| 清理 | `POST /ee/sports_live/NewsKind/del` id=19 | 200 |
| 残留检查 | `POST /ee/sports_live/NewsKind/query` | `matched=[]` |

> 说明：写操作仅创建/删除一个测试用资讯分类，未修改现有业务数据；账号、Cookie 不落库。
