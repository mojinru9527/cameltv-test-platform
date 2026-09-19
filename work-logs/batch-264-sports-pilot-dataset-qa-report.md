# Batch 264 — QA 报告

> **QA (🔍)** | Date: 2026-09-19 | Verdict: **PASS**
> 档位：轻量批次（数据 + 证据，零平台代码改动）

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 4（A1–A4） | 4 | 0 | 0 |

## 可执行门禁

| 命令 | 结果 |
|------|------|
| `python scripts/build_pilot_baseline.py --project-id 1 --environment-id 12 --module-prefix 体育` | **meets_target=true**：counts api **50** / web **30**，shortfall **0/0**，exit **0** |
| `pwsh scripts/git/scan-common-bugs.ps1` | HARD **0** / WARN 344（= 主干基线，非阻断） |
| `pwsh scripts/git/audit-cconditions.ps1` | hard errors **0** / warnings **0** |
| CI 范围分类 | 本批仅 `work-logs/**` → `{"backend": false, "frontend": false, "reasons": ["documentation"]}` |

## 逐条验证

### A1 试点集达到 50 + 30 ✅

本机实测（临时 SQLite，零生产/测试环境写入）：

```
① 导入仓库内契约 test-platform-v2/tests/api-testing/specs/test5-contracts/camel-service.openapi.json
   preview → 197 endpoints（18 个 controller 模块，version 1.0）
   confirm → created_count=197, updated=0, skipped=0, generated_case_count=0

② 用平台自带确定性生成器生成接口用例（无需模型）
   cases created: 591 ｜ endpoint errors: 0
   样例：module=sports-live-controller, case_type=api, priority=P0

③ 口径归一（选择器要求 module LIKE '<前缀>%'）
   591 条接口用例 module → 体育/接口/<controller>
   写入 30 条 Web 用例（case_type=ui，module=体育/...）
   by type: [('api', 591), ('ui', 30)]

④ 用试点选择器实测
   counts: api 50, web 30 ｜ targets: api 50, web 30 ｜ shortfall: api 0, web 0
   meets_target: true ｜ exit 0 ｜ baseline 样本见 evidence/batch-264/baseline-sample.json
```

### A2 30 条 Web 用例来自真实页面 ✅

全部断言只基于实测事实（`evidence/batch-264/test5-web-recon-20260919.json`）：

```
篮球站 https://camel-bball-test5.elelive.cn/basketball   200（标题 Basketball Live Scores, Stats & Fixtures）
  /q/news 200(232KB) · /my 200(202KB)
  /basketball/league/National%20Basketball%20League 200(665KB)
  /basketball/game/match-melbourne-united-vs-adelaide-36ers/n54ql7tp055krvy 200(537KB)
  /rss.xml 200(251KB)
直播站 https://camelive-g3-test5.elelive.cn              200（h1 Football Today - Watch Live Streaming…）
  /ar 200(833KB) · /manifest.webmanifest 200(705B)
  导航实测：Football / Basketball / Home / News / My / Camel Live / Indonesian Super League / Indian Calcutta Football League
```

用例覆盖：首页加载、导航完整性、赛事列表、新闻列表/详情、个人中心、联赛页 ×4、比赛详情、搜索空态、登录入口（**不落凭据**）、赛程/比分区块、多语言、RSS/PWA、移动端响应式、未知路由兜底。

### A3 用例集不含任何凭据 ✅

用例只用「账号槽位名」概念（`--account-slot sports-tester-01`），文件内无账号、密码、token；符合 09 §3.1 / H3。

### A4 门禁 ✅

见上表。

## 缺陷列表

| # | 严重级 | 描述 | 状态 |
|---|:------:|------|------|
| D1 | P3 | 选择器要求 `module LIKE '<前缀>%'`，而契约导入产生的模块名是 controller（`sports-live-controller` 等），两者口径不一致；不归一就永远选到 0 条 | ✅ 本批固化口径：接口用例归入 `体育/接口/<controller>`，Web 用例归入 `体育/<栏目>`，`--module-prefix 体育` 即可同时命中 |
| D2 | P3 | `baseline-sample.json` 的 `fingerprint_confidence=LOW` | 说明：本机样本未提供完整环境指纹组件（非密因子），置信度低属如实反映；真实环境跑时应带 `--components-file` |

## bug-guard「未关闭已知风险」表核对（三问）

**1) 本批是否新增清单中任一项？** 否——零代码改动，未新增「用户输入→出网/落盘/执行代码」路径。
**2) 本批是否修复/关闭任一项？** 无关项；本批只产出数据与证据。
**3) 新增路径是否过铁律？** 不适用。用例文本不含凭据，未触发「凭据外发」类风险。

## 发布建议

状态：**READY**　必修复：0　建议修复：0

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 3h / ~1.5h | 0/0/0/2 | 0 | 需求（口径未先对齐：模块前缀 vs 导入模块名） | 写选片脚本前先读选择器实现，确认过滤字段的真实取值 |
