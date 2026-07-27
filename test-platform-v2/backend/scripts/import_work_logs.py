"""批量导入 work-logs/ 历史工件到知识库。

Usage: python scripts/import_work_logs.py

将 work-logs/ 下所有 .md 文件（跳过 _TEMPLATE.md）按要求分类导入：
- prd-summary / pm-plan → para_category="project"
- kanban (DEV-*.md)     → para_category="area"
- design-spec / leader-verdict / qa-report 等 → para_category="resource"
- 其余                  → para_category="archive"

同时导入 10 条反复出现的问题模式。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 确保 backend 在 sys.path
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.services.knowledge.ingest_service import ingest_platform_knowledge_in_new_session

WORK_LOGS = Path("../../work-logs").resolve()  # f:/CamelTv/work-logs/
PROJECT_ID = 1  # 默认项目

# ── 文件名 → PARA 分类规则 ──

def classify(filename: str, dirname: str) -> str:
    """根据文件名和所在目录返回 para_category。"""
    base = filename.lower()
    if base.endswith("-prd-summary.md") or base.endswith("-pm-plan.md"):
        return "project"
    if "kanbans" in dirname and base.startswith("dev-"):
        return "area"
    if any(base.endswith(s) for s in [
        "-design-spec.md", "-leader-verdict.md", "-qa-report.md",
        "-dev-review.md", "-fact-check.md", "-a11y-audit.md",
    ]) or "reviews" in dirname:
        return "resource"
    return "archive"


def extract_batch_name(filename: str) -> str:
    """从文件名提取 batch 标识。"""
    parts = filename.replace(".md", "").split("-")
    if parts[0] == "batch":
        return "-".join(parts[:3]) if len(parts) >= 3 else "-".join(parts)
    return filename.replace(".md", "")


def artifact_label(filename: str) -> str:
    """提取工件类型标签。"""
    mapping = {
        "prd-summary": "PRD摘要",
        "pm-plan": "PM计划",
        "design-spec": "设计规范",
        "leader-verdict": "Leader判决",
        "qa-report": "QA报告",
        "dev-review": "Dev审查",
        "fact-check": "事实核查",
        "a11y-audit": "无障碍审计",
        "proposal": "提案",
        "cleanup-summary": "清理摘要",
    }
    for key, label in mapping.items():
        if key in filename.lower():
            return label
    return "工件"


def import_work_logs() -> None:
    count = 0
    skipped = 0

    for root, dirs, files in os.walk(str(WORK_LOGS)):
        # 跳过 summaries 目录（与 daily/weekly 摘要区别对待）
        for fname in sorted(files):
            if not fname.endswith(".md") or fname == "_TEMPLATE.md":
                continue

            fpath = Path(root) / fname
            rel_dir = str(Path(root).relative_to(WORK_LOGS))
            para = classify(fname, rel_dir)
            batch = extract_batch_name(fname)
            label = artifact_label(fname)
            title = f"{batch} — {label}"

            try:
                raw = fpath.read_text(encoding="utf-8")
            except Exception:
                print(f"  [skip] 无法读取: {fpath}")
                skipped += 1
                continue

            source_id = ingest_platform_knowledge_in_new_session(
                project_id=PROJECT_ID,
                title=title,
                raw_content=raw,
                para_category=para,
                knowledge_domain="platform",
                source_ref=str(fpath),
                tags=[batch, label],
            )
            if source_id:
                count += 1
                print(f"  [{para:>8}] #{source_id:>3}  {title}")
            else:
                skipped += 1
                print(f"  [skip]          {title}  (重复或入库失败)")

    print(f"\n导入完成: {count} 条成功, {skipped} 条跳过")


# ── 10 条反复出现的问题模式 ──

PROBLEM_PATTERNS = [
    {
        "title": "P1: 文档-代码漂移",
        "description": (
            "6份文档在「7天36次交付」Sprint后落后代码2-3个版本。"
            "根因：没有逐批次文档更新机制。"
            "已通过 cameltv-doc-check skill + Slice 0 全面修正解决。"
            "教训：每次 batch 交付必须更新相关文档，作为硬门禁。"
        ),
        "affected_modules": ["CLAUDE.md", "docs/", "ADR"],
    },
    {
        "title": "P2: RBAC 权限边界越权",
        "description": (
            "Batch 18: 三个端点错误使用 wiki:diff 而非 wiki:approve 权限，Tester角色绕过审核。"
            "Batch 11: ai_artifact_allow_batch_import 开关定义但代码零引用。"
            "根因：权限分配未与 Spec 中的权限矩阵交叉验证。"
            "教训：权限矩阵 vs 代码交叉验证应作为 QA/Leader 标准抽检项。"
        ),
        "affected_modules": ["RBAC", "seed.py", "权限中间件"],
    },
    {
        "title": "P3: 脱敏清洗覆盖缺口",
        "description": (
            "sanitize() 函数有6个绕过向量（非JSON token参数、裸JWT、内联Cookie等）。"
            "根因：脱敏正则只覆盖 happy-path，无对抗性绕过用例。"
            "教训：安全敏感字符串处理函数必须写对抗性测试用例。"
        ),
        "affected_modules": ["sanitize.py", "knowledge ingest"],
    },
    {
        "title": "P4: 配置默认值安全性",
        "description": (
            "Batch 11: knowledge_ingest_enabled 默认 True，合并到 develop 会自动激活。"
            "Batch 18: lanhu_mcp_enabled 默认 True 但 import 路径无校验。"
            "根因：Review checklist 缺少「默认安全」审计步骤。"
            "教训：所有新能力默认 OFF，合并要求显式门禁校验。"
        ),
        "affected_modules": ["config.py", "feature flags"],
    },
    {
        "title": "P5: 数据库迁移测试缺口",
        "description": (
            "alembic upgrade head 从空库执行时在 migration 0002 失败（重复列）。"
            "根因：Dev 环境依赖 AUTO_CREATE_TABLES，掩盖迁移完整性问题。"
            "教训：预发布前必须做 alembic upgrade/downgrade 双向验证。"
        ),
        "affected_modules": ["alembic/", "database migration"],
    },
    {
        "title": "P6: 前端状态管理碎片化",
        "description": (
            "15+ 页面手动管理 loading/error 状态而非使用 AsyncState 模式。"
            "双主题系统（data-theme + data-theme-id）共存，维护翻倍。"
            "defect/index.tsx 988行、perftest/index.tsx 828行——巨型组件反模式。"
            "根因：PR review 阶段未强制执行标准 UI 模式。"
            "教训：在 CLAUDE.md 中定义组件大小上限和状态管理模式。"
        ),
        "affected_modules": ["frontend/src/pages/*", "AsyncState", "主题系统"],
    },
    {
        "title": "P7: LLM 输出未持久化",
        "description": (
            "LLM 分析阶段的 review_items 和 contradictions 只做了 len() 计数但未持久化。"
            "低置信度 Review Items 被静默丢弃。"
            "根因：LLM 生成的中间信号未作为一等数据对待。"
            "教训：所有 LLM 生成的审查/置信度信号必须作为可审计工件持久化。"
        ),
        "affected_modules": ["agent_orchestrator", "wiki_ingest", "ai_artifact"],
    },
    {
        "title": "P8: CI 门禁在错误分支",
        "description": (
            "pr-check.yml 只在 pull_request branches: [main, master] 触发，develop PR 绕过 pytest + tsc 门禁。"
            "根因：团队切换到 develop 为主要开发分支后未更新 CI 配置。"
            "教训：分支配置审计应纳入平台基础设施健康检查。"
        ),
        "affected_modules": [".github/workflows/", "CI/CD"],
    },
    {
        "title": "P9: 死配置/孤儿开关",
        "description": (
            "ai_artifact_allow_batch_import 定义但代码零引用；lanhu_mcp_enabled 定义但 import 入口未校验。"
            "根因：配置开关作为占位符添加但从未完成接线或验证。"
            "教训：每个配置布尔值必须至少有一个消费者——可做静态分析检查。"
        ),
        "affected_modules": ["config.py", "feature flags"],
    },
    {
        "title": "P10: 契约提取污染",
        "description": (
            "contract_extractor._gather_wiki_text 只过滤 superseded 状态，"
            "允许 rejected/draft/pending Wiki 页面污染对比结果。"
            "根因：过滤条件默认为宽松而非严格；安全默认应为「仅 approved」。"
            "教训：仅 approved/verified 数据可进入对比/规范流水线。"
        ),
        "affected_modules": ["wiki/", "contract_extractor", "diff"],
    },
]


def import_problem_patterns() -> None:
    print("\n── 导入问题模式 ──")
    count = 0
    for p in PROBLEM_PATTERNS:
        body = f"## {p['title']}\n\n{p['description']}\n\n**涉及模块**: {', '.join(p['affected_modules'])}"
        source_id = ingest_platform_knowledge_in_new_session(
            project_id=PROJECT_ID,
            title=p["title"],
            raw_content=body,
            para_category="area",
            knowledge_domain="platform",
            source_ref="work-logs analysis",
            tags=["问题模式", "平台研发"] + p["affected_modules"],
            metadata={"type": "problem_pattern", "affected": p["affected_modules"]},
        )
        if source_id:
            count += 1
            print(f"  [area] #{source_id:>3}  {p['title']}")
        else:
            print(f"  [skip]       {p['title']}  (重复)")
    print(f"问题模式导入: {count}/{len(PROBLEM_PATTERNS)} 条")


if __name__ == "__main__":
    print(f"Work-logs 目录: {WORK_LOGS}")
    print(f"目标项目 ID: {PROJECT_ID}\n")
    import_work_logs()
    import_problem_patterns()
    print("\n全部完成。")
