# Batch 145 — QA 报告
> **QA (🔍)** | Date: 2026-08-11 | Verdict: PASS

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 12 | 12 | 0 | 0 |

## 可执行门禁（命令 + 退出码 + 摘要）
| 门禁 | 命令 | 退出码 | 结果 |
|------|------|--------|------|
| 后端全量 pytest | `.venv\Scripts\python -m pytest -q` | 0 | **1322 passed, 3 skipped, 0 failed**（290s；首轮 5 failed 均为 lanhu-mcp 子模块未初始化，`git submodule update --init` 后全绿） |
| 受影响 pytest | `pytest tests/test_lanhu_ocr_merge.py tests/test_lanhu_screenshot_service.py` | 0 | **25 passed** |
| ruff F821 | `python -m ruff check app --select F821` | 0 | All checks passed |
| 前端 typecheck | `pnpm run typecheck` (tsc -b) | 0 | 通过 |
| 前端 build | `pnpm run build` (vite) | 0 | 通过（9.16s） |
| 前端 vitest | `pnpm test` (vitest run) | 0 | **444 passed / 109 files** |
| 锁文件 Windows | `pip install --require-hashes --dry-run -r requirements.lock` | 0 | 通过（覆盖全部 117 包哈希） |
| 锁文件 Linux | Docker `pip install --no-cache-dir --require-hashes -r requirements.lock` | 0 | 通过（117 包含 rapidocr-onnxruntime 1.4.4 / opencv-python 5.0.0.93 / pyclipper / shapely / six） |
| 内置 CLI 实测 | `python -m app.services.lanhu_evidence.rapidocr_cli --image ocr-test.png` | 0 | 4 块中文全识别（赛事回放详情页面 / matchld 必填 / 分钟数必填 / 比赛推送开关），逐行 JSON 兼容 parse_command_output |
| Provider 全链路 | `LocalCommandOcrProvider().recognize(png)` | - | status=success, 4 blocks（子进程 UTF-8 + sys.executable 定位修复验证） |
| Linux 容器 OCR 冒烟 | Docker `python smoke.py`（apt 系统库 + 锁安装 + cv2 + rapidocr） | 0 | cv2 5.0.0 导入成功，4 块中文识别正确 |
| scan-common-bugs | `scan-common-bugs.ps1` | - | HARD=4：main.py:87 except:pass（基线，本批未改动）；rapidocr_cli 3 处 print 为 CLI stdout 数据通道契约（豁免，见缺陷区） |

## 逐条件验证
### C1: 内置 OCR 引擎默认可用（R1）
**变更文件**: `config.py:203` `local_ocr_provider.py` `rapidocr_cli.py` `requirements.txt/lock` `Dockerfile`
| 检查项 | 结果 | 说明 |
| **✅ PASS** | `lanhu_ocr_command` 默认 `{python} -m app.services.lanhu_evidence.rapidocr_cli --image "{image}"`；本地实测 CLI 与 Provider 均 status=success |
### C2: 保留低置信度文本（R2）
**变更文件**: `local_ocr_provider.py`
| **✅ PASS** | 移除 min_conf 过滤；单测 `test_local_provider_keeps_low_confidence_blocks` 验证 0.42 置信度块保留 |
### C3: 截图 2x DPR（R3）
**变更文件**: `screenshot_service.py:182-185` `config.py:198`
| **✅ PASS** | `browser.new_page(..., device_scale_factor=settings.lanhu_capture_device_scale_factor)`，默认 2.0；单测覆盖配置默认值 |
### C4: 前端展示最全文本（R4）
**变更文件**: `PrototypePreview.tsx:369`
| **✅ PASS** | 数据链路 batch-144 已用 merged_text；本批文案改为「该页提取文字（OCR+DOM 合并）」 |
### C5: 依赖可部署（win+linux）
**变更文件**: `requirements.txt` `requirements.lock`
| **✅ PASS** | 锁增量合并 5 个新包（纯新增 125 行、0 删除）；Windows `--require-hashes` dry-run 与 Linux 容器全量安装均通过 |
### C6: Dockerfile 系统库
**变更文件**: `Dockerfile`
| **✅ PASS** | ldd 实测 opencv 缺 libxcb/libGL/libglib 等，补齐 7 个 apt 包；Linux 容器 cv2 导入 + OCR 冒烟通过 |
### C7: 无调试遗留
**变更文件**: 全部
| **✅ PASS** | 无 console.log/debugger/breakpoint；rapidocr_cli 的 print 为 CLI 输出契约（见缺陷 D1 豁免说明） |
### C8: 回归
**变更文件**: 全部
| **✅ PASS** | 后端 1322 全量 + 前端 444 全量，无新增失败（基线无已知失败集合） |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| D1 | P3（豁免） | scan-common-bugs 将 rapidocr_cli.py 的 3 处 `print` 标记为调试遗留 | CLI stdout 是 subprocess 数据通道（逐行 JSON），stderr 为错误通道，属契约必需；若改用 logger 会破坏与 `parse_command_output` 的兼容 | 豁免（设计必需） |
| D2 | P3（基线） | audit-cconditions 报孤儿条件 C138-1/C140-1（leader-verdict 有、C-CONDITIONS.md 无） | origin/main 上同样缺失，批次 138/140 遗留，非本批引入 | 基线，建议后续批次同步追踪器 |
| D3 | P3（基线） | main.py:87 `except OSError: pass` | 本批未改动该文件 | 基线 |

## 发布建议
状态: **READY**    必修复: 0    建议修复: 0（D1 为设计必需豁免；D2/D3 为基线遗留，不影响本批）

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 6h / 实际 ~6h | 0/0/0/3 | 2（锁文件空行格式、{python} 占位缺失） | 依赖集成与跨平台路径 | 锁文件合并先对比原格式；子进程命令用 sys.executable 定位解释器 |

**技能使用**: `cameltv-bug-guard` → 依赖/部署铁律核对；`cameltv-agent-team` → 流水线门禁；锁文件增量生成经验（pip-compile 7.6.0 输出全平台哈希）将回写 KB。
