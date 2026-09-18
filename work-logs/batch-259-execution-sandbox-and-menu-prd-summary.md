# Batch 259 — PRD Summary

> **Product (🟦)** | Date: 2026-09-18 | Status: Review
> **批次档位**: 完整批次（六件）

## 0. 批次模式判定（Product 第 1 步）

```text
mode: full
判定依据: 命中触发器 ×4 —— 执行链路变更（H1 本地执行沙箱 + 危险 API 静态拦截）、
          权限/凭据模型变更（密钥派生统一 + 启动 fail-fast）、
          新配置（沙箱与出网白名单配置项）、前端行为变更（一级菜单割到 4 个入口）
豁免记录: 无（完整批次不允许豁免）
```

对应 `docs/agent-team/pipeline-modes.md` §1。

## 1. 问题陈述

B1（Batch 258）把「用户输入 → 出网」这条链收口并合入 main。剩下的三条审计风险
（`work-logs/reviews/2026-09-18-code-audit-baseline.md` 的 S4/S5/S6）都落在**执行与落盘**这条链上，
而它们的共同点是：**"看起来安全"的地方其实是薄弱点**。

| 事实（`main@2ced1baf` 实测） | 后果 |
|---|---|
| `app/integrations/object_storage/local.py:24-26` 用 `normpath(join(base, rel))`，无收敛校验 | 一旦文件名可控即任意路径写；`../../etc/passwd` 形式 URI 直接逃逸 |
| 密钥派生有两套：`cipher.py:26` 用 `effective_secret_key`，`ai_config_service.py:61-62` 用 `secret_key` | 同一份明文按调用路径加密成不同密文；换 SECRET_KEY 后存量密文解不开 |
| `case_compiler_service.py:6` 把 `npx playwright test --dry-run` 称作 **sandbox 校验** | dry-run 仍会执行 spec 顶层语句，**不是安全边界**；这句注释会让人误以为已有沙箱 |
| `test_plan_service.py:612` 以 `validate=False` 调用编译器 | 计划执行路径**跳过**语法校验，坏 spec 直接进执行 |
| `execution_sandbox.py` 只做环境变量白名单 + POSIX rlimit | 不限制文件写入、不限制出网；H1 的"无持久卷写 / 无内网 egress"尚未成立 |
| tester 一级导航仍远超 4 项 | 02 白名单 §2.1 的「4 入口 + 专家区」承诺无法执行校验 |

一句话：**B1 让"外部输入"有了边界，B2 要让"执行与落盘"也有边界，并且把没边界的地方如实说清楚。**

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 对象存储路径逃逸 | 可逃逸（无校验） | `../../etc/passwd` 形式 URI 全部被拒 + 回归用例 | 本批 |
| 密钥派生实现数 | 2 | 1（`cipher.py`）；`rg "sha256\(.*secret_key"` 只命中 `cipher.py` | 本批 |
| 无 SECRET_KEY 但有密文 | 静默用另一套密钥 | 启动 fail-fast 并给出可读原因 | 本批 |
| dry-run 被称作沙箱的处 | 1（`case_compiler_service.py:6`） | 0；文档/注释改为「语法检查，不是安全边界」 | 本批 |
| 计划执行路径 `validate=False` | 1 处 | 0 | 本批 |
| 危险 API 静态拦截 | 无 | 含 `child_process`/`execSync`/`fs` 写/`net`/`process.env` 的 spec 在执行前被拒 | 本批 |
| tester 一级导航项 | >4 | ≤4 + 专家区，且有可执行断言 | 本批 |

## 3. 非目标（本次不做）

- **不做 OS 级容器沙箱**（seccomp/namespace/bubblewrap）：沿用 `execution_sandbox.py` 的定位，
  在进程内把"能拿到什么"收紧（环境、文件、网络），把"要容器"留给自托管裸机场景按需评估。
  理由：控制面（云端单机）本就不执行，节点在测试人员机器上；本批先把**可达面**收敛并**如实标注边界**。
- **不动老队列** `ui_test_service` / `api_task_worker`（§4 硬约束 2）。
- **不重写智能`Healing`/`Campaigns`** 等引擎概念页：B2-6 只做"一级导航收敛 + 隐藏清单"，页面本身不动。
- **不改业务断言语义**：本批只加守卫与拦截，不改用例通过/失败判定。

## 4. 用户故事 + 验收标准

- As a 安全负责人, I want 生成代码里的危险 API 在执行前被拦下, so that LLM 产出的 spec 不会在节点上读写任意文件或访问内网。
  验收：Given 一段含 `execSync` 的 spec, When 提交执行, Then **在执行前**被拒并给出可读原因（指明命中的 API 与行号）。

- As a 运维, I want 沙箱里读 `.env`、连内网、写持久卷都会失败, so that "沙箱"这个词是有内容的。
  验收：Given 沙箱配置, When 子进程尝试上述三种动作, Then 全部失败，且有回归用例。

- As a 平台维护者, I want 密钥只有一个派生实现、缺 SECRET_KEY 时启动就报错, so that 换密钥不会让存量密文静默解不开。
  验收：Given 无 SECRET_KEY 且库中已有密文, When 启动, Then fail-fast 且错误可读。

- As a 测试工程师, I want 一级菜单只剩 4 个入口 + 专家区, so that 我知道"今天该点哪里"。
  验收：Given tester 登录, When 看一级导航, Then ≤4 项；被隐藏页面仍可经权限 + 搜索直达。

- As a 评审者, I want 「dry-run = 沙箱」这句错误定位被彻底纠正, so that 没人再把它当安全边界。
  验收：Given 代码与文档, When 全量搜索, Then 不再有把 dry-run 称作 sandbox 的表述；计划执行路径无 `validate=False`。

## 5. 技术考量

- **S4 修法**：与 `app/api/v1/lanhu_evidence_assets.py:86` 的 `is_relative_to` 写法保持一致（同一仓库只留一种收敛写法）。
- **S5 修法**：`ai_config_service` 的 `_fernet` 改为调用 `cipher.py`；新增启动校验（无 SECRET_KEY 且存在密文 → fail-fast）。
  需注意存量数据：dev 用 `effective_secret_key` 自动生成，因此"无 SECRET_KEY"只允许在没有密文时成立。
- **静态拦截落点**：必须在**写文件/执行之前**（`case_compiler_service` 生成后、`playwright_executor` 落盘前）统一挂一个
  `assert_spec_safe()`；拦截失败即拒，并给出可读原因（含命中行）。
  已知边界：静态检查不是沙箱，能拦住"明显的"危险 API；真正的隔离仍靠 B2-1 的进程约束——两者都必须有，不能互相替代。
- **菜单收敛**：`frontend/src/layouts/nav-config.ts` 是唯一事实源，`nav-config.test.ts` 已有测试基础；
  隐藏项走 `menu_service.HIDDEN_MENU_CODES` 风格的白名单，保证"隐藏但可达"。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批合入 main | 平台研发 | required checks 全绿 + Leader APPROVED |
| 随发布火车上 test | 测试团队 | 迁移/配置生效 + 菜单走查 |
| B3 起 | 试点 | 知识主线在收敛后的 4 入口内可用 |

## 7. 技能使用

- `cameltv-bug-guard` → 开工前对照「未关闭已知风险」表核对 S4/S5/S6 证据位置（非测试证据）。
- `cameltv-agent-team` → 批次档位判定与工件骨架（非测试证据）。
- `cameltv-ui-conventions` → B2-6 菜单/导航的样式与无障碍基线（B2-6 执行时使用）。
