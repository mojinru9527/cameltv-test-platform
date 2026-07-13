"""Phase P2 Task 8: Wiki Diff Quality —— 差异分类器 12 维覆盖、证据追踪、产物生成、边缘情况。

测试结构：
  - TestClassifierQuality: 差异分类器功能正确性
  - TestAllDimensions: 覆盖全部 12 个维度
  - TestEvidenceTracking: 每条差异项必须包含证据
  - TestArtifactCreation: 已采纳差异转 pending AiArtifact
  - TestEdgeCases: 空输入、相同内容、缺失字段
  - TestContractExtractorFields: 契约抽取透传新字段
"""
from __future__ import annotations

import json

from app.models.knowledge import AiArtifact, KnowledgeChunk
from app.models.wiki import WikiDiffItem, WikiDiffTask
from app.services.wiki import compare_service, contract_extractor, diff_classifier


# ═══════════════════════════════════════════════════════════════
# helpers
# ═══════════════════════════════════════════════════════════════

def _contract(**over):
    base = {
        "requirement_key": "match_push", "title": "比赛推送", "module": "赛事模块",
        "client_scope": ["app"], "summary": "",
        "business_rules": [{"id": "R1", "rule": "matchId 必填", "evidence": "蓝湖 P2"}],
        "fields": [{"name": "matchId", "location": "query", "type": "string", "required": True}],
        "apis": [{"method": "GET", "path": "/ee/test/matchpush"}],
        "acceptance_criteria": ["返回 code=0 且数据不为空"],
        "exception_paths": ["matchId 为空时返回错误提示"],
        "test_cases": [{"id": "TC-001", "title": "matchId 必填校验"}],
        "permissions": [{"role": "普通用户", "actions": ["read"]}],
        "data_dependencies": [{"name": "match_info", "source": "赛事服务", "type": "api"}],
        "version": "1.0.0",
        "source_refs": [{"knowledge_chunk_id": 1, "title": "比赛推送规则"}],
    }
    base.update(over)
    return base


def _empty():
    return {
        "requirement_key": "", "title": "", "module": "",
        "client_scope": [], "summary": "",
        "business_rules": [], "fields": [], "apis": [],
        "acceptance_criteria": [], "exception_paths": [], "test_cases": [],
        "permissions": [], "data_dependencies": [], "version": "", "source_refs": [],
    }


# ═══════════════════════════════════════════════════════════════
# TestClassifierQuality
# ═══════════════════════════════════════════════════════════════

