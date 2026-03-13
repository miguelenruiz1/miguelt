"""Base schemas and shared types."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# Legacy field types (still used by CustomProductField / CustomSupplierField)
FieldType = Literal["text", "number", "select", "boolean", "date", "reference"]


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
