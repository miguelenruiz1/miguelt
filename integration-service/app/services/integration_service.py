"""Core business logic for integrations — config, sync, invoicing."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import get_adapter
from app.core.errors import AdapterError, NotFoundError, ValidationError
from app.core.security import decrypt_credentials, encrypt_credentials
from app.repositories.integration_repo import (
    IntegrationConfigRepository, SyncJobRepository, SyncLogRepository,
)


class IntegrationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.config_repo = IntegrationConfigRepository(db)
        self.job_repo = SyncJobRepository(db)
        self.log_repo = SyncLogRepository(db)

    # ── Config Management ───────────────────────────────────────────

    async def list_configs(self, tenant_id: str):
        configs = await self.config_repo.list_for_tenant(tenant_id)
        for c in configs:
            c.credentials_enc = None  # never expose encrypted creds
        return configs

    async def get_config(self, config_id: str, tenant_id: str):
        config = await self.config_repo.get(config_id, tenant_id)
        if not config:
            raise NotFoundError("Integration config not found")
        config.credentials_enc = None
        return config

    async def upsert_config(self, tenant_id: str, data: dict, user_id: str | None = None):
        adapter = get_adapter(data["provider_slug"])
        if not adapter:
            raise ValidationError(f"Unknown provider: {data['provider_slug']}")

        credentials = data.pop("credentials", {})
        if credentials:
            data["credentials_enc"] = encrypt_credentials(json.dumps(credentials))

        data["tenant_id"] = tenant_id
        if not data.get("display_name"):
            data["display_name"] = adapter.display_name
        data["created_by"] = user_id

        config = await self.config_repo.upsert(data)
        config.credentials_enc = None
        return config

    async def delete_config(self, config_id: str, tenant_id: str):
        config = await self.config_repo.get(config_id, tenant_id)
        if not config:
            raise NotFoundError("Integration config not found")
        await self.config_repo.delete(config)

    async def test_connection(self, tenant_id: str, provider_slug: str, credentials: dict | None = None):
        adapter = get_adapter(provider_slug)
        if not adapter:
            raise ValidationError(f"Unknown provider: {provider_slug}")

        if credentials is None:
            config = await self.config_repo.get_by_provider(tenant_id, provider_slug)
            if not config or not config.credentials_enc:
                raise ValidationError("No credentials configured")
            credentials = json.loads(decrypt_credentials(config.credentials_enc))

        return await adapter.test_connection(credentials)

    # ── Sync ────────────────────────────────────────────────────────

    async def _get_credentials(self, config) -> dict:
        if not config.credentials_enc:
            raise ValidationError("No credentials configured for this integration")
        return json.loads(decrypt_credentials(config.credentials_enc))

    async def sync(self, tenant_id: str, provider_slug: str, direction: str, entity_type: str, user_id: str | None = None):
        config = await self.config_repo.get_by_provider(tenant_id, provider_slug)
        if not config:
            raise NotFoundError(f"Integration '{provider_slug}' not configured")
        if not config.is_active:
            raise ValidationError(f"Integration '{provider_slug}' is not active")

        adapter = get_adapter(provider_slug)
        if not adapter:
            raise ValidationError(f"No adapter for provider: {provider_slug}")

        credentials = await self._get_credentials(config)

        # Create sync job
        job = await self.job_repo.create({
            "tenant_id": tenant_id,
            "integration_id": config.id,
            "provider_slug": provider_slug,
            "direction": direction,
            "entity_type": entity_type,
            "status": "running",
            "started_at": datetime.now(timezone.utc),
            "triggered_by": user_id,
        })

        try:
            if entity_type == "products":
                # For push: we'd fetch products from inventory-service
                results = await adapter.sync_products(credentials, [], direction)
            elif entity_type == "customers":
                results = await adapter.sync_customers(credentials, [], direction)
            else:
                raise ValidationError(f"Unsupported entity type: {entity_type}")

            synced = sum(1 for r in results if r.get("status") == "success")
            failed = sum(1 for r in results if r.get("status") == "error")

            for r in results:
                await self.log_repo.create({
                    "sync_job_id": job.id,
                    "tenant_id": tenant_id,
                    "entity_type": entity_type,
                    "local_id": r.get("local_id"),
                    "remote_id": r.get("remote_id"),
                    "action": direction,
                    "status": r.get("status", "success"),
                    "error_detail": r.get("detail"),
                })

            await self.job_repo.update(job, {
                "status": "completed",
                "total_records": len(results),
                "synced_records": synced,
                "failed_records": failed,
                "completed_at": datetime.now(timezone.utc),
            })

            config.last_sync_at = datetime.now(timezone.utc)
            await self.db.flush()

        except Exception as e:
            await self.job_repo.update(job, {
                "status": "failed",
                "error_summary": str(e),
                "completed_at": datetime.now(timezone.utc),
            })
            raise

        return job

    # ── Invoicing ───────────────────────────────────────────────────

    async def create_invoice(self, tenant_id: str, provider_slug: str, invoice_data: dict, user_id: str | None = None):
        config = await self.config_repo.get_by_provider(tenant_id, provider_slug)
        if not config:
            raise NotFoundError(f"Integration '{provider_slug}' not configured")
        if not config.is_active:
            raise ValidationError(f"Integration '{provider_slug}' is not active")

        adapter = get_adapter(provider_slug)
        if not adapter:
            raise ValidationError(f"No adapter for provider: {provider_slug}")

        credentials = await self._get_credentials(config)
        result = await adapter.create_invoice(credentials, invoice_data)

        # Atomic log: the adapter call already hit DIAN/Matías so the remote
        # side is committed. If we crash between the external write and this
        # log insert we lose the CUFE permanently and can't reconcile. Wrap
        # in a nested transaction and, on failure, emit a structured warning
        # with the raw result so the operator can re-create the log from
        # log lines — better than silent data loss.
        try:
            async with self.db.begin_nested():
                await self.log_repo.create({
                    "sync_job_id": "manual",
                    "tenant_id": tenant_id,
                    "entity_type": "invoice",
                    "local_id": invoice_data.get("order_number"),
                    "remote_id": result.get("remote_id"),
                    "action": "create_invoice",
                    "status": "success",
                    "response_data": result,
                })
            await self.db.flush()
        except Exception:
            import structlog as _structlog
            _structlog.get_logger(__name__).exception(
                "invoice_log_persist_failed",
                tenant_id=tenant_id,
                provider_slug=provider_slug,
                remote_id=result.get("remote_id"),
                cufe=result.get("cufe"),
                invoice_number=invoice_data.get("invoice_number"),
            )
            # Surface the disaster to the caller — the invoice WAS created at
            # DIAN and has a CUFE; the record is now in the log line only.
            raise

        return result

    async def get_invoice(self, tenant_id: str, provider_slug: str, remote_id: str):
        config = await self.config_repo.get_by_provider(tenant_id, provider_slug)
        if not config:
            raise NotFoundError(f"Integration '{provider_slug}' not configured")

        adapter = get_adapter(provider_slug)
        if not adapter:
            raise ValidationError(f"No adapter for provider: {provider_slug}")

        credentials = await self._get_credentials(config)
        return await adapter.get_invoice(credentials, remote_id)

    async def list_remote_invoices(self, tenant_id: str, provider_slug: str, params: dict | None = None):
        config = await self.config_repo.get_by_provider(tenant_id, provider_slug)
        if not config:
            raise NotFoundError(f"Integration '{provider_slug}' not configured")

        adapter = get_adapter(provider_slug)
        if not adapter:
            raise ValidationError(f"No adapter for provider: {provider_slug}")

        credentials = await self._get_credentials(config)
        return await adapter.list_invoices(credentials, params)

    # ── Sync History ────────────────────────────────────────────────

    async def list_sync_jobs(self, tenant_id: str, **kwargs):
        return await self.job_repo.list(tenant_id, **kwargs)

    async def get_sync_job_logs(self, job_id: str, tenant_id: str, offset: int = 0, limit: int = 100):
        """Fetch a sync job's log entries, scoped to the caller's tenant.

        Without the tenant check an authenticated user from tenant A could
        read logs of tenant B just by guessing job UUIDs — classic IDOR.
        """
        job = await self.job_repo.get_by_id(job_id)
        if not job or str(job.tenant_id) != str(tenant_id):
            raise NotFoundError(f"Sync job '{job_id}' not found")
        return await self.log_repo.list_by_job(job_id, offset, limit)
