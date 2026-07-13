"""
将生产环境测试结果一次性入库到知识库 (knowledge_source → chunks → vector embedding)。

用法:
  cd test-platform-v2/backend
  python scripts/ingest_prod_results.py

幂等设计：同内容不会重复入库（source_service 按 content_hash 去重）。
"""
import json
import sys
import os

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import SessionLocal
from app.services.knowledge import source_service, chunk_service
from app.services.knowledge.sanitize import sanitize
from app.services.knowledge.vectorize import embed_pending_chunks_in_new_session

PROJECT_ID = 1  # 默认项目


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ingest_report(report_path: str, source_type: str, title: str):
    """将 JSON 测试报告存入知识库。"""
    data = load_json(report_path)
    # 去除明文凭据后脱敏入库
    data.pop("credentials", None)
    raw = json.dumps(data, ensure_ascii=False, indent=2)
    content = sanitize(raw)

    db = SessionLocal()
    try:
        src = source_service.record_source(
            db,
            project_id=PROJECT_ID,
            source_type=source_type,
            source_id=None,
            title=title,
            source_ref=report_path,
            raw_content=content,
            metadata={"test_env": "production", "site": "https://www.camel1.tv"},
        )
        if src is None:
            print(f"  [SKIP] No change: {title}")
            db.close()
            return

        # Slice into chunks
        parts = chunk_service.slice_text(content, max_chars=1500)
        chunks = [
            {"chunk_type": "execution_result", "title": f"{title} #{i+1}", "content": p, "tags": [source_type, "production"]}
            for i, p in enumerate(parts)
        ]
        created = chunk_service.make_chunks(db, src, chunks)
        db.commit()
        print(f"  [OK] {title}: {created} chunks, source_id={src.id}")

        # Vector embedding
        embed_pending_chunks_in_new_session(PROJECT_ID, source_id=src.id)
        print(f"  [VEC] Embedding complete for source #{src.id}")
    except Exception as e:
        print(f"  [FAIL] {title}: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    storage = os.path.join(base, "storage")

    reports = [
        (os.path.join(storage, "production-test-report-20260713.json"), "production_test", "Production Full Test Report"),
        (os.path.join(storage, "prod-api-results.json"), "api_test", "Production API Test Results"),
        (os.path.join(storage, "prod-service-endpoints.json"), "api_catalog", "Production API Endpoint Catalog"),
    ]

    print("=" * 60)
    print("[KB Ingest] Production test results -> Knowledge Base")
    print("=" * 60)

    for path, stype, title in reports:
        if os.path.exists(path):
            print(f"\n[INGEST] {title}")
            print(f"  File: {path}")
            ingest_report(path, stype, title)
        else:
            print(f"\n[SKIP] File not found: {path}")

    print("\n" + "=" * 60)
    print("[KB Ingest] Done")
    print("=" * 60)


if __name__ == "__main__":
    main()
