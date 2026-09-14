"""Standalone internal AI Gateway service.

This process owns AI routing, response cache, shadow execution and local
embeddings. The public API delegates to it through /internal/ai/v1/* when
``AI_GATEWAY_URL`` is configured.
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.schemas.common import R
from app.services import ai_client
from app.services.knowledge.embedding_service import embedding_service

app = FastAPI(title="CamelTv AI Gateway", version="1.0.0")


class ChatRequest(BaseModel):
    project_id: int = 0
    system_prompt: str
    user_message: str
    max_tokens: int | None = None
    temperature: float | None = None
    json_mode: bool = True
    cache_namespace: str | None = None


class EmbedRequest(BaseModel):
    texts: list[str] = Field(default_factory=list, max_length=256)


def require_internal_token(
    x_ai_gateway_token: str | None = Header(default=None),
) -> None:
    expected = settings.ai_gateway_token or ""
    if not expected:
        raise HTTPException(status_code=503, detail="AI Gateway token is not configured")
    if x_ai_gateway_token != expected:
        raise HTTPException(status_code=401, detail="Invalid AI Gateway token")


@app.get("/internal/ai/v1/health")
def health() -> dict[str, Any]:
    # Deployment gate: a gateway without an internal token must never be
    # considered healthy, otherwise compose ``--wait`` would accept a topology
    # in which every authenticated AI call fails with 503 at runtime.
    if not (settings.ai_gateway_token or ""):
        raise HTTPException(status_code=503, detail="AI Gateway token is not configured")
    return R.ok(
        {
            "ok": True,
            "role": settings.ai_gateway_role,
            "runtime_mode": settings.ai_runtime_mode,
            "token_configured": bool(settings.ai_gateway_token),
        }
    ).model_dump()


@app.post("/internal/ai/v1/chat", dependencies=[Depends(require_internal_token)])
def chat(body: ChatRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    summary = ai_client.chat_completions_full(
        db,
        body.project_id,
        system_prompt=body.system_prompt,
        user_message=body.user_message,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
        json_mode=body.json_mode,
        cache_namespace=body.cache_namespace,
    )
    return R.ok(summary).model_dump()


@app.post("/internal/ai/v1/embed", dependencies=[Depends(require_internal_token)])
def embed(body: EmbedRequest) -> dict[str, Any]:
    vectors = embedding_service.embed(body.texts)
    if vectors is None:
        raise HTTPException(status_code=503, detail="Local embedding is unavailable")
    return R.ok({"vectors": vectors.tolist(), "dim": int(vectors.shape[1])}).model_dump()

