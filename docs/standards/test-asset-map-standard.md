---
title: "测试资产底图标准（Test Asset Map Standard）"
owner: "qa-team"
last_reviewed: "2026-11-06"
status: "active"
expires: "2027-05-06"
tags: ["standard", "case-generation", "interaction", "chain", "coverage"]
related: ["../.claude/skills/interaction-case-augmenter/SKILL.md", "interaction-case-augmentation.md", "./project-adapters/"]
---

# 测试资产底图标准

> 解决三个问题：① 换项目能不能复用；② 什么时间做什么事；③ 覆盖到什么程度算够。
> 一句话：**准则与引擎跨项目恒定，项目差异只写适配器，覆盖率按断言与链路计量。**

## 1. 三层复用模型

| 层 | 内容 | 是否随项目变化 | 位置 |
|---|---|---|---|
| **L1 通用资产** | 24 条交互准则 + 断言库、矩阵 Schema、链路分层模型（L1 域内/L2 跨域/L3 补偿）、覆盖率口径、门禁规则、引擎 | **不变**（改一次全项目受益） | `.claude/skills/interaction-case-augmenter/references/interaction-rules.json`、`scripts/test-asset-map/` |
| **L2 项目适配器** | 页面源、接口源、业务域映射、业务闭环、平台清单 | 每项目一份 YAML（约 50–150 行） | `docs/standards/project-adapters/<project>.adapter.yaml` |
| **L3 项目实例** | 84 页清单、2016 格矩阵、34 条域内链、缺陷模式库 | 由引擎自动生成 + 人工校准 | `docs/standards/project-adapters/out/<project>/` |

> 判断一个资产属于哪层的方法：**换项目后需要人工改写的，就是 L2/L3；不需要改的就是 L1**。

### 1.1 复用契约（必须保持稳定的接口）

引擎只依赖以下四件事，任何项目只要提供它们即可复用：

```yaml
pages:        # 页面清单：platform / page_id / group / name / path / page_kind
interfaces:   # 接口清单：method / path / name
domain_map:   # 业务域 = 一组路径前缀（人工校准点）
closures:     # 业务闭环 = 业务域的有序组合（人工校准点）
```

输出格式恒定：`page-inventory.json`、`rule-page-matrix.csv`、`interface-chain-graph.json`、`summary.json`。
**用例模板、缺陷模式库 schema、准则库格式不得随项目改动**；项目差异一律进适配器。

### 1.2 跨项目验证（实测）

| 项目 | 页面源 | 接口源 | 结果 |
|---|---|---|---|
| 未来娃屿 | `sys_menu` + `app.json` 导出（84 页） | Apifox 端点清单（535） | 2016 格 / 适用 1541 / 覆盖 17.3%；34 域 / 未归类 7 |
| CamelTv 体育 | OpenAPI `tags`（4 域） | `cameltv-openapi.yaml`（5 端点） | 96 格 / 适用 76 / 覆盖 0%（无基线）；2 域 / 未归类 1 |

同一份引擎、同一份准则库，**改动只有适配器**。CamelTv 那组"0% 覆盖"不是失败，而是首轮接入的正确输出：直接产出缺口清单。

## 2. 标准作业流程（什么时间做什么事）

