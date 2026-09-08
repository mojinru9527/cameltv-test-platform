from unittest.mock import Mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.knowledge import KnowledgeChunk
from app.services.knowledge import vectorize


@pytest.mark.parametrize('worker,rag', [(False, True), (True, False)])
def test_disabled_catchup_never_opens_database(monkeypatch, worker, rag):
    monkeypatch.setattr(settings, 'worker_execution_enabled', worker)
    monkeypatch.setattr(settings, 'rag_enabled', rag)
    database = Mock(side_effect=AssertionError('database must remain untouched'))
    monkeypatch.setattr(vectorize, 'SessionLocal', database)
    assert vectorize.embed_pending_projects_in_new_session() == {'projects': 0, 'embedded': 0}
    database.assert_not_called()


def test_catchup_resumes_pending_projects_and_is_idempotent(db_session, monkeypatch):
    monkeypatch.setattr(settings, 'worker_execution_enabled', True)
    monkeypatch.setattr(settings, 'rag_enabled', True)
    monkeypatch.setattr(settings, 'embedding_batch_size', 1)
    monkeypatch.setattr(vectorize, 'SessionLocal', sessionmaker(bind=db_session.get_bind()))
    monkeypatch.setattr(vectorize.embedding_service, 'available', lambda: True)
    rows = [
        KnowledgeChunk(project_id=1, source_id=1, content='pending one'),
        KnowledgeChunk(project_id=1, source_id=1, content='pending two'),
        KnowledgeChunk(project_id=2, source_id=2, content='pending other project'),
        KnowledgeChunk(project_id=3, source_id=3, content='deleted', is_deleted=True),
        KnowledgeChunk(project_id=4, source_id=4, content='already embedded', embedding_id='existing'),
    ]
    db_session.add_all(rows)
    db_session.commit()
    batches = []

    def store(db, chunks):
        batches.append([chunk.id for chunk in chunks])
        for chunk in chunks:
            chunk.embedding_id = f'vector-{chunk.id}'
        db.flush()
        return len(chunks)

    monkeypatch.setattr(vectorize, '_embed_and_store', store)
    assert vectorize.embed_pending_projects_in_new_session() == {'projects': 2, 'embedded': 3}
    assert len(batches) == 3
    assert all(len(batch) == 1 for batch in batches)
    assert vectorize.embed_pending_projects_in_new_session() == {'projects': 0, 'embedded': 0}
    db_session.expire_all()
    assert db_session.get(KnowledgeChunk, rows[3].id).embedding_id == ''
    assert db_session.get(KnowledgeChunk, rows[4].id).embedding_id == 'existing'


def test_busy_embedding_stays_pending_for_next_sweep(db_session, monkeypatch):
    monkeypatch.setattr(settings, 'worker_execution_enabled', True)
    monkeypatch.setattr(settings, 'rag_enabled', True)
    monkeypatch.setattr(vectorize, 'SessionLocal', sessionmaker(bind=db_session.get_bind()))
    monkeypatch.setattr(vectorize.embedding_service, 'available', lambda: True)
    db_session.add(KnowledgeChunk(project_id=1, source_id=1, content='retry me'))
    db_session.commit()
    store = Mock(return_value=0)
    monkeypatch.setattr(vectorize, '_embed_and_store', store)
    assert vectorize.embed_pending_projects_in_new_session() == {'projects': 1, 'embedded': 0}
    assert store.call_count == 1
    db_session.expire_all()
    assert db_session.scalar(select(KnowledgeChunk)).embedding_id == ''
