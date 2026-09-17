---
title: "全量代码审计基线（两次对比）— 2026-09-18"
owner: "qa-team"
created: "2026-09-18"
status: "active"
tags: ["audit", "review", "baseline", "open-code-review", "archify", "recurring-issues"]
related:
  - ".claude/skills/cameltv-bug-guard/SKILL.md"
  - ".claude/skills/cameltv-agent-team/SKILL.md"
  - "docs/platform-refactor/01-platform-positioning-and-mainline.md"
---

# 全量代码审计基线（2026-09-18）

> **用途**：这是「跨批次常犯问题核对」规则的事实源。回答一个问题：
> **哪些问题在 98 个提交 / 15 个批次之后，仍然原样存在？**
>
> 两次审计口径一致：同一套工具、同一套规则、同一个范围（`test-platform-v2/backend` + `frontend`）。
> 唯一变量是代码版本。因此"两版都在"的条目可以判定为**流程性遗漏**，而不是某次实现的疏忽。

## 1. 审计对象与方法

| 项目 | 第一次 | 第二次 |
|------|--------|--------|
| 版本 | `10e69b36`（Batch 255 前的功能分支） | `96cd5b65`（main，Batch 255） |
| 工具 | `alibaba/open-code-review` v1.12.5 — **delegation 模式**（OCR 只做文件选择 + 规则解析，审查推理由宿主 agent 完成，不消耗 LLM 额度） | 同左 |
| 文件选择 | `ocr delegate preview --from <root> --to HEAD --format json` | 同上（5042 个文件 / 1970 可审 / 128.8 万新增行） |
| 规则解析 | `ocr delegate rule`（Python 规则组 + TS·React 规则组 + 依赖/部署规则组） | 同左 |
| 机械扫描 | `ruff`（F/E9/B/S/C4/ASYNC/RUF/SIM/PERF/PIE）、`tsc -b`、`eslint --max-warnings=0`、路由鉴权扫描（552 路由）、循环内 DB 访问扫描、useEffect cleanup 扫描 | 同左（633 路由） |

**未覆盖（诚实披露）**：两次都**没有**跑通全量 `pytest`（287 个测试文件）与全量 `vitest`——本机 16 GB 内存仅余约 2.4 GB，
pytest 在采集阶段 `MemoryError`、vitest worker 崩溃；单文件范围均通过（pytest 10/10、vitest 9/9）。
因此本基线**不覆盖测试质量与覆盖率**，只看代码本身。

## 2. 结论总览

| 类别 | 条目 | 说明 |
|------|------|------|
| ✅ 已修复 | 3 | Batch 243/其他批次确实修掉了 |
| ⚠️ 两版都在（流程性遗漏） | 8 | 本次固化进 `cameltv-bug-guard` |
| 🆕 新增观察 | 3 | 第二次才出现或位置新增 |

## 3. ✅ 已修复（进回归，不要回退）

| 编号 | 问题 | 第一次证据 | 修复证据 |
|------|------|-----------|---------|
| F-1 | Playground 任意代码执行只要求 `uitest:trigger` | `app/api/v1/playground.py` 用 `require_permission("uitest:trigger")` | 改为独立权限 `uitest:code_execute`（`app/seed.py:129` 定义，tester 默认角色**不含**），并有回归 `tests/test_playground_security.py`（无该权限 403） |
| F-2 | 仪表盘 N+1（按项目循环 + 7 天 × 项目重复查询） | `app/services/dashboard_service.py:195,237` | 改为预聚合字典后内存拼装（`dashboard_service.py:281-283`） |
| F-3 | 需求抓取超时分类依赖 except 顺序 | 同文件已有注释提示 | 保持正确（`except httpx.TimeoutException` 在 `HTTPError` 之前） |

## 4. ⚠️ 两版都在 — 已固化为 `cameltv-bug-guard` 铁律

