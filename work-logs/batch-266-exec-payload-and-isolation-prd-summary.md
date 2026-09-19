# Batch 266 PRD — 执行链路可执行性：payload / 断言 / 用例隔离

> **Product** | Date: 2026-09-19 | 档位：**完整批次**
> 触发器：命中 `pipeline-modes.md` 的**执行链路变更**（节点执行器断言语义与用例隔离）+ 数据口径变更。

## 1. 背景（三条实测缺陷）

| 编号 | 现象 | 证据 |
|---|---|---|
| `C264-3` | 驱动 payload 只带 brief（`{id,title,module,priority}`）→ API 侧裸 `GET <base>/`（404×50）、Web 侧 `steps=[]`（30/30 空过） | Batch 264 证据 `pilot-payload-vacuous-execution-20260919.json` |
| `C264-4` | 节点一个 job 只建一次浏览器上下文 → 用例共享 cookie/localStorage，站点状态串味；`expect_visible` 只看首个匹配 | 同上 + `web-executable-cases-run-20260919.json` |
| 新发现 | 平台生成器产出的断言类型 `response_time` / 小写 `jsonpath` / `expected=null`（存在性）节点均不识别 → 一律判失败 | 本批实跑 job 13：`{"type":"response_time"}`、`{"type":"jsonpath","path":"$.data","expected":null}` 全部 `passed:false` |

## 2. 目标行为

1. 节点断言支持 `status` / `status_code`（等值 + `operator`: eq/gte/gt/lte/lt）、`json_path` / `jsonpath`（`expected=null` = 存在性）、`text_contains`、`not_empty`、`response_time`（毫秒上限）；**未识别类型/算子仍必须失败**（不许静默放过）。
2. Web 执行**每条用例独立浏览器上下文**；单步异常与单用例异常都收敛成"该用例失败"，不得拖垮整个 job。
3. 驱动按 case id 从平台库取**可执行定义**（`api_method/api_endpoint/api_headers/api_body/api_assertions`；web 取 `steps[].action`），取不到就**明确报错**，不再空过。

## 3. 非目标

- ❌ 不改平台控制面权限模型与数据库 Schema；
- ❌ 不引入真实被测系统凭据（账号仍只以槽位名传递）；
- ❌ 不替自动生成用例"补齐真实参数"（属数据集质量，另登记）。

## 4. 验收判据

| # | 判据 |
|---|------|
| A1 | 节点断言：新增断言类型/算子有回归测试，未知类型/算子仍失败 |
| A2 | Web 隔离：`run_web_cases` 每条用例新建上下文（工厂调用次数 = 用例数） |
| A3 | 驱动：payload 携带可执行定义；缺定义时明确失败并列出用例 |
| A4 | 实跑：真实 Test5 上 Web 用例不再空过（截图/步骤为真），API 用例按真实响应给出通过/失败 |
