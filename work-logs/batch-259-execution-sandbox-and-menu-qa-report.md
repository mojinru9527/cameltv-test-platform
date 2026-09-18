# Batch 259 — QA 报告

> **QA (🔍)** | Date: 2026-09-19 | Verdict: **PASS（附 2 条 C 条件）**
> 批次档位：完整批次（六件）。范围：`docs/platform-refactor/10-...backlog.md` §2 的 B2-1…B2-6。

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 6（B2-1…B2-6） | 6 | 0 | 0（2 条局部不成立项转 C 条件，未伪造成通过） |

## 可执行门禁（命令 / 退出码 / 摘要）

### 后端

| 命令 | 退出码 | 摘要 |
|------|:------:|------|
| `python -m ruff check app/ --select F821` | 0 | All checks passed! |
| `python -c "import app.main"` | 0 | import OK |
| `python -m alembic heads` | 0 | `20260924_batch258_execution_payload (head)` —— 单头（本批无新迁移） |
| `pytest`（本批域 9 个文件） | 0 | **85 passed, 1 skipped**（skip = 符号链接需 Windows 开发者模式） |
| `pytest tests/test_execution_sandbox.py tests/resource_budget` | 0 | 77 passed, 2 skipped |

### 前端

| 命令 | 退出码 | 摘要 |
|------|:------:|------|
| `npm ci` | 0 | 850 packages（无新增依赖） |
| `npm run typecheck` | 0 | `tsc -b` 无错误 |
| `npm run lint` | 0 | `eslint . --max-warnings=0` 无告警 |
| `npx vitest run --maxWorkers=2` | 0 | **165 文件 / 722 例全绿** |
| `npm run build` | 0 | `✓ built in 10.21s` |

> 本机首次 `npm test` 触发 **JS heap OOM**（16GB 机器，与审计基线记录的 pytest MemoryError 同源）。
> 改用 `--maxWorkers=2` 后全绿；CI 跑在内存更大的 runner 上，不受此限制。
> 该现象记入下方缺陷 D4，供后续批次复用解法。

## 逐条件验证

### B2-1: 本地执行沙箱 H1 ✅ PASS（关闭 C258-2）
**变更**: `app/core/execution_sandbox.py`（边界声明 + 白名单下发）、`app/core/config.py`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 无平台 SECRET / DB 口令 | ✅ | **真起子进程**读 `SECRET_KEY`/`DATABASE_URL`/provider token 全为 `None` |
| E2E 契约变量保留 | ✅ | `CAMELTV_BASE_URL` 仍透传（否则体育用例会因缺变量失败） |
| 出网白名单唯一事实源 | ✅ | `execution_egress_allowlist` → `CAMELTV_EGRESS_ALLOWLIST`；未配置时不臆造 |
| 读 `.env` / 连内网 / 写持久卷被拒 | ✅ | 三类代码在执行前被 `spec_guard` 拦截 |
| 边界如实声明 | ✅ | docstring 明写"进程内做不到内核级隔离，属部署层"；并有断言守着这句话 |

### B2-2: 危险 API 静态拦截 ✅ PASS
**变更**: `app/core/spec_guard.py`（新增）+ 三条执行路径接入
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 含 `execSync` 的 spec 执行前被拒 | ✅ | 断言 `subprocess.run` **从未被调用**，并给出含行号/规则名的可读原因 |
| 覆盖"生成代码→执行"全链路 | ✅ | playground（落盘前）/ playwright_executor（起进程前，覆盖 ui_test 与计划执行）/ 编译器（编译期提示） |
| 不误伤正常用例 | ✅ | `page.goto`/`page.request`/`waitForResponse` 全放行；仅 `CAMELTV_*` 环境变量可读 |