| 阶段 | 触发时点 | 必须做的事 | 产出物 | 准出（DoD） | 耗时参考 |
|---|---|---|---|---|---|
| **P0 项目接入** | 新项目 / 换项目 / 新增大端（如新增平板端） | ① 导出页面源与接口源 ② 写适配器 ③ 跑引擎 ④ **人工校准域映射与业务闭环** ⑤ 导入历史缺陷建 Pattern 库 ⑥ 标注环境能力矩阵 | 三份底图 + Pattern 库 + 能力矩阵 | 页面清单覆盖 = 100%；接口分配率 ≥ 95%（未归类 ≤5% 且逐条说明）；Pattern 库 schema 校验通过 | 0.5–1 人天 |
| **P1 需求进入** | 需求评审通过当天 | ① 底图 diff：新增/变更页面与接口 ② 生成「变更影响清单」：受影响页面 × 准则、受影响接口 × 链路 | 影响清单 + 增量矩阵 | 每条新需求 ≥1 个准则覆盖点 + ≥1 个链路节点 | 0.5 人天/迭代 |
| **P2 用例设计** | 需求进入后 1–2 天 | ① 按矩阵 NONE 格生成**参数化用例族** ② 设计链路用例（L1/L2/L3）③ 每条用例绑断言 ID ④ 标执行载体 | 用例集 + 断言台账 + 链路契约（夹具/门禁/清理） | P0 页面断言覆盖 100%、P1 ≥80%、P2 ≥50%；每条链路有夹具链与清理契约 | 2–3 人天/迭代 |
| **P3 执行** | 提测后 | ① P0 链路 → P0 断言 → P1 → 抽样 ② 失败取证 ③ 阻断登记 | 执行报告 + 证据 | 阻断率 ≤10%；每个失败有请求/响应/截图；未执行为 0 条无理由 | 按规模 |
| **P4 缺陷回流** | 缺陷确认当天（不是周末） | ① 定位 `(准则, 页面, 断言)` 三元组 ② **该准则在全部适用页面重算状态** ③ 补断言 → 更新矩阵 ④ 回归锚定 | 更新后的 Pattern 库 + 矩阵 + 复检清单 | 每条缺陷可追溯到三元组；受影响页面状态已重算；同类页面已复检 | 0.2 人天/缺陷 |
| **P5 版本验收** | 发布前 2 天 | ① 覆盖率报告 ② 链路通过率 ③ 历史缺陷复发率 ④ 结论 READY/CONDITIONAL/NEEDS WORK | 验收报告 | 无 P0/P1 未闭环；P0 链路通过率 100%；断言覆盖率达阶段目标；复发率 ≤5% | 0.5 人天 |

### 2.1 关键约束（违反即返工）

1. **P0 未完成不得进入 P2**：没有底图就设计用例，等于凭记忆写。
2. **P4 不得只改那一条用例**：必须按准则在全部适用页面复检（本次 REG-25 只改一条就是反例）。
3. **不得用「用例数」作为验收指标**：只看断言覆盖率、链路通过率、复发率。
4. **不得跳过人工校准**：域映射与业务闭环是唯一必须人工确认的两处（机器只能给候选）。

## 3. 覆盖率口径（统一算法）

| 指标 | 公式 | 目标 |
|---|---|---|
| **断言覆盖率** | 已覆盖格 / 适用格（`rule × page`，覆盖=预期结果中存在该准则断言） | P0 页面 100%，P1 80%，P2 50% |
| **接口分配率** | 已归入链路域的接口 / 全部接口 | ≥95%（剩余逐条说明） |
| **链路可执行率** | 具备夹具链 + 入口门禁 + 清理契约的链路 / 全部链路 | ≥80% |
| **缺陷复发率** | 复发的历史缺陷 / 历史缺陷总数 | ≤5% |
| **阻断率** | 阻塞用例 / 计划用例 | ≤10% |

> 反例（本次实测）：未来娃屿断言覆盖率 17.3%、零覆盖页面 47/84、接口链路分配仅为"域内链"级别而可执行链路 0 条。这些数字比"1230 条用例、需求覆盖 100%"更能说明真实水位。

## 4. 适配器编写指南（换项目只做这四件事）

