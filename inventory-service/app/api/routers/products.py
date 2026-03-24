"""Products CRUD endpoints."""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, UploadFile, status, HTTPException
from fastapi.responses import ORJSONResponse

from app.api.deps import ModuleUser, require_permission
from app.core.settings import get_settings
from app.db.session import get_db_session
from app.domain.schemas import PaginatedProducts, ProductCreate, ProductOut, ProductUpdate
from app.services.product_service import ProductService
from app.services.audit_service import InventoryAuditService
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/products", tags=["products"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


def _build_product_out(product, has_movements: bool = False) -> dict:
    out = ProductOut.model_validate(product).model_dump(mode="json")
    out["has_movements"] = has_movements
    return out


@router.get("", response_model=PaginatedProducts)
async def list_products(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    product_type_id: str | None = None,
    is_active: bool | None = True,
    search: str | None = None,
    stock_status: str | None = Query(None, regex="^(low|out)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> ORJSONResponse:
    svc = ProductService(db)
    items, total = await svc.list(
        tenant_id=current_user["tenant_id"],
        product_type_id=product_type_id,
        is_active=is_active,
        search=search,
        stock_status=stock_status,
        offset=offset,
        limit=limit,
    )
    return ORJSONResponse({
        "items": [_build_product_out(p) for p in items],
        "total": total,
        "offset": offset,
        "limit": limit,
    })


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    body: ProductCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = ProductService(db)
    audit = InventoryAuditService(db)
    data = body.model_dump()
    data["created_by"] = current_user.get("id")
    product = await svc.create(current_user["tenant_id"], data)
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.product.create", resource_type="product",
        resource_id=product.id, new_data=body.model_dump(), ip_address=_ip(request),
    )
    return ORJSONResponse(_build_product_out(product), status_code=201)


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = ProductService(db)
    product = await svc.get(product_id, current_user["tenant_id"])
    hm = await svc.has_movements(product.id, current_user["tenant_id"])
    return ORJSONResponse(_build_product_out(product, has_movements=hm))


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: str,
    body: ProductUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = ProductService(db)
    audit = InventoryAuditService(db)
    old = await svc.get(product_id, current_user["tenant_id"])
    old_data = ProductOut.model_validate(old).model_dump(mode="json")
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_by"] = current_user.get("id")
    product = await svc.update(product_id, current_user["tenant_id"], update_data)
    hm = await svc.has_movements(product.id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.product.update", resource_type="product",
        resource_id=product.id, old_data=old_data,
        new_data=body.model_dump(exclude_none=True), ip_address=_ip(request),
    )
    return ORJSONResponse(_build_product_out(product, has_movements=hm))


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    svc = ProductService(db)
    audit = InventoryAuditService(db)
    await svc.delete(product_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.product.delete", resource_type="product",
        resource_id=product_id, ip_address=_ip(request),
    )
    return Response(status_code=204)


@router.post("/{product_id}/images", response_model=ProductOut)
async def upload_product_image(
    product_id: str,
    file: UploadFile,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    settings = get_settings()

    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no soportado. Usa JPG, PNG, WebP o GIF.",
        )

    content = await file.read()
    if len(content) > settings.MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"La imagen excede el límite de {settings.MAX_IMAGE_SIZE // (1024*1024)} MB.",
        )

    ext = file.content_type.split("/")[-1].replace("jpeg", "jpg")
    filename = f"{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
    images_dir = Path(settings.UPLOAD_DIR) / "products"
    images_dir.mkdir(parents=True, exist_ok=True)
    (images_dir / filename).write_bytes(content)

    image_url = f"/uploads/products/{filename}"

    svc = ProductService(db)
    product = await svc.get(product_id, current_user["tenant_id"])
    current_images: list = list(product.images or [])
    current_images.append(image_url)
    product = await svc.update(product_id, current_user["tenant_id"], {"images": current_images})
    hm = await svc.has_movements(product.id, current_user["tenant_id"])
    return ORJSONResponse(_build_product_out(product, has_movements=hm))


@router.delete("/{product_id}/images")
async def delete_product_image(
    product_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
    image_url: str = Query(...),
) -> ORJSONResponse:
    settings = get_settings()

    # Remove file from disk
    if "/products/" in image_url:
        fname = image_url.split("/products/")[-1]
        if not re.match(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}(_[a-f0-9]+)?\.\w{2,5}$", fname):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL de imagen inválida.")
        fpath = Path(settings.UPLOAD_DIR) / "products" / fname
        if fpath.exists():
            fpath.unlink()

    svc = ProductService(db)
    product = await svc.get(product_id, current_user["tenant_id"])
    current_images: list = [img for img in (product.images or []) if img != image_url]
    product = await svc.update(product_id, current_user["tenant_id"], {"images": current_images})
    hm = await svc.has_movements(product.id, current_user["tenant_id"])
    return ORJSONResponse(_build_product_out(product, has_movements=hm))


