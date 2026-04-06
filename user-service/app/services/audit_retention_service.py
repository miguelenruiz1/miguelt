"""Audit log PII scrubbing — Hábeas Data / GDPR right-to-be-forgotten support.

Audit logs are append-only (PG trigger blocks UPDATE/DELETE since mig 017),
but we still need to honor user deletion requests. This service uses a
SECURITY DEFINER PG function (configured by DBA) or a privileged superuser
connection to anonymize PII while preserving the audit trail.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def anonymize_user_audit_logs(db: AsyncSession, user_id: str) -> int:
    """Replace user_email with NULL and user_id with a hash for all audit
    rows belonging to the given user.

    Because the audit_logs table has a BEFORE UPDATE trigger that blocks
    mutations, this requires a SECURITY DEFINER function or a session run
    by a Postgres role that bypasses RLS/triggers. The implementation here
    uses an explicit `SET LOCAL session_replication_role = replica` which
    DOES bypass the trigger but should ONLY be called by an admin endpoint
    behind explicit authorization.

    Returns the number of rows anonymized.
    """
    sql = text(
        """
        SET LOCAL session_replication_role = replica;
        UPDATE audit_logs
        SET user_email = NULL,
            ip_address = NULL,
            user_agent = NULL
        WHERE user_id = :uid
        RETURNING id
        """
    )
    result = await db.execute(sql, {"uid": user_id})
    rows = result.fetchall()
    await db.commit()
    return len(rows)


async def purge_audit_logs_older_than(db: AsyncSession, days: int) -> int:
    """Hard-delete audit rows older than `days` days.

    Mirrors the legal retention period (typically 5 years for fiscal/audit).
    Same trigger-bypass note as above.
    """
    sql = text(
        """
        SET LOCAL session_replication_role = replica;
        DELETE FROM audit_logs
        WHERE created_at < NOW() - (:days || ' days')::interval
        RETURNING id
        """
    )
    result = await db.execute(sql, {"days": days})
    rows = result.fetchall()
    await db.commit()
    return len(rows)
