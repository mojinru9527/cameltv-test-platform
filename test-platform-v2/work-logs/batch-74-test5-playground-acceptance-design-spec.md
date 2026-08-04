# Batch 74 — Design Spec（Test5 契约登记 + Playground 实证 + J15/J16 验收）

> **Design (🎨)** | Date: 2026-08-04

## 1. Test5 契约登记（Slice 1）

### 数据源（2026-08-04 实测）
- 网关：`camel-api-gateway05.svc.elelive.cn:80`（OpenVPN 内网，经 VPN DNS 10.7.7.1 解析到
  `192.168.50.170`；DNS 不稳定，脚本用 `--resolve` 直连）。
- 服务枚举：`GET /actuator/gateway/routes` → 10 个路由服务：
  `camel-service / payment-service / studio-service / api-gateway-service / gateway-service /
   camel-mimo / live-platform / konfi-service / account-service / admin-service`。
- 契约：`GET /{service}/v3/api-docs`（Knife4j OpenAPI3），无需鉴权（已验证 camel-service 200/159KB/197 paths）。

### 落盘结构
```
scripts/executor/fetch-test5-contracts.sh        # 可复现拉取脚本（WSL 内执行）
test-platform-v2/tests/api-testing/specs/test5-contracts/
  {service}.openapi.json                          # 每服务 OpenAPI 原文
  manifest.json                                   # 清单：url/size/sha256/info.version/paths/fetched_at
```
脚本要点：解析网关 IP（VPN DNS 优先，失败回退 192.168.50.170）；逐服务 curl；
用 python3 生成 manifest；幂等可重复执行；不含任何凭据。

## 2. Playground Gherkin→Playwright（Slice 2）

### 映射规则（在既有 `_ACTION_MAP` 上扩展）
- 前缀：`Given/When/Then/And/当/且/则`（大小写不敏感，忽略「我」）。
- 导航：打开/访问/进入/前往 URL → `page.goto`。
- 点击：点击/单击「选择器」 → `page.click`。
- 输入：在「选择器」输入/填写/填入「文本」 → `page.fill(sel, text)`。
- 断言文本：看到/显示/包含「文本」 → `toContainText`。
- 断言可见：元素「可见/出现」 → `toBeVisible`。
- URL 断言：url 应包含 → `toHaveURL`。
- 等待：等待 N 秒/毫秒 → `page.waitForTimeout`。
- 截图：截图 → `page.screenshot`。
- 无法匹配的步骤 → 保持 TODO（诚实降级），但需在响应里说明（本批目标用例全部可映射）。

### 用例来源
- `CompileRequest` 增加可选 `case_id`：提供时从 `functional_cases` 加载步骤文本编译；
  否则用 `source`。后端补接口字段与测试。

### 执行链（C22-C2/C3 证据）
- 本地起后端 8041 + 前端 5211；`playwright` 通过 `backend/package.json`/npx 可用。
- C22-C2：TC-LIVE-001（构造真实功能用例）compile(case_id) → 无 TODO → tsc → headless 执行 → 截图。
- C22-C3：6 条用例（3 API + 3 功能）统一批量执行 → 6/6 有结果 → 报告生成/导出。

## 3. Playground 前端入口（Slice 3）

- 新增 `frontend/src/pages/playground/index.tsx`：源文本 + source_type + compile → 展示 spec →
  execute → 结果/截图；遵循既有页面模式（PageHeader + Card + Button/Textarea/Select），
  深色模式与视觉 token 走 `cameltv-ui-conventions`。
- 路由 `/playground` 加入 `router/index.tsx`；菜单种子（`seed.py _MENUS`）与
  `CommandPalette` 同步登记；`docs/能力产品化决策清单.md` Playground 行改「正式 UI」。

## 4. J15 / J16 验收（Slice 4/5）

- J15：真实浏览器（Playwright headless）打开 `https://www.camellofutbol.com` 首页与任一
  只读页面；断言（标题/元素/无 5xx）+ 截图；只读授权范围内，不做登录/写入/压测。
- J16：从 match replays 页提取真实媒体 URL（mp4/hls），用平台 `/av-checks` 任务
  （ffprobe `probe_stream`）执行格式/帧率/音轨/健康检查；结果任务 id + 指标 + 原始输出登记。

## 5. 交互/边界

- 所有外部访问只读；凭据类不进仓库（C63-2）。
- Playground execute 超时上限保持 120s；并发安全（execute 使用独立临时目录）。
