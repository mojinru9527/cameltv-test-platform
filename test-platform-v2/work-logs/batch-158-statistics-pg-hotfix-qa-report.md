# Batch 158 — QA 报告（生产 500 热修）

> **QA (🔍)** | Date: 2026-08-12 | Verdict: PASS | Mode: light

## 门禁
| 项 | 结果 |
|----|------|
| ruff F821 | ✅ 0 |
| 受影响 pytest | ✅ 10 passed（test_batch158_statistics_pg ×2 + test_batch149_statistics + test_coverage_report） |
| 生产只读复验（修复后代码） | ✅ project 1/7 stats/coverage/dashboard 全部 OK（修复前 3×2 全 ERROR） |
| 调试/凭据残留 | ✅ 无（诊断脚本不落库、不打印密钥） |

## 根因与修复
- 根因：`statistics_service._execution_filter` else 分支裸标量子查询作 WHERE（Batch 149 引入，PG 严格类型报错，SQLite 不报）。
- 修复：补 `IN (...)` 包装。
- 回归测试：PG dialect 编译断言（修复前该断言会失败）。

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 实际约 1.5h | 0/1/0/0 | 0 | 方言差异（SQLite 宽松掩盖 PG 报错） | 新查询需补 PG dialect 编译断言 + 上线前对生产库只读复验 |