### B2-3: 纠正「dry-run = 沙箱」 ✅ PASS
**变更**: `app/services/case_compiler_service.py`、`app/services/test_plan_service.py`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 不再把 dry-run 称作沙箱 | ✅ | 编译器模块内 0 处 sandbox；全仓无 sandbox 与 dry-run 同行 |
| 计划执行路径无 `validate=False` | ✅ | 已移除；测试断言该实参写法不得出现 |
| 默认开启校验 | ✅ | `compile_to_playwright.validate` 默认 `True`（签名断言） |

### B2-4: 本地对象存储路径收敛 ✅ PASS（关闭审计 S4）
**变更**: `app/integrations/object_storage/local.py`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| `../../etc/passwd` 形式 URI 被拒 | ✅ | 含 `../`、`..\..\`（Windows 分隔符）、深层穿越、空/空白 URI |
| 逃逸写入未发生 | ✅ | 断言 base 之外的文件不存在 |
| 符号链接逃逸 | ✅ | `resolve()` + `is_relative_to` 兜住（Windows 无权限时 skip，不伪造） |
| 正常读写删不受影响 | ✅ | 往返、深层目录创建、`/project/...` 前导斜杠规范形式 |

### B2-5: 密钥派生统一 + 启动 fail-fast ✅ PASS（关闭审计 S5）
**变更**: `app/services/ai_config_service.py`、`app/core/cipher.py`、`app/main.py`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 单一派生实现 | ✅ | Fernet 密钥构造（`urlsafe_b64encode`）全仓仅 `cipher.py` 1 处 |
| 两处密文互认 | ✅ | `ai_config_service` 加密 → `cipher` 解密；反向亦然 |
| 无 SECRET_KEY + 有密文 → fail-fast | ✅ | 启动即报错，文案给出两种修法；无密文时不误报 |
| 密钥轮换仍走可读业务错误 | ✅ | 既有契约不变（避免裸 500） |

### B2-6: 一级菜单收敛 4 入口 + 专家区 ✅ PASS（1 条局部不成立项 → C259-1）
**变更**: `frontend/src/layouts/nav-config.ts`、`AssetsMoreGroup.tsx`、`MainLayout.tsx`、`page-explanations.ts`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| tester 一级导航 ≤4 | ✅ | 恰好 4：我的待办 / 版本验收 / 结果与缺陷 / 知识库；新增 `PRIMARY_ENTRY_LIMIT` 与防回涨断言 |
| 专家区独立且不占额度 | ✅ | 原「资产与更多」更名「专家区」，二级容器 + 权限门禁 |
| 隐藏 ≠ 删除 | ✅ | 每个可见菜单恰好出现一次；`/requirement`、`/testcase`、`/apitest`、`/uitest` 等路由仍在（路由表核对 + 断言） |
| 被隐藏页面可经**搜索**直达 | ❌ | **平台当前没有全局搜索/命令面板**（`rg` 无命中）——本批不新增该能力，登记 C259-1，不伪造 |

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|:------:|------|------|------|
| D1 | P3 | 守卫被自己的注释误伤（B2-5）：注释里写了 `sha256(settings.secret_key)`，命中「单一派生」检查 | 首轮 `test_only_cipher_py_derives_key_from_secret` FAIL | ✅ 改措辞，未放宽守卫 |
| D2 | P3 | 同类问题二次出现（B2-3）：注释里写了 `validate=False`，命中「计划路径不得关闭校验」检查 | 首轮断言 FAIL | ✅ 改措辞；已在测试注释里写明"prose 也会命中" |
| D3 | P3 | 新 IA 的分组项顺序期望写错（按 `sort` 而非 `codes` 顺序） | `nav-config.test.ts` 2 例 FAIL | ✅ 按既有契约（codes 顺序）修正期望 |
| D4 | P3 | 本机全量 `npm test` JS heap OOM（非代码缺陷） | `FATAL ERROR: JavaScript heap out of memory` | ✅ 以 `--maxWorkers=2` 复跑全绿；解法记入本报告供后续复用 |

无未修复缺陷。D1/D2 是同一类问题（字面量守卫 vs 散文），已连续两批出现 → 见下文 bug-guard 第 1 问。

## bug-guard「未关闭已知风险」表核对（每批必答三问）

**1) 本批是否新增了清单中的任一项？** 否（但有 1 条"复发模式"需登记）。
- 本批引入的新路径均按铁律加守卫：对象存储写入（收敛）、密钥派生（单一实现）、生成代码执行（静态拦截 + 环境白名单）。
- **复发模式登记**：D1/D2 属于"字面量守卫被散文误伤"，与清单中的静态检查类问题同源。
  处理：已在两条测试注释里写明该机制；**未升级为自动检查**（避免过度工程），
  但若第三次出现，按 bug-guard 规则 3 应升级为可执行校验。

**2) 本批是否修复/关闭了其中任一项？** 是，关闭 2 条 + 1 条部分关闭：

| 编号 | 风险 | 关闭证据 |
|------|------|---------|
| S4 | 本地对象存储路径未收敛 | commit `6c4b7942`；`tests/test_batch259_object_storage_containment.py` 17 例 |
| S5 | 密钥加密两套派生 | commit `9da274f8`；`tests/test_batch259_key_derivation_unification.py` 9 例 + 2 条可执行校验 |
| S6 | 把 dry-run 当沙箱 | **部分关闭**：表述纠正（`58bfc5b8`）+ 危险 API 静态拦截（`1c216955`）；真正的无凭据沙箱容器仍需节点侧部署层落地 → **C259-2** |

**3) 本批新增的「外部输入 → 出网 / 落盘 / 执行代码」路径，是否都过了对应铁律？** 是：

| 路径 | 铁律 | 校验 |
|------|------|------|
| 生成代码落盘（playground/编译器） | 执行前静态拦截 | `test_batch259_spec_guard.py` 20 例（含"起进程前拒绝"） |
| 生成代码执行（playwright_executor） | 执行前静态拦截 + 环境白名单 | 同上 + `test_batch259_execution_sandbox_h1.py` |
| 对象存储写入 | 路径拼接必须收敛 | 17 例（含符号链接逃逸） |
| 密文读写 | 单一密钥派生 | 9 例（含 fail-fast） |

## CI 分层核对

本 PR 改动 `test-platform-v2/backend/**` + `test-platform-v2/frontend/**` + `work-logs/**`
→ 前后端 required 都会实跑，**不存在跳过**。QA 不依赖 job 名称推断质量：上表门禁均在本机 worktree 实跑并记录退出码。

## 发布建议

状态：**READY**（B2-1…B2-6 全绿；2 条局部不成立项已如实登记为 C 条件）
必修复：0　建议修复：0

**行为变更提示（需随发布说明）**：
1. 一级导航由 5 个控件收敛为 4 入口 + 专家区；需求源从资产桶移到「版本验收」；
2. 计划执行路径恢复语法校验（编译期会跑 `npx tsc` + `playwright test --dry-run`，各 15s 超时，`npx` 缺失时优雅降级）；
3. 未配置 `SECRET_KEY` 且库中已有密文时**拒绝启动**（部署前需确认）；
4. 含危险 API 的 spec 在执行前被拒（此前会真的执行）。

## 复盘卡（Batch 75 起强制）

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 22h / ~14h | 0/0/0/4 | 3 | 工具链（字面量守卫 vs 散文）+ 环境（内存） | 写"字面量守卫"时先约定：测试断言的目标文案不要出现在注释里，注释用改写表述（本批已两次踩坑） |

**技能使用**: `cameltv-bug-guard` → 三问与未关闭风险表核对（非测试证据）；`cameltv-agent-team` → 批次档位与工件骨架（非测试证据）；`cameltv-ui-conventions` 未调用（本批 UI 变更是导航结构而非组件样式，未涉及样式规范判定）。