| 编号 | 问题 | 证据（main@96cd5b6） | 风险 |
|------|------|----------------------|------|
| S1 | 用户可控 URL 出网无 SSRF 守卫 | `app/services/requirement_source_service.py:80-90` | 可打内网/`127.0.0.1`/云元数据，响应入库回读 = 数据外带 |
| S2 | SaaS 令牌按"域名含关键字"外发 | 同文件 `:71-75` + `:128,145` | `pingcode.attacker.tld` 直接收割企业 Token |
| S3 | `subprocess(shell=True)` + `{image}` 未加引号 | `app/services/lanhu_evidence/local_ocr_provider.py:62-74` | 路径含空格/元字符时命令变形或注入 |
| S4 | 本地对象存储路径未收敛到 base | `app/integrations/object_storage/local.py:24-26` | 一旦有用户可控文件名即任意路径写入 |
| S5 | 密钥加密两套派生实现 | `app/core/cipher.py:21` vs `app/services/ai_config_service.py:61-62` | dev 无 SECRET_KEY 时等价公开常量密钥；轮换后密文解不开 |
| S6 | 把 `playwright --dry-run` 当沙箱 | `app/services/case_compiler_service.py:290-345`；`test_plan_service._compile_ui_case(validate=False)` | dry-run 仍执行 spec 顶层语句 → LLM 生成代码可在后端执行 |
| S7 | 静默吞异常 + 异常链丢失 | `ruff`: `S110` 11 处 / `S112` 7 处 / `B904` 32 处（第一次 28 处，**上升**） | 线上问题只剩"业务报错"，无法定位 |
| S8 | 类级可变默认值 `RUF012` | `ruff`: 18 处（第一次 15 处，**上升**），集中在 `app/services/sync/*.py`、`smart_regression/service.py` | 实例间共享可变对象 → 串数据 |

## 5. 🆕 新增观察（第二次才出现）

| 编号 | 观察 | 证据 |
|------|------|------|
| N-1 | 新增首屏数据 effect 无 cleanup（同类问题换位置复发） | `frontend/src/pages/metrics/index.tsx:12`（`getOperationsMetrics().then(setM).catch(() => {})`） |
| N-2 | 前端裸 `.catch(() => {})` 静默吞错 | 同上；`pages/knowledge/components/SearchTab.tsx:72-86` 为同模式的既有实例 |
| N-3 | `noqa` 失效堆积 | `ruff RUF100`：132 → 164 处（注释掉的规则不再触发，说明规则集在漂移而清理没跟上） |

## 6. 保持良好（两次都通过，作为回归基线）

| 项 | 结果 |
|----|------|
| 路由鉴权覆盖 | 633 个路由中仅 9 个无鉴权依赖，且全部为合理公开端点（login/register/forgot/reset/sso-config/public-access/logout/health×2） |
| 前端编译与静态检查 | `tsc -b` ✅ 0；`eslint . --max-warnings=0` ✅ 0 |
| 前端安全基线 | `console.log`/`debugger`/`eval`/`new Function`/`dangerouslySetInnerHTML` 均 0 命中；token 不落 localStorage |
| 错误穿透 | `api/client.ts` 统一拆 envelope、FastAPI 422 `detail` 数组转可读文案、401 统一登出 |
| 路径越权防护样例 | `lanhu_evidence_assets.download` 的 `is_relative_to(storage_dir)`；Playwright runner 的 spec 路径收敛 |
| 上传体量控制 | 按实际字节数（`_MAX_UPLOAD_BYTES + 1`）而非 Content-Length 限制 |

## 7. 复现命令

```powershell
# 确定性文件选择 + 规则解析（delegation，无需 LLM）
ocr delegate preview --from ad4d1d25b1239736b363ab9f6c5533d99fbba3a9 --to HEAD --format json --repo .
ocr delegate rule --format json test-platform-v2/backend/app/main.py ...

# 机械门禁（对任意 worktree 都可用，ruff 不需要项目依赖）
python -m ruff check test-platform-v2/backend/app --select F,E9,B,S,C4,ASYNC,RUF,SIM,PERF,PIE --statistics
cd test-platform-v2/frontend ; npx tsc -b ; npx eslint . --max-warnings=0

# 专项扫描（只读）
python <repo>/_audit/route-auth-audit.py test-platform-v2/backend/app/api     # 路由鉴权
python <repo>/_audit/nplus1-audit.py test-platform-v2/backend/app            # 循环内 DB 访问
node   <repo>/_audit/use-effect-audit.mjs test-platform-v2/frontend/src      # 异步 effect cleanup
```

## 8. 后续（下一批 Product/Leader 应处理）

1. 把 S1–S6 登记为 C 条件（本次是直接任务，未擅自写入 `C-CONDITIONS.md`）。
2. 把 S7/S8 的数量做成 CI 棘轮（只降不升），而不是靠人工 grep。
3. 给「生成代码 → 执行」链路补沙箱设计（与 ADR-0026 的执行归属一并考虑）。

