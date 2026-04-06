"""Atomic per-tenant counter primitive used by PO / SO / Remission / Invoice numbering.

Why a counter table instead of a Postgres SEQUENCE:
- We need a counter scoped per tenant + per year (multi-tenant SaaS).
- Postgres sequences are cluster-wide and don't restart per tenant.
- An UPSERT ON CONFLICT … RETURNING is atomic and race-free in a single statement.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SequenceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def next_value(self, tenant_id: str, scope: str) -> int:
        """Increment and return the next value for (tenant_id, scope).

        Atomic: uses INSERT ON CONFLICT DO UPDATE … RETURNING in a single
        statement, so concurrent calls are serialized at the row level.
        """
        sql = text(
            """
            INSERT INTO sequence_counters (tenant_id, scope, value, updated_at)
            VALUES (:tenant_id::uuid, :scope, 1, NOW())
            ON CONFLICT (tenant_id, scope) DO UPDATE
                SET value = sequence_counters.value + 1,
                    updated_at = NOW()
            RETURNING value
            """
        )
        result = await self.db.execute(
            sql,
            {"tenant_id": str(tenant_id), "scope": scope},
        )
        return int(result.scalar_one())
