# Batch 227 AI 全链路就绪向导证据索引

> 基线：`origin/main@55e70ae1` | 场景：体育业务 `16.0.0` | Date: 2026-09-03

本目录记录接入向导的增量验收。Batch 226 的 B1-B15 与外部阻塞证据继续作为业务基线；本批修改了 onboarding 页面和契约，因此页面、接口、迁移和回归均重新执行，不复用旧页面截图。证据不包含账号、密码、Token、API Key 或运行数据库。

| 证据 ID | 覆盖范围 | 类型 | 基线/增量 | 证据 | 结论 | 复用规则 |
|---------|----------|------|-----------|------|------|----------|
| E227-01 | 体育 16.0.0 输入 | 清单 | 增量 | `manifests/sports-16-input.json` | PASS | 输入文件哈希不变时可复用 |
| E227-02 | 创建与 readiness API | 契约 | 增量 | `contracts/onboarding-openapi-contract.json` | PASS | 路由或 schema 未变时可复用 |
| E227-03 | 登录、六字段、保存、OpenAPI 导入、AI 阻断 | 回归 | 增量 | `regression/browser-result.json` | PASS | onboarding 页面或接口未变时可复用 |
| E227-04 | 桌面 1440x900 | 截图 | 增量 | `pc-usage-snapshots/desktop-1440x900.png` | PASS | 页面布局未变时可复用 |
| E227-05 | 保存后的桌面状态 | 截图 | 增量 | `pc-usage-snapshots/desktop-sports-16-saved.png` | PASS | 页面布局未变时可复用 |
| E227-06 | 平板 768x1024 | 截图 | 增量 | `pc-usage-snapshots/tablet-768x1024.png` | PASS | 页面布局未变时可复用 |
| E227-07 | 手机 390x844 | 截图 | 增量 | `pc-usage-snapshots/mobile-390x844.png` | PASS | 页面布局未变时可复用 |

## 浏览器结论

- 使用完整体育 `16.0.0` 需求正文创建接入记录并成功导入本地真实 OpenAPI。
- readiness 请求 1 次、创建请求 1 次、步骤推进请求 1 次；无控制台错误或页面异常。
- AI 未配置、Temporal 未启用、Worker 离线均显示“需要处理”；AI 方案按钮 fail-closed。
- 三视口 `scrollWidth == clientWidth`，无横向溢出；长需求默认收起，平台状态保持可扫描。
- 服务回归证明同版本不同需求在访问 OpenAPI 前即被拒绝，且不产生导入批次。
- 本地 OpenAPI 只用于验证平台接入能力，不代表体育目标服务已提供真实 OpenAPI 或被测环境。
