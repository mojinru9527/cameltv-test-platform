# 🗂️ Dev 部门项目看板 — Batch 204 体育接口服务只读 GET 全量回归

## 📋 项目信息
| 字段 | 值 |
|------|-----|
| **项目名称** | 体育 8 服务只读 GET 全量回归（资产 + 用例） |
| **关联 PRD-lite** | [batch-204-sports-get-full-regression-prd-lite.md](../batch-204-sports-get-full-regression-prd-lite.md) |
| **总预估工时** | 4h（实际 ~4.5h） |
| **已用批次** | 1 批 |
| **看板创建** | 2026-08-25 |
| **最后更新** | 2026-08-25（QA PASS，待总确认合入） |

## 🎯 交付切片进度
| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 范围与黑名单口径（变更型 GET 豁免清单） | ✅ | ✅ | ✅ | ✅ | ⏳ | PRD-lite |
| 2 | 端点全量回归 523 条真实执行 + 分类矩阵 | ✅ | ✅ | ✅ | ✅ | ⏳ | 证据 JSON |
| 3 | GET 用例回归（is_deleted=0，10 条）+ 残留清理 | ✅ | ✅ | ✅ | ✅ | ⏳ | QA 报告 |
| 4 | B204-FIX-1 存量用例 URL 服务前缀（api_spec_ref 回退） | ✅ | ✅ | ✅ | ✅ | ⏳ | commit a049c95b |
| 5 | 三件套 + 看板 + C204-1/2/3 登记 | ✅ | ✅ | ✅ | ⏳ | ⏳ | 本批 docs |

## 📍 当前位置
```
Batch 204 — 回归矩阵产出（523 端点 + 10 用例），1 项平台缺陷已修（a049c95b）
├── ✅ 端点: PASS 75 / PASS_UNVERIFIED 5 / BUSINESS_ERR 193 / NEED_PARAMS 232 / NETWORK 18 / SERVER_ERR 0
├── ✅ 用例: 修复后 #2416 getById?id=1 → 200 + status=200 + data.id=1 all_pass
├── 🔄 待办: 用户一次总确认 → push → Draft PR → checks 绿 → 合入
└── ⏳ 遗留: C204-1（两副本服务网关无路由）/ C204-2（18 条慢接口）/ C204-3（负向断言口径）
```

## ⚠️ 阻塞与风险
| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| camel-service-final / camel-test-confirm 网关无路由 | P1 | 232 端点 + 5 用例 404；需确认服务状态后归档/启用 | 体育侧/网关运维 | 2026-08-25 |
| 18 条聚合类慢接口 | P2 | 25s+，引擎 30s 超时边缘 | 服务侧优化 | 2026-08-25 |
| 负向用例断言口径失配 | P2 | HTTP 4xx vs 网关信封 status=400 | Dev（下批） | 2026-08-25 |
| 605 条软删除迁移用例 | P3 | 占 GET 用例 97%，建议清理/归档视图 | QA 数据治理 | 2026-08-25 |

## 🔗 相关工件
| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD-lite | work-logs/batch-204-sports-get-full-regression-prd-lite.md | ✅ |
| QA 报告 | work-logs/batch-204-sports-get-full-regression-qa-report.md | ✅ |
| Leader 判决 | work-logs/batch-204-sports-get-full-regression-leader-verdict.md | ✅ |
| C 条件 | C204-1/C204-2/C204-3（C-CONDITIONS.md） | 🆕 |
