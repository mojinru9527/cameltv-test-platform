# Batch 107 — QA Report（接口用例生成「测试考虑点」全量固化）

> **QA (🔍)** | Date: 2026-08-06 | Verdict: 需改进（功能落地，知识中心导入受阻登记障碍）

## 1. 交付与生产证据

| 资产 | 结果 | 证据 |
|------|------|------|
| 规范落盘 | `tests/test-case-standards/接口测试考虑点【辅助作用】.md`（101 节点全量转写）+ CLAUDE.md/api-checklist 引用 | 文件 diff + XMind 解析对照（2026-08-06 实测解析 101 节点） |
| 规则生成器 9 类新模板 | smoke/scenario/extra_param/security_ext/performance_low/data_test/stability/compatibility/monitoring 全部生成 | `api_case_generation_service.py` + 单测 10/10 |
| 真实样本响应结构断言 | list_visible 实测 35 条（原 33），正向/冒烟/返回值结构 3 条含业务断言（envelope/data/records≤30/核心字段非空/8 条 hints） | `generate_cases_from_real_sample` 实测输出 |
| 全量默认模板 | 18 条覆盖全部 9 类新场景（security_ext 3 / performance_low 2 / data_test 2 / stability 2 / monitoring 2） | 生成器实测输出 |
| AI 提示词注入 | api 上下文含 api-checklist + 测试考虑点；提示词断言要求含「响应结构/关键字段」 | `_load_skill_context_for('api')` + `_build_system_prompt` 实测 |
| 前端/schema 默认模板 | AssetTab 与 schema 默认集 15 项同步 | 文件 diff + tsc/build 通过 |
| 知识中心导入 | **受阻**：capture 返回 HTTP 200 + 业务码 409「内容重复」，知识源列表确认无该文档（total=5 均为体育文档）→ C102-2 确认复现 | 生产 API 实测（sportsadmin） |

## 2. 硬门禁

| 门禁 | 结果 |
|------|------|
| 后端受影响模块 pytest | ✅ 54 passed（spec_checklist 10 + real_sample 3 + apitest_generation 16 + openapi_import 9 + api_task_worker 16） |
| ruff F821（4 个后端文件） | ✅ All checks passed |
| 前端 typecheck | ✅ tsc -b 通过 |
| 前端 build | ✅ 8.40s 构建成功 |
| 前端 vitest（apitest） | ✅ 3/3 passed |
| Alembic | ✅ 单头（20260806_batch106_project_invite，本批无迁移） |
| scan-common-bugs | ✅ HARD 0 / WARN 209（基线持平，未新增） |
| validate_repo_boundaries --check | ✅ PASS |
| 调试残留 | ✅ 无 console.log/print/breakpoint/debugger |

## 3. 缺陷/障碍（P0–P3）

| # | 级别 | 问题 | 实测证据 | 处理 |
|---|:----:|------|---------|------|
| B107-1 | P2 | 知识中心导入规范文档失败：`/knowledge/capture` 返回业务码 409「内容重复」，但知识源列表无该文档（C102-2 复现：去重误判） | 生产 API：登录 200 → capture HTTP 200 + code 409 → sources total=5（无本规范） | 登记障碍 C107-1；规范先落盘仓库，capture 修复后导入 |
| B107-2 | P2 | 场景测试用例为「待关联」模板：单接口生成器无接口关联图谱，无法自动生成多接口串联步骤 | 生成器输出 scenario 用例标注"需接口关联配置后补全" | 登记 C107-2：接口关联能力后续批次 |

## 4. 诚实性说明

- 本批为生成能力与规范落盘，未改动数据库 Schema（无需迁移）；生产库未做任何写入（知识导入失败即停止，未产生脏数据）。
- 性能模板按用户指示为 P2/P3 低优先级辅助检查，非阻塞断言。
- XSS 按思维导图标注「暂不进行」豁免；现有基础 XSS 覆盖保留。
- 知识中心导入依赖 C102-2 修复，属平台既有障碍，非本批引入。

## 5. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 0.5d | 0/0/2/0 | 0 | 外部依赖+平台障碍 | 知识导入先行探测 capture 状态；场景测试需接口关联数据 |

**技能使用**：`cameltv-agent-team`（六部门流水线）、`test-case-design`（api-checklist/测试考虑点规范）。
