# Batch 272 证据 — 真实浏览器渲染与"搜索直达"验证（2026-09-23）

> 环境：本机 worktree 起真实前后端 —— 后端 `127.0.0.1:5949`（指向本地试点库 `probe.db`），
> 前端 `vite dev 127.0.0.1:5948`（代理到 5949）；浏览器 = Playwright Chromium（1440×1000）。
> 账号：`tester`（非超管）/ `drill-admin`（超管），经**真实登录表单**登录（cookie 注入不会触发前端内存态，会渲染成 guest 菜单——第一次尝试就是这样，已修正）。

## 1. tester（非超管，19 个菜单）：侧栏被瘦身

```
侧栏渲染：
CamelTv | 测试平台 | 导航菜单 | 工作台 | 版本验收 | 版本验收任务 | 版本发布包 | 需求文档 |
结果与缺陷 | 缺陷管理 | 报告中心 | 知识中心 | 专家区 | 5 |
其余 7 个模块已收进搜索：按 Ctrl/⌘ + K 输入名称直达 | 测试同学 | tester@cameltv.local

一级入口：4 行（工作台 / 版本验收 / 结果与缺陷 / 知识中心）
专家区保留：5 项（用例服务 / 接口测试 / UI 自动化 / 测试数据集 / 目标环境）
搜索直达：7 项（定时任务 / 我的项目 / DSH 任务 / AI 配置 / 蓝湖证据包 / 运营指标 / 业务引导）
截图：nav-b272-tester.png
```

对账：4 行（7 个 code）+ 保留 5 + 搜索 7 = **19** = `/system/menus` 返回数 ✓（瘦身 ≠ 下架）

## 2. drill-admin（超管，20 个菜单）：保持全景（不瘦身）

```
侧栏渲染：
… 知识中心 | 专家区 | 13 | 超级管理员 | admin@cameltv.local

专家区：13 项（资产 5 + 引擎与配置 4 + 个人 4）
搜索提示：无（searchOnly = 0）
截图：nav-b272-admin.png
```

对账：4 行（7 个 code）+ 专家区 13 = **20** ✓

## 3. 关键闭环：被瘦身模块**从命令面板搜到并直达**

```
[tester] 按 Ctrl+K → 在命令面板输入「定时」
         → 命中「定时任务」
         → 点击后 URL 变为 /schedule      ← 该模块已不在侧栏，仍可搜到并直达
截图：nav-b272-tester-palette.png
机器可读结果：nav-b272-render.json（tester.palette = {matched: "定时任务", navigatedTo: "/schedule"}）
```

## 4. 复现命令

```bash
# 后端（本地试点库，不碰生产）
DATABASE_URL=sqlite:///…/probe.db python -m uvicorn app.main:app --host 127.0.0.1 --port 5949
# 前端
cd test-platform-v2/frontend && npm run dev -- --port 5948 --strictPort
# 浏览器验证脚本（临时放在 frontend 目录下运行，跑完已删除，不入库）
node _b272_verify.mjs <证据输出目录>
```

## 5. 本地环境的副作用（如实登记）

| 项 | 说明 |
|----|------|
| 试点库 `tester` 口令 | 为让浏览器能真登录，本地试点库里把 `tester` 的口令重置为临时值（仅 `C:\Users\26029\AppData\Local\Temp\cameltv-pilot-probe-…\probe.db`，**不涉及生产**） |
| 后端/前端进程 | 验证用 5949/5948 两个进程，验证结束后已停止 |

## 6. 未覆盖（不夸大）

- **未在生产/测试环境验证**：本批是前端渲染逻辑变更，验证在本地真实前后端完成；生产要等下次发布火车。
- **未跑 a11y 套件**：`npm run test:a11y:ci` 需要 Playwright 全量基线，本批只做了侧栏/命令面板的定点验证（新增提示用的是既有语义类，未引入新色彩/尺寸）。
