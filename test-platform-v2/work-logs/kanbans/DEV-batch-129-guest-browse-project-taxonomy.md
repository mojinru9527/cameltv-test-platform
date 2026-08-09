# 🗂️ Dev 看板 — Batch 129（访客功能浏览、项目引导与用例重分类）

| 字段 | 值 |
|------|-----|
| 项目 | 访客功能浏览、项目引导与用例重分类 |
| 模式 | full |
| 执行器 | codex |
| 分支 | feature/batch-129-guest-browse-project-taxonomy |
| Worktree | F:/CamelTv-worktrees/codex-batch-129-guest-browse-project-taxonomy |
| 前/后端端口 | 5192 / 8022 |
| 关联 PRD | `../batch-129-guest-browse-project-taxonomy-prd-summary.md` |
| 关联 PM 计划 | `../batch-129-guest-browse-project-taxonomy-pm-plan.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | Product / PM / Design / 实现计划 | ✅ | ✅ | ✅ | ✅ | ⏳ | C104-5/C122-4 纳入 |
| 1 | 访客模块说明与登录动作分离 | ✅ | 🔄 | ⏳ | ⏳ | ⏳ | 红灯已验证；匿名业务 API=0 |
| 2 | 无项目布局边界与创建 CTA | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | Outlet 不挂载 |
| 3 | 31 旧域后端重分类与 surface 契约 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 单一事实源 |
| 4 | 脑图消费 surface 与动态筛选 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 无未知则不显示“其他” |
| 5 | QA / Network / 三视口 / Leader | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 增量证据替换 Batch 128 基线 |
| 6 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 一次总确认 |

## 📍 当前位置

```text
Batch 129
├─ ✅ Slice 0：工件与实现计划自检
├─ 🔄 Slice 1：测试先行实现访客模块说明（RED）
├─ ⏳ Slice 2：测试先行实现无项目边界
├─ ⏳ Slice 3：测试先行实现旧域重分类
├─ ⏳ Slice 4：脑图统一消费 surface
├─ ⏳ Slice 5：QA / 浏览器 / Leader
└─ ⏳ Slice 6：用户总确认 → Draft PR → checks → merge
```

## 决策记录

- 访客看到静态模块能力说明，不读取匿名业务数据。
- 项目缺失在布局层阻断，而不是逐页吞掉错误。
- 旧域映射在后端维护；列表响应输出 `surface`，脑图不再复制业务规则。
- 未知域继续作为“其他”数据质量信号，但 UI 不固定展示空筛选。

## 风险

| 风险 | 严重度 | 缓解 |
|------|--------|------|
| 公开说明与真实能力漂移 | P2 | 目录按现有路由/页面编写，并用当前公开菜单全覆盖测试 |
| 无项目白名单过宽造成请求 | P1 | 仅放行 `/my-projects`、`/organizations`，Network 验证 |
| 旧域误归类 | P1 | 31 域逐项基于仓库规范锁定测试，未知不猜测 |
