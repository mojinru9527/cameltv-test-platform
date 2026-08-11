# Batch 145 — Leader Verdict
> **Leader (🎯)** | Date: 2026-08-11 | Decision: APPROVED

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 4.5/5 | 根因定位准确（4 点叠加），方案最小化落地；锁文件双平台验证、Linux 容器 OCR 冒烟证据充分 |
| 风险 | 低 | 新依赖 opencv-python 5.0（rapidocr 约束解析所得）已实测可用；模型随 wheel 打包无运行时下载风险；CLI 每段启动子进程可接受 |
| 覆盖 | 4.5/5 | 后端 1322 / 前端 444 全量通过；OCR 实测中文 4 块全识别 |

## 关键决策（已批准）
1. **采用 rapidocr_onnxruntime 1.4.4**（CPU 中文 OCR 最优解：PP-OCRv4、模型随 wheel 打包 ~16MB、无 torch/paddle 重依赖）。否决 PaddleOCR（重一个量级）/ EasyOCR（需 torch）/ Tesseract（中文弱）/ 云 API（需联网+费用）。
2. **内置 OCR CLI + 命令模板默认指向**：`lanhu_ocr_command` 默认 `{python} -m app.services.lanhu_evidence.rapidocr_cli --image "{image}"`；`{python}` 由 provider 替换为 `sys.executable`，规避 Windows venv 未激活时子进程解析到系统 python 的缺陷。
3. **保留全部识别块**：移除 `lanhu_ocr_min_confidence` 过滤，置信度仅作参考展示，根治小字/模糊字缺失。
4. **截图 2x DPR**：`lanhu_capture_device_scale_factor=2.0`，小字更清晰，提升 OCR 命中率。
5. **锁文件增量合并**：pip-compile 7.6.0 增量解析 5 个新包（opencv-python/pyclipper/rapidocr-onnxruntime/shapely/six），win/linux 哈希一致（pip-compile 7.6 默认输出全平台哈希），保留原锁格式与头部注释，双平台 `--require-hashes` 验证通过。
6. **Dockerfile 补 opencv 系统库**（ldd 实测）：libgl1 libglib2.0-0 libxcb1 libx11-6 libxext6 libsm6 libice6。

## 抽检通过
- ✅ `config.py:198,203` — 新配置默认值与内置 CLI 模板正确。
- ✅ `local_ocr_provider.py:62-81` — {python}/{image} 替换 + UTF-8 子进程解码 + 无置信度过滤。
- ✅ `rapidocr_cli.py` — 逐行 JSON 输出契约，bbox 4 点归一化，模型随包离线可用。
- ✅ `screenshot_service.py:182-185` — device_scale_factor 透传。
- ✅ `requirements.lock` — 纯新增 125 行（5 包），0 删除，头部注释保留。
- ✅ `Dockerfile` — apt 系统库追加（无续行注释陷阱）。
- ✅ QA 硬门禁全绿：后端 pytest 1322 passed / ruff F821 0 / 前端 typecheck+build / vitest 444 passed。
- ✅ 锁文件 Windows `--require-hashes --dry-run` 与 Linux 容器全量安装通过；Linux 容器 cv2+rapidocr OCR 冒烟通过。

## 判决
**APPROVED**。用户一次总确认（推送+PR+合入）后，待 PR 必需检查全绿、`audit-ai-pr -RequireSuccessfulChecks` 通过即可 squash 合入 main。

## 下一批次 Leader 条件
- 无新增。本批内完成追踪器补登：C138-1（批次 137 要求“生产配置真实 OCR 引擎”）由本批实现（内置 rapidocr 默认生效）并关闭；C140-1（Railway 控制台加卷）置 Deferred（外部执行项）。

## 知识审计
(a) 本批可入库知识：
- rapidocr_onnxruntime：CPU 中文 OCR 选型结论 + 模型随 wheel 打包（无需下载）+ opencv-python 在 slim 镜像需 libxcb/libGL 等系统库。
- pip-compile 7.6.0 增量生成锁：输出全平台哈希（win/linux 一致），合并时保留原锁格式与头部注释。
- 子进程 OCR 命令必须用 `sys.executable` 定位解释器（Windows venv 未激活时 `python` 解析到系统解释器）。
(b) 已入库：`test-platform-v2/work-logs/evidence/batch-145/knowledge-notes.md`（本批工件内，scope 合规）。
(c) 与既有 KB 冲突：无。

## 流程回写
| 发现 | 处理 | 落点 |
|------|------|------|
| C138-1/C140-1 孤儿条件（verdict 有、追踪器无） | 本批内补登：C138-1 关闭（证据=本批实现+Linux 容器 OCR 冒烟），C140-1 置 Deferred（外部 Railway 加卷） | C-CONDITIONS.md + 本判决 |
| scan-common-bugs 将 CLI stdout print 标记为调试遗留 | 豁免（subprocess 数据通道契约），QA 报告 D1 记录 | batch-145 QA 报告 |
| 锁文件合并易引入格式噪音（空行/头注释） | 本批修正为纯新增 125 行；经验入知识库 | evidence/batch-145/knowledge-notes.md |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 6h / 实际 ~6h | 0/0/0/3 | 2 | 依赖集成 + 跨平台解释器路径 | 锁合并先比对原格式；子进程命令用 sys.executable |

**技能使用**: `cameltv-agent-team` 六部门流水线；`cameltv-bug-guard` 依赖/部署铁律；`cameltv-ui-conventions` 前端走查（无样式变更）。
