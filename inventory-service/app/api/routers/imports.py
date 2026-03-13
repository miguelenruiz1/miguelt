"""Product CSV import and demo data endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import ORJSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, require_permission
from app.db.session import get_db_session
from app.services.import_service import ImportService

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


class DemoRequest(BaseModel):
    industries: list[str]


@router.post("/products")
async def import_products_csv(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.manage"))],
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
):
    """Upload a CSV file to bulk-create products with optional initial stock."""
    content = await file.read()
    csv_text = content.decode("utf-8-sig")  # handles BOM from Excel

    svc = ImportService(db)
    tenant_id = current_user.get("tenant_id", "default")
    user_id = current_user.get("id", "1")

    result = await svc.import_products_csv(tenant_id, csv_text, user_id)
    return ORJSONResponse(result)


@router.get("/templates/{name}")
async def download_template(
    name: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.view"))],
    db: AsyncSession = Depends(get_db_session),
):
    """Download a CSV template (basic, pet_food, technology, cleaning)."""
    if name not in ("basic", "pet_food", "technology", "cleaning"):
        return ORJSONResponse({"detail": f"Template no encontrado: {name}"}, status_code=404)

    svc = ImportService(db)
    csv_content = svc.generate_template(name)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=template_{name}.csv"},
    )


@router.post("/demo")
async def import_demo(
    body: DemoRequest,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    db: AsyncSession = Depends(get_db_session),
):
    """Seed demo data for selected industries."""
    svc = ImportService(db)
    tenant_id = current_user.get("tenant_id", "default")
    user_id = current_user.get("id", "1")

    results = []
    for industry in body.industries:
        if industry not in ("pet_food", "technology", "cleaning"):
            results.append({"industry": industry, "error": f"Industria desconocida: {industry}"})
            continue
        result = await svc.seed_demo(tenant_id, industry, user_id)
        results.append(result)

    return ORJSONResponse(results)


@router.delete("/demo")
async def delete_demo(
    body: DemoRequest,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("inventory.config"))],
    db: AsyncSession = Depends(get_db_session),
):
    """Delete demo data for selected industries."""
    svc = ImportService(db)
    tenant_id = current_user.get("tenant_id", "default")

    results = []
    for industry in body.industries:
        if industry not in ("pet_food", "technology", "cleaning"):
            results.append({"industry": industry, "error": f"Industria desconocida: {industry}"})
            continue
        result = await svc.delete_demo(tenant_id, industry)
        results.append(result)

    return ORJSONResponse(results)
