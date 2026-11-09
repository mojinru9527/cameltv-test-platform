# Batch 281（M1 / TA-007）— QA Report

> **部门**：🔍 QA · **日期**：2026-11-10

| # | 标准 | 结果 | 证据 |
|---|------|:----:|------|
| A1 | 上传/下载 roundtrip | ✅ | sha256/size/mime/URI 全对 |
| A2 | 同 hash 去重 | ✅ | 2 行 1 文件、URI 相同 |
| A3 | 跨项目 403 | ✅ | get/list/read/mark_redaction 全抛 |
| A4 | 非法参数 | ✅ | 类型/成对引用/未知 run |
| A5 | 脱敏单向 | ✅ | sanitized→rejected 被拒 |
| A6 | 路径穿越 | ✅ | `/etc/passwd` 抛 ArtifactStorageError |
| A7 | 迁移 + 回归 | ✅ | up/down/up 0/0/0；1392 passed；ratchet PASS |

## 缺陷

| # | 现象 | 修复 |
|---|------|------|
| 1 | mypy `Settings has no attribute storage_dir` | `getattr(settings,"storage_dir",None) or "storage"` |
| 2 | PowerShell 内联 Python 引号失败（工具问题，非代码） | 改用补丁脚本文件 |

## 风险

- 生产对象存储未接（本批仅 FS）；M1 Console 联调前先用 FS；
- 无留存/GC：文件只增不减，运维批次补 retention。

## 判定

A1–A7 全绿，建议 Leader APPROVED。