class TestClassifierQuality:
    """分类器功能正确性：字段/覆盖缺口/业务规则/接口等基本场景。"""

    def test_detects_field_and_coverage_gap(self):
        left = _contract(
            fields=[{"name": "matchId", "required": True, "type": "string"}],
            test_cases=[],
        )
        right = _contract(
            fields=[
                {"name": "matchId", "required": True, "type": "string"},
                {"name": "minutes", "required": True, "type": "integer"},
            ],
            test_cases=["matchId 必填校验"],
        )
        items = diff_classifier.classify(left, right)
        assert any(i["diff_type"] == "missing_in_left" and i["dimension"] == "字段" for i in items), \
            "应检测到左侧缺少 minutes 字段"
        assert any(i["diff_type"] == "coverage_gap" for i in items), \
            "左侧有字段但无用例 → 覆盖缺口"

    def test_missing_rule_and_field_and_api(self):
        left = _contract(
            business_rules=[{"id": "R1", "rule": "matchId 必填"}],
            fields=[], apis=[],
        )
        right = _contract(
            business_rules=[
                {"id": "R1", "rule": "matchId 必填"},
                {"id": "R2", "rule": "minis 范围 0-90"},
            ],
            fields=[{"name": "matchId", "type": "string", "required": True}],
            apis=[{"method": "GET", "path": "/ee/test/matchpush"}],
        )
        items = diff_classifier.classify(left, right)
        dims = {i["dimension"] for i in items}
        assert "业务规则" in dims and "字段" in dims and "接口" in dims
        assert any(i["diff_type"] == "missing_in_left" and "minis" in i["title"] for i in items)
        api_item = next(i for i in items if i["dimension"] == "接口")
        assert api_item["severity"] == "P0", "接口缺失应为 P0"

    def test_field_conflict(self):
        left = _contract(fields=[{"name": "matchId", "type": "string", "required": True}])
        right = _contract(fields=[{"name": "matchId", "type": "int", "required": False}])
        items = diff_classifier.classify(left, right)
        conflicts = [i for i in items if i["diff_type"] == "conflict" and i["dimension"] == "字段"]
        assert len(conflicts) == 1

    def test_field_conflict_includes_location(self):
        left = _contract(fields=[{"name": "x", "location": "query", "type": "string", "required": True}])
        right = _contract(fields=[{"name": "x", "location": "body", "type": "string", "required": True}])
        items = diff_classifier.classify(left, right)
        conflicts = [i for i in items if i["diff_type"] == "conflict" and i["dimension"] == "字段"]
        assert len(conflicts) == 1
        assert "location" in conflicts[0]["suggestion"]

    def test_api_method_ambiguous(self):
        left = _contract(apis=[{"method": "GET", "path": "/ee/match"}])
        right = _contract(apis=[{"method": "POST", "path": "/ee/match"}])
        items = diff_classifier.classify(left, right)
        ambiguous = [i for i in items if i["diff_type"] == "ambiguous" and i["dimension"] == "接口"]
        assert len(ambiguous) == 1

    def test_identical_contracts_minimal_diff(self):
        c = _contract(test_cases=[{"id": 1}], source_refs=[{"x": 1}])  # 有 source_refs → 无证据缺项
        items = diff_classifier.classify(c, c)
        # 完全一致时不应有 missing/conflict/changed 差异
        assert not any(i["diff_type"] in ("missing_in_left", "missing_in_right", "conflict", "changed") for i in items), \
            "相同契约不应产生 missing/conflict/changed 差异"

    def test_summarize(self):
        items = diff_classifier.classify(
            _contract(fields=[]),
            _contract(fields=[{"name": "x", "type": "string", "required": True}]),
        )
        s = diff_classifier.summarize(items)
        assert s["total"] == len(items) and "by_severity" in s and "by_dimension" in s
        assert s["by_dimension"].get("字段", 0) >= 1


# ═══════════════════════════════════════════════════════════════
# TestAllDimensions
# ═══════════════════════════════════════════════════════════════

class TestAllDimensions:
    """覆盖全部 12 个维度：需求范围/客户端/业务规则/字段/接口/异常路径/
    权限角色/数据依赖/验收标准/测试覆盖/版本/证据。"""

    ALL_DIMS = {
        "需求范围", "客户端", "业务规则", "字段", "接口", "异常路径",
        "权限角色", "数据依赖", "验收标准", "测试覆盖", "版本", "证据",
    }

    def test_all_dimensions_covered_in_comprehensive_diff(self):
        """构造大幅不一致的左右契约，确保 12 维至少有一个差异项。"""
        left = _contract(
            title="比赛推送 v1",
            module="赛事",
            client_scope=["app"],
            business_rules=[{"id": "R1", "rule": "matchId 必填", "evidence": "P1"}],
            fields=[{"name": "matchId", "type": "string", "required": True}],
            apis=[{"method": "GET", "path": "/ee/matchpush"}],
            exception_paths=["matchId 为空"],
            acceptance_criteria=["返回 code=0"],
            test_cases=[],  # 触发 coverage_gap
            permissions=[{"role": "user", "actions": ["read"]}],
            data_dependencies=[{"name": "match_info", "source": "srv", "type": "api"}],
            version="1.0",
            source_refs=[{"knowledge_chunk_id": 1}],  # 左有 source_refs
        )
        right = _contract(
            title="比赛推送 v2",
            module="赛事管理",
            client_scope=["app", "web"],
            business_rules=[{"id": "R2", "rule": "minis 0-90", "evidence": "P2"}],
            fields=[{"name": "minutes", "type": "integer", "required": True}],
            apis=[{"method": "POST", "path": "/ee/matchpush"}],
            exception_paths=["网络超时"],
            acceptance_criteria=[],
            test_cases=["TC-001"],
            permissions=[{"role": "admin", "actions": ["read", "write"]}],
            data_dependencies=[{"name": "score", "source": "score_srv", "type": "ws"}],
            version="2.0",
            source_refs=[],  # 右无 source_refs → 证据维度
        )
        items = diff_classifier.classify(left, right)
        covered = {i["dimension"] for i in items}
        missing = self.ALL_DIMS - covered
        assert not missing, f"未覆盖维度: {missing}。已覆盖: {covered}。共 {len(items)} 项。"

    def test_dimension_mapping_is_closed(self):
        """所有 diff 项的 dimension 必须来自 12 维封闭列表。"""
        items = diff_classifier.classify(_contract(fields=[]), _contract())
        for it in items:
            assert it["dimension"] in self.ALL_DIMS, \
                f"非法维度「{it['dimension']}」，允许: {self.ALL_DIMS}"


