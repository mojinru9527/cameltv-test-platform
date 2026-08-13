# Batch 167 — QA 报告（版本级三类型覆盖主链路 Phase 0–3）
> **QA (🔍)** | Date: 2026-08-13 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 7 个 PM 任务 | 7 | 0 | 0 |

## 可执行门禁（实测命令与退出码）
| 门禁 | 命令 | 结果 |
|------|------|------|
| 后端 F821 | `python -m ruff check app --select F821` | ✅ All checks passed（exit 0） |
| 后端导入 | `python -c "from app.main import app"` | ✅ import ok（exit 0） |
| Alembic 单头 | `python -m alembic heads` | ✅ `20260813_b167_version_coverage (head)` |
| 后端全量回归 | `python -m pytest -q` | ✅ **1420 passed, 3 skipped**（exit 0，含新增 20 个 batch167 用例） |
| 前端 typecheck | `npm run typecheck` | ✅ exit 0 |
| 前端 build | `npm run build` | ✅ vite build 8.22s |
| 前端全量单测 | `npm test`（vitest run） | ✅ **113 files / 458 tests passed** |

## 逐条件验证
### Task 1 Schema 迁移
- 迁移含三张表加列，全部幂等守卫（表不存在跳过）；旧库 stamp 场景回归通过。
- 验证：`test_batch48_requirement_migration`、`test_organization_migration`、`test_project_invite` 全绿。

### Task 2 覆盖矩阵（Phase 0）
- 新文件 `services/version_coverage_service.py` + `GET /release-bundles/{id}/coverage`。
- 验证：`test_batch167_version_coverage.py` 4/4：三类型覆盖、执行覆盖、空模块树回退、envelope 60% 门禁。

### Task 3 需求源适配 + 完整提取（Phase 1）
- `requirement_source_service` URL 分类/超时错误分类/HTML→文本；PingCode/Confluence 缺 token fail closed。
- `ai_service` 分块提取 + 合并去重；`extraction_meta` 透出 mode/chunks/truncated/fallback。
- 验证：`test_batch167_requirement_source.py` 9/9（含 source_url 上传、质量端点、分块合并单测）。

### Task 4 接口真实绑定（Phase 2）
- `POST /requirements/{id}/generate-api-from-endpoints`：integration FP 匹配已导入端点，确定性生成 + requirement_module_id 回填，幂等。
- 验证：`test_batch167_api_binding.py` 3/3（生成、无端点 fail closed、envelope）。

### Task 5 UI 变体 + 计划三类关联（Phase 3a）
- `import_cases(create_ui_cases=True)` 为 P0/P1 有步骤功能用例生成 UI 变体并入计划；默认 False 保持旧契约精确相等。
- 验证：`test_batch167_ui_variants.py` 3/3。

### Task 6 auto_ui 执行（Phase 3b）
- `execute_all_cases(auto_ui=True)` manual P0/P1 有步骤自动转 UI；LLM 优先编译、规则引擎兜底；执行后回写 UI 任务；无步骤 skip。
- 验证：`test_batch167_auto_ui.py` 5/5（转换、P2 skip、关闭 skip、环境 base_url、编译回退）。

### Task 7 前端接入
- 版本详情：覆盖矩阵 tab + 接入配置五字段 + 导入需求；AiResultModal：真实接口生成按钮；ExtractionModal：提取质量徽标；PlanDetail：auto_ui 开关。
- 验证：typecheck/build 全绿；受影响组件测试通过；全量 vitest 458/458（更新 2 个旧契约断言以反映显式 `create_ui_cases` 字段）。

## 缺陷列表（开发-修复闭环记录）
| # | 严重级 | 描述 | 状态 |
|---|--------|------|------|
| 1 | P1 | 迁移在旧库 stamp 场景对不存在表执行 ALTER | ✅ 已修：迁移加表存在守卫 |
| 2 | P1 | ReleaseBundle 模型接入字段缺失导致 CRUD 500 | ✅ 已修：模型补齐字段 |
| 3 | P1 | execute-all 的 auto_ui 参数误传 auto-execute 路由 | ✅ 已修：移除重复透传 |
| 4 | P2 | import 返回新增 ui_created 破坏旧契约精确相等 | ✅ 已修：仅在 >0 时返回，schema 不默认注入 |
| 5 | P2 | api_headers 未序列化导致 sqlite 绑定失败 | ✅ 已修：json.dumps |
| 6 | P2 | 前端模板字符串被脚本插值破坏 | ✅ 已修：还原模板字面量 |

## 发布建议
状态: **READY** | 必修复: 0 | 建议修复: 0
说明：真实账号/登录态与写操作数据准备依赖外部输入，未在本批伪造；60% 达标需真实版本数据后复测（C167-2）。

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 8h / 实际约 6h | 0/3/3/0 | 3 | 技术债（PowerShell 批量文本补丁静默失败 + 旧契约兼容） | 修改多文件/多行代码优先用 Python 脚本整段重写而非 PS 字符串替换，改后立即 ruff/typecheck 验证 |

**技能使用**: cameltv-bug-guard → 迁移守卫、envelope 契约、StaticPool；cameltv-ui-conventions → 覆盖面板/徽标/加载空态。
