"""切片 3 (VNext-3) —— 需求契约抽取 / 差异分类 / 差异转待审 AI 产物。"""
from __future__ import annotations

from app.models.knowledge import AiArtifact, KnowledgeChunk
from app.models.wiki import WikiDiffItem, WikiDiffTask, WikiPage
from app.services.wiki import compare_service, contract_extractor, diff_classifier


def _contract(**over):
    base = {
        "requirement_key": "match_push", "title": "比赛推送", "module": "赛事模块",
        "client_scope": ["app"], "summary": "",
        "business_rules": [{"id": "R1", "rule": "matchId 必填"}],
        "fields": [{"name": "matchId", "location": "query", "type": "string", "required": True}],
        "apis": [{"method": "GET", "path": "/ee/test/matchpush"}],
        "acceptance_criteria": [], "exception_paths": [], "test_cases": [], "source_refs": [],
    }
    base.update(over)
    return base


class TestClassifier:
    def test_missing_rule_and_field_and_api(self):
        left = _contract(business_rules=[{"id": "R1", "rule": "matchId 必填"}],
                         fields=[], apis=[])
        right = _contract(
            business_rules=[{"id": "R1", "rule": "matchId 必填"}, {"id": "R2", "rule": "minis 范围 0-90"}],
            fields=[{"name": "matchId", "type": "string", "required": True}],
            apis=[{"method": "GET", "path": "/ee/test/matchpush"}])
        items = diff_classifier.classify(left, right)
        dims = {i["dimension"] for i in items}
        assert "业务规则" in dims and "字段" in dims and "接口" in dims
        # 左侧缺 R2 规则
        assert any(i["diff_type"] == "missing_in_left" and "minis" in i["title"] for i in items)
        # 接口缺失是 P0
        api_item = next(i for i in items if i["dimension"] == "接口")
        assert api_item["severity"] == "P0"

    def test_field_conflict(self):
        left = _contract(fields=[{"name": "matchId", "type": "string", "required": True}])
        right = _contract(fields=[{"name": "matchId", "type": "int", "required": False}])
        items = diff_classifier.classify(left, right)
        conflicts = [i for i in items if i["diff_type"] == "conflict" and i["dimension"] == "字段"]
        assert len(conflicts) == 1

    def test_coverage_gap_when_no_test_cases(self):
        c = _contract(test_cases=[])
        items = diff_classifier.classify(c, c)
        assert any(i["diff_type"] == "coverage_gap" for i in items)

    def test_identical_contracts_minimal_diff(self):
        c = _contract(test_cases=[{"id": 1}])  # 有用例 → 无覆盖缺口
        items = diff_classifier.classify(c, c)
        # 完全一致时不应有 missing/conflict
        assert not any(i["diff_type"] in ("missing_in_left", "missing_in_right", "conflict") for i in items)

    def test_summarize(self):
        items = diff_classifier.classify(_contract(fields=[]), _contract())
        s = diff_classifier.summarize(items)
        assert s["total"] == len(items) and "by_severity" in s and "by_dimension" in s


class TestContractExtractorFallback:
    def test_rag_gathers_chunks_fallback(self, db_session, monkeypatch):
        db_session.add(KnowledgeChunk(project_id=1, source_id=1, chunk_type="requirement_rule",
                                      title="比赛推送", content="matchId 必填", status="active"))
        db_session.flush()
        # LLM 不可用 → 退化最小契约（summary 保留片段）
        monkeypatch.setattr(contract_extractor, "_call_llm_sync",
                            lambda *a, **k: {"result": None, "raw": "", "error": "no key"})
        c = contract_extractor.extract_contract(db_session, 1, kb_type="platform_rag", query="比赛推送")
        assert c["title"] == "比赛推送" and "matchId" in c["summary"]
        assert c["source_refs"] and c["source_refs"][0]["chunk_id"]

    def test_wiki_gathers_pages(self, db_session, monkeypatch):
        db_session.add(WikiPage(project_id=1, page_type="requirement", slug="mp", title="比赛推送",
                                content_md="matchId 必填", review_status="approved"))
        db_session.flush()
        monkeypatch.setattr(contract_extractor, "_call_llm_sync",
                            lambda *a, **k: {"result": {"title": "比赛推送", "business_rules": [{"rule": "matchId 必填"}]},
                                             "raw": "", "error": None})
        c = contract_extractor.extract_contract(db_session, 1, kb_type="platform_wiki", query="比赛推送")
        assert c["business_rules"][0]["rule"] == "matchId 必填"
        assert c["source_refs"][0]["wiki_page_id"]

    def test_wiki_excludes_non_approved_pages(self, db_session, monkeypatch):
        """C2 回归：契约抽取只纳入 approved 页，draft/pending/rejected/superseded 均排除。"""
        for st in ("draft", "pending", "rejected", "superseded"):
            db_session.add(WikiPage(project_id=1, page_type="requirement", slug=f"mp-{st}",
                                    title="比赛推送", content_md="matchId 必填", review_status=st))
        db_session.flush()
        # 仅有非 approved 页 → gather 结果为空 → 走"未找到相关内容"退化契约，不调用 LLM
        called = {"n": 0}

        def _spy(*a, **k):
            called["n"] += 1
            return {"result": None, "raw": "", "error": None}

        monkeypatch.setattr(contract_extractor, "_call_llm_sync", _spy)
        c = contract_extractor.extract_contract(db_session, 1, kb_type="platform_wiki", query="比赛推送")
        assert called["n"] == 0, "非 approved 页不应进入契约抽取"
        assert c["source_refs"] == [] and "未找到相关内容" in c["summary"]


class TestCreateArtifact:
    def test_diff_item_to_pending_artifact(self, db_session):
        task = WikiDiffTask(project_id=1, title="t", status="success")
        db_session.add(task); db_session.flush()
        item = WikiDiffItem(task_id=task.id, project_id=1, dimension="字段", diff_type="missing_in_left",
                            severity="P1", title="左侧缺少字段 matchId", suggestion="补充边界用例")
        db_session.add(item); db_session.flush()

        art = compare_service.create_artifact_from_item(db_session, 1, item)
        db_session.flush()
        assert art.review_status == "pending" and art.artifact_type == "test_case"
        assert item.resolved_artifact_id == art.id and item.review_status == "accepted"
        # 业务规则维度 → business_rule 产物类型
        item2 = WikiDiffItem(task_id=task.id, project_id=1, dimension="业务规则",
                             diff_type="missing_in_right", severity="P1", title="右侧缺规则")
        db_session.add(item2); db_session.flush()
        art2 = compare_service.create_artifact_from_item(db_session, 1, item2)
        assert art2.artifact_type == "business_rule"
        assert db_session.query(AiArtifact).filter_by(project_id=1, review_status="pending").count() == 2
