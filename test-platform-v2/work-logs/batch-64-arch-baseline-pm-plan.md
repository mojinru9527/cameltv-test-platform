# Batch 64 — PM Plan（架构解析与仓库拆分基线）

> **PM (🟨)** | Date: 2026-08-02

## 规格摘要

**原始需求**: PRD §1（三仓分离 / V1 退役门禁 / 生产交付清单 / 资深架构师解析）。本批为**零业务代码改动**的架构基线批次：交付物 = 分析报告 + 决策 ADR + 生产交付清单 + 机器可校验仓库边界 + 六部门工件。
**目标时间**: 单批次（2026-08-02），无 UI 排期。

## 开发任务

### [x] Task 1: 现状盘点与 V1→V2 覆盖矩阵
**描述**: 盘点 V1（11 件 CLI 工具 + server 路由 + web-ui）与 V2（32 路由域 / 24 页面域 / 服务层）的逐项对应关系，产出覆盖矩阵与处置判定（已覆盖/部分/缺失）。
**验收标准**: 矩阵覆盖全部 11 件工具与 10 组 server 路由；每行给出 V2 等价物路径或「缺失」结论；结论写入架构解析报告 §4。
**涉及文件**: `test-platform/cli/tp.py`、`test-platform/tools/*`、`test-platform-v2/backend/app/api/v1/*`、`test-platform-v2/backend/app/services/*`、`docs/repo-map.md`
**参考**: PRD §1/§2、`test-platform-v2/CLAUDE.md`（模块成熟度表）

### [x] Task 2: 架构解析报告
**描述**: 以资深架构师视角撰写现状评估（优势/风险/债务）、三仓目标架构、拆分阶段路线、运维平台衔接、生产交付框架。
**验收标准**: 报告含可核对的证据锚点（文件:行号）；三仓拆分路线含 P0–P4 阶段与退出条件；风险部分引用真实证据。
**涉及文件**: 新增 `docs/architecture/batch-64-architecture-analysis.md`
**参考**: PRD §4、ADR-0003/0015、`测试平台-前后端分离重构方案.md`

### [x] Task 3: ADR-0016 三仓分离决策
**描述**: 新增 ADR 记录「前端/后端/运维平台三仓分离」目标架构决策（取代目录级分离的 ADR-0003 作为交付目标），并同步更新 ADR README 与 repo-map。
**验收标准**: ADR 包含背景/决策/后果/弃选方案/分阶段执行；README 索引表与 repo-map ADR 清单新增 0016。
**涉及文件**: 新增 `docs/adr/0016-three-repository-separation.md`；更新 `docs/adr/README.md`、`docs/repo-map.md`
**参考**: `docs/adr/template.md`、ADR-0003、ADR-0015

### [x] Task 4: 生产交付清单
**描述**: 整理业务平台生产/测试域名、测试平台自身生产基础设施（Vercel/Supabase）、服务器/数据库/中间件地址、账号与凭证槽位、网络访问条件，输出单份客户交付清单（不含明文 Secret）。
**验收标准**: 清单条目与 `docs/测试平台全功能验收文档-环境链接与账号汇总.md`、`test-platform/config/environments/prod.yaml`、`test-platform-v2/deploy/` 交叉核对一致；无明文密码/Token；标注待补项。
**涉及文件**: 新增 `docs/production-delivery/生产环境交付清单.md`
**参考**: PRD §4 用户故事 3、ADR-0015 §4、Batch 58 文档

### [x] Task 5: 仓库边界事实源与校验器
**描述**: 新增 `repo-boundaries.json`（最长前缀归属，覆盖全部已跟踪路径）与 `scripts/repo-split/validate_repo_boundaries.py`（纯标准库，`--check` / `--selftest`），把「拆分后路径属于哪个仓库」变成机器可校验约束。
**验收标准**: `--selftest` 通过；`--check` 对当前仓库退出码 0 且输出覆盖统计；新增未声明路径/重复归属/无效 schema 均非零退出。
**涉及文件**: 新增 `repo-boundaries.json`、`scripts/repo-split/validate_repo_boundaries.py`、`scripts/repo-split/README.md`
**参考**: PRD §4 用户故事 2、`docs/能力产品化决策清单.md`

### [x] Task 6: 六部门工件与 C 条件落库
**描述**: 补齐 PRD/PM/Design/Dev 看板/QA/Leader 六份工件；Leader 判决后将 C64 条件（及 Batch 63 未落库的 C63 条件）追加到 `C-CONDITIONS.md`。
**验收标准**: 六份工件齐全且互相引用；C-CONDITIONS.md 新增 C63-1~3 与 C64-1~4 条目；`git diff --check` 通过。
**涉及文件**: `test-platform-v2/work-logs/batch-64-arch-baseline-*.md`、`test-platform-v2/work-logs/kanbans/DEV-batch-64-arch-baseline.md`、`C-CONDITIONS.md`
**参考**: SKILL.md 六部门模板、DEPARTMENTS.md

## 质量要求

- [x] 纯文档+脚本批次：无 FastAPI/React 业务代码改动（0 功能回归）
- [x] 校验脚本纯标准库（无新依赖），Python 3.10+ 兼容
- [x] 所有文档遵循 `docs/document-standards.md` 元数据约定
- [x] 无明文 Secret 进入仓库；生产地址以槽位/引用名表达
- [x] 文档新鲜度：ADR/CLAUDE 引用同步更新
