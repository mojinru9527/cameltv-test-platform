# TC-B60-FP-DATA-001：体育 Test5 数据集 UI 验收

执行日期：2026-07-30
入口：`/dataset`
视口：`1440×900`

## 数据来源

使用仓库 R1 文档 `tests/api-testing/cases/Test5-六服务增改查用例.md` 中已经执行过的安全用例，保留以下非敏感字段：用例编号、服务、HTTP 方法、路径、执行范围和预期业务码。

最终数据集 `batch60-Test5-safe-api-cases` 共 5 行，覆盖 live、camel、payment、studio 和 konfi；不包含 Token、Cookie、密码、用户数据或密钥。

## 已执行结果

| 操作 | 结果 |
| --- | --- |
| 损坏 JSON 预览 | 后端明确返回业务失败，UI 显示无法解析，未执行数据集创建 |
| JSON 预览 | 5 行、6 列正确 |
| 新增数据集 | 成功持久化并在列表显示 JSON/5 行 |
| 编辑描述 | PUT 成功，详情回显来源和无敏感数据声明 |
| 打开详情 | 5 条用例编号及服务/方法/路径均可见 |
| 删除临时数据集 | 二次确认后删除，正式 R1 数据集保留 |

快照：

- `../pc-usage-snapshots/FP-DATA-001-01-sports-dataset-list-PASS.png`
- `../pc-usage-snapshots/FP-DATA-001-02-sports-dataset-detail-PASS.png`

CSV/文件上传、分页、跨项目隔离、使用中删除和 API 任务参数化绑定尚未执行，模块状态为 `PARTIAL PASS`。
