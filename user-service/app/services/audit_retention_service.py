"""Audit log PII scrubbing — Hábeas Data / GDPR right-to-be-forgotten support.

Audit logs are append-only (PG trigger blocks UPDATE/DELETE since mig 017),
but we still need to honor user deletion requests. The trigger checks the
session GUC `app.allow_audit_mutation` and skips when set to 'on', so the
service can grant a per-statement bypass without needing PG superuser.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession


class AuditMutationNotAllowed(RuntimeError):
    """Raised when the DB role lacks the privileges required to bypass the
    audit-log immutability trigger. The deployment needs either:
      - the GUC-aware trigger from migration 017+ (preferred), or
      - a SECURITY DEFINER function provisioned by the DBA, or
      - the role granted SUPERUSER (NOT recommended in prod).
    """


async def _allow_mutation(db: AsyncSession) -> None:
    """Best-effort: open a per-tx bypass that the BEFORE-trigger respects.

    First tries the GUC-based bypass (works for any role). Falls back to
    `session_replication_role = replica` which requires SUPERUSER and will
    raise a clear error if the role is not privileged.
    """
    try:
        await db.execute(text("SET LOCAL app.allow_audit_mutation = 'on'"))
        return
    except DBAPIError:
        pass
    try:
        await db.execute(text("SET LOCAL session_replication_role = replica"))
    except DBAPIError as exc:
        raise AuditMutationNotAllowed(
            "DB role cannot bypass audit_logs immutability trigger. "
            "Provision a SECURITY DEFINER function or grant the GUC "
            "'app.allow_audit_mutation' (see mig 017)."
        ) from exc


async def anonymize_user_audit_logs(db: AsyncSession, user_id: str) -> int:
    """Replace PII columns with NULL for all audit rows belonging to a user.

    Returns the number of rows anonymized.
    """
    await _allow_mutation(db)
    sql = text(
        """
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
    """
    await _allow_mutation(db)
    sql = text(
        """
        DELETE FROM audit_logs
        WHERE created_at < NOW() - (:days || ' days')::interval
        RETURNING id
        """
    )
    result = await db.execute(sql, {"days": days})
    rows = result.fetchall()
    await db.commit()
    return len(rows)
