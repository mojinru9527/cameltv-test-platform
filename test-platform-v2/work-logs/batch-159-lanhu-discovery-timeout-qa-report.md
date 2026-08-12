# Batch 159 — QA 报告（蓝湖提取失败热修）

> **QA (🔍)** | Date: 2026-08-12 | Verdict: PASS | Mode: light

## 门禁
| 项 | 结果 |
|----|------|
| ruff F821 | ✅ 0 |
| 受影响 pytest | ✅ 85 passed（蓝湖全量：page_discovery/worker/import/models/latest_version/provider/login/cookie/batch159×5） |
| 子模块 | ✅ lanhu-mcp 初始化到 pinned 3cfd2ef |
| 调试/凭据残留 | ✅ 无（未打印 Cookie/密码） |

## 逐项验证
| 检查项 | 结果 |
|--------|------|
| 超时自动重试 1 次后成功 | ✅ 单测（首次 httpx.ReadTimeout → 第二次 downloaded） |
| 空 str 异常透出类型名 | ✅ 单测（TimeoutError() → error 含 TimeoutError） |
| discover_pages 兜底含 status | ✅ 单测（provider status=failed） |\n| 有界下载（capture_all_pages=false+pageId） | ✅ 只下目标页/同文件夹，其它页面不下；目标页缺失回退全量（单测×2） |\n| 全量路径顺序保持 | ✅ 受限下载仍先失败，不生成页面证据（既有契约测试通过） |
| 常量放宽 | ✅ 1000 / 300MB / 300s（新 MCP 生效）；整体超时 600s |
| 旧版 MCP 兼容 | ✅ inspect signature 只传支持参数，行为不变 |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 实际约 1h | 0/1/0/0 | 1 | 外部依赖无整体超时 + 空异常 str 被吞 | 外部 I/O 必须整体超时 + 异常透出 `str(e) or type`；上线前对真实链接冒烟 |

