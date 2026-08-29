# Clean Code 规范 Gherkin 验收套件（适配版）

> 本目录是把 `test-platform-v2/docs/clean-code-standards.md`（简称「规范」）转成 **Gherkin（BDD）验收场景** 的套件。每条 `Scenario` 对应规范的一个强制/建议条目，写成 Given/When/Then 形式，既可作为**人工评审清单**，也可作为后续接入静态检查 / behave / pytest-bdd 自动化门禁的需求基线。

> **承接门禁**：本套件是 [测试平台 代码开发校验门禁](../../docs/code-development-gate.md) 的 **G3 行为验收** 层。门禁把 G0–G4 五道闸串起来，`tests/clean-code/*.feature` 对应其中 G3（行为验收）。

## 适用对象

- **被测对象**：`test-platform-v2/backend/`（Python · FastAPI）与 `test-platform-v2/frontend/`（TypeScript · React）的**已提交代码**。
- **执行方式**：仓库当前**没有** Gherkin 运行器（无 behave / pytest-bdd / cucumber）。因此本套件是**先落地为可读的验收基线**；接入自动化时按 `8. 自动化接入建议` 迁移。

## 文件 → 规范章节映射

| Feature 文件 | 对应规范章节 | 主题 |
|-------------|-------------|------|
| [01-naming.feature](01-naming.feature) | §3 命名规范 | 意图命名 / PEP 8 / 术语表 / 布尔前缀 |
| [02-functions.feature](02-functions.feature) | §4 函数规范 | 函数大小 / 单一职责 / SLAP / 副作用收敛 / 魔法数字 |
| [03-error-handling.feature](03-error-handling.feature) | §5 错误处理 | 统一异常体系 / 预期失败显式化 / AbortError 放行 / 前端错误呈现 |
| [04-layering.feature](04-layering.feature) | §6 分层与依赖方向 | 分层单向 / 路由禁 ORM / Store 不调 API / 队列原语 |
| [05-testing.feature](05-testing.feature) | §8 测试与代码质量 | pytest/Vitest / FIRST / 正负覆盖 / 错误路径 / 纯函数快照 |
| [06-comments.feature](06-comments.feature) | §9 注释规范 | 注释讲「为什么」/ 强制注释场景 / 无调试遗留 |
| [07-ai-generated-code.feature](07-ai-generated-code.feature) | §7 与 AI 生成代码适配 | 生成代码过门禁 / 不硬编码凭据 / persona 约束 / 三桶过滤 |
| [08-delivery-checklist.feature](08-delivery-checklist.feature) | §10 交付与自检清单 | 与 `AGENTS.md` §3 对齐的 push 前自查 |

## 约定

- **关键字**：使用国际标准 Gherkin 关键字（`Feature` / `Background` / `Scenario` / `Given` / `When` / `Then` / `And`），描述内容用中文，保证与 cucumber / behave / pytest-bdd 兼容。
- **每条 Scenario 可直接执行**：Given = 前置/输入，When = 触发动作，Then = 可验证断言（对应规范里的 `[强制]` 或 `[建议]`）。
- **正负覆盖**：规范要求「每个需求点 ≥1 正面 + ≥1 负面」，本套件对关键条目同时给出正面与负面场景。
- **编号**：`CC-{主题缩写}-{序号:03d}`，如 `CC-NAME-001`。

## 人工执行（当前方式）

按 Feature 文件逐个对照待评审/待提交的代码评审：

1. 打开对应 Feature 文件。
2. 对每条 Scenario 的 `Then` 断言，在 `git diff` 或目标文件中找到证据（✓）或反例（✗）。
3. 任一条 `Then` 不满足 → 标记为「不满足，需修复」；`[强制]` 条目不满足即 Block PR。

## 自动化接入建议（后续）

接入 behave（Python）或 pytest-bdd，把 `Then` 断言翻译成静态检查步骤：

1. **命名/函数/注释/调试遗留** → 对接现有 `ruff`（F821 已启用）+ 自研正则/ast 检查。
2. **路由禁 ORM / Store 不调 API / 分层单向** → 对接守卫测试 `tests/test_route_layer_orm_ban.py`、`tests/test_route_inventory.py`（已是平台既有守卫）。
3. **错误处理 / AbortError / P0 覆盖** → 对接 pytest + httpx 与前端 Vitest 的对应测试。
4. **凭据 / 硬编码** → 对接 `AGENTS.md` §3.1 / §3.5 的凭据扫描（`ai-delivery-policy.yml` 已有分支策略）。

> ⚠️ 本套件本身**不代替** `test-platform-v2/` 的 pytest/Vitest 业务回归；它是针对 `clean-code-standards.md` 的「代码质量验收」面向的 BDD 表述。
