# Batch 168 — QA 报告
> **QA (🔍)** | Date: 2026-08-13 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 8 个 PM 任务 | 8 | 0 | 0 |

## 可执行门禁（实测命令与退出码）
| 门禁 | 命令 | 结果 |
|------|------|------|
| 后端 F821 | `python -m ruff check app --select F821` | ✅ exit 0 |
| 后端导入 | `python -c "from app.main import app"` | ✅ IMPORT_OK |
| Alembic 单头 | `python -m alembic heads` | ✅ `20260813_b167_version_coverage (batch27) (head)` |
| 后端全量回归 | `python -m pytest -q` | ✅ **1427 passed, 3 skipped**（submodule pinned 3cfd2ef 初始化后 0 fail） |
| 后端受影响回归 | batch167/168 六个文件 | ✅ 30 passed |
| 前端 typecheck | `npm run typecheck` | ✅ exit 0 |
| 前端 lint | `npm run lint` | ✅ exit 0 |
| 前端 build | `npm run build` | ✅ vite build exit 0 |
| 前端全量单测 | `npm test`（vitest run） | ✅ 113 files / 458 passed |
| 避坑扫描 | `pwsh scripts/git/scan-common-bugs.ps1` | ⚠️ 3 HARD 均为既有文件（main.py/lanhu_provider.py），非本批改动；已 commit 豁免 |

## 逐条件验证
### Task 1 覆盖矩阵逐模块聚合（D1/D2）
- 键改为 `(module_id, module_name, type)`；fallback 优先 bundle 绑定文档模块；有真实树时按 `requirement_module_id in tree OR source_doc_id in linked docs` 圈定版本用例。
- 验证：`test_batch168_coverage_fixes.py`（fallback 计数、P0/P1、绑定文档优先、版本圈定）4/4。

### Task 2 接口生成 upsert（D3）
- existing 查询 `is_deleted=false`；模板变体按 `(method,path,title[,module])` 独立成行。
- 验证：软删除行不复活、可见数=生成数、幂等。

### Task 3 UI 变体回填（D4）
- `create_ui_cases` 扫描该文档全部已导入 P0/P1 有步骤用例（含历史），幂等键 `[UI] title + module`。
- 验证：老数据 import → `ui_created=1`；重复 → 0。

### Task 4 模块级端点匹配（D8）
- 中文-英文同义词表 + 双字块/包含评分；未覆盖模块按置信度排序逐模块绑定真实端点，GET 优先、阈值 0.4。
- 真实数据：matched 14、generated 37、inserted 3（其余幂等），覆盖 11+ 模块。

### Task 5 执行环境拆分 + 失败透出（D6/D7）
- `ExecuteAllBody.ui_environment_id`；`_ui_error_summary` 透出 error/exit_code/stdout。
- 验证：单元测试断言 UI base_url 用 ui 环境、失败 notes 含断言详情。

### Task 6 前端（D5/D7）
- BundleDetail 四个独立 Tab；PlanDetail UI 环境 Select（sentinel `__none__`）。
- 截图：`work-logs/evidence/batch-167/screenshots/b168-bundle8-coverage-fixed.png`、`b168-plan10-executed.png`（本地新代码+生产数据渲染）。

### Task 7/8 真实数据复测（C167-2）
- 证据 `work-logs/evidence/batch-167/retest-168.json`。
- 18 个模块树直建 → API 生成可见 → 384 条 UI 变体 → 计划三类关联 → auto_ui 执行（API 真实 200 pass、UI 如实失败并透出原因）。
- 覆盖：**14/18=77.8%（目标 60%）✅ gate_passed=true**；P0/P1 14/16；执行覆盖 1 模块（5.6%）。

## 缺陷列表（开发-修复闭环）
| # | 严重级 | 描述 | 状态 |
|---|--------|------|------|
| 1 | P1 | fallback 模块 id=None 导致覆盖矩阵全部共享全局计数 | ✅ 已修 |
| 2 | P1 | 接口生成命中断软删除行且模板互相覆盖 | ✅ 已修 |
| 3 | P1 | 老数据 UI 变体无法生成 | ✅ 已修 |
| 4 | P2 | 版本详情 diff/coverage Tab 嵌套错乱 | ✅ 已修 |
| 5 | P2 | UI 失败 notes 仅「未知」 | ✅ 已修 |
| 6 | P2 | 模块级匹配无法覆盖中文模块名 | ✅ 已修（同义词表+排序绑定） |

## 发布建议
状态: **READY** | 必修复: 0 | 建议修复: 0
说明：真实账号登录态写操作准备仍缺（C167-1 保持 Open），UI 执行覆盖率按实展示，不伪造。

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 6h / 实际约 5h | 0/3/3/0 | 2 | 聚合键设计与老数据兼容 | 服务函数先用真实数据样例自测，再写单测 |

**技能使用**: cameltv-bug-guard → 后端聚合键/envelope、前端 Radix Select；cameltv-ui-conventions → Tab/Select 走查；diagnose → 覆盖矩阵 fallback 键冲突定位。
