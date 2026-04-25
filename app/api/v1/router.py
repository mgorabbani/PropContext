from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health, properties

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
