# Batch 100 — PRD（V1 整体退役：web-ui/server/cli 覆盖矩阵移除）

> **Product (🟦)** | Date: 2026-08-06 | Status: Review

```markdown
mode: full
豁免理由: 无（V1 整体移除，重构/配置变更，走完整六部门流水线）。
非目标: 不迁移 V1 的旧数据（历史 DB 快照保持 DEFERRED）；不移除 CI 回归所需的 Playwright API 测试资产
（迁移保留）；不改动 V2 业务代码；业务 DB/Redis 地址以交付清单为准（不依赖 V1 config）。
```

## 1. 问题陈述

Batch 98 已删除 11 个 V1 工具并迁移 CI；Batch 99 完成真机验收。V1 剩余部分（web-ui/server/cli/core/config/
docker/platform_tests/脚本/文档）已无生产消费者，继续保留制造维护噪音与文档误导。按用户规则
「V2 能覆盖则移除，用不上则移除」执行 V1 整体退役：

- `web-ui`（React+AntD）→ V2 前端已覆盖 → **移除**
- `server`（FastAPI 旧后端）→ V2 后端已覆盖 → **移除**
- `cli`/`core`/`config` → CI 已迁移、无消费者 → **移除**（业务地址已在交付清单登记）
- `tests/api-testing/generated` + `specs/cameltv-openapi.yaml` → CI 每日回归依赖 → **迁移保留**到根 `tests/`

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| V1 目录 | 87 个 tracked 文件 | 移除 77 个；10 个测试资产迁移到 `tests/api-testing/` |
| CI 回归 | 引用 `test-platform/tests/api-testing/generated` | 指向 `tests/api-testing/generated`，workflow 可用 |
| 可执行引用 | 4 处 `test-platform/`（非 v2） | 0 处（`rg -P 'test-platform/(?!v2)'` 非文档 0 命中） |
| 仓库边界 | deprecated-v1 存在 | 移除 deprecated-v1；boundary PASS |
| 文档 | CLAUDE/COMMANDS/repo-map 等含 v1 章节 | 标记退役或移除；关键文档更新 |
| C64-1 | V1 整体移除待覆盖矩阵 | 关闭（web-ui/server 由 V2 覆盖，CLI 无消费者，测试资产迁移） |

## 3. 用户故事 + 验收标准

- As a **维护者**, I want 移除无消费者的 V1 代码，so that 仓库瘦身、文档不再误导。
- As a **CI 负责人**, I want 回归测试资产保留且路径更新，so that 每日 API 回归与生产冒烟不中断。

Given V1 移除且测试资产迁移，When 全仓执行非文档引用扫描与仓库边界校验，Then 0 命中且 PASS。

## 4. 技术考量

- 迁移优先：先 `git mv` 测试资产到 `tests/api-testing/`，再更新 CI 路径，最后删除 V1 其余部分（先迁后删）。
- 本地 `test-platform/.env`（gitignored 业务凭据）删除前复制到仓库外安全位置，防丢失。
- 边界：`repo-boundaries.json` 移除 `deprecated-v1`；`validate_repo_boundaries.py` 文案同步。
- 文档：CLAUDE.md / COMMANDS.md / repo-map.md / 规划文档 / 交付清单 / 技能文档 更新为退役状态。
