# Batch 232 - Leader Verdict

> Leader | Date: 2026-09-07 | Decision: **有条件通过（平台代码）**；Mission 9101 业务验收仍为 **FAIL**

## 判决摘要

平台改造方向正确，代码与本地回归门禁已通过；Mission 9101 的真实 Quality Gate 为 4/5，UI 自动化在 Test5 发现 11 个资源/控制台错误，缺陷 `B232-TEST5-001` 尚未复验关闭。

Leader 将“测试平台版本是否可发布”和“被测篮球业务是否通过”拆成两个结论。平台准确暴露 FAIL 是正确行为，不能因为发现被测系统缺陷而禁止平台修复上线；因此平台代码在用户总确认、Draft PR required checks 与最终审计通过后可转为 APPROVED 并发布。Mission 9101 继续打回，不能改写成 PASS。

旧 Leader“条件通过”判决失效。原因不是页面缺少文案，而是此前没有以非空资料片段、逐用例执行、物理证据、Build/Campaign、变化/影响/Lineage/缺口记录作为通过前提。

## 审查结果

| 维度 | 结果 | 说明 |
|---|---|---|
| 需求适配 | 通过 | 需求 → 分析 → 契约 → 三类用例 → 执行/证据 → 验收已形成事实链 |
| 数据真实性 | 通过 | 空片段、占位数据、缺 Build/Campaign、缺执行证据都会失败关闭 |
| 页面可解释性 | 通过 | 用户提出的资料、范围、契约、场景、执行及 6 个后续页均显示真实数据 |
| 平台回归 | 通过 | 后端 2510、前端 695；静态、构建、迁移和浏览器检查通过 |
| 被测业务 | **未通过** | Test5 UI 用例 BUSINESS_FAIL，Gate G5 未通过 |
| AI 成本控制 | 通过 | 稳定公共前缀、OpenAI 路由键、供应商 usage 落库和相同请求去重均有测试 |
| 生产状态 | **未发布** | 分支未推送、无 PR、未合并 main、未部署生产；平台发布等待远端门禁 |

## 打回条件

1. 修复或明确处置 Test5 的 Google GSI 403、图片代理 503/504、NBA CDN HTTP2 错误。
2. 从 UI Run #3 创建的原始失败链执行复验，保留新的截图、视频、步骤和断言证据。
3. Quality Gate 必须重新计算为 5/5，不能人工覆盖为 PASS。
4. 生产发布后，在生产测试平台新建/关联 16.0.0 任务并分别执行需求测试、版本回归、生产回归；不得复用历史空任务。

在以上业务问题关闭前，Leader 不授权把 Mission 9101 标记为通过。平台代码交付必须先按仓库规则重新取得一次总确认，并在 Draft PR required checks 全绿及最终审计通过后才可合入；最终 APPROVED 只能在这些条件满足后给出。生产发布仍走独立发布流程。

## 已确认的设计原则

1. 生命周期状态是持久化事实的投影，不是预期步骤清单。
2. FUNCTIONAL、API、UI 三条 lane 缺一不可完成。
3. 每条 Run 必须有步骤、断言、已校验物理证据和回放清单。
4. 验收必须绑定真实 Build 与 Campaign；完整证据链仍可能得出 FAIL。
5. 变化、影响、Lineage 和场景缺口必须来自对应记录，不能由前端补默认值。
6. 历史 PASS 与当前事实不一致时必须降级为 `NOT_EVALUATED`。
7. 供应商缓存只对输入前缀生效；输出不宣称“命中缓存”，相同请求通过应用内去重避免再次生成。
8. OpenAI 专用缓存字段必须按官方 hostname 门控；非 OpenAI 兼容端点只利用其原生自动缓存与 usage 字段。

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 空资料/占位数据可被误判为完成 | 生命周期完整性改为验证非空片段、有效引用、三 lane、执行证据和验收实体 | `test-platform-v2/backend/app/modules/aitde/mission/lifecycle.py` + 后端生命周期测试 |
| 完整事实链不等于业务通过 | 保留 `integrity_status=COMPLETE`，同时由 Gate 独立输出 `acceptance=FAIL` | 生命周期服务、验收页、QA 报告 |
| 加载动画曾被当作响应式证据 | 浏览器验收必须等待业务文本锚点后截图 | `work-logs/evidence/batch-232-ai-test-lifecycle/platform-ui/browser-report.json` |
| 子页面重复读取聚合接口 | 场景页复用 MissionLayout 的同一查询缓存并逐页统计请求 | `test-platform-v2/frontend/src/pages/missions/scenarios.tsx` + 浏览器报告 |
| AI usage 被共享客户端丢弃 | 归一化 OpenAI/DeepSeek 缓存字段并写入 AI 操作记录 | `test-platform-v2/backend/app/services/ai_client.py` + AI 调试抽屉 |
| 相同歧义/意图请求重复生成 | Provider 单操作精确去重，稳定公共前缀支持跨 Mission 供应商缓存 | AITDE provider + `cache-v1.txt` |

## 知识审计

- 可复用知识已写入本批 PRD、QA、Leader 流程回写与回归测试：稳定内容必须位于动态需求之前，供应商专用字段必须按真实 hostname 门控。
- 与仓库现有“统一共享 AI client”“不伪造 AI 成功/数据”的知识一致，无冲突；本批不新增外部依赖或跨模块缓存存储。
- 不建立跨任务持久化输出缓存，因为需求、合同与审批状态变化会造成陈旧测试结论；仅在单次操作内对精确相同输入去重。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 12h / 实际跨会话无法可靠计量 | 0/3/2/0 | 3 | 流程 + 外部依赖 + 成本可观测性 | Leader 抽检同时核对事实、物理证据、最终 Gate 与供应商 usage，不接受页面状态或估算值代替真实证据 |

**Skills used**: Agent Team 管理判决和流程回写；Bug Guard 约束失败关闭；UI conventions 约束状态可读性；Playwright 提供三视口及逐页请求证据。