# ═══════════════════════════════════════════════════════════════
# TestEvidenceTracking
# ═══════════════════════════════════════════════════════════════

class TestEvidenceTracking:
    """每条差异项必须携带 evidence 列表，引用来源（wiki_page/knowledge_chunk 等）。"""

    def test_every_item_has_evidence_field(self):
        items = diff_classifier.classify(_contract(fields=[]), _contract())
        for it in items:
            assert "evidence" in it, "每条差异项必须有 evidence 字段"
            assert isinstance(it["evidence"], list), "evidence 必须是 list"

    def test_missing_item_uses_right_evidence(self):
        left = _contract(
            fields=[],
            source_refs=[{"knowledge_chunk_id": 1, "title": "左侧来源"}],
        )
        right = _contract(
            fields=[{"name": "matchId", "type": "string", "required": True}],
            source_refs=[{"wiki_page_id": 42, "title": "右侧 Wiki"}],
        )
        items = diff_classifier.classify(left, right)
        field_items = [i for i in items if i["dimension"] == "字段" and i["diff_type"] == "missing_in_left"]
        assert len(field_items) > 0
        for it in field_items:
            assert len(it["evidence"]) > 0, "missing_in_left 应引用右侧证据"
            # evidence should have wiki_page source from the right side
            ev_types = {e.get("source_type", e.get("wiki_page_id") and "wiki_page") for e in it["evidence"]}
            # at minimum, some evidence must be present
            assert any(e.get("wiki_page_id") == 42 for e in it["evidence"] if isinstance(e, dict)), \
                f"证据应包含右侧 wiki_page_id=42，实际: {it['evidence']}"

    def test_conflict_item_uses_both_evidence(self):
        left = _contract(
            fields=[{"name": "x", "type": "string", "required": True}],
            source_refs=[{"knowledge_chunk_id": 10}],
        )
        right = _contract(
            fields=[{"name": "x", "type": "int", "required": False}],
            source_refs=[{"wiki_page_id": 20}],
        )
        items = diff_classifier.classify(left, right)
        conflicts = [i for i in items if i["diff_type"] == "conflict" and i["dimension"] == "字段"]
        for it in conflicts:
            assert len(it["evidence"]) >= 2, "conflict 应包含两侧证据"

    def test_evidence_quality_dimension_flags_missing_source_refs(self):
        """证据维度：一侧 source_refs 为空时产生提示。"""
        right_no_refs = _contract(source_refs=[])
        items = diff_classifier.classify(_contract(), right_no_refs)
        evidence_items = [i for i in items if i["dimension"] == "证据"]
        assert any(i["diff_type"] == "missing_in_right" for i in evidence_items), \
            "右侧 source_refs 为空应产生 missing_in_right 证据提示"


# ═══════════════════════════════════════════════════════════════
# TestArtifactCreation
# ═══════════════════════════════════════════════════════════════

