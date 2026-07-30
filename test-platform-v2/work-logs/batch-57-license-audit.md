---
title: "Batch 57 前后端生产依赖许可证审计"
owner: "qa-team"
created: "2026-07-29"
last_reviewed: "2026-07-30"
status: "closed-with-notice"
expires: "2027-01-29"
tags: ["batch-57", "license", "supply-chain", "production"]
related:
  - "batch-57-environment-targets-and-batch56-acceptance.md"
  - "../../docs/work-logs/batch-56-production-acceptance-execution-matrix.md"
---

# Batch 57 前后端生产依赖许可证审计

## 1. 结论

`G56-015` 的许可证审计证据已完成，可以关闭；但发布责任人仍必须遵循
`psycopg2-binary` 的归档与 NOTICE 要求。

- 前端 production dependency 清单已完整扫描，没有发现第三方
  GPL、AGPL、LGPL、UNKNOWN 或 Proprietary 包。
- 后端在干净 Linux Python 3.12 容器中以 `--require-hashes` 完整物化
  `requirements.lock` 的 111 个包，机器可读清单与 SHA 已归档；Windows
  环境的版本漂移不再作为锁文件审计证据。
- `psycopg2-binary==2.9.12` 是直接生产依赖，采用 LGPL with exceptions。
  本批已确定工程分发策略：外部分发必须随制品保留适用许可证、LGPLv3+
  正文、OpenSSL linking exception 和 NOTICE；实际发布仍需负责人做最终合规判断。
- `uvloop==0.22.1` 无 Windows 可用发行物，但已在 Linux 完整物化；以后在
  Linux CI/部署环境复跑同一命令即可。

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
| Linux 精确安装 | 111 / 111，版本逐项匹配 |
| 安装命令 | `python -m pip install --require-hashes -r requirements.lock` |
| 安装与导出退出码 | 0 |
| 机器可读清单 | `evidence/batch-57-license-audit/backend-requirements-lock-linux-licenses.json` |
| lock SHA-256 | `c52df71d6a82a12b1b0e8c5d90dd6fb99cc529e6001253516613cd68ccfefcd3` |

对扫描器异常元数据及缺失项进行了精确包复核：

| 包 | 许可证结论 | 处置 |
| --- | --- | --- |
| `caio==0.9.25` | Apache-2.0 | 发行包 `COPYING` 已复核 |
| `fastembed==0.8.0` | Apache-2.0 | wheel `LICENSE` 已复核；Other/Proprietary classifier 为元数据误报 |
| `py-rust-stemmers==0.1.8` | MIT | 官方仓库/发行包已复核 |
| `SecretStorage==3.5.0` | BSD-3-Clause | 精确发行物已复核 |
| `jeepney==0.9.0` | MIT | 精确发行物已复核 |
| `uvloop==0.22.1` | MIT / Apache-2.0 | 官方发行说明；需 Linux 物化 |
| `psycopg2-binary==2.9.12` | LGPL with exceptions | 已归档原文并建立强制 NOTICE/许可证随制品分发策略 |

官方复核入口：

- <https://www.psycopg.org/docs/license.html>
- <https://github.com/qdrant/fastembed>
- <https://github.com/qdrant/py-rust-stemmers>
- <https://pypi.org/project/SecretStorage/3.5.0/>
- <https://pypi.org/project/jeepney/0.9.0/>
- <https://pypi.org/project/uvloop/0.22.1/>

Linux 扫描器仍会原样标出 `fastembed==0.8.0` 的 Other/Proprietary 和
`py-rust-stemmers==0.1.8` 的 UNKNOWN 元数据；已用其精确发行包 LICENSE
复核为 Apache-2.0 和 MIT，故它们不是未评估许可证。`psycopg2-binary`
是唯一 LGPL 标记项。

已归档 `psycopg2_binary-2.9.12.dist-info/licenses/LICENSE` 的正文与来源
路径/哈希，并在 `../THIRD_PARTY_NOTICES.md` 写入外部分发时保留 LGPLv3+
及 OpenSSL linking exception 的工程要求。该记录不是法律意见；发布责任人
应按实际发行方式完成最终合规判断。

## 4. 已完成的关闭证据

1. Linux 容器精确安装与机器可读清单：
   `evidence/batch-57-license-audit/README.md`。
2. 111 项 JSON 清单及自身 SHA：
   `evidence/batch-57-license-audit/backend-requirements-lock-linux-licenses.json`。
3. psycopg2-binary LICENSE 正文与容器来源哈希：
   `evidence/batch-57-license-audit/psycopg2-binary-2.9.12-LICENSE`。
4. 外部分发 NOTICE 策略：`../THIRD_PARTY_NOTICES.md`。

以上是可复核的工程许可证审计证据；法律责任和实际发布决定仍由发布负责人承担。
