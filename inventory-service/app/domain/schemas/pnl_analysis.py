"""Schemas for AI-powered P&L analysis."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PnLAlert(BaseModel):
    titulo: str
    detalle: str
    severidad: Literal["alta", "media", "baja"]
    producto_sku: str | None = None


class PnLOportunidad(BaseModel):
    titulo: str
    detalle: str
    impacto_estimado: str
    producto_sku: str | None = None


class PnLProductoEstrella(BaseModel):
    sku: str
    nombre: str
    razon: str


class PnLRecomendacion(BaseModel):
    accion: str
    prioridad: Literal["alta", "media", "baja"]
    producto_sku: str | None = None
    plazo: Literal["inmediato", "esta_semana", "este_mes"] | None = None


class PnLAnalysis(BaseModel):
    resumen: str
    alertas: list[PnLAlert] = []
    oportunidades: list[PnLOportunidad] = []
    productos_estrella: list[PnLProductoEstrella] = []
    recomendaciones: list[PnLRecomendacion] = []
    is_cached: bool = False
    cached_at: datetime | None = None
    cache_source: Literal["fresh", "session_cache", "last_saved"] = "fresh"