class TestArtifactCreation:
    """已采纳差异 → pending AiArtifact，不直接导入正式资产。"""

    def test_diff_item_to_pending_artifact(self, db_session):
        task = WikiDiffTask(project_id=1, title="t", status="success")
        db_session.add(task); db_session.flush()
        item = WikiDiffItem(
            task_id=task.id, project_id=1, dimension="字段",
            diff_type="missing_in_left", severity="P1",
            title="左侧缺少字段 matchId", suggestion="补充边界用例",
            evidence_json=json.dumps([{"wiki_page_id": 1, "title": "比赛推送"}], ensure_ascii=False),
        )
        db_session.add(item); db_session.flush()

        art = compare_service.create_artifact_from_item(db_session, 1, item)
        db_session.flush()
        assert art.review_status == "pending", "产物必须是 pending 状态，不能直接导入正式资产"
        assert art.artifact_type == "test_case"
        assert item.resolved_artifact_id == art.id
        assert item.review_status == "accepted"

    def test_business_rule_dimension_maps_to_business_rule_type(self, db_session):
        task = WikiDiffTask(project_id=1, title="t", status="success")
        db_session.add(task); db_session.flush()
        item = WikiDiffItem(
            task_id=task.id, project_id=1, dimension="业务规则",
            diff_type="missing_in_right", severity="P1", title="右侧缺规则",
        )
        db_session.add(item); db_session.flush()
        art = compare_service.create_artifact_from_item(db_session, 1, item)
        assert art.artifact_type == "business_rule"

    def test_version_dimension_maps_to_regression_scope(self, db_session):
        task = WikiDiffTask(project_id=1, title="t", status="success")
        db_session.add(task); db_session.flush()
        item = WikiDiffItem(
            task_id=task.id, project_id=1, dimension="版本",
            diff_type="changed", severity="P2", title="版本不一致",
        )
        db_session.add(item); db_session.flush()
        art = compare_service.create_artifact_from_item(db_session, 1, item)
        assert art.artifact_type == "regression_scope"

    def test_data_dependency_dimension_maps_to_test_data(self, db_session):
        task = WikiDiffTask(project_id=1, title="t", status="success")
        db_session.add(task); db_session.flush()
        item = WikiDiffItem(
            task_id=task.id, project_id=1, dimension="数据依赖",
            diff_type="missing_in_left", severity="P2", title="数据依赖缺失",
        )
        db_session.add(item); db_session.flush()
        art = compare_service.create_artifact_from_item(db_session, 1, item)
        assert art.artifact_type == "test_data"

    def test_artifact_content_includes_diff_details(self, db_session):
        task = WikiDiffTask(project_id=1, title="t", status="success")
        db_session.add(task); db_session.flush()
        item = WikiDiffItem(
            task_id=task.id, project_id=1, dimension="接口",
            diff_type="missing_in_left", severity="P0",
            title="左侧缺少接口 GET /ee/test",
            left_value="", right_value="GET /ee/test",
            suggestion="绑定接口并补充用例",
            evidence_json=json.dumps([{"source_type": "wiki_page", "id": 5}], ensure_ascii=False),
        )
        db_session.add(item); db_session.flush()
        art = compare_service.create_artifact_from_item(db_session, 1, item)
        content = json.loads(art.content_json)
        assert content["from_diff_item"] == item.id
        assert content["dimension"] == "接口"
        assert content["severity"] == "P0"
        assert "GET /ee/test" in content["right_value"]

    def test_artifact_source_refs_copied_from_evidence(self, db_session):
        task = WikiDiffTask(project_id=1, title="t", status="success")
        db_session.add(task); db_session.flush()
        evidence = [{"source_type": "wiki_page", "id": 1, "title": "比赛推送"}]
        item = WikiDiffItem(
            task_id=task.id, project_id=1, dimension="字段",
            diff_type="missing_in_left", severity="P1", title="缺字段",
            evidence_json=json.dumps(evidence, ensure_ascii=False),
        )
        db_session.add(item); db_session.flush()
        art = compare_service.create_artifact_from_item(db_session, 1, item)
        assert art.source_refs == item.evidence_json


