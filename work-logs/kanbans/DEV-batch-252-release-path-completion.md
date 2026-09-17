# 🗂️ Dev 部门项目看板 — batch-252-release-path-completion

> **用途**：追踪多批次开发的进度节点，防止上下文丢失。每次 Dev 部门启动时**必须先读取本看板**。

---

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | Batch 252 — 发布链路收口（C248-8 / C249-5 / C249-6 / C249-7） |
| **关联 PM 计划** | [batch-252-release-path-completion-pm-plan.md](../batch-252-release-path-completion-pm-plan.md) |
| **关联 PRD** | [batch-252-release-path-completion-prd-summary.md](../batch-252-release-path-completion-prd-summary.md) |
| **总预估工时** | 3h |
| **已用批次** | 1 批 |
| **看板创建** | 2026-09-17 |
| **最后更新** | 2026-09-17 |

---

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | C248-8 Node 供给失败即中断 | ✅ | ✅ | ✅ | ✅ | ⏳ | runner 真实构建成功（node v22.23.2 / npm 10.9.8） |
| 2 | C249-7 控制面 COPY 通配 + 守卫 | ✅ | ✅ | ✅ | ✅ | ⏳ | 守卫含负向用例（报 migrations.py） |
| 3 | C249-5 沿用镜像核对 | ✅ | ✅ | ✅ | ✅ | ⏳ | 生产双向验证 OK(0) / BLOCK(1) |
| 4 | C249-6 技能回写 | ✅ | ✅ | ✅ | ✅ | ⏳ | SKILL.md + DEPARTMENTS.md + CHANGELOG |
| 5 | 批次工件 + C 条件关闭 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：待用户一次的推送确认 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

---

## 📍 当前位置

```
Batch 252 — 发布链路收口
├── ✅ 已完成: 4 条条件全部修复（4 个切片提交 883abd2a / bbea56ba / 1f030809 / c3dd4d22）
├── ✅ 已完成: 证据（runner 真实构建、镜像内核验、核对脚本双向、DryRun 回归、契约/守卫测试）
├── 🔄 进行中: 批次工件 + C-CONDITIONS 关闭 → 提交
└── ⏳ 下一步: 用户确认后推送/PR/合入；可选再做一次端到端 release.ps1 发布验收
```

---

## 📜 批次记录

### Batch 252 — 发布链路收口（2026-09-17）
- **产出**：`test-platform-v2/backend/Dockerfile`（Node 供给硬化）、`tests/test_image_split_cache_contract.py`（+1 契约）、
  `deploy/release-console/{Dockerfile,image_contract.py,README.md}`、`scripts/ops/{release.ps1,verify-reused-image.ps1}`、
  `.claude/skills/cameltv-agent-team/{SKILL.md,DEPARTMENTS.md,CHANGELOG.md}`
- **测试**：控制面 66 passed / ruff 全绿；后端图形契约 6 passed
- **审批**：待用户推送确认
- **耗时**：约 2.5h

---

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 生产磁盘余量长期紧张（8.7G / 门槛 8G） | P2 | 每次发布都要先清上一版 tar；沿用镜像核对能降低风险但不能解决容量 | 运维（后续批次） | 2026-09-17 |
| 本机 BuildKit 默认网络取 `.deb` 偶发失败 | P3 | 已用 `--network=host` 固化；CI/其它机器需各自确认 | 平台（观察） | 2026-09-17 |

---

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [batch-252-release-path-completion-prd-summary.md](../batch-252-release-path-completion-prd-summary.md) | ✅ |
| PM 计划 | [batch-252-release-path-completion-pm-plan.md](../batch-252-release-path-completion-pm-plan.md) | ✅ |
| 设计规范 | [batch-252-release-path-completion-design-spec.md](../batch-252-release-path-completion-design-spec.md) | ✅ |
| QA 报告 | [batch-252-release-path-completion-qa-report.md](../batch-252-release-path-completion-qa-report.md) | ✅ |
| Leader 判决 | [batch-252-release-path-completion-leader-verdict.md](../batch-252-release-path-completion-leader-verdict.md) | ✅ |
