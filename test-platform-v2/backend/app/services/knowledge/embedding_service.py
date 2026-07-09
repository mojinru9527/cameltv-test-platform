"""嵌入服务（M2 RAG）—— 本地 fastembed(onnx) 生成切片/查询向量，离线不外传。

设计（见 ADR-0010）：
- **懒加载**：模型在首次真正需要时才加载/下载；导入本模块永不触发下载或报错。
- **优雅降级**：fastembed 未安装 / 模型下载失败 / 计算异常 → 返回 None 并记日志，
  绝不抛异常，保证 M1 入库与主流程不受影响。
- **L2 归一化**：写入前归一化，检索时余弦相似度退化为点积，简化 vector_store。
- 单例 `embedding_service` 供入库管线与检索复用。
"""
from __future__ import annotations

import logging
import threading

from app.core.config import settings

logger = logging.getLogger("knowledge.embedding")


class EmbeddingService:
    """本地 onnx 文本嵌入（bge-small-zh-v1.5，512 维）。线程安全懒加载。"""

    def __init__(
        self,
        model_name: str | None = None,
        dim: int | None = None,
        cache_dir: str | None = None,
    ) -> None:
        self._model_name = model_name or settings.embedding_model
        self._dim = dim or settings.embedding_dim
        self._cache_dir = cache_dir or settings.embedding_cache_dir or None
        self._model = None
        self._unavailable = False
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dim(self) -> int:
        return self._dim

    def _ensure_model(self) -> None:
        if self._model is not None or self._unavailable:
            return
        with self._lock:
            if self._model is not None or self._unavailable:
                return
            try:
                from fastembed import TextEmbedding  # 延迟导入：未装依赖也不影响 app 启动

                self._model = TextEmbedding(
                    model_name=self._model_name, cache_dir=self._cache_dir
                )
                logger.info("嵌入模型已加载: %s", self._model_name)
            except Exception:  # noqa: BLE001 — 任何失败都降级，不得中断主流程
                logger.exception(
                    "加载嵌入模型失败（fastembed 未安装或模型下载失败），RAG 嵌入将被跳过"
                )
                self._unavailable = True

    def available(self) -> bool:
        """模型是否就绪（会触发首次加载/下载）。"""
        self._ensure_model()
        return self._model is not None

    def embed(self, texts: list[str]):
        """批量嵌入，返回 np.ndarray[float32, (n, dim)]（已 L2 归一化）；不可用/异常返回 None。"""
        texts = [t if isinstance(t, str) else "" for t in (texts or [])]
        if not texts:
            return None
        self._ensure_model()
        if self._model is None:
            return None
        try:
            import numpy as np

            vecs = list(self._model.embed(texts))  # generator[np.ndarray]
            arr = np.asarray(vecs, dtype=np.float32)
            if arr.ndim != 2 or arr.shape[0] != len(texts):
                logger.warning("嵌入输出形状异常: %s（期望 (%d, dim)）", arr.shape, len(texts))
                return None
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return arr / norms
        except Exception:  # noqa: BLE001
            logger.exception("嵌入计算失败")
            return None

    def embed_one(self, text: str):
        """单文本嵌入，返回 np.ndarray[float32, (dim,)] 或 None。"""
        arr = self.embed([text or ""])
        if arr is None or len(arr) == 0:
            return None
        return arr[0]

    def embed_query(self, query: str):
        """查询侧嵌入：bge 建议对 query 加检索前缀以对齐训练目标。"""
        prefix = settings.embedding_query_prefix or ""
        return self.embed_one(f"{prefix}{query or ''}")


# 进程级单例（懒加载，导入无副作用）
embedding_service = EmbeddingService()
