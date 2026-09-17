# Batch 250 — Leader Verdict（发布护栏）

> **🎯 Leader** | Date: 2026-09-17 | 抽检：PRD / 代码 / QA / 证据 / 流程回写

## 1. 抽检结论

| 部门 | 工件 | 抽检要点 | 结论 |
|---|---|---|---|
| 🟦 Product | `batch-250-release-guardrails-prd-summary.md` | 轻量批次判定有依据（`mode: light` + 豁免理由）；非目标明确列出 C249-5/6/7 不在本批；三条用户故事均为既有行为加固 | 通过 |
| 🟨 PM | 同文件 §5 + 看板 | 3 个切片各 30–60 分钟粒度，无 PRD 外需求 | 通过 |
| 🎨 Design | N/A | 本批无 UI/接口契约变化，控制面 `static/index.html` 未改动 | 通过（豁免理由已记录） |
| 💻 Dev | 2 个 commit（`2580c2ea`、`f186181d`） | 开关/清理与可观测性分切片提交；未夹带 `test-platform-v2` 改动 | 通过 |
| 🔍 QA | `batch-250-release-guardrails-qa-report.md` | 51 passed + 全目录 lint + DryRun 零副作用逐项核对；P2 缺陷 2 个均已修 | 通过 |

## 2. 判决

**APPROVED**

依据：①用户一次总确认已取得，PR #467 经 required checks 全绿后 squash 合入 main（`82aa9f4f`）；
②C249-1/-3 有实测证据（DryRun 零副作用、控制面全目录 lint 全绿）；
③C249-4 有失败路径单测 + **生产发布验收**（`release-20260917-0006` → `PRODUCTION_VERIFIED`，
远端顺序为迁移→校验→停旧→起新，迁移校验命令实测 rc=0 并打印 `CAMELTV_MIGRATION target=… actual=…`）。

**附条件**：验收暴露 1 个 P2 缺口（成功路径的正向证据被 4000 字符日志窗口截断）→ 登记 **C250-1**；
该缺口不影响 C249-4 的目标场景（迁移失败时状态行必在尾部，可被解析并落进事件 reason）。

## 3. 本批关闭 / 保持开放的条件

| ID | 内容 | 处置 |
|----|------|------|
| C249-1 | `release.ps1 -DryRun` | ✅ 本批关闭（DryRun 零副作用实测 + PR #467 合入） |
| C249-3 | 控制面测试 E402 清理 | ✅ 本批关闭（`ruff check .` 全绿 + PR #467 合入） |
| C249-4 | 迁移失败可观测性 | ✅ 本批关闭（失败路径单测 + M5 生产验收通过） |
| **C250-1** | **迁移状态行的正向证据被 `ExecutorResult.logs` 的 4000 字符尾部窗口截断**（成功发布时事件 reason 只剩 `publish succeeded`）；建议从完整远端输出解析并单独随事件记录 | **新增 Open（P2）** |
| C249-5 | 沿用旧镜像前核对 `RUNNER_ENDPOINTS`；补丁镜像必须含 `alembic/versions` | 保持 Open（本批验收发布将顺带观察，不单独关闭） |
| C249-6 | SKILL.md/DEPARTMENTS.md 补「合并前先比对两侧同名文件规模」 | 保持 Open（属流程文档回写） |
| C249-7 | 控制面 Dockerfile 显式 COPY → `COPY *.py ./` 或守卫测试 | 保持 Open |

> 本批新增 1 个 C 条件（C250-1），已同步追加到 `C-CONDITIONS.md`；C249-5/-6/-7 保持 Open。

## 4. 合入前置（已完成）

1. ✅ 用户一次总确认已取得（推送 + Draft PR + required checks 通过后合入）。
2. ✅ `audit-ai-pr.ps1 -RequireSuccessfulChecks` 全绿（ChecksRequired=True、MergeState=CLEAN，PR #467）。
3. ✅ 合入后已完成：控制面镜像重建部署 → 真实发布验收（M5）→ 证据落盘 → C249-1/-3/-4 置 Closed。

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 发布路径无演练开关，QA 实测函数即触发真实构建（Batch 249 事故） | 已修复：`-DryRun` 只算 manifest/digest 并显式声明"未构建/未登记/未上传/未发布" | `scripts/ops/release.ps1` + `C249-1`（本批关闭） |
| 迁移校验失败时远程零输出，控制面无法判读 | 已修复：校验步骤打印 `CAMELTV_MIGRATION target/actual`，事件 reason 落差异 | `deploy/release-console/{migrations,app}.py` + `C249-4` |
| 控制面 Dockerfile 显式列举 COPY 曾漏 `migrations.py`（"恢复平面"会起不来） | 已由 PR #464 补；系统性防复发（改 `COPY *.py ./` 或守卫测试）仍待做 | `C249-7`（保持 Open） |
| 沿用旧镜像 retag 是本仓库常规做法，但缺"转发面/版本目录已同步"的核对清单 | 本批不处理，验收发布时记录观察 | `C249-5`（保持 Open） |
| 把诊断写进事件时依赖"日志尾部窗口"：成功发布的长输出会把早期状态行挤出 4000 字符窗口 | 生产验收暴露 → 开条件：从**完整远端输出**解析迁移状态并单独记录 | `C250-1`（新增 Open） |
| `--target runner` 本机构建再次 `exit 127`（C248-8 复现），本次被迫复用已验证 runner 镜像 | 维持既有绕过方式并记录；不扩大本批范围 | `C248-8`（保持 Open） |

## 6. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h / 实际约 5h（含发布验收与两次 runner 构建尝试） | 0/0/3/2 | 2 | 工具链 + 流程 | ①发布路径的新命令先用 `-DryRun`/单测锁住"命令构造 + 空跑"再上生产；②凡是要进事件/返回体的诊断，必须取自**完整输出**，不能依赖日志尾部窗口 |