```yaml
project: <id>
platforms: [ {key, label}, ... ]

pages:
  source: file | openapi_tags | static     # RuoYi→file(sys_menu 导出)；Next/Router→file；纯 API 项目→openapi_tags
  path: sources/<project>.pages.json

interfaces:
  source: endpoints_json | openapi
  path: sources/<project>.endpoints.json
  domain_map:                              # ★ 人工校准点 1：业务域 = 路径前缀组
    - { name: 资产-组件, prefixes: ["/system/component"] }
  default_domain: 其他

cases: { path: sources/<project>.cases.json }   # 首轮可空

business_closures:                         # ★ 人工校准点 2：跨域闭环
  - { id: CLOSURE-ORDER, name: 下单闭环, chain: [资产-组件, 商品-C端, 订单-C端] }

output_dir: out/<project>
```

### 4.1 不同技术栈的页面源取法

| 技术栈 | 页面源 | 取法 |
|---|---|---|
| RuoYi / 后台管理系统 | 菜单表 | `select menu_name,path,component from sys_menu where menu_type='C'` |
| 微信小程序 | `app.json` | `pages` + `subPackages[].pages` |
| Next.js / React Router | 路由文件 | 静态扫描 `app/**/page.tsx` 或 `routes.ts` |
| 纯 API / 中台 | OpenAPI tags | 先按 tag 粗分，后续补网关路由 |
| 硬件 / 平板 App | 手工 + 接口 | 适配器 `pages.source: static` 列出页面 |

## 5. 与现有资产的关系

- 本标准的 L1 准则库是 `interaction-case-augmenter` 的输入，不替代它；
- 底图产出的 NONE 格 = 用例生成的任务清单，生成仍走 `test-case-design` + 增强层；
- 链路图产出的 L1/L2 链 = 接口用例的编排骨架，仍按 `api-checklist.md` 的断言要求落地；
- 历史缺陷仍由 `bug-pattern-curator` 维护，但**每条缺陷必须落到 `(准则, 页面, 断言)` 三元组**。

## 6. 新项目 30 分钟上手清单

1. 准备页面源、接口源两个文件；
2. 复制 `cameltv-sports.adapter.yaml` 改四处（pages/interfaces/domain_map/closures）；
3. 跑 `python scripts/test-asset-map/build_asset_map.py <adapter>`；
4. 看 `summary.json`：未归类接口是否 ≤5%、零覆盖页面清单是否符合预期；
5. 人工校准域映射与闭环（唯一需要脑力的部分）；
6. 把 `summary.json` 的缺口清单排进 P2 用例设计。

## 7. 页面源适配器（以可访问环境 + 源码 + PRD 为准）

> 页面清单不得从数据库字段倒推。统一由 `scripts/test-asset-map/adapters.py` 从四类权威源生成。

| 子命令 | 输入 | 适用场景 | 实测（未来娃屿） |
|---|---|---|---|
| `crawl-web` | 已登录态 + 入口 URL | 环境已可访问的 Web/后台；**按角色**爬取可见菜单 | operator 13 / auditor 7 / launcher 5 / clerk 2 页 |
| `scan-source` | 前端源码目录 | 拿到源码时最全（含隐藏/超管页、路由参数页） | 94 条（静态路由 + views 目录） |
| `scan-mp` | 小程序 `app.json` | 小程序/分包页面 | 27 页（6 主包 + 21 分包） |
| `parse-prd` | 需求/PRD 文本 | 补"需求有、实现未找到"的候选 | 54 条候选（需人工确认） |
| `merge` | 多来源 `label=path` | 交叉验证 + 缺口清单 | 合并 152 条；PRD-only 缺口 53 |

**关键结论**：单一来源必然不全——爬虫只看到角色可见菜单（超管页看不到），源码能看到隐藏路由（如 `/forgot-password`），PRD 能看到尚未实现或命名不同的页面。**必须三源交叉 + 人工裁决**。

## 8. 可执行断言（A01–A24 脚本化）

`scripts/test-asset-map/run_assertions.py`：

- `web`：Playwright 逐页测量 —— A07 溢出（scrollWidth）、A21 对比度（WCAG）、A22 三档视口、A23 键盘焦点
- `http`：声明式 spec —— A05 幂等、A06 参数、A11 权限、A12 越权、A19 一致性、A20 错误语义

