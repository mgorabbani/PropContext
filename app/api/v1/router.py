from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import ask, events, health, lint, properties, webhook, wiki

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(wiki.router, prefix="/wiki", tags=["wiki"])
api_router.include_router(ask.router, prefix="/ask", tags=["ask"])
api_router.include_router(lint.router, prefix="/lint", tags=["lint"])
