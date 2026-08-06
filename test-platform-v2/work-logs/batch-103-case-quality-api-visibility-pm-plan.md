# Batch 103 — PM Plan（用例质量与接口可视优化）

> **PM (🟨)** | Date: 2026-08-06 | Status: Review

## 切片拆解

| # | 任务 | 描述 | 验收标准 | 涉及文件 |
|---|------|------|---------|---------|
| 1 | 批次工件 + 需求登记 | PRD/PM/Design/看板 + C-CONDITIONS（C103-1/2）+ backlog Epic | 工件齐全；audit 0 硬错 | `test-platform-v2/work-logs/batch-103-*`、`C-CONDITIONS.md`、`docs/改进任务backlog.md` |
| 2 | AI 生成规范对齐 | `ai_service` 提示词注入用例规范（等价类/边界值/场景法/错误推测 + 正负向） | 生成产物字段完整；单测覆盖提示词关键约束 | `test-platform-v2/backend/app/services/ai_service.py` + 测试 |
| 3 | 功能用例覆盖度补强 | 用户端 92 FP → ≥184 条（≥2 条/FP）；运营后台同步补强；补生成重导入生产 | 用例库计数达标；覆盖缺口报告 | 生产 API/DB、`scripts/sports/` |
| 4 | 接口用例可视 | TestCase/AIGeneratedCase 增加请求参数+断言；执行结果回填；前端详情渲染 | 接口用例详情可见 参数/断言/结果 | backend schema + frontend 用例详情 |
| 5 | QA + Leader + 一次总确认 | 门禁/证据/判决；push → Draft PR → checks → 合入 | 全绿；PR 合入 main | `test-platform-v2/work-logs/batch-103-*` |

## 依赖与顺序

1 → 2 → 3 → 4 → 5。覆盖度补强依赖规范对齐（Slice 2）完成。

## 范围外

新功能模块梳理、Test5 内网、生产账号、性能优化（C99-1）、iOS 真机（CP-C2/C84-1）。
