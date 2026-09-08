import weakref
from unittest.mock import patch

import numpy as np
import pytest

from app.core.resource_budget import FileBudget
from app.services.knowledge import embedding_service as embedding


@pytest.mark.parametrize('operation', ['available', 'embed', 'error'])
def test_model_released_before_shared_capacity_is_returned(tmp_path, operation):
    budget = FileBudget(tmp_path, 1)
    service = embedding.EmbeddingService(dim=2)
    references, destroyed_while_admitted = [], []

    class Model:
        def embed(self, texts):
            if operation == 'error':
                raise RuntimeError('inference failure')
            return [np.array([3.0, 4.0]) for _ in texts]

        def __del__(self):
            lease = budget.try_acquire('browser', 'must-wait')
            destroyed_while_admitted.append(lease is None)
            if lease is not None:
                lease.release()

    def load():
        if service._model is None:
            service._model = Model()
            references.append(weakref.ref(service._model))

    with patch.object(embedding, 'configured_budget', return_value=budget), \
            patch.object(embedding.logger, 'exception'), \
            patch.object(service, '_ensure_model', side_effect=load):
        for _ in range(2):
            if operation == 'available':
                assert service.available() is True
            elif operation == 'error':
                assert service.embed(['text']) is None
            else:
                np.testing.assert_allclose(service.embed(['text']), [[0.6, 0.8]])
            assert service._model is None
            assert all(reference() is None for reference in references)
    assert destroyed_while_admitted == [True, True]
    with budget.wait('browser', 'next', timeout=0):
        pass


def test_unbudgeted_runtime_keeps_existing_model_cache():
    service = embedding.EmbeddingService(dim=2)
    model = type('Model', (), {'embed': lambda self, texts: [np.array([3., 4.]) for _ in texts]})()
    service._model = model
    with patch.object(embedding, 'configured_budget', return_value=None):
        np.testing.assert_allclose(service.embed(['text']), [[0.6, 0.8]])
        assert service._model is model
