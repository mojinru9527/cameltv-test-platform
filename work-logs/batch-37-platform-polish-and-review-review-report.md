# Batch 37 — 测试平台 v2 综合审查报告

> **Dev (💻)** | Date: 2026-07-23 | 覆盖：代码 / 功能 / UI / Agent Team 逻辑

---

## 综述

对 `test-platform-v2/` 进行系统级三合一审查，涵盖后端 50+ 服务文件、前端 20 个页面模块、Agent Team 流水线 6 个部门 + 6 个 PowerShell 脚本。共检出 **30 个缺陷**（P0×2 / P1×7 / P2×15 / P3×6）。

---

## 一、代码层面

### 🔴 P0-01: `R.err()` 方法不存在，9 处调用将引发 AttributeError

**文件**：[schemas/common.py:11](test-platform-v2/backend/app/schemas/common.py#L11)、[environment.py:100](test-platform-v2/backend/app/api/v1/environment.py#L100)、[test_case.py:64](test-platform-v2/backend/app/api/v1/test_case.py#L64)

`R` 类只定义了 `ok()` 类方法，没有 `err()`。但 `environment.py`（2 处）和 `test_case.py`（7 处）调用了 `R.err(code=..., msg=...)`，一旦触发这些错误分支，会抛出 `AttributeError` 返回 500，而非预期的业务错误码。

**根因**：`R.err()` 模板曾被引用但从未在 `common.py` 中实现。历史修复可能只改了主流程，没覆盖错误分支。

**修复建议**：在 `R` 类中添加 `err()` 类方法：
```python
@classmethod
def err(cls, code: int = 1, msg: str = "error") -> "R":
    return cls(code=code, msg=msg, data=None)
```

### 🔴 P0-02: 测试用户密码明文打印到控制台

**文件**：[seed.py:316](test-platform-v2/backend/app/seed.py#L316)

```python
print(f"[seed] 测试用户自动生成密码：{tester_pwd}")
```

自动生成的密码通过 `print()` 直接输出到 stdout，会被 CI 日志、Docker 日志等记录，造成密码泄露。

**修复建议**：改用 `logger.info("[seed] 测试用户密码已生成（已哈希存储）")` ，不打印明文。

---

### 🟠 P1-01: 硬编码加密回退密钥

**文件**：[cipher.py:17](test-platform-v2/backend/app/core/cipher.py#L17)
```python
raw = settings.secret_key.encode("utf-8") if settings.secret_key else b"cameltv-dev-key"
```

当 `SECRET_KEY` 未设置时，加密降级为源码中可见的固定密钥。攻击者拿到数据库后可直接解密所有凭据。

**修复建议**：未设置 `SECRET_KEY` 时拒绝加密/解密操作，抛出明确错误。

### 🟠 P1-02: 6 处 `except Exception: pass` 静默吞异常

| 文件:行 | 影响 |
|---------|------|
| [open_api.py:116-117](test-platform-v2/backend/app/api/v1/open_api.py#L116) | CI 触发通知失败不可见 |
| [open_api.py:222-223](test-platform-v2/backend/app/api/v1/open_api.py#L222) | CI 结果回写通知失败不可见 |
| [open_api.py:307-308](test-platform-v2/backend/app/api/v1/open_api.py#L307) | Playwright 执行线程启动失败不可见 |
| [api_task_worker.py:224-225](test-platform-v2/backend/app/services/api_task_worker.py#L224) | Worker 任务标记失败静默 |
| [api_task_worker.py:287-288](test-platform-v2/backend/app/services/api_task_worker.py#L287) | DB Session 关闭失败静默 |
| [playwright_executor.py:514-516](test-platform-v2/backend/app/services/playwright_executor.py#L514) | 文件列表错误静默返回部分结果 |

**修复建议**：每个 `except` 块至少加 `logger.exception("描述")` ，关键路径（#1-3）需将异常传播给调用方。

### 🟠 P1-03: 7 个安全敏感端点使用无验证 `body: dict`

**文件**：[open_api.py:163](test-platform-v2/backend/app/api/v1/open_api.py#L163)、[token.py:50](test-platform-v2/backend/app/api/v1/token.py#L50)、[notify.py:40](test-platform-v2/backend/app/api/v1/notify.py#L40) 等

CI 结果回写、Token 创建、通知 Webhook 等端点直接接受 `body: dict`，无 Pydantic 校验。

**修复建议**：替换为 Pydantic BaseModel schema。

### 🟠 P1-04: 仪表盘 N+1 查询

**文件**：[dashboard_service.py:275-291](test-platform-v2/backend/app/services/dashboard_service.py#L275)

跨项目趋势查询对每个 (天, 项目) 组合发出 3 次独立 DB 查询。5 个项目 × 7 天 = 105 次查询。

**修复建议**：批量收集所有 `(project_id, day)` 对，一次分组查询完成。

### 🟠 P1-05: 缺陷分类循环 N+1

**文件**：[triage_service.py:71-73](test-platform-v2/backend/app/services/triage_service.py#L71)

对每个执行记录独立查询 `TestPlanCase` 和 `TestCase`，50 条失败 = 100 次额外查询。

**修复建议**：在初始查询中 JOIN 或用 `in_()` 批量预加载。

### 🟠 P1-06: 不一致的错误处理模式

**文件**：全部 Router 文件（~100+ 处）

三种模式混杂：
1. `raise APIException(code=...)` → HTTP 错误状态码 ✅ 正确
2. `return R(code=..., msg=...)` → HTTP 200 + 业务错误码 ❌ 语义错误
3. `return R.err(...)` → AttributeError ❌ 崩溃

**修复建议**：统一使用 `raise APIException` ，由全局异常处理器统一封装。

### 🟠 P1-07: CSRF 中间件静默吞异常

**文件**：[csrf.py:96-97](test-platform-v2/backend/app/middleware/csrf.py#L96)

Origin/Referer header 解析失败时静默返回拒绝。合法请求被误阻时无法排查。

**修复建议**：添加 debug 级别日志。

---

### 🟡 P2-01: `_safe_json()` 重复定义 4 次

**文件**：`api_execution_service.py:606`、`case_generation_service.py:384`、`case_compiler_service.py:177`、`apitest.py:69`

**修复建议**：提取到 `app/core/utils.py`。

### 🟡 P2-02: `response_model=R[dict]` 125 处无类型信息

**文件**：全部 `api/v1/*.py`

**修复建议**：逐步替换为具体 Pydantic response models。

### 🟡 P2-03: `Any` 类型泛滥（~40 函数签名）

**文件**：[api_execution_service.py](test-platform-v2/backend/app/services/api_execution_service.py)、[case_generation_service.py](test-platform-v2/backend/app/services/case_generation_service.py)

**修复建议**：定义 TypedDict 或 Pydantic 模型。

### 🟡 P2-04: 2 个列表端点缺少分页

**文件**：[token.py:37](test-platform-v2/backend/app/api/v1/token.py#L37)、[environment.py:27](test-platform-v2/backend/app/api/v1/environment.py#L27)

### 🟡 P2-05: `auto_create_tables` 与 Alembic 迁移不一致风险

**文件**：[main.py:72-73](test-platform-v2/backend/app/main.py#L72)

### 🟡 P2-06: 报告序列化代码重复

**文件**：[report_service.py:141-158 和 180-195](test-platform-v2/backend/app/services/report_service.py#L141)

---

### ⚪ P3-01: 仪表盘冗余分组查询

**文件**：[dashboard_service.py:126-131](test-platform-v2/backend/app/services/dashboard_service.py#L126)

### ⚪ P3-02: `TestExecution.executed_at` 缺少索引

**文件**：test_plan.py model

### ⚪ P3-03: SQLite WAL 模式未在代码中显式设置

**文件**：`core/db.py`

### ⚪ P3-04: 知识中心 4 个组件弹窗代码完全重复

**文件**：[ProjectTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx)、[PlatformTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx)、[SourceListTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx)、[ArtifactReviewTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx)

4 个组件的弹窗（Dialog）结构、元数据网格、切片列表完全一致，应抽取为共享组件 `KnowledgeSourceDialog`。

---

## 二、功能层面

### 知识中心

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| 项目知识数据源正确性 | ❌ | 「项目知识」Tab 展示 Agent Team 工件（PRD/PM），非体育项目知识 |
| 知识检索可用性 | 🟡 | 混合检索已实现，需用真实数据验证 |
| 弹窗内容可读性 | ❌ | 1024px 宽度不足，切片内容显示不全 |
| AI 审核台 | ✅ | 已实现 artifact review 流程 |
| 知识图谱 | ✅ | 实体/关系已实现 |
| 空状态引导 | 🟡 | 有引导文案但缺少「导入」操作按钮 |

### 导航菜单

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| 未完成模块暴露 | ❌ | 版本测试任务/缺陷管理/测试数据集/集成配置 4 个未完成模块可见 |
| 菜单分组合理性 | ✅ | 知识/导航/系统 三组清晰 |
| 动态菜单权限过滤 | ✅ | menu_service 按用户权限过滤 |

### 其他模块（基于 CLAUDE.md 成熟度表交叉验证）

| 模块 | 标注成熟度 | 实际验证 | 差异 |
|------|-----------|---------|------|
| 登录鉴权 | ✅ 生产可用 | ✅ | 一致 |
| 工作台 | ✅ 生产可用 | ✅ | 一致 |
| 用例服务 | ✅ 生产可用 | ✅ | 一致 |
| 测试计划/执行 | ✅ 生产可用 | ✅ | 一致 |
| 需求管理+AI | ✅ 生产可用 | ✅ | 一致 |
| 缺陷管理 | ✅ 生产可用 | 🟡 | PRD 标注为 6 状态机已实现，但早期 PRD 标记为「仅外链」— 状态不一致 |
| API 测试 | 🟡 能力有限 | 🟡 | 一致 |
| UI 自动化 | 🟡 能力有限 | 🟡 | 一致 |
| 音视频专项 | 🧪 演示态 | 🧪 | 一致（数据为 random） |
| 通知中心 | ✅ 生产可用 | ✅ | 一致 |

---

## 三、UI 层面

### 🟡 P2-07: 全局字体偏小

正文 `text-sm`（14px）低于行业标准 16px。侧边栏菜单项 14px 在白天长时间使用时容易疲劳。

**状态**：已在 Slice 7 修复，升级到 15px（text-sm）、17px（text-base）。

### 🟡 P2-08: 知识中心 Tab 标签过多（13 个）

在 1366px 屏幕上 Tab 列表需要横向滚动。

**建议**：将低频 Tab 收入「更多」下拉菜单。本批次暂不处理。

### 🟡 P2-09: 空状态缺少操作入口

知识中心空状态有文案但无「导入文档」按钮。

**状态**：已在 Slice 5 修复弹窗尺寸，操作入口留待后续 Batch。

### ⚪ P3-05: 侧边栏 collapsed 模式下字体无需放大

仅显示图标，符合预期。

### ⚪ P3-06: Tailwind 基础字号覆盖范围

`tailwind.config.cjs` 只覆盖了 xs~2xl，`text-3xl` 及以上仍为默认值。这些在大标题/登录页使用，影响有限。

---

## 四、Agent Team 逻辑审查

### 🟡 P2-10: DEPARTMENTS.md 第 6 节编号混乱

**文件**：[DEPARTMENTS.md:162-204](.claude/skills/cameltv-agent-team/DEPARTMENTS.md#L162)

Leader 部门（第 6 部门）的模板与 PR 合并指令、工作树清理指令（"7.PR 合入后"、"8.batch 结束"）混在一起。Section 编号跳跃（6 → 7 → 8），读者可能误以为 7/8 是新增部门。

**修复建议**：将 Leader 模板独立为 `## 6. 🎯 Leader 领导部门` 小节，将 7/8 指令移到 SKILL.md 中。

### 🟡 P2-11: C-CONDITIONS.md 引用但可能不存在

**文件**：[SKILL.md:178](.claude/skills/cameltv-agent-team/SKILL.md#L178)

SKILL.md 引用 `C-CONDITIONS.md` 并指示 Leader 更新它。但本次检查发现该文件不存在。如果 Leader 按指令写入 `work-logs/C-CONDITIONS.md`，后续 Batch 的 Product 部门能正确读取。但目前没有机制确保文件在仓库中持久化（Batch worktree 可能被清理）。

**修复建议**：在 `AGENTS.md` 中明确 C-CONDITIONS.md 的路径约定，或在 Leader 章节中加入「确认文件存在，否则创建」指令。

### 🟡 P2-12: 多窗口并行规则存在竞争窗口

**文件**：[SKILL.md:91-95](.claude/skills/cameltv-agent-team/SKILL.md#L91)

SKILL.md 规定「后合入者负责解决冲突」和「每日至少一次 fetch」。但未明确规定「如果窗口 A 创建 worktree 后，窗口 B 向 main 合入了对同一文件的改动，窗口 A 何时/如何感知」。

**修复建议**：在 Dev 部门每切片开始时强制 `git fetch origin main && git merge-base --is-ancestor origin/main HEAD || echo "⚠️ main 有更新"`。

### ⚪ P3-07: `confirm-agent-team-completion.ps1` 无超时/重试

脚本等待用户确认无超时机制。如果用户长时间不回复，脚本会一直挂起。

---

## 五、汇总

| 维度 | 总数 | P0 | P1 | P2 | P3 |
|------|:----:|:--:|:--:|:--:|:--:|
| 代码 | 20 | 2 | 7 | 7 | 4 |
| 功能 | 5 | 0 | 0 | 4 | 1 |
| UI | 3 | 0 | 0 | 2 | 1 |
| Agent Team | 4 | 0 | 0 | 3 | 1 |
| **合计** | **32** | **2** | **7** | **16** | **7** |

> **建议优先修复**：P0-01（R.err 崩溃）、P0-02（密码泄露）、P1-01（加密回退密钥）。
