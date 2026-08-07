# Batch 112 — Leader Verdict（response_structure 断言引擎 + 4 端点校准 + 批量全绿 + C111-3）

> **Leader (🎯)** | Date: 2026-08-07 | Decision: **APPROVED（有条件通过，C111-2/C111-3 部署后验证）**

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求聚焦 | PASS | 完整批次；范围=引擎缺口/4 端点校准/批量重跑/C111-3，无蔓延；用户方向（知识中心/UI 交互）登记 C112-1/2 未混批 |
| 实现质量 | PASS | 引擎 TDD 14 新测试 + 全量 1167 回归；语义与脚本侧完全对齐（envelope 严格 / data.* 动态豁免） |
| 证据 | PASS | 单测/回归/ruff/Alembic/边界/扫描全绿；4 端点生产实跑 + 干跑 36/36 |
| 诚实性 | PASS | 生产批量重跑与 UI 定时标注为部署后验证（C111-2/3）；news/get 服务端缺陷如实登记 B112-1 |

## 关键决策（已批准）

1. **引擎语义对齐脚本侧**：`response_structure` 按 `execute-interface-cases.py` 口径实现
   （envelope 缺失失败、`data.*` 缺失 warning、records 字段键存在为准、len_lte/hint），
   平台与脚本双口径归一；动态数据豁免为 B110-5 既定口径。
2. **4 端点校准 = 契约必填请求头补齐 + 真实参数**：login→formData+clientip、ads→三头、
   search→Accept-Language；news/get 生产全 id 业务 400（B112-1 服务端缺陷），用户端用例重指向
   `get_visible`（用户可见端点，同真实 id）。
3. **生产执行部署后验证**：Railway 部署新引擎后执行校准脚本 → `run-batch-execution.py --label batch-112`
   （目标 170 全绿 + 按端点明细）→ `setup-ui-schedule.py --label batch-112`（10/10），
   随后关闭 C111-2/C111-3。
4. **用户方向承接**：知识中心「模块-接口-功能」关联梳理与 UI 交互用例补充登记 C112-1/C112-2（P1），
   下一批次执行，不在本批混入。

## 抽检通过

- ✅ `api_execution_service.py:333-337` — `response_structure` 分支接入 `_run_assertions`
- ✅ `api_execution_service.py:_assert_response_structure/_structure_resolve/_structure_split` —
  语义与脚本对齐；hint/动态豁免/len_lte 覆盖
- ✅ `test_api_execution_response_structure.py` — 14 用例（envelope 缺失失败/data 动态豁免/records 路径/len_lte 边界/hint）
- ✅ 后端全量 pytest — 1167 passed / 3 skipped / 0 failed（exit 0）
- ✅ ruff F821 / Alembic 单头 / scan HARD=0 / validate_repo_boundaries PASS
- ✅ 4 端点生产实跑校准干跑 — 36/36（login 9、ads 21、search 3、news 3）

## 判决

**APPROVED（有条件通过）**：进入一次总确认 → push → Draft PR → required checks → 合入 main →
Railway 部署后执行 C111-2（批量重跑 170 全绿 + 回填核对）与 C111-3（UI 定时 10/10 核对），
证据落盘 `evidence/batch-112/` 后关闭 C111-2/C111-3。

## 下一批次 Leader 条件

- C112-1（P1）：知识中心「体育平台模块-接口-功能」关联梳理，沉淀为用例生成基座
  （用户 2026-08-07 方向：用户端+运营端需求为主、接口为辅、真实体育平台落地补充调整）。
- C112-2（P1）：UI 交互点击跳转类用例补充（用户 2026-08-07 方向：当前用例缺页面交互维度）。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 平台断言引擎不支持生成器产出的 response_structure → 批量执行 102/170 误失败 | 引擎补齐 + TDD + 全量回归 | `api_execution_service.py` + `test_api_execution_response_structure.py` |
| XHR 样本未采集请求头 → 4 端点用例缺契约必填头 | 校准脚本按契约补头 + 采集工具（B10）补头捕获 | `calibrate-interface-cases.py` + `改进任务backlog.md` B112-2 |
| 编辑工具默认落主仓库 cwd（本批首次补丁误写 F:\CamelTv） | 已迁移至任务 worktree + 逐补丁核验落点（C104-5） | 流程执行记录（C104-5） |
| news/get 生产全 id 400 而 get_visible 正常 | 服务端缺陷登记 B112-1；用户端用例重指向 get_visible | `改进任务backlog.md` SPORT-INT |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 0.5d | 0/1/1/0 | 1 | 工具链 + 外部依赖 | 生成用例先补契约请求头再落库；生产执行前置确认部署与凭据 |

**技能使用**：`cameltv-agent-team`（流水线）、`cameltv-bug-guard`、`test-case-design`、`cameltv-api-test`。
