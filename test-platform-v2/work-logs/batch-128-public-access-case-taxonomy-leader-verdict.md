# Batch 128 — Leader Verdict（公开访问、普通注册与用例分类体系）

> **Leader (🎯)** | Date: 2026-08-09 | Decision: APPROVED（CI lint 基线修复后待重新总确认）

## 评审摘要

| 维度 | 评分 | 结论 |
|------|------|------|
| 用户问题闭环 | 5/5 | 三项原始问题均有代码、契约、测试和真实浏览器证据 |
| 公开访问安全 | 5/5 | 访客只看能力目录；受保护 Outlet/API 不挂载；点击和直达统一登录 Dialog |
| 外放注册 | 4.8/5 | 默认普通注册，保留受控邀请码、项目邀请、限流、配额和撤销语义 |
| 用例信息架构 | 5/5 | 服务与脑图共享用户端/运营后台/接口测试分类逻辑和多级模块路径 |
| 交付质量 | 5/5 | 后端 1238、前端 lint/397/typecheck/build、三视口 Playwright、OpenAPI、F821 本地全绿；首轮 CI lint 基线失败已最小修复 |
| 风险 | 中 | 涉及鉴权入口与生产注册默认值；无迁移，可回退，需 required checks 和发布配置复核 |

## Leader 抽检

- **权限边界**：公开菜单不是匿名业务数据；`MainLayout` 在访客态不渲染 `<Outlet>`，避免“先请求再隐藏”。
- **登录闭环**：模块点击与直达路径均打开同一 Dialog；Dialog 登录后恢复原目标路由。
- **注册兼容**：无邀请码可注册；显式强制环境仍必填；项目邀请仍免平台邀请码；用户主动填写的邀请码仍必须有效。
- **分类兼容**：新 `/taxonomy` 为静态路由且位于 `/{case_id}` 前；旧 domains 接口和 DB schema 不变。
- **数据真实性**：类型计数来自 `/stats`，taxonomy 排除软删除；`functional` 与 `manual` 合并为 canonical 功能用例。
- **响应式与 a11y**：三视口无横向溢出；登录字段、类型入口、界面筛选和全屏控制均有稳定可访问名称。
- **CI 返工**：首轮 Draft PR 仅因 `MainLayout.tsx` 的 unused-vars 抑制计数过期而失败；最小更新 `eslint-suppressions.json` 后，lint、397 项测试、typecheck、build 全绿，不放宽规则。

## 判决

**APPROVED**。首轮 Draft PR 已建立，CI lint 基线修复经 QA 与 Leader 复核后保持 APPROVED。由于修复会新增提交，原总确认失效；用户明确重新确认当前文件与提交范围后，可推送 `feature/batch-128-public-access-case-taxonomy`，required checks 全绿后执行最终审计、转 Ready 并 squash merge。

以下事项不阻塞代码合入，但不得描述为已经生产生效：

- Railway/test/prod 外部变量没有在本批修改；发布时必须核对注册开关与邀请码策略。
- 本分支尚未进入发布火车，生产访客路径需部署后只读复验。
- 现有 npm 锁文件依赖告警未因本批新增依赖而扩大，仍需独立依赖治理。

## 下一批次 Leader 条件

本批不新增 C 条件。继续沿用既有外部部署、知识资产和 iOS/Test5 条件；普通注册生产开关由发布清单跟踪，不伪造已部署状态。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 整体路由守卫阻断产品发现 | 访客壳 + 安全公开目录 + Outlet 门禁 | `MainLayout.tsx`、`/auth/public-access` |
| “可选邀请码”可能破坏撤销语义 | 不填写可跳过，填写即严格校验 | `auth_service.register` + 全量回归 |
| domain 名称包含端别但 UI 未消费 | 无迁移 taxonomy 推导并复用到服务/脑图 | `test_case_service.py`、用例服务、脑图 |
| 生成类型漂移 | 重新生成 OpenAPI 类型 | `frontend/src/types/api.d.ts` |
| 清理变量后 ESLint 抑制计数漂移 | 仅将 `MainLayout.tsx` unused-vars 抑制计数 6 调整为 4，并全量复验前端 | `frontend/eslint-suppressions.json`、QA 报告 |

**技能影响**：Agent Team 要求把 Product→PM→Design→Dev→QA→Leader 证据完整落盘；UI/Playwright 技能促成三视口、Network、控制台和真实注册项目闭环验收。
