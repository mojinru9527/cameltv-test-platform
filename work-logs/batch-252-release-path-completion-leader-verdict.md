# Batch 252 — Leader Verdict（发布链路收口）

> **🎯 Leader** | Date: 2026-09-17 | 抽检：PRD / PM / Design / Dev / QA / 流程回写

## 1. 抽检结论

| 部门 | 工件 | 抽检要点 | 结论 |
|---|---|---|---|
| 🟦 Product | `batch-252-…-prd-summary.md` | 完整批次判定成立（触及后端 Dockerfile 构建配置）；4 条条件各有 M1–M5 可判定指标；非目标写明不追其它历史 Open 条件 | 通过 |
| 🟨 PM | `batch-252-…-pm-plan.md` | 7 个 30–60 分钟任务 + 依赖顺序；无 PRD 外需求 | 通过 |
| 🎨 Design | `batch-252-…-design-spec.md` | 给出了可落地的四份契约（Node 供给 / 沿用镜像核对接口 / 控制面 COPY / 技能回写形态），与代码一一对应 | 通过 |
| 💻 Dev | 4 个切片提交（`883abd2a`/`bbea56ba`/`1f030809`/`c3dd4d22`） | 按条件分片；未夹带平台业务代码改动 | 通过 |
| 🔍 QA | `batch-252-…-qa-report.md` | runner 真实构建成功 + 镜像内核验 + 核对脚本双向验证 + 负向对照；含根因与复盘卡 | 通过 |

## 2. 判决

**APPROVED（待用户推送确认 + required checks 全绿）**

依据：C248-8 不再是"绕过"而是"能构建"——`--target runner` 真实构建成功（`node v22.23.2 / npm 10.9.8`），
且契约测试锁死"装不上就立刻失败"；C249-5 有可执行核对并在生产双向验证（OK/0 vs BLOCK/1）；
C249-7 有含负向用例的 import 图守卫；C249-6 三份技能文件齐备且 CHANGELOG 同批。

## 3. 条件处置

| ID | 内容 | 处置 |
|----|------|------|
| C248-8 | `--target runner` 本机不可构建 | ✅ **本批关闭**（失败即中断 + node/npm 断言 + 真实构建验收 + buildx `--network=host`） |
| C249-5 | 沿用旧镜像前核对 `RUNNER_ENDPOINTS` / `alembic/versions` | ✅ **本批关闭**（核对脚本 + README + 生产双向验证） |
| C249-6 | SKILL.md/DEPARTMENTS.md 补"合并前先比对两侧同名文件规模" | ✅ **本批关闭**（技能回写 + CHANGELOG） |
| C249-7 | 控制面 Dockerfile 显式 COPY | ✅ **本批关闭**（通配 + import 图守卫） |

> 本批**未新增** C 条件（BuildKit 网络偶发失败已随 C248-8 一并固化处理，未另开条件）。

## 4. 合入前置

1. 用户逐次确认：推送 `feature/batch-252-release-path-completion` + 创建 Draft PR + required checks 通过后合入 main。
2. `audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks` 全绿。
3. 合入后：清理任务 worktree；可选——用一次真实 `release.ps1 -Publish` 验证"发布不再需要手工组装镜像"。

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| shell 用 `curl … \| bash -` 装工具链会**吞掉下载失败**，退化成"有 node 没 npm"，且被缓存长期掩盖 | Dockerfile 改为"落盘再执行 + 同层断言"；契约测试禁止回退 | `test-platform-v2/backend/Dockerfile` + `tests/test_image_split_cache_contract.py` + C248-8（本批关闭） |
| 沿用旧镜像缺核对手段，隐患只能靠人记得 | 固化为纯函数 + 一键脚本 + README 清单 | `deploy/release-console/image_contract.py`、`scripts/ops/verify-reused-image.ps1` + C249-5（本批关闭） |
| 控制面 Dockerfile 显式列举 COPY，新增模块会漏拷（曾导致恢复平面起不来） | 改通配 + 按 import 图的守卫测试（含负向用例） | `deploy/release-console/Dockerfile` + `tests/test_dockerfile_copy_guard.py` + C249-7（本批关闭） |
| Batch 249 曾在已被 main 取代的分支上白做一轮，经验未回写 | 写入技能与部门文件 + CHANGELOG | `.claude/skills/cameltv-agent-team/{SKILL.md,DEPARTMENTS.md,CHANGELOG.md}` + C249-6（本批关闭） |
| 本机 BuildKit 默认网络取个别 `.deb` 稳定失败（两次复现） | 发布脚本 buildx 固定 `--network=host` 并写明原因 | `scripts/ops/release.ps1` |

## 6. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h / 实际约 2.5h | 0/0/0/0 | 2 | 工具链 + 技术债 | ①管道装工具必须显式传播失败；②契约测试解析 Dockerfile 先剔除注释行；③发现"某层长期 CACHED"时要主动重建验证，缓存会掩盖缺陷 |