**校准是必须的工序**（否则产生假失败）。本轮经过 3 轮校准：

| 假失败类别 | 现象 | 处理 |
|---|---|---|
| 设计内的横向滚动 | 表格 `overflow-x:auto` 被误判溢出 | 排除 `auto/scroll` 容器 |
| 省略号截断 | `text-overflow:ellipsis` 被误判溢出 | 排除 ellipsis/nowrap |
| 媒体/装饰盒 | 56×56 图片容器 scrollWidth 70 | 只检查有文本的容器 |
| 断言器自身 spec 透传 bug | `max_ms`/`absent_fields` 未生效 → 2 条误判 PASS | 修 runner，同时支持节点级与 expect 级 |

校准后实测（6 个后台页面）：**R07 6/6 PASS、R21 6/6 FAIL（最低 2.46:1）、R22 6/6 PASS**；HTTP 断言 8 条中 6 条 FAIL（对应上一轮发现的问题）。

> 已知限制：响应时间单次采样不稳定（同一接口冷 4317ms / 热 906ms），应改为多次采样取 P95。

## 9. 链路执行器（fixtures → entry_gate → steps → cleanup）

`scripts/test-asset-map/run_chain.py` + 声明式 JSON 规格：

```
fixtures（造数，可跨角色）→ entry_gate（前置不成立即 BLOCKED）→ steps（状态/数据/幂等断言）→ cleanup（必执行）
```

实测 `CHAIN-CART-ORDER-READONLY`：后台取组件 → C 端商品详情 → 购物车 → 订单详情（校验不泄露 openid）→ 可退金额 → 退款记录，**7/7 通过**；其中 `/refundable` 返回业务码 4100（不可退），说明链路用例能暴露"单接口看不见的业务语义"，需业务确认文案。

## 10. 覆盖率门禁（CI 可执行）

`scripts/test-asset-map/gate.py` 读取 `summary.json` + 断言 CSV，按阈值返回退出码：

```powershell
python scripts/test-asset-map/gate.py --summary out/futurewayu/summary.json \
  --assertions all-assertions.csv --min-page-coverage 0.95 --max-unassigned 0.05 \
  --min-assert-pass 0.90 --require-rules R07,R11,R19,R20,R21,R22
```

本轮实测：页面清单 84/84 ✅、接口未归类 7/535 ✅、必需规则齐备 ✅、**断言通过率 53.8% ❌（14/26）→ exit 1**。门禁按预期阻断了当前质量水平。

## 11. 剩余缺口状态

| 缺口 | 状态 | 证据 |
|---|---|---|
| 页面源适配器（爬取/源码/小程序/PRD） | ✅ 已关闭 | 4 源 + merge：爬取 13/7/5/2、源码 94、小程序 27、PRD 54 → 合并 120 条 / PRD-only 缺口 21 |
| 断言脚本化（24 条准则） | ✅ 已关闭 | 24/24 有可执行路径：web 12 + http 8 + chain 2 + N/A 1 + web/http 1；实测 web 72 行（53 PASS / 6 FAIL / 13 N/A）、http 13 条（7 PASS / 6 FAIL） |
| 链路执行器 + 34 条域内链 | ✅ 已关闭 | 生成 34 条规格（3 ready / 31 skeleton）；3 条 P0 只读链全部 PASS |
| CI 门禁 | ✅ 已关闭 | `.github/workflows/asset-map-gate.yml`：static（PR 必跑）+ live（self-hosted 手动）；golden 全 PASS、真实数据按预期 FAIL |
| 域映射候选生成 | ✅ 已关闭 | `suggest_domains.py`：24 候选覆盖 485 唯一路径，2 个兜底域带成员提示，人工从"从零划"变"确认" |
| 执行载体/能力矩阵 | ✅ 已关闭 | `futurewayu.capabilities.yaml` + `build_capability_matrix.py`：页面 46/84 可执行，链路 5/34（28 条因骨架、5 条因能力） |
| 31 条骨架链细化 | ❌ 未做 | 需按 P1/P2 优先级逐条补夹具与写阶段断言 |
| 断言稳定性 | 🟡 部分 | 响应时间单次采样不稳（冷 4317ms / 热 906ms），应改多采样 P95 |


