# Batch 60 系统管理 PC 验收证据

## 1. 结论

`FP-SYS-001` 在 Batch 60 本地隔离环境完成 PC 端真实后端验收，结论为 `PASS`。证据覆盖用户、角色、权限收敛、只读角色、审计持久化和 Cookie 会话下的 CSV 导出。凭据仅存在于本地执行进程，不写入截图、CSV 或本文档。

## 2. 执行范围

| 项目 | 实际结果 | 证据 |
| --- | --- | --- |
| 角色管理 | 展示 `admin`、`tester`、`batch60_readonly` 三个角色；只读角色为本项目数据范围且只保留 9 个只读权限 | `../pc-usage-snapshots/FP-SYS-001-01-roles-PASS.png` |
| 用户管理 | 展示管理员、测试人员和 Batch 60 甲方只读验收账号，角色绑定与启用状态可回读 | `../pc-usage-snapshots/FP-SYS-001-02-users-PASS.png` |
| 审计持久化 | 两次临时用户创建在请求结束后仍可由审计页查询，操作人、动作、目标、详情和本地 IP 均可核对 | `../pc-usage-snapshots/FP-SYS-001-03-audit-PASS.png` |
| 只读角色 | 只读账号登录项目 B 后只显示获授权菜单；用例页无新增、编辑、删除和批量写入口 | `../pc-usage-snapshots/FP-SYS-001-04-readonly-role-PASS.png` |
| CSV 导出 | Cookie 会话和当前项目头下成功导出 2 条 `user:create` 审计记录；与审计页的时间、操作人和目标一致 | `FP-SYS-001-audit-user-create.csv` |

## 3. Batch 60 问题关闭

| 问题 | 根因 | 关闭证据 |
| --- | --- | --- |
| 审计持久化丢失 | 请求级数据库会话成功结束时未统一提交，部分只 `flush` 的审计记录在会话边界丢失 | `backend/tests/test_batch60_audit_durability.py` 2/2 通过；审计页和 CSV 均回读到跨请求持久化记录 |
| 审计 CSV Cookie 会话失败 | 二进制导出仍读取已废弃的 `localStorage.access_token`，未携带 httpOnly Cookie 和当前项目头 | `frontend/src/api/__tests__/system.test.ts` 1/1 通过；实际 CSV 导出成功 |
| 用例数量硬编码 | 用例页把“全部/功能用例”固定写成 901/795，无法反映当前项目和只读项目的真实数量 | `caseListFormatters.test.ts` 新增项目领域聚合测试；只读项目截图回读 `全部 (0)`、`功能用例 (0)` |

## 4. 文件完整性

| 文件 | 像素/记录 | 字节 | SHA-256 |
| --- | --- | ---: | --- |
| `../pc-usage-snapshots/FP-SYS-001-01-roles-PASS.png` | 1440×900 | 77,576 | `bf728a96341956c2c5ecb2321b8988877793ead42979ab903161754757d95e4f` |
| `../pc-usage-snapshots/FP-SYS-001-02-users-PASS.png` | 1440×900 | 87,922 | `65664b93b8589b77a2b2eead86ccc63334efc563e41bb6f12e4138ab4a50c013` |
| `../pc-usage-snapshots/FP-SYS-001-03-audit-PASS.png` | 1440×900 | 92,269 | `83f0d1036cff617880b0f15080fdeb195e99054564cf494bf53091e0cfd26e01` |
| `../pc-usage-snapshots/FP-SYS-001-04-readonly-role-PASS.png` | 1434×958 | 66,121 | `addfc0191374e734db9069e435213b487e855dc12e51b98a66aa55ff0cf22ad2` |
| `FP-SYS-001-audit-user-create.csv` | 2 条记录 | 581 | `a24b34eb93da044ea240d42867555971094019dd3add6a6c3f80e08ed20ce289` |

前三张操作截图为统一 `1440×900` PC 视口。只读角色图为最终通过态内容截图，实际文件尺寸为 `1434×958`；尺寸差异已如实登记，不改变其权限收敛结论。

## 5. 敏感信息检查

- 四张截图经逐张人工检查，未出现密码、Token、Cookie、Secret、连接串或私钥。
- CSV 敏感词扫描未命中 `password`、`Authorization`、`Bearer`、`Cookie`、`Secret`、API Key、Token 或私钥字段。
- 图中邮箱均为 `cameltv.local` 本地测试身份；CSV 仅含 Batch 60 临时用户名、本地域名和 `127.0.0.1`，不含真实个人或体育业务凭据。

## 6. 定向自检

| 命令 | 结果 |
| --- | --- |
| `python -m pytest tests/test_batch60_audit_durability.py -q` | `2 passed` |
| `npm test -- --run src/api/__tests__/system.test.ts src/pages/testcase/__tests__/caseListFormatters.test.ts` | `2 files / 8 tests passed` |
