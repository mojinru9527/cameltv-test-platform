# Batch 117 — PM Plan

> **PM (🟨)** | Date: 2026-08-07

## 开发任务

### [ ] Task 1: 覆盖缺口报告（C116-3）
**描述**: `coverage_report.py`：输入 extraction（modules→function_points）与生成结果（functional_cases 含 module/标题），
输出 模块×功能点 覆盖矩阵 + 缺口清单；generate-async _job 结果附 coverage_report。
**验收标准**: 单测（全覆盖/有缺口/空 extraction）。
**涉及文件**: - `backend/app/services/coverage_report.py`（新增）
            - `backend/app/api/v1/requirement.py`（async _job 附报告）

### [ ] Task 2: 前端 async 轮询（C116-2）
**描述**: api/requirement.ts 增 extract/generate async 封装 + fetchAiTask；
index.tsx/ReviewPage.tsx 生成/提取改 async+poll（2s，AbortController 清理）；结果落库沿用现有。
**验收标准**: typecheck/build + 相关 vitest 通过。
**涉及文件**: - `frontend/src/api/requirement.ts`
            - `frontend/src/pages/requirement/index.tsx`、`ReviewPage.tsx`

## 质量要求

- [ ] 前端 useEffect/轮询有 cleanup（AbortController/cancelled）
- [ ] 后端受影响模块 pytest + ruff F821
- [ ] scan-common-bugs HARD=0