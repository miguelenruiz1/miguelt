"""Checkout router — build Wompi payment URLs."""
from __future__ import annotations

import hashlib
import urllib.parse
from decimal import Decimal
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.db.session import get_db_session
from app.core.errors import NotFoundError
from app.core.settings import get_settings
from app.db.models import BillingCycle, InvoiceStatus
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.payment_repo import PaymentGatewayRepository
from app.repositories.plan_repo import PlanRepository
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/v1/payments", tags=["checkout"])
log = structlog.get_logger(__name__)


class CheckoutRequest(BaseModel):
    plan_slug: str = Field(..., min_length=1, max_length=100)
    billing_cycle: str = Field(default="monthly")


class CheckoutResponse(BaseModel):
    checkout_url: str
    invoice_id: str


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create checkout session with payment URL",
)
async def create_checkout(
    body: CheckoutRequest,
    current_user: Annotated[dict, Depends(require_permission("subscription.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> CheckoutResponse:
    """
    1. Get or create subscription for tenant
    2. Create invoice (status=open) for the plan
    3. Get active gateway config for tenant
    4. Build checkout URL based on gateway
    5. Return { checkout_url, invoice_id }
    """
    tenant_id = current_user.get("tenant_id", "default")
    performed_by = current_user.get("id") or current_user.get("email")

    plan_repo = PlanRepository(db)
    invoice_repo = InvoiceRepository(db)
    payment_repo = PaymentGatewayRepository(db)
    sub_svc = SubscriptionService(db)

    # 1. Resolve plan
    plan = await plan_repo.get_by_slug(body.plan_slug)
    if not plan:
        raise NotFoundError(f"Plan '{body.plan_slug}' not found")

    # Determine amount
    billing_cycle = body.billing_cycle
    if billing_cycle == "annual" and plan.price_annual is not None:
        amount = plan.price_annual
    else:
        amount = plan.price_monthly
        billing_cycle = "monthly"

    if amount <= Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Free plans do not require checkout",
        )

    # 2. Get or create subscription
    sub = await sub_svc.get_or_create(tenant_id, body.plan_slug)

    # 3. Create invoice
    invoice_number = await invoice_repo.next_invoice_number()
    invoice = await invoice_repo.create({
        "subscription_id": sub.id,
        "tenant_id": tenant_id,
        "invoice_number": invoice_number,
        "status": InvoiceStatus.open,
        "amount": amount,
        "currency": plan.currency,
        "period_start": sub.current_period_start,
        "period_end": sub.current_period_end,
        "line_items": [
            {
                "description": f"{plan.name} plan — {billing_cycle}",
                "quantity": 1,
                "unit_price": float(amount),
                "amount": float(amount),
            }
        ],
    })

    # 4. Get Wompi gateway config (try tenant first, then platform-level)
    gateway_config = await payment_repo.get(tenant_id, "wompi")
    if not gateway_config:
        gateway_config = await payment_repo.get("platform", "wompi")
    if not gateway_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wompi no está configurado. Configúralo desde Plataforma → Pasarela de Cobro.",
        )

    # 5. Build Wompi checkout URL with integrity signature
    creds = gateway_config.credentials or {}
    is_test = gateway_config.is_test_mode
    public_key = creds.get("public_key", "")
    integrity_key = creds.get("integrity_key", "")

    amount_cents = int(amount * 100)
    reference = f"{tenant_id}:{invoice.id}"

    settings = get_settings()
    app_url = settings.APP_URL

    # Wompi integrity signature: SHA256("{reference}{amount_in_cents}{currency}{integrity_key}")
    signature_payload = f"{reference}{amount_cents}{plan.currency}{integrity_key}"
    integrity_signature = hashlib.sha256(signature_payload.encode("utf-8")).hexdigest()

    base = "https://checkout.wompi.co/p/" if not is_test else "https://sandbox.wompi.co/p/"
    params = {
        "public-key": public_key,
        "currency": plan.currency,
        "amount-in-cents": str(amount_cents),
        "reference": reference,
        "signature:integrity": integrity_signature,
        "redirect-url": f"{app_url}/checkout/result?ref={reference}",
    }
    checkout_url = f"{base}?{urllib.parse.urlencode(params)}"

    log.info(
        "checkout_created",
        tenant_id=tenant_id,
        plan=body.plan_slug,
        gateway="wompi",
        invoice_id=invoice.id,
        amount=float(amount),
        is_test=is_test,
    )

    return CheckoutResponse(checkout_url=checkout_url, invoice_id=invoice.id)
