---
title: "体育平台 本地测试平台（v1 旧版）"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "maintenance"
expires: "2026-12-26"
tags: ["test-platform", "v1", "cli", "legacy", "maintenance"]
related: ["test-platform-v2/README.md", "test-platform/CLAUDE.md"]
---

# 体育平台 · 本地测试平台

多站点 × 多环境的 6 件套测试工具,统一 CLI `tp` 驱动。基于《test-测试平台设计方案.md》落地。

| 工具 | CLI | 作用 |
| --- | --- | --- |
| 流量监控器 | `tp capture` | mitmproxy 抓站点真实请求 → 录制(Diff/Mock 的数据源) |
| 接口 Diff 比对器 | `tp apidiff` | 同批请求打两环境,JSON 逐字段比对,分级 HTML 报告 |
| Mock Server | `tp mock` | 容器化 WireMock:录制转 stub、故障注入、场景切换 |
| 环境健康检查器 | `tp envcheck` | 并发探活 DB/Redis/MQ/HTTP/版本/预置数据,红绿灯 |
| 测试数据工厂 | `tp datafactory` | YAML 规则造成套关联数据,约束/脏数据/模板,灌库 |
| 日志聚合分析器 | `tp logagg` | 按 traceId 串全链路日志,ERROR 高亮,根因聚类 |
| 测试报告聚合器 | `tp report` | 多框架报告→sqlite→streamlit 趋势看板、flaky 检测 |

---

## 一、安装

```powershell
cd test-platform
./setup.ps1          # Windows;macOS/Linux 用 bash setup.sh
```

脚本会:建独立 venv(`test-platform/.venv`)→ 装依赖 → `pip install -e .`(提供 `tp` 命令)→ 装 Playwright Chromium → 生成 `.env`。

**仍需手动的外部依赖:**
1. **Docker Desktop** — Mock Server 用:`docker pull wiremock/wiremock:3.5.4`
2. **mitmproxy CA 证书** — 抓 HTTPS 必需:先 `tp capture --site camel1 --env prod`,浏览器访问 `http://mitm.it` 装证书
3. 填写 **`.env`**:各站点/环境凭据 + `UPSTREAM_PROXY`(访问站点的上游代理)

激活与自检:
```powershell
.\.venv\Scripts\Activate.ps1
tp config show --site camel1 --env prod      # 打印合并后配置
tp config sites                               # 列出全部站点及环境
```

---

## 二、多站点 × 多环境配置体系（核心）

```
config/sites/
  _base/            共享 API 基线(apis.yaml)+ Diff 忽略规则(ignore.yaml)
  camel1/
    site.yaml       extends:_base + 本站点接口差异覆盖(deep-merge;null=删除)
    logs.yaml       日志源(日志聚合用)
    environments/
      prod.yaml     base_url / proxy / db / redis / mq / 期望版本
      test1.yaml
      test2.yaml
  _template/        加新站点时复制此目录
```

合并顺序:`platform.yaml ⊕ site.yaml(⊕_base) ⊕ environments/<env>.yaml` → 单一 `RunContext`,所有工具消费。
所有命令统一用 `--site <站点> --env <环境>`;`envcheck/config` 支持 `--site all --env all` 批量。
敏感信息用 `${VAR}` 引 `.env`,不明文入库。

**加一个新站点(如 camel2):**
```powershell
Copy-Item -Recurse config/sites/_template config/sites/camel2
# 1) 改 camel2/site.yaml:写 description,只填与基线不同的接口
# 2) 改 camel2/environments/*.yaml:base_url、proxy、db/redis/mq
# 3) 在 .env 增加 camel2 各环境凭据
tp config show --site camel2 --env prod        # 验证
```

**“接口有差异”怎么写(camel2 与基线不同):**
```yaml
# config/sites/camel2/site.yaml
apis:
  ugc_list:
    query: {categoryId: "BASKETBALL"}   # 改默认参数
  refund_first_bet: null                # 本站点没有该接口 → 删除
  site2_special:                        # 本站点独有接口 → 新增
    path: /api/site2/special
    method: GET
```

---

## 三、各工具用法速查

```powershell
# 流量监控:抓 camel1 生产真实请求(经上游代理),Ctrl+C 结束
tp capture --site camel1 --env prod --port 8081

# 接口 Diff:把录制流量回放到 prod 与 test1 比对
tp apidiff --site camel1 --base prod --target test1 --cases data/recordings/camel1-prod.jsonl
#   → data/reports/camel1-diff-prod-test1.html;有高危差异退出码=2(可卡 CI)

# Mock:录制转 stub → 起容器 → 注入故障
tp mock convert --site camel1 --recording data/recordings/camel1-prod.jsonl
tp mock up --site camel1 --port 8080
tp mock inject --path /api/pay/order --status 500        # 或 --scenario timeout
tp mock down

# 环境健康检查:红绿灯(任一红→退出码1,fail fast)
tp envcheck --site camel1 --env test1
tp envcheck --site all --env all                          # 批量

# 数据工厂:造用户+订单灌库 / 用 VIP 模板 / 脏数据 / 导出
tp datafactory --site camel1 --env test1 --rule tools/data_factory/examples/user.yaml --count 50
tp datafactory --site camel1 --env test1 --template vip_user --count 10
tp datafactory --site camel1 --env test1 --rule ...user.yaml --mode dirty --output sql

# 日志聚合:按 traceId 串链路 / 批量聚类失败根因
tp logagg trace --site camel1 --env test1 --id abc123
tp logagg batch --site camel1 --env test1 --report data/reports/pytest.xml

# 报告看板:入库 → 起 streamlit
tp report ingest --file data/reports/pytest.xml --build 1024 --branch main
tp report serve --port 8090
```

---

## 四、串起来的一天

```
09:00 tp envcheck         —— 10 秒确认 test1 可测,版本/证书没问题
09:10 tp datafactory      —— 灌一套「VIP 用户+订单」关联数据
09:20 tp mock up + inject —— 顶替未完成的下游,配个超时场景
09:30 跑回归套件(pytest/playwright,下游连 Mock)
10:00 tp logagg trace     —— 用例红了,2 分钟定位脏字段
10:30 tp report ingest+serve —— 看趋势、flaky、按模块归因
14:00 tp capture → apidiff —— 上线前把生产流量回放到新版本验回归
```

---

## 五、目录结构

```
test-platform/
├── setup.ps1 / setup.sh        一键搭建
├── requirements.txt            统一依赖
├── pyproject.toml              提供 tp 命令
├── config/                     platform.yaml + sites/(多站点多环境) + schema/
├── core/                       配置模型/加载合并/HTTP/录制/日志(6 工具共享)
├── tools/                      6 件套实现
├── cli/tp.py                   统一 CLI 入口
├── docker/wiremock/            WireMock compose + 各站点 stub
├── data/                       运行产物(录制/报告/sqlite,gitignore)
└── platform_tests/             平台自测(配置合并/覆盖/插值)
```

> 说明:设计文档所列「AI 测试用例生成器」本平台未实现(仓库内原无代码),`tp` 预留接入位。
> 接口基线 `_base/apis.yaml` 的路径/字段为依据测试用例的推断占位,联调后以真实接口文档校正。
