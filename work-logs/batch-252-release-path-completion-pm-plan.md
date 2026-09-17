# Batch 252 — PM 计划（发布链路收口）

> **🟨 PM** | Date: 2026-09-17 | 关联 PRD：[batch-252-release-path-completion-prd-summary.md](batch-252-release-path-completion-prd-summary.md)

| # | 任务（30–60 min 粒度） | 验收标准 | 涉及文件 | 参考 |
|---|------------------------|---------|---------|------|
| T1 | 修 runner 的 Node 安装层：setup 脚本先落盘再执行 + 断言 node 22 / npm | 契约测试通过；真实构建日志出现 `node v22… / npm …` | `test-platform-v2/backend/Dockerfile`；`tests/test_image_split_cache_contract.py` | PRD US-1 / M1·M2 |
| T2 | runner 真实构建验收（`--target runner`） | 构建成功且产出镜像；失败时保留完整日志 | 无（验收动作） | PRD M1 |
| T3 | 沿用镜像核对：纯函数 + 单元测试 | `parse_runner_endpoints` / `contract_diff` / `verify_image` 用例全绿（含真实源码解析） | `deploy/release-console/image_contract.py`；`tests/test_image_contract.py` | PRD US-2 / M3 |
| T4 | 一键核对脚本 + 生产双向验证 | runner 镜像 OK(0)、不合规镜像 BLOCK(1) | `scripts/ops/verify-reused-image.ps1` | PRD M3 |
| T5 | 控制面 Dockerfile 改通配 + import 图守卫测试 | 守卫测试在"显式列表回退"时报 `migrations.py` | `deploy/release-console/Dockerfile`；`tests/test_dockerfile_copy_guard.py` | PRD US-3 / M4 |
| T6 | 技能回写：SKILL.md + DEPARTMENTS.md + CHANGELOG | 两处动作描述存在；CHANGELOG 有一条含日期/批次/摘要/动因 | `.claude/skills/cameltv-agent-team/*` | PRD US-4 / M5 |
| T7 | 批次工件 + QA/Leader + C 条件关闭 | 6 件工件齐全；C248-8/C249-5/C249-6/C249-7 → Closed | `work-logs/**`；`C-CONDITIONS.md` | AGENTS.md §2.1.2 |

## 依赖与顺序

```
T1 → T2（先有修复才谈构建验收）
T3 → T4（先有纯函数才有脚本）
T5 / T6 可与 T1 并行，但提交按切片拆分
T7 最后（依赖 T2/T4 的证据）
```

## 不做（防范围蔓延）

- 不引入 `|| true` 之类的"容错"来让构建通过。
- 不顺手改 mirror / apt 源策略（属基础设施决策，不在本批）。
