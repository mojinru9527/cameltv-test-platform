---
name: cameltv-doc-check
description: Use when asked to check document freshness.
---

# CamelTv 文档保鲜检查

检查知识库文档保鲜状态，基于 `scripts/check_doc_freshness.py`。

## 工作流程
1. 扫描: `python scripts/check_doc_freshness.py`
2. 修复: `python scripts/check_doc_freshness.py --fix`
3. 验证: `python scripts/check_doc_freshness.py --ci`
