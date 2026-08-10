# Batch 131 — 用例模块树计数守恒 QA 报告
> **QA (🔍)** | Date: 2026-08-10 | Verdict: PASS（发布建议 READY）

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 5（PRD 验收标准） | 5 | 0 | 0 |

## 可执行门禁（命令 / 退出码 / 日志摘要）
| 门禁 | 命令 | 退出码 | 结果 |
|------|------|:---:|------|
| 定向 Vitest | `npx vitest run caseTaxonomyFilters.test.ts index.test.tsx DomainTree.test.tsx` | 0 | 3 文件 11 用例全过 |
| 前端类型检查 | `npm run typecheck`（tsc -b） | 0 | 无 TS 错误 |
| 前端构建 | `npm run build`（tsc -b && vite build） | 0 | built in 8.12s |
| 前端全量回归 | `npm test`（vitest run） | 0 | **109 文件 / 440 用例全过，无新增失败** |
| 常见 Bug 扫描 | `scan-common-bugs.ps1` | 2 | HARD=0，WARN=251（仓库基线，本批未引入 HARD；改动文件无 console/debugger/TODO 类） |
| C 条件审计 | `audit-cconditions.ps1 -RequireLatestBatch` | 0 | hard errors=0, warnings=0 |
| 浏览器验收 | Playwright（API mock + FAQ帮助 27 夹具，1440×900） | 0 | `browser-acceptance.json` status=pass |
| 截图核验 | vision（qwen-vl）描述截图 | 0 | 确认 `直属用例 (18)` 行存在，27 = 18+5+2+1+1 守恒 |

CI 分层：本批变更仅 `test-platform-v2/frontend/**` → 按 AGENTS.md §4.2 前端 required；后端重测试应跳过，不影响本批结论（无后端文件变更）。

## 逐条件验证（PRD §4）
| 验收标准 | 结果 | 证据 |
|----------|:---:|------|
| 父节点有直属用例时，展开后首个说明项显示 `直属用例 (差值)`，父级=直属+直接子级 | ✅ PASS | 浏览器：FAQ帮助 (27) 下渲染 `直属用例 (18)` + faq内容 (5) + 帮助中心 (2) + 异常恢复 (1) + 重复与并发 (1)；单元测试 countDirectCases(27,[5,2,1,1])=18；截图 vision 核验守恒 |
| 父节点没有直属用例时不显示 0 数量说明项 | ✅ PASS | countDirectCases(9,[5,2,1,1])=0；index.tsx 仅在 `direct > 0` 时插入核算行；单元测试覆盖 |
| 后端异常（子级合计>父级）时直属按 0 处理，不显示负数 | ✅ PASS | countDirectCases(8,[9])=0（Math.max 兜底）；单元测试覆盖 |
| 点击真实节点原筛选逻辑不变 | ✅ PASS | 浏览器：点击 用户端 / FAQ帮助 后 /test-cases 列表请求 1→2→3 递增，筛选仍触发 |
| 直属统计项不可点击且不发送请求 | ✅ PASS | 浏览器：核算行为 `div[role=note]` 非 button；点击后列表请求数保持 3 不变；DomainTree 单测断言 `queryByRole('button', name: /直属用例/) === null` |

**多模块通用性（用户确认项）**: 规则为递归实现，对任意业务域（surface→domain）与任意层级模块（module→submodule）统一生效：只要父节点存在直接子级且直属用例 > 0，即插入只读核算行。页面单测夹具已扩为“FAQ帮助 + 赛事详情/订单列表 二级模块”双域结构，浏览器证据同夹具验证，三处守恒全部成立，证明非 FAQ帮助 专属修复。

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 无 | - | - | - | - |

## 发布建议
状态: **READY** · 必修复: 0 · 建议修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 3h / 实际 2.5h | 0/0/0/0 | 0 | 流程 | 轻量修复批次先确认既有 worktree/PRD 状态再续跑，避免重复定位 |

**技能使用**: `vision` → 截图守恒核验（非测试证据）；`cameltv-agent-team` → 轻量批次工件约束；`cameltv-ui-conventions` → 只读核算行采用语义类 + role=note；`cameltv-bug-guard` → 无新增请求/副作用/接口漂移，N+1 铁律核查通过。