# ═══════════════════════════════════════════════════════════════
# TestEdgeCases
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """边缘情况：空输入、相同内容、缺失字段、None 处理。"""

    def test_both_empty_contracts(self):
        items = diff_classifier.classify({}, {})
        assert len(items) == 1
        assert items[0]["dimension"] == "需求范围"
        assert items[0]["diff_type"] == "ambiguous"

    def test_both_none(self):
        items = diff_classifier.classify(None, None)  # type: ignore
        assert len(items) == 1
        assert items[0]["dimension"] == "需求范围"

    def test_left_empty_right_populated(self):
        items = diff_classifier.classify({}, _contract())
        assert len(items) == 1
        assert items[0]["dimension"] == "需求范围"
        assert items[0]["diff_type"] == "missing_in_left"
        assert items[0]["severity"] == "P0"

    def test_right_empty_left_populated(self):
        items = diff_classifier.classify(_contract(), {})
        assert len(items) == 1
        assert items[0]["dimension"] == "需求范围"
        assert items[0]["diff_type"] == "missing_in_right"
        assert items[0]["severity"] == "P0"

    def test_identical_complex_contracts(self):
        """完全相同的复杂契约不应有差异，除了证据维度可能因 source_refs 为空触发。"""
        c = _contract(
            source_refs=[{"knowledge_chunk_id": 1}],
            business_rules=[{"id": "R1", "rule": "x", "evidence": "p1"}],
        )
        items = diff_classifier.classify(c, c)
        # 允许证据维度的 coverage_gap 或 ambiguous（如果业务规则无 evidence）
        non_evidence = [i for i in items if i["dimension"] != "证据"]
        # 同契约内容里业务规则的 evidence 字段从 _rule_text 取的是 rule 值，可能不包含 evidence
        # 但主要断言是：不应有 missing/conflict 差异
        problematic = [i for i in non_evidence if i["diff_type"] in ("missing_in_left", "missing_in_right", "conflict")]
        assert len(problematic) == 0, f"完全相同的契约不应产生 missing/conflict 差异: {problematic}"

    def test_missing_fields_in_contract(self):
        """契约缺少部分字段时，对应维度不产生误报。"""
        partial = {
            "title": "仅标题",
            "business_rules": [{"id": "R1", "rule": "test"}],
        }
        items = diff_classifier.classify(partial, partial)
        # 相同 partial 不应有 missing/conflict
        problematic = [i for i in items if i["diff_type"] in ("missing_in_left", "missing_in_right", "conflict")]
        assert len(problematic) == 0

    def test_none_fields_not_list(self):
        """契约中字段为 None 或非列表时不应崩溃，且应视为空列表。
        注意：当一侧 fields=None（视为空）而另一侧有字段时，应正确检测缺失。"""
        bad_contract = {
            "title": "test", "fields": None, "apis": "not_a_list",
            "business_rules": None, "client_scope": None,
            "source_refs": [{"knowledge_chunk_id": 1}],  # 避免证据维度干扰
        }
        items = diff_classifier.classify(bad_contract, _contract())
        # 不应抛异常，返回有意义的结果
        assert isinstance(items, list)
        # fields=None 视为空列表，右侧有 matchId，左侧缺 matchId 是正确行为
        field_missing = [i for i in items if i["dimension"] == "字段" and i["diff_type"] == "missing_in_left"]
        assert len(field_missing) >= 1, "fields=None 视为空列表，应检测到左侧缺字段"

    def test_client_scope_detects_multi_client(self):
        left = _contract(client_scope=["app"])
        right = _contract(client_scope=["app", "web", "admin"])
        items = diff_classifier.classify(left, right)
        client_items = [i for i in items if i["dimension"] == "客户端" and i["diff_type"] == "missing_in_left"]
        assert len(client_items) == 2  # web + admin

    def test_version_detected(self):
        left = _contract(version="1.0.0")
        right = _contract(version="2.0.0")
        items = diff_classifier.classify(left, right)
        version_items = [i for i in items if i["dimension"] == "版本"]
        assert len(version_items) >= 1
        assert any(i["diff_type"] == "changed" for i in version_items)

    def test_permissions_dimension(self):
        left = _contract(permissions=[{"role": "user", "actions": ["read"]}])
        right = _contract(permissions=[
            {"role": "user", "actions": ["read"]},
            {"role": "admin", "actions": ["read", "write"]},
        ])
        items = diff_classifier.classify(left, right)
        perm_items = [i for i in items if i["dimension"] == "权限角色"]
        assert len(perm_items) >= 1
        assert any(i["diff_type"] == "missing_in_left" for i in perm_items)

    def test_data_dependency_dimension(self):
        left = _contract(data_dependencies=[])
        right = _contract(data_dependencies=[
            {"name": "match_info", "source": "赛事服务", "type": "api"},
        ])
        items = diff_classifier.classify(left, right)
        dep_items = [i for i in items if i["dimension"] == "数据依赖"]
        assert len(dep_items) >= 1
        assert dep_items[0]["diff_type"] == "missing_in_left"

    def test_acceptance_criteria_item_level_diff(self):
        """验收标准逐条缺失（细粒度）"""
        left = _contract(acceptance_criteria=["A"])
        right = _contract(acceptance_criteria=["A", "B", "C"])
        items = diff_classifier.classify(left, right)
        ac_items = [i for i in items if i["dimension"] == "验收标准"]
        # 至少有一条 ambiguous + 两条 missing_in_left
        assert len(ac_items) >= 2
        missing = [i for i in ac_items if i["diff_type"] == "missing_in_left"]
        assert len(missing) == 2

    def test_business_rule_conflict_same_key(self):
        """同 key 不同文本 → conflict"""
        left = _contract(business_rules=[{"id": "R1", "rule": "max 100"}])
        right = _contract(business_rules=[{"id": "R1", "rule": "max 200"}])
        items = diff_classifier.classify(left, right)
        conflicts = [i for i in items if i["dimension"] == "业务规则" and i["diff_type"] == "conflict"]
        assert len(conflicts) == 1