## 12. CI 接入

工作流：`.github/workflows/asset-map-gate.yml`

| Job | 触发 | 内容 | 失败处理 |
|---|---|---|---|
| `static` | PR（路径：`docs/standards/**`、`scripts/test-asset-map/**`、skill 目录） | 工具链单测 → 双项目底图构建 → 域候选 → 链路规格 → **golden 断言门禁自检** | 阻断 PR |
| `live` | 仅 `workflow_dispatch`（self-hosted runner） | 恢复 `ASSET_MAP_ENV_JSON` 凭据 → HTTP 断言 → 3 条 P0 只读链 → 真实阈值门禁 | 阻断并上传 `runtime/` 证据 |

设计要点：
1. **静态门禁用 golden 断言**（全 PASS）验证管线本身，不受环境与数据影响；真实阈值只在 live 跑。
2. 凭据只从 secrets 注入，落盘 `runtime/env.json` 后 `chmod 600`，不进 artifact 的敏感明文（仅结果 CSV）。
3. `static` 同时构建两个项目适配器，**换项目复用性每次 PR 都被验证**。

本地等价校验：

```powershell
python -m pytest scripts/test-asset-map -q
python scripts/test-asset-map/build_asset_map.py docs/standards/project-adapters/futurewayu.adapter.yaml
python scripts/test-asset-map/gate.py --summary docs/standards/project-adapters/out/futurewayu/summary.json \
  --assertions docs/standards/project-adapters/fixtures/golden-assertions.csv \
  --min-page-coverage 0.95 --max-unassigned 0.05 --min-assert-pass 0.9 \
  --require-rules R01,R07,R11,R19,R20,R21,R22 --out gate-report.json
```

实测：单测 12 项通过；static 门禁 **PASS（exit 0）**；live 真实数据 **FAIL（断言通过率不达标）**——两者行为都符合预期。


## 13. 能力矩阵（哪些能跑、为什么不能跑）

`futurewayu.capabilities.yaml` + `build_capability_matrix.py` 把「页面/链路」与「环境能力」对齐：

| 能力 | 可用 | 依据 |
|---|---|---|
| web-admin / admin-token / c-end-token / db-readonly / redis-read / server-log | ✅ | 本轮实测可用 |
| mini-program-runtime | ❌ | 无该小程序开发者权限，开发者工具导入被拦 |
| pad-device / screen-device | ❌ | 无 1.3.26 安装包；有 PICKUP_SCREEN 记录但无设备令牌 |
| payment-sandbox / youzan-buyer / callback-signature | ❌ | 生产资金红线；无买家账号与商户证书 |

实测：**页面 46/84 可执行（54.8%）**（后台 46/46，小程序 0/27、平板 0/5、叫号屏 0/2、有赞 0/4）；
**链路 5/34 可执行（14.7%）**，阻塞 28 条为骨架未细化、5 条为能力缺失。

## 14. 链路就绪度

| 状态 | 数量 | 含义 |
|---|---:|---|
| `ready` | 6 | 含夹具/注入的完整规格（3 P0 + 3 P1） |
| `ready-readonly` | 25 | 只读步骤 + 无凭证拒绝注入，可直接执行 |
| `skeleton` | 3 | 纯写域（回调/社区-互动/身份卡-C端），需夹具与写权限批准 |

6 条 ready 链实测 **全部 PASS**（共 29 个步骤）。其中：
- 认证链使用**不存在的用户名**验证非法登录被拒，避免锁定真实账号；实测返回 403（非 200，未发 token）。
- 消息链刻意**不调用 C 端消息详情**（会标记已读，产生副作用）。
- 有赞-交易链因 `payment-sandbox` + `callback-signature` 能力缺失，无法进入资金环节，只覆盖只读配置段。

