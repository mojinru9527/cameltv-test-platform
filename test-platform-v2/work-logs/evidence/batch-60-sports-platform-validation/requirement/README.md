# Batch 60 需求上传首轮证据

执行日期：2026-07-30
执行人：Codex Agent Team
代码 SHA：`d15ed2197e41bbcecfac733f059160a912373317`
环境：Batch 60 local，前端 `5196`，后端 `8026`，独立 SQLite `platform-local.db`

## TC-B60-REQ-001：R1 体育 Markdown 上传成功

| 项目 | 结果 |
| --- | --- |
| 输入来源 | `产品需求/产品需求-天声猜猜猜-20260617_145800.md` |
| 上传文件名 | `batch60-天声猜猜猜-真实需求.md` |
| UI | 显示文档标题和上传成功反馈 |
| HTTP | `POST /api/v1/requirements/upload` → 200 |
| 业务返回 | `code=0`，文档 ID `1`，`file_type=md`，`status=parsed` |
| DB | `requirement_document` 中 ID `1`、项目 `1`、标题/来源/状态一致 |
| 审计 | `sys_audit_log` 新增 `requirement:upload`，target 保存文档 ID/标题 |
| 浏览器异常 | 控制台错误 0，失败响应 0 |
| 状态 | 通过 |

截图：`TC-B60-REQ-001-upload.png`

## TC-B60-REQ-002：空 Markdown 被拒绝且无副作用

| 项目 | 结果 |
| --- | --- |
| 输入 | 文件名 `batch60-empty.md`，内容 0 字节 |
| UI | 显示“上传失败” |
| HTTP | `POST /api/v1/requirements/upload` → 400 |
| 业务返回 | `code=400`，`msg=上传文件不能为空` |
| DB | 总需求仍为 1；`batch60-empty.md` 记录为 0 |
| 审计 | `requirement:upload` 总数仍为 1，无失败写入审计副作用 |
| 状态 | 通过 |

截图：`TC-B60-REQ-002-empty-rejected.png`

## 观察

知识源表没有新增对应记录。当前需求上传接口把知识摄取安排为 post-commit 后台任务；需要结合配置和服务约定继续确认这是“AI/向量能力禁用时的预期跳过”，还是后台摄取失败但 UI 未告知。当前不直接登记缺陷，待执行知识中心闭环后判定。
