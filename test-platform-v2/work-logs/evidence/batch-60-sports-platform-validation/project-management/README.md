# TC-B60-FP-PROJ-001：项目管理、成员与质量门禁

执行日期：2026-07-30
入口：`/project`
视口：`1440×900`

## 已执行结果

| 操作 | 结果 |
| --- | --- |
| 空编码/名称保存 | 两个必填错误同时显示，项目 POST 数 0 |
| 编辑项目 B | 描述更新为 Batch 60 多项目/RBAC/真实体育数据用途 |
| 成员角色 | seeded `tester` 在项目 B 中添加/更新为“测试人员”并回读 |
| 质量门禁 | 当前体育项目保存通过率 95%、P0 上限 0、P1 上限 3、启用 |
| 新增项目后顶部选择器 | 原实现未更新；修复后新项目立即出现，无需重新登录 |
| 停用项目 | 原 UI 错称物理删除；修复后明确停用，顶部选择器移除，管理表保留“禁用”历史 |

回归：`src/stores/__tests__/auth.test.ts` 13 条通过；前端 typecheck 通过；真实浏览器全流程通过。

快照：

- `../pc-usage-snapshots/FP-PROJ-001-02-project-quality-gate-PASS.png`
- `../pc-usage-snapshots/FP-PROJ-001-03-project-members-PASS.png`

项目切换陈旧页面修复的前后证据另见 `../project-isolation/`。重名、移除当前用户、低权限、全项目作用域页面和项目主题仍待执行，因此模块为 `PARTIAL PASS`。
