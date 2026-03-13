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
        if not re.match(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.\w{2,5}$", fname):
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
