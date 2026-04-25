from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import buildings, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(buildings.router, prefix="/buildings", tags=["buildings"])
