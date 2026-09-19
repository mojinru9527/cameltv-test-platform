# Batch 261 — Design Spec

> **Design (🎨)** | Date: 2026-09-19 | Status: 就绪

## 0. 技术体系确认

后端 FastAPI + SQLAlchemy 2.0 + Alembic；前端 shadcn/ui + Radix + Tailwind。本批以证据可校验性与试点制备为主。

## 1. 模块与接口规格

### 1.1 `app/services/evidence_bundle_service.py`（B4-1，新增）

| 符号 | 契约 |
|------|------|
| `FILE_TYPE_MAP` | 文件名后缀 → `EvidenceType` 的唯一映射（见 §1.2）；**这是本批新增的唯一"新口径"**，其余全部复用既有策略 |
| `evidence_type_for(name) -> str \| None` | 按后缀判定；未识别返回 None（计入 `unclassified`，不参与必需证据判定） |
| `verify_bundle(job_id, attempt, *, adapter_type, oracle_type) -> dict` | 逐文件 sha256 比对 + 缺失/多余检测 + 必需证据判定 |
| `adapter_oracle_for_kind(kind) -> tuple[str, str]` | `api → (API, API)`、`web → (UI, UI)`；未知 kind → `(MANUAL, UI)`（保守） |

返回结构：

```json
{
  "job_id": 12, "attempt": 1,
  "verdict": "verified | tampered | missing | incomplete",
  "files": [{"name": "c1.request.json", "evidence_type": "REQUEST",
             "status": "ok|tampered|missing", "expected_sha256": "…", "actual_sha256": "…"}],
  "tampered": ["…"], "missing": ["…"], "extra": ["…"], "unclassified": ["…"],
  "completeness": {"required": ["REQUEST","RESPONSE"], "present": ["REQUEST"],
                   "missing": ["RESPONSE"], "complete": false}
}
```

### 1.2 文件名 → EvidenceType 映射（唯一新口径）

| 后缀 | EvidenceType | 依据 |
|------|--------------|------|
| `*.request.json` | `REQUEST` | 节点 `run-api` 落盘的请求回放 |
| `*.response.json` | `RESPONSE` | 节点 `run-api` 落盘的响应 |
| `*.png` | `SCREENSHOT` | 节点 `run-web` 截图 |
| `*.console.json` | `CONSOLE` | 节点 `run-web` 控制台错误 |
| `*.trace.zip` | `PW_TRACE` | Playwright trace（若节点上传） |
| `results.json` / `manifest.json` | 不参与必需证据 | 属汇总与清单，不是"证据类型" |

### 1.3 新增接口

| 接口 | 契约 |
|------|------|
| `GET /execution-jobs/{job_id}/evidence/verify?attempt=` | 返回 §1.1 结构；权限 `execution:view`；无 bundle → `verdict="missing"` 且 `reason` 可读 |

### 1.4 前端 `EvidenceBundlePanel`

| 状态 | 呈现 |
|------|------|
| 通过 | 每文件绿色/中性徽标；显示"必需证据齐备" |
| 篡改 | 该文件行 `text-destructive` + `tampered` 徽标；顶部汇总"校验失败：N 个文件被改动" |
| 缺失 | 列出缺失的**必需证据类型**（而不是只列文件名），回答"还缺什么" |
| 错误 | 可重试 + 可读原因 |

## 2. 与既有策略的收敛（关键决策）

**不新建完整率口径**：`completeness.required_evidence(adapter, oracle)` 与 `is_complete(present, required)` 仍是唯一判定实现；
本服务只做两件事——把外部证据包**翻译**成该策略能吃的输入，以及**在判定前把篡改/缺失的文件排除**。

**为什么"篡改的文件不算满足必需证据"**：既有策略的 V3.9-R1 加固写得很清楚——"A required evidence is COMPLETE only when the artifact is physically usable — sanitized, hash-valid, non-empty, and confirmed present"。
如果只在 verdict 上标 `tampered` 却仍把它计入必需证据，就会出现"证据被改过、但完整率 100%、放行结论照样成立"的荒唐结果。本批用测试把这条钉住。

## 3. 设计 QA 走查发现（附文件:行号）

### 🟠 P2-1 两处"完整率"口径并存的风险
`app/services/execution_evidence_store.py`（B1 落的 manifest/sha256）与 `app/modules/aitde/assertion/completeness.py`（既有策略）都能回答"证据齐不齐"，但互不知道对方。
→ **建议**：本批让前者产出 manifest、后者做判定，中间由 `evidence_bundle_service` 翻译（§2），**不做第二套判定**。

### 🟠 P2-2 篡改检测若只做"标记"会留下放行漏洞
只报 `tampered` 而不把它排除出必需证据 → 被改过的证据仍可满足完整率。
→ **建议**：判定输入先剔除 `tampered/missing` 文件（§2），并用测试固化。

### 🟡 P3-1 未识别文件名的处理
节点未来新增证据类型（如 `*.trace.zip`）时，若直接忽略会让"完整率 100%"掩盖"有新证据没被校验"。
→ **建议**：返回 `unclassified` 清单（不参与必需证据判定，但显式可见）。

### 🟡 P3-2 本机无环境导致 B4-3/4/5 无法产出真实数字
Test5 需 VPN（`C258-1`）、库内无体育资产（`C260-1`）。
→ **建议**：B4-3/4/5 交付"一条命令 + 前置检查"的演练与报告模板，环境不可达时**明确失败**，不静默降级为替身。

## 4. 设计签核

结论：**通过**（P2-1/P2-2 即本批 Task 1；P3-1/P3-2 已纳入设计约束与 C 条件）。
