# Batch 208 — AI 链 C 条件 — QA 报告
> **QA (🔍)** | Date: 2026-09-02 | Verdict: READY（6 项环境/基线与本批无关，同 Batch 207 缺陷表）

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 | 说明 |
|--------|------|------|------|------|
| 全量 backend pytest | 2382 | 6 | 0 | 6 项环境/基线（lanhu-mcp 子模块未初始化、notification 夹具缺失） |
| 新增/受影响单测 | 151 | 0 | 0 | 见下 |

## 可执行门禁
- `ruff check app --select F821` → exit 0
- `python -m pytest -q`（backend 全量）→ 2382 passed / 6 failed / 9 skipped / 1 xfailed（9m15s）；与 Batch 207 基线失败集合完全一致，无新增
- Alembic 单头（v39 迁移测试通过）；本批无迁移/无 API 变更（route inventory 通过）
- 受影响定向集 136+15 passed（ai_client / llm_sync / llm_json_client / ai_service / legacy_cutover / v38 / v39 / reality / module_extractor）

## 逐条件验证
| 条件 | 结果 | 证据 |
|------|------|------|
| C5 共享 client 四栈收敛 | PASS | test_ai_client 8 + 收敛相关 70+（ai_service/legacy/knowledge/llm_sync）|
| C6 门控统一 is_configured | PASS | test_ai_client（三分支）+ ADR-0023 |
| C3 PromptEvaluation run_golden | PASS | test_batch208_golden_runner 3（trusted/BLOCKED-未配置/BLOCKED-调用失败）|
| C4 store loader | PASS | test_batch208_snapshot_loader 5 + source_diff_registry 保持 |
| C7 module_extractor AI 边界 | PASS | test_module_extractor_ai_boundary 4 |

## 缺陷列表
| # | 严重级 | 描述 | 状态 |
|----|--------|------|------|
| 1-3 | P2(环境) | lanhu-mcp 子模块未初始化（test_lanhu_provider/login_hook/deploy_compose） | 基线/环境 |
| 4 | P2(基线) | notification_channel 表夹具缺失（test_batch148_p0_fixes） | 测试夹具基线 |

## 发布建议
状态: READY。必修复: 0。建议修复（另批次）: lanhu-mcp 子模块初始化、notification 夹具。

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~10h vs 多会话推进 | 0/0/0/0（无本批缺陷） | 1（golden runner 失败路径先写 trusted） | 设计未先想失败语义 | runner 类先写失败路径测试再实现 |

**技能使用**: cameltv-bug-guard；karpathy-guidelines。
