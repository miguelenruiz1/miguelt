"""Router for compliance supply chain nodes — EUDR Art. 9.1.e-f."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.models.record import ComplianceRecord
from app.models.supply_chain_node import ComplianceSupplyChainNode
from app.schemas.supply_chain import (
    ReorderRequest,
    SupplyChainNodeCreate,
    SupplyChainNodeResponse,
    SupplyChainNodeUpdate,
)

log = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/compliance/records/{record_id}/supply-chain",
    tags=["supply-chain"],
)


def _tenant_id(user: dict) -> uuid.UUID:
    raw = str(user.get("tenant_id", "00000000-0000-0000-0000-000000000001"))
    try:
        return uuid.UUID(raw)
    except ValueError:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _get_record(record_id: uuid.UUID, tid: uuid.UUID, db: AsyncSession) -> ComplianceRecord:
    record = (
        await db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.id == record_id,
                ComplianceRecord.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError(f"Record '{record_id}' not found")
    return record


@router.post("/", response_model=SupplyChainNodeResponse, status_code=status.HTTP_201_CREATED)
async def add_node(
    record_id: uuid.UUID,
    body: SupplyChainNodeCreate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    await _get_record(record_id, tid, db)

    # Check sequence_order conflict
    existing = (
        await db.execute(
            select(ComplianceSupplyChainNode).where(
                ComplianceSupplyChainNode.record_id == record_id,
                ComplianceSupplyChainNode.sequence_order == body.sequence_order,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Sequence order {body.sequence_order} already used in this record")

    data = body.model_dump(exclude_unset=True)
    node = ComplianceSupplyChainNode(tenant_id=tid, record_id=record_id, **data)
    db.add(node)
    await db.flush()
    await db.refresh(node)
    return node


@router.get("/", response_model=list[SupplyChainNodeResponse])
async def list_nodes(
    record_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    await _get_record(record_id, tid, db)

    nodes = (
        await db.execute(
            select(ComplianceSupplyChainNode)
            .where(ComplianceSupplyChainNode.record_id == record_id)
            .order_by(ComplianceSupplyChainNode.sequence_order)
        )
    ).scalars().all()
    return nodes


@router.patch("/{node_id}", response_model=SupplyChainNodeResponse)
async def update_node(
    record_id: uuid.UUID,
    node_id: uuid.UUID,
    body: SupplyChainNodeUpdate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    node = (
        await db.execute(
            select(ComplianceSupplyChainNode).where(
                ComplianceSupplyChainNode.id == node_id,
                ComplianceSupplyChainNode.record_id == record_id,
                ComplianceSupplyChainNode.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if node is None:
        raise NotFoundError(f"Supply chain node '{node_id}' not found")

    update_data = body.model_dump(exclude_unset=True)

    # Check sequence_order conflict if changing it
    new_seq = update_data.get("sequence_order")
    if new_seq is not None and new_seq != node.sequence_order:
        conflict = (
            await db.execute(
                select(ComplianceSupplyChainNode).where(
                    ComplianceSupplyChainNode.record_id == record_id,
                    ComplianceSupplyChainNode.sequence_order == new_seq,
                    ComplianceSupplyChainNode.id != node_id,
                )
            )
        ).scalar_one_or_none()
        if conflict is not None:
            raise ConflictError(f"Sequence order {new_seq} already used")

    for key, val in update_data.items():
        setattr(node, key, val)

    await db.flush()
    await db.refresh(node)
    return node


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    record_id: uuid.UUID,
    node_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    node = (
        await db.execute(
            select(ComplianceSupplyChainNode).where(
                ComplianceSupplyChainNode.id == node_id,
                ComplianceSupplyChainNode.record_id == record_id,
                ComplianceSupplyChainNode.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if node is None:
        raise NotFoundError(f"Supply chain node '{node_id}' not found")

    await db.delete(node)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/reorder", response_model=list[SupplyChainNodeResponse])
async def reorder_nodes(
    record_id: uuid.UUID,
    body: ReorderRequest,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    await _get_record(record_id, tid, db)

    nodes = (
        await db.execute(
            select(ComplianceSupplyChainNode)
            .where(
                ComplianceSupplyChainNode.record_id == record_id,
                ComplianceSupplyChainNode.tenant_id == tid,
            )
        )
    ).scalars().all()

    node_map = {str(n.id): n for n in nodes}

    for item in body.order:
        nid = str(item.get("node_id", ""))
        seq = item.get("sequence_order")
        if nid in node_map and seq is not None:
            node_map[nid].sequence_order = seq

    await db.flush()

    # Return refreshed list
    updated = (
        await db.execute(
            select(ComplianceSupplyChainNode)
            .where(ComplianceSupplyChainNode.record_id == record_id)
            .order_by(ComplianceSupplyChainNode.sequence_order)
        )
    ).scalars().all()
    return updated
