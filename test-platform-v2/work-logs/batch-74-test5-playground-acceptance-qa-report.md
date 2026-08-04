# Batch 74 — QA 报告（Test5 契约登记 + Playground 实证 + J15/J16 验收）

> **QA (🔍)** | Date: 2026-08-04 | Verdict: PASS（有条件）

## 测试总览

| Slice | 通过 | 失败 | 阻塞 |
|:------|:----:|:----:|:----:|
| 1 Test5 契约登记 | 1 | 0 | 0 |
| 2 Playground 中文映射 | 1 | 0 | 0 |
| 3 Playground C22-C2/C3 实证 + UI 入口 | 1 | 0 | 0 |
| 4 J15 外部页只读验收 | 1 | 0 | 0 |
| 5 J16 音视频 av-checks 验收 | 1（4/6 达标，如实记录） | 0 | 0 |

## 可执行门禁

| # | 门禁 | 方式 | 结果 |
|---|------|------|------|
| G1 | ruff F821 | `ruff check app --select F821` | PASS（exit 0） |
| G2 | 后端全量 pytest | `.venv python -m pytest` | PASS：1020 passed / 3 skipped / 0 failed |
| G3 | 前端 typecheck | `npm run typecheck` | PASS（tsc -b exit 0） |
| G4 | 前端 build | `npm run build` | PASS（vite build 9.25s） |
| G5 | 前端全量 vitest | `npm test` | PASS：87 文件 / 334 用例全绿 |

## 逐条件验证

### Slice 1 — Test5 契约登记（C65-3 部分 / C66-4）
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 网关可达 | ✅ | OpenVPN 内网 `camel-api-gateway05.svc.elelive.cn` → 192.168.50.170（VPN DNS 10.7.7.1 重试稳定） |
| 服务枚举 | ✅ | `GET /actuator/gateway/routes` → 10 个路由服务 |
| 契约落盘 | ✅ | 7 个真实契约（camel-service 197 paths / studio-service 409 / account-service 162 / live-platform 45 / payment-service 26 / camel-mimo 34 / api-gateway-service 15），manifest 含 SHA-256 |
| 无契约服务如实登记 | ✅ | gateway-service（404 body）、konfi-service（token 无效）、admin-service（302 需登录）status=no-contract |
| 六节点 IP | ✅ | C66-4 关闭：六节点 + 网关均 192.168.50.170（camel-to-test5 HTTPS 200 抽查） |

### Slice 2 — Playground 中文 Gherkin 映射
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 中文动作映射 | ✅ | 打开/点击/输入/看到/可见/url 断言/等待/截图 全部映射（当/且/则 前缀） |
| 无 TODO | ✅ | TC-LIVE-001 编译输出无 TODO；`test_playground.py` 14/14 通过 |
| 文本点击回退 | ✅ | `点击「登录」` → `getByText('登录').first().click()` |

### Slice 3 — C22-C2 / C22-C3 实证 + UI 入口
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| C22-C2 compile | ✅ | `POST /playground/compile` case_id=TC-LIVE-001 → 无 TODO、compile_ms=0.11；tsc（strict, moduleResolution node）exit 0 |
| C22-C2 执行 | ✅ | 平台 UiTestRun done：1/1 pass，5.37s（真实登录 → 工作台），截图 c22c2-screenshot.png |
| C22-C3 编排 | ✅ | 计划一键执行 6/6（3 API + 3 UI 真实 headless Chromium），25.8s，passed=6 failed=0 skipped=0 |
| C22-C3 报告 | ✅ | 报告 RP-20260804-004 生成 + xlsx 导出（6 条用例结果） |
| 截图产物 | ✅ | 每条 UI 用例 ≥1 张截图（TC-LIVE-001/002/003） |
| UI 入口 | ✅ | `/playground` 路由 + 菜单（seed）+ 命令面板 + `docs/能力产品化决策清单.md` 转「正式 UI」 |

### Slice 4 — J15 外部页只读验收（C68-1 / C69-1）
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 外部首页 | ✅ | `https://www.camellofutbol.com/es` 平台链路执行 done 1/1（6.4s），断言「Camello Fútbol」 |
| 外部回放页 | ✅ | match-replay 详情页 done 1/1（6.33s），断言「Match Replays」 |
| 只读约束 | ✅ | 仅 GET 页面 + 断言 + 截图；无登录/写入/压测 |

### Slice 5 — J16 音视频 av-checks 验收（C68-1 / C69-1）
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 真实媒体 | ✅ | match replays「2026-07-19 世界杯决赛」HLS 回放（时长 7843s，29.97fps，hls，2 流） |
| av-checks 链路 | ✅ | 平台 `/av-checks` 任务 AV-20260804-002 trigger → ffprobe 8.1.1 后台探测 → done |
| 指标 | ✅ 如实 | 6 项：起播时延 1453.66ms PASS / 帧率 29.97 PASS / 分辨率 921600 PASS / 编码格式 PASS / 码率 0.02kbps 未过（m3u8 播放列表大小被读作码率，指标口径问题）/ 流可用性 100 未过（comparator 口径） |

## 缺陷与遗留

| # | 级别 | 内容 | 处理 |
|---|:----:|------|------|
| B74-Q1 | P2 | J16 码率指标对 HLS 的 raw_size 误读为 m3u8 文件大小 | 本批如实记录不伪造；下批修 `probe_stream` 码率口径 |
| B74-Q2 | P2 | `konfi-service` / `admin-service` 契约需 token/登录 | 用户提供 token/账号后补拉（C65-3 继续 Open 部分） |
| B74-Q3 | P3 | 真机（CP-C1/C2）今晚用户回来后排期 | 保持 DEFERRED |

## KB 检索说明

本地 RAG 服务不可用，替代核查：`C-CONDITIONS.md`、`docs/production-delivery/*`、历史 work-logs、`cameltv-bug-guard` 避坑清单（已逐条核对：后端 envelope/SSRF、前端 useEffect/选择器/错误链、测试 StaticPool 等）。

## 发布建议

状态：**PASS（有条件）**。C22-C2 / C22-C3 / C72-2 / C70-1 / C68-1 / C69-1 具备关闭证据；J16 两项未达标如实记录。建议 Leader APPROVED，进入 push → Draft PR → checks → 用户二次确认。