@router.get("/{product_id}/customer-prices")
async def get_product_customer_prices(
    product_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
):
    """Return all customers with active special prices for this product."""
    from app.services.customer_price_service import CustomerPriceService
    from app.domain.schemas.customer_price import CustomerPriceOut
    svc = CustomerPriceService(db)
    prices = await svc.list_for_product(current_user["tenant_id"], product_id, active_only=True)
    return [CustomerPriceOut.model_validate(p) for p in prices]


@router.get("/{product_id}/cost-history")
async def get_product_cost_history(
    product_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
    limit: int = 10,
    supplier_id: str | None = None,
):
    from sqlalchemy import select as _sel
    from app.db.models.cost_history import ProductCostHistory
    from app.domain.schemas.cost_history import ProductCostHistoryOut
    q = _sel(ProductCostHistory).where(ProductCostHistory.product_id == product_id, ProductCostHistory.tenant_id == current_user["tenant_id"]).order_by(ProductCostHistory.received_at.desc()).limit(limit)
    if supplier_id:
        q = q.where(ProductCostHistory.supplier_id == supplier_id)
    result = await db.execute(q)
    return [ProductCostHistoryOut.model_validate(h) for h in result.scalars().all()]


@router.get("/{product_id}/pricing")
async def get_product_pricing(
    product_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import select as _sel, func as _func
    from app.db.models.cost_history import ProductCostHistory
    from app.db.models.production import StockLayer
    from app.domain.schemas.cost_history import ProductCostHistoryOut
    svc = ProductService(db)
    product = await svc.get(product_id, current_user["tenant_id"])
    hist_result = await db.execute(_sel(ProductCostHistory).where(ProductCostHistory.product_id == product_id, ProductCostHistory.tenant_id == current_user["tenant_id"]).order_by(ProductCostHistory.received_at.desc()).limit(5))
    history = [ProductCostHistoryOut.model_validate(h) for h in hist_result.scalars().all()]
    avg_result = await db.execute(_sel(_func.sum(StockLayer.unit_cost * StockLayer.quantity_remaining), _func.sum(StockLayer.quantity_remaining)).where(StockLayer.entity_id == product_id, StockLayer.quantity_remaining > 0))
    row = avg_result.one()
    current_avg_cost = float(row[0] / row[1]) if row[1] and row[1] > 0 else None
    return {"last_purchase_cost": float(product.last_purchase_cost) if product.last_purchase_cost else None, "last_purchase_date": product.last_purchase_date.isoformat() if product.last_purchase_date else None, "last_purchase_supplier": product.last_purchase_supplier, "suggested_sale_price": float(product.suggested_sale_price) if product.suggested_sale_price else None, "minimum_sale_price": float(product.minimum_sale_price) if product.minimum_sale_price else None, "margin_target": float(product.margin_target) if product.margin_target else None, "margin_minimum": float(product.margin_minimum) if product.margin_minimum else None, "margin_cost_method": product.margin_cost_method, "current_avg_cost": current_avg_cost, "cost_history": history}


@router.post("/{product_id}/recalculate-prices")
async def recalculate_product_prices(
    product_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
):
    from app.services.pricing_engine import PricingEngine
    svc = ProductService(db)
    product = await svc.get(product_id, current_user["tenant_id"])
    engine = PricingEngine(db)
    await engine.recalculate_product_prices(product, current_user["tenant_id"])
    return _build_product_out(product)


@router.patch("/{product_id}/margins")
async def update_product_margins(
    product_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    db: AsyncSession = Depends(get_db_session),
    margin_target: float | None = None,
    margin_minimum: float | None = None,
    margin_cost_method: str | None = None,
):
    from decimal import Decimal
    from app.services.pricing_engine import PricingEngine
    svc = ProductService(db)
    update_data: dict = {}
    if margin_target is not None:
        update_data["margin_target"] = Decimal(str(margin_target))
    if margin_minimum is not None:
        update_data["margin_minimum"] = Decimal(str(margin_minimum))
    if margin_cost_method is not None:
        update_data["margin_cost_method"] = margin_cost_method
    product = await svc.update(product_id, current_user["tenant_id"], update_data)
    engine = PricingEngine(db)
    await engine.recalculate_product_prices(product, current_user["tenant_id"])
    return _build_product_out(product)


@router.post("/fix-zero-costs", response_model=dict)
async def fix_zero_costs(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    """Find products with sales but zero cost, and patch from last received PO."""
    from app.db.models import Product
    from app.db.models.cost_history import ProductCostHistory
    from decimal import Decimal

    tenant_id = current_user["tenant_id"]

    # Find products with zero/null weighted_avg_cost or last_purchase_cost
    result = await db.execute(
        select(Product)
        .where(
            Product.tenant_id == tenant_id,
            Product.is_active == True,
            or_(
                Product.last_purchase_cost == None,
                Product.last_purchase_cost == 0,
            ),
        )
    )
    zero_cost_products = result.scalars().all()

    fixed = []
    for product in zero_cost_products:
        # Find last cost history record
        cost_result = await db.execute(
            select(ProductCostHistory)
            .where(
                ProductCostHistory.product_id == product.id,
                ProductCostHistory.tenant_id == tenant_id,
                ProductCostHistory.unit_cost_base_uom > 0,
            )
            .order_by(ProductCostHistory.received_at.desc())
            .limit(1)
        )
        last_cost = cost_result.scalar_one_or_none()

        if last_cost:
            product.last_purchase_cost = last_cost.unit_cost_base_uom
            product.last_purchase_date = last_cost.received_at
            product.last_purchase_supplier = last_cost.supplier_name
            fixed.append({
                "sku": product.sku,
                "name": product.name,
                "patched_cost": float(last_cost.unit_cost_base_uom),
                "source": f"PO cost history ({last_cost.purchase_order_id[:8] if last_cost.purchase_order_id else 'N/A'})",
            })

    await db.flush()

    # Audit
    if fixed:
        audit = InventoryAuditService(db)
        await audit.log(
            tenant_id=tenant_id,
            user=current_user,
            action="inventory.product.fix_costs",
            resource_type="product",
            resource_id="batch",
            new_data={"fixed_count": len(fixed), "products": fixed},
        )

    return ORJSONResponse({
        "scanned": len(zero_cost_products),
        "fixed": len(fixed),
        "products": fixed,
    })


@router.get("/{product_id}/purchase-documents")
async def get_product_purchase_documents(
    product_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    """Get all PO attachments (invoices, remissions) linked to a product via cost history."""
    from app.db.models.cost_history import ProductCostHistory
    from app.db.models.purchase_order import PurchaseOrder

    tenant_id = current_user["tenant_id"]

    # Get all PO IDs that supplied this product
    cost_records = (await db.execute(
        select(
            ProductCostHistory.purchase_order_id,
            ProductCostHistory.supplier_name,
            ProductCostHistory.unit_cost_base_uom,
            ProductCostHistory.qty_purchased,
            ProductCostHistory.total_cost,
            ProductCostHistory.received_at,
        )
        .where(
            ProductCostHistory.product_id == product_id,
            ProductCostHistory.tenant_id == tenant_id,
        )
        .order_by(ProductCostHistory.received_at.desc())
    )).all()

    if not cost_records:
        return ORJSONResponse({"documents": [], "cost_records": []})

    po_ids = list({r[0] for r in cost_records})

    # Fetch POs with their attachments
    pos = (await db.execute(
        select(PurchaseOrder.id, PurchaseOrder.po_number, PurchaseOrder.attachments,
               PurchaseOrder.supplier_invoice_number, PurchaseOrder.supplier_invoice_date,
               PurchaseOrder.supplier_invoice_total)
        .where(PurchaseOrder.id.in_(po_ids))
    )).all()

    documents = []
    for po_row in pos:
        po_id, po_number, attachments, inv_number, inv_date, inv_total = po_row
        for att in (attachments or []):
            documents.append({
                "po_id": po_id,
                "po_number": po_number,
                "file_name": att.get("name", ""),
                "file_url": att.get("url", ""),
                "file_type": att.get("type", "other"),
                "classification": att.get("classification", att.get("type", "other")),
                "supplier_invoice_number": inv_number,
                "supplier_invoice_date": str(inv_date) if inv_date else None,
                "supplier_invoice_total": float(inv_total) if inv_total else None,
            })

    records = [
        {
            "po_id": r[0],
            "supplier_name": r[1],
            "unit_cost": float(r[2]),
            "qty": float(r[3]),
            "total_cost": float(r[4]),
            "received_at": r[5].isoformat() if r[5] else None,
        }
        for r in cost_records
    ]

    return ORJSONResponse({"documents": documents, "cost_records": records})
