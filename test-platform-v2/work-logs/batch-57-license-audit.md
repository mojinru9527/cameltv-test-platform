---
title: "Batch 57 前后端生产依赖许可证审计"
owner: "qa-team"
created: "2026-07-29"
last_reviewed: "2026-07-29"
status: "partial"
expires: "2027-01-29"
tags: ["batch-57", "license", "supply-chain", "production"]
related:
  - "batch-57-environment-targets-and-batch56-acceptance.md"
  - "../../docs/work-logs/batch-56-production-acceptance-execution-matrix.md"
---

# Batch 57 前后端生产依赖许可证审计

## 1. 结论

`G56-015` 保持 `OPEN / PARTIAL`，本次不能关闭。

- 前端 production dependency 清单已完整扫描，没有发现第三方
  GPL、AGPL、LGPL、UNKNOWN 或 Proprietary 包。
- 后端 `requirements.lock` 有 111 个精确锁定包，但当前 Windows Python
  环境只有 67 个版本完全匹配、41 个版本漂移、3 个缺失，不能用当前环境的
  `pip-licenses` 结果冒充锁文件全量结论。
- `psycopg2-binary==2.9.12` 是直接生产依赖，采用 LGPL with exceptions。
  发布负责人仍需确认分发/归档方式，并保留适用的许可证和 NOTICE。
- `uvloop==0.22.1` 在锁文件中没有平台条件，当前 Windows 无可用发行物，
  导致按锁文件的完整 hash 下载在解析阶段退出。最终扫描必须在干净 Linux
  CI/部署环境执行。

## 2. 前端证据

| 检查 | 结果 |
| --- | --- |
| 锁文件 | npm package-lock v3 |
| 直接 production dependencies | 44；与 `package.json` 一致 |
| 扫描实例 | 235 |
| 命令 | `npx --yes license-checker --production --json` |
| 退出码 | 0 |
| 禁止/待确认第三方许可证 | 0 |

许可证分布：

| 许可证 | 数量 |
| --- | ---: |
| MIT | 176 |
| ISC | 36 |
| BSD-2-Clause | 9 |
| Apache-2.0 OR MIT | 4 |
| BSD-3-Clause | 3 |
| 其他宽松许可证 | 6 |
| UNLICENSED | 1 |

唯一 UNLICENSED 项是仓库根包 `cameltv-test-frontend@2.1.0`，其
`package.json` 明确 `private: true`，不是第三方依赖。

## 3. 后端证据

| 检查 | 结果 |
| --- | --- |
| 锁定包 | 111 |
| 当前环境精确匹配 | 67 |
| 当前环境版本漂移 | 41 |
| 当前环境缺失 | 3 |
| `pip-licenses` 当前环境扫描 | 退出码 0，仅作差异分析 |
| 锁文件 hash 下载 | 退出码 1；`uvloop==0.22.1` 不支持当前 Windows |

对扫描器异常元数据及缺失项进行了精确包复核：

| 包 | 许可证结论 | 处置 |
| --- | --- | --- |
| `caio==0.9.25` | Apache-2.0 | 发行包 `COPYING` 已复核 |
| `fastembed==0.8.0` | Apache-2.0 | wheel `LICENSE` 已复核；Other/Proprietary classifier 为元数据误报 |
| `py-rust-stemmers==0.1.8` | MIT | 官方仓库/发行包已复核 |
| `SecretStorage==3.5.0` | BSD-3-Clause | 精确发行物已复核 |
| `jeepney==0.9.0` | MIT | 精确发行物已复核 |
| `uvloop==0.22.1` | MIT / Apache-2.0 | 官方发行说明；需 Linux 物化 |
| `psycopg2-binary==2.9.12` | LGPL with exceptions | 需负责人确认分发与 NOTICE 策略 |

官方复核入口：

- <https://www.psycopg.org/docs/license.html>
- <https://github.com/qdrant/fastembed>
- <https://github.com/qdrant/py-rust-stemmers>
- <https://pypi.org/project/SecretStorage/3.5.0/>
- <https://pypi.org/project/jeepney/0.9.0/>
- <https://pypi.org/project/uvloop/0.22.1/>

## 4. 关闭条件

1. 在干净 Linux CI/部署环境按 `requirements.lock` 精确安装或下载全部 111
   个包，并产出机器可读许可证清单。
2. 核对清单中无未评估的 GPL/AGPL/UNKNOWN/Proprietary。
3. 发布负责人确认 `psycopg2-binary` 的 LGPL 分发/归档方式。
4. 将许可证文本、NOTICE、命令、退出码、固定 lock SHA 和报告一并归档。

完成以上四项后才能关闭 `G56-015`。
