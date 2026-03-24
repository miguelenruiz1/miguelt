"""Enums shared across inventory models."""
from __future__ import annotations

import enum


class WarehouseType(str, enum.Enum):
    main       = "main"
    secondary  = "secondary"
    virtual    = "virtual"
    transit    = "transit"


class MovementType(str, enum.Enum):
    purchase       = "purchase"
    sale           = "sale"
    transfer       = "transfer"
    adjustment_in  = "adjustment_in"
    adjustment_out = "adjustment_out"
    return_         = "return"
    waste           = "waste"
    production_in   = "production_in"
    production_out  = "production_out"


class POStatus(str, enum.Enum):
    draft            = "draft"
    pending_approval = "pending_approval"
    approved         = "approved"
    sent             = "sent"
    confirmed = "confirmed"
    partial   = "partial"
    received  = "received"
    canceled     = "canceled"
    consolidated = "consolidated"


class CycleCountStatus(str, enum.Enum):
    draft       = "draft"
    in_progress = "in_progress"
    completed   = "completed"
    approved    = "approved"
    canceled    = "canceled"


class SalesOrderStatus(str, enum.Enum):
    draft              = "draft"
    pending_approval   = "pending_approval"
    confirmed          = "confirmed"
    picking            = "picking"
    shipped            = "shipped"
    delivered          = "delivered"
    returned           = "returned"
    canceled           = "canceled"
    rejected           = "rejected"


class CycleCountMethodology(str, enum.Enum):
    control_group          = "control_group"
    location_audit         = "location_audit"
    random_selection       = "random_selection"
    diminishing_population = "diminishing_population"
    product_category       = "product_category"
    abc                    = "abc"