# ═══════════════════════════════════════════════════════════════
# TestContractExtractorFields
# ═══════════════════════════════════════════════════════════════

class TestContractExtractorFields:
    """契约抽取透传新字段（permissions / data_dependencies / version）。"""

    def test_empty_contract_keys_include_new_fields(self):
        """_EMPTY_CONTRACT_KEYS 应包含 permissions / data_dependencies / version。"""
        from app.services.wiki.contract_extractor import _EMPTY_CONTRACT_KEYS
        assert "permissions" in _EMPTY_CONTRACT_KEYS
        assert "data_dependencies" in _EMPTY_CONTRACT_KEYS
        assert "version" in _EMPTY_CONTRACT_KEYS

    def test_contract_extractor_rag_fallback_has_new_keys(self, db_session, monkeypatch):
        """退化模式（LLM 不可用）下的契约也应包含新字段。"""
        db_session.add(KnowledgeChunk(
            project_id=1, source_id=1, chunk_type="requirement_rule",
            title="比赛推送", content="matchId 必填", status="active",
        ))
        db_session.flush()
        monkeypatch.setattr(contract_extractor, "_call_llm_sync",
                            lambda *a, **k: {"result": None, "raw": "", "error": "no key"})
        c = contract_extractor.extract_contract(db_session, 1, kb_type="platform_rag", query="比赛推送")
        for key in ("permissions", "data_dependencies", "version"):
            assert key in c, f"契约应包含键 '{key}'"
            assert isinstance(c[key], list) if key != "version" else True

    def test_contract_extractor_llm_has_new_keys(self, db_session, monkeypatch):
        """LLM 成功模式下的契约应保留新字段。"""
        db_session.add(KnowledgeChunk(
            project_id=1, source_id=1, chunk_type="requirement_rule",
            title="比赛推送", content="matchId 必填", status="active",
        ))
        db_session.flush()
        monkeypatch.setattr(contract_extractor, "_call_llm_sync", lambda *a, **k: {
            "result": {
                "title": "比赛推送", "permissions": [{"role": "user", "actions": ["read"]}],
                "data_dependencies": [{"name": "m", "source": "s", "type": "api"}],
                "version": "1.0.0",
            },
            "raw": "", "error": None,
        })
        c = contract_extractor.extract_contract(db_session, 1, kb_type="platform_rag", query="比赛推送")
        assert c["permissions"] == [{"role": "user", "actions": ["read"]}]
        assert c["data_dependencies"] == [{"name": "m", "source": "s", "type": "api"}]
        assert c["version"] == "1.0.0"
