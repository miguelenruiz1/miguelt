"""Schemas for compliance validation results."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ValidationResult(BaseModel):
    valid: bool
    compliance_status: str
    missing_fields: list[str]
    missing_plots: bool
    warnings: list[str]
    framework: str
    checked_at: datetime
