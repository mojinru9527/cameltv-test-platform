# Batch 129 — Leader Verdict（访客功能浏览、项目引导与用例重分类）

> **Leader (🎯)** | Date: 2026-08-09 | Decision: APPROVED（待用户总确认与 required checks）

## 评审摘要

| 维度 | 评分 | 结论 |
|------|------|------|
| 用户问题闭环 | 5/5 | 三项反馈均有实现、自动化、Network 与视觉证据 |
| 公开访问安全 | 5/5 | 只公开静态能力说明；匿名业务 API=0；具体使用显式登录 |
| 新用户起步 | 5/5 | 无项目在 Outlet 上层阻断，项目/组织起步页可达 |
| 数据分类 | 5/5 | 476 条、31 域全部归类；列表与脑图共享单一事实源 |
| 工程质量 | 5/5 | 后端 1270、前端 434、lint/type/build/F821/浏览器三视口全绿 |
| 风险 | 中低 | 涉及主布局和响应契约，但无迁移、兼容新增字段、可按提交回退 |

## Leader 抽检

- **浏览/使用分离**：侧栏与首页导航仅切换路径；`GuestModulePreview` 不 import 业务页面，CTA 才打开共享登录 Dialog。
- **路由安全**：访客直达 `/mindmap` 与 `/testcase` 只渲染静态说明；Network 没有用例/计划/报告等业务请求。
- **项目边界**：`ProjectAccessBoundary` 在 `currentProjectId == null` 时不渲染 children；只放行 `/my-projects`、`/organizations`。
- **权限文案**：有 `project:self_create` 时引导创建；无权限时提示联系管理员，不承诺无法执行的操作。
- **分类优先级**：API 类型优先于 domain；显式端别词优先；旧域精确映射；未知仍为“其他”。
- **契约一致性**：`TestCaseOut.surface`、`_row_to_dict`、taxonomy 和脑图消费链路一致；OpenAPI 已重新生成。
- **完整数据**：Batch 110 审计源 476 = 227 用户端 + 249 运营后台，other_domains=[]。
- **视觉与 a11y**：桌面/平板/手机无横向溢出；页面 h1、按钮名称和对话框名称均可访问。

## 判决

**APPROVED FOR TOTAL CONFIRMATION**。本地产品、设计、开发、QA 与 Leader 六部门证据齐全。用户确认当前提交与文件范围后，可推送 `feature/batch-129-guest-browse-project-taxonomy`、创建指向 `main` 的 Draft PR；只有 required checks 全绿且 `audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过，才可转 Ready 并 squash merge。

以下事项不阻塞合入，但不能描述为已完成：

- 尚未推送、创建 PR 或合并；当前没有用户总确认。
- 合入 main 不等于生产发布；生产数据分类和公开访问必须在后续发布窗口复验。
- 锁文件既有 4 个 high severity 依赖告警未因本批新增依赖而扩大，继续由依赖治理处理。

## C 条件与流程回写

- C104-5：首个补丁前核对批次 worktree、metadata、分支与 clean 状态，满足。
- C122-4：用例服务与脑图统一消费后端 `surface`，并对完整存量审计集验证，满足。
- 本批不新增 C 条件；其余外部 Open/Deferred 条件保持原解除条件。
