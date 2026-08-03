# Batch 72 — PM Plan（最终优化与决策材料）

> **PM (🟨)** | Date: 2026-08-04

## 开发任务

### [ ] Task 1: C71-1 并发后真实耗时实测
**描述**: batch-72 后端（8039）上传 147 FP R1 文档 → 提取 → 分批并发生成；计时与 batch-69 串行 682s 对比登记。
**验收标准**: 实测耗时 + 下降率写入 QA；用例数与 batch-69（331）一致性说明。
**涉及文件**: `work-logs/batch-72-*-qa-report.md`

### [ ] Task 2: C71-2 模板字段级编辑
**描述**: TemplateManager 编辑对话框标题/描述已可编辑；补充行内快捷重命名（标题 input）或确认现有编辑覆盖即可。
**验收标准**: 编辑标题/描述保存后列表更新；Vitest/E2E。
**涉及文件**: `frontend/src/pages/report/TemplateManager.tsx`

### [ ] Task 3: C70-1 Playground 评估
**描述**: 核对 `playground.py`（compile/execute）与 C22-C2/C3 runner 证据（batch-66 执行器登记）；评估是否开放前端入口。
**验收标准**: 结论写入设计/QA；开放则补入口，否则维持 API-only 并文档化。
**涉及文件**: `backend/app/api/v1/playground.py`、`docs/能力产品化决策清单.md`

### [ ] Task 4: C68-4 发布决策材料
**描述**: `docs/production-delivery/生产环境交付清单.md` 增加决策材料：选项（保持 vercel.app / 自定义域名 + Cloudflare / 仅内网）、
影响、推荐与待用户确认项。
**验收标准**: 材料完整；C-CONDITIONS C68-4 备注更新。
**涉及文件**: `docs/production-delivery/生产环境交付清单.md`、`C-CONDITIONS.md`

### [ ] Task 5: QA + Leader + PR
**描述**: 六部门工件 + 看板；走 push 授权 → Draft PR → checks → 二次确认 → 合入。

## 质量要求
- [ ] ruff F821、受影响 pytest、前端 lint/typecheck/build、受影响 Vitest 全绿
- [ ] 每 PASS 带证据；决策材料不含臆测