## 15. 全量扫描与缺陷聚合（R21）

28 个后台页面 × R07/R21/R22 = 84 行：

| 准则 | 结果 |
|---|---|
| R07 文本溢出 | **28/28 PASS** |
| R22 三档视口 | **28/28 PASS** |
| R21 对比度 | **27/28 有测量值且全部低于 4.5:1**；最低 **2.17:1**，中位 **2.46:1**，违规文本元素合计 **317 处** |

**聚合为 1 条缺陷**（不是 28 条）：同一套主题色 token 不达标。典型违规为次级按钮（「新增店铺/新增设备/新增轮播图」2.46:1）与筛选标签（3.43:1）。
关闭标准：`run_assertions.py web --rules R21` 全量 28 页 **28/28 PASS**。

> 附：本轮"跑通一次 CI"发现真实问题——`futurewayu.endpoints.json` 被 gitignore 导致干净检出必挂；已将接口清单入库、用例基线改为缺失时降级，修复后干净检出 static job 全绿（12 单测 + 双项目 + golden 门禁 exit 0）。


## 16. 28 条骨架链→就绪（本轮）

### 16.1 就绪度提升

| 指标 | 上一轮 | 本轮 |
|---|---:|---:|
| ready | 6 | 6 |
| ready-readonly | 0 | **25** |
| skeleton | 28 | **3** |
| 校验器 invalid | 4 | **0** |
| 能力可执行链路 | 5/34（14.7%） | **29/34（85.3%）** |

做法：`gen_chain_specs.py` 按接口依赖图自动取**安全只读步骤**（排除 `{}` 路径、写动词、含 read/refresh/print 等副作用词的 GET），每步带 `expect`，每条链追加一条**无凭证拒绝注入**（鉴权断言）。纯写域不硬凑，写 `blocked_reason`。

### 16.2 校验器（validate_chains.py）

把"就绪"变成机器可校验，5 条规则：step 必须有 expect；变量引用必须可被 fixture 提取；写步骤必须有 cleanup（或 `cleanup_not_applicable` 理由）；ready 链必须有 ≥1 步且带注入/说明；零步骤必须写 blocked_reason。
CI 已加该步骤，invalid 直接阻断。

### 16.3 批量只读执行结果

| 指标 | 结果 |
|---|---|
| 链路 | **23/31 PASS**（74.2%） |
| 步骤 | **87/98 PASS（88.8%）** |
| 失败归因 | 8 条**全部**为 `product-500`，无规格噪声 |

**8 条失败收敛为 1 条缺陷**：缺参/内部异常返回 500 兜底，命中 **11 个接口**（订阅消息 templates/statuses/status、banner enabledList、appVersion/latest、oss audit-status、search、pickupOrder station/screen 与 station/orders、youzan channel/batches、youzan goods alert/detail）。

关闭标准：缺参返回 400/422 且 msg 指明缺失字段；复跑 **31/31 PASS**。

### 16.4 踩坑记录（都已修）

| 问题 | 现象 | 修法 |
|---|---|---|
| 裸数组响应 | `/system/aiProcessRecord/list` 返回 JSON 数组 → runner `AttributeError` | 数组视为 200 成功体 |
| `/monitor` 前缀漏判 | 运营访问监控接口 403 被判 FAIL | 管理员前缀补 `/monitor`、`/tool` |
| 公开接口注入误判 | banner/bgImage 无凭证本就 200 | 公开前缀注入口径 [200,401,403] |
| 设备接口 401 | `/device/**` 需设备令牌 | 非缺陷，按能力缺口登记 |
| 旧规格残留 | domain 改名后旧 JSON 仍在 | 生成前清理 `CHAIN-*.json` |
