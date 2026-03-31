"""Pydantic schemas — re-exports from submodules."""
from app.domain.schemas.base import OrmBase, FieldType
from app.domain.schemas.category import CategoryCreate, CategoryUpdate, CategoryOut, PaginatedCategories
from app.domain.schemas.product import ProductCreate, ProductUpdate, ProductOut, PaginatedProducts
from app.domain.schemas.warehouse import (
    WarehouseCreate, WarehouseUpdate, WarehouseOut,
    LocationCreate, LocationUpdate, LocationOut,
)
from app.domain.schemas.stock import (
    StockLevelOut, ReceiveStockIn, IssueStockIn, TransferStockIn, AdjustStockIn,
    AdjustInStockIn, AdjustOutStockIn,
    AssignLocationIn,
    ReturnStockIn, WasteStockIn,
    QCActionIn,
    StockMovementOut, PaginatedStockLevels, PaginatedMovements,
)
from app.domain.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierOut, PaginatedSuppliers
from app.domain.schemas.purchase_order import (
    POLineCreate, POCreate, POUpdate, POLineOut, POOut, PaginatedPOs,
    LineReceiptIn, ReceivePOIn, PORejectIn, POApprovalLogOut, POKPIs,
    ConsolidateRequest, ConsolidationCandidate, ConsolidationResult, ConsolidationInfo,
)
from app.domain.schemas.config import (
    MovementTypeCreate, MovementTypeUpdate, MovementTypeOut,
    WarehouseTypeCreate, WarehouseTypeUpdate, WarehouseTypeOut,
    ProductTypeCreate, ProductTypeUpdate, ProductTypeOut,
    OrderTypeCreate, OrderTypeUpdate, OrderTypeOut,
    CustomFieldCreate, CustomFieldUpdate, CustomFieldOut,
    SupplierTypeCreate, SupplierTypeUpdate, SupplierTypeOut,
    CustomSupplierFieldCreate, CustomSupplierFieldUpdate, CustomSupplierFieldOut,
    CustomWarehouseFieldCreate, CustomWarehouseFieldUpdate, CustomWarehouseFieldOut,
    CustomMovementFieldCreate, CustomMovementFieldUpdate, CustomMovementFieldOut,
    SerialStatusCreate, SerialStatusUpdate, SerialStatusOut,
    EventTypeCreate, EventTypeUpdate, EventTypeOut,
    EventSeverityCreate, EventSeverityUpdate, EventSeverityOut,
    EventStatusCreate, EventStatusUpdate, EventStatusOut,
)
from app.domain.schemas.analytics import MovementTrend, AnalyticsOverview
from app.domain.schemas.events import (
    EventCreate, EventStatusChange, EventImpactCreate,
    EventOut, EventImpactOut, EventStatusLogOut, PaginatedEvents,
)
from app.domain.schemas.tracking import (
    SerialCreate, SerialUpdate, SerialOut, PaginatedSerials,
    BatchCreate, BatchUpdate, BatchOut, PaginatedBatches,
    BatchDispatchEntry, TraceForwardOut,
    SOBatchEntry, TraceBackwardOut,
    BatchSearchResult,
)
from app.domain.schemas.production import (
    RecipeComponentCreate, RecipeCreate, RecipeUpdate,
    RecipeComponentOut, RecipeOut,
    ProductionRunCreate, ProductionRunUpdate, ProductionRunOut, ProductionRunReject, PaginatedProductionRuns,
    EmissionLineCreate, EmissionCreate, EmissionLineOut, EmissionOut,
    ReceiptLineCreate, ReceiptCreate, ReceiptLineOut, ReceiptOut,
    ProductionResourceCreate, ProductionResourceUpdate, ProductionResourceOut,
    RecipeResourceCreate, RecipeResourceOut, RunResourceCostOut,
    MRPRequest, MRPLine, MRPResult,
    CapacityLine, CapacityResult,
    StockLayerOut,
)
from app.domain.schemas.cycle_count import (
    CycleCountCreate, RecordCountIn, RecountIn,
    CycleCountItemOut, CycleCountOut, PaginatedCycleCounts,
    IRASnapshotOut, IRAComputeOut, FeasibilityOut, ProductDiscrepancyOut,
)
from app.domain.schemas.uom import (
    UoMCreate, UoMOut, UoMConversionCreate, UoMConversionOut,
    ConvertRequest, ConvertResponse,
)
from app.domain.schemas.cost_history import ProductCostHistoryOut, PaginatedCostHistory
from app.domain.schemas.pricing import (
    ProductPricingOut, MarginUpdateIn,
    GlobalMarginOut, GlobalMarginUpdateIn,
)
from app.domain.schemas.audit import AuditLogOut, PaginatedAuditLogs
from app.domain.schemas.partner import PartnerCreate, PartnerUpdate, PartnerOut, PaginatedPartners
from app.domain.schemas.pagination import (
    PaginatedRecipes, PaginatedWarehouses,
    PaginatedCustomerTypes, PaginatedLocations,
    PaginatedProductTypes, PaginatedOrderTypes, PaginatedSupplierTypes,
    PaginatedMovementTypes, PaginatedWarehouseTypes,
    PaginatedEventTypes, PaginatedEventSeverities, PaginatedEventStatuses,
    PaginatedSerialStatuses,
    PaginatedCustomFields, PaginatedCustomSupplierFields,
    PaginatedCustomWarehouseFields, PaginatedCustomMovementFields,
)

__all__ = [
    # Base
    "OrmBase", "FieldType",
    # Category
    "CategoryCreate", "CategoryUpdate", "CategoryOut", "PaginatedCategories",
    # Product
    "ProductCreate", "ProductUpdate", "ProductOut", "PaginatedProducts",
    # Warehouse
    "WarehouseCreate", "WarehouseUpdate", "WarehouseOut",
    "LocationCreate", "LocationUpdate", "LocationOut",
    # Stock
    "StockLevelOut", "ReceiveStockIn", "IssueStockIn", "TransferStockIn", "AdjustStockIn",
    "AdjustInStockIn", "AdjustOutStockIn",
    "ReturnStockIn", "WasteStockIn",
    "QCActionIn",
    "StockMovementOut", "PaginatedStockLevels", "PaginatedMovements",
    # Supplier
    "SupplierCreate", "SupplierUpdate", "SupplierOut", "PaginatedSuppliers",
    # Purchase Order
    "POLineCreate", "POCreate", "POUpdate", "POLineOut", "POOut", "PaginatedPOs",
    "LineReceiptIn", "ReceivePOIn",
    "ConsolidateRequest", "ConsolidationCandidate", "ConsolidationResult", "ConsolidationInfo",
    # Config types
    "MovementTypeCreate", "MovementTypeUpdate", "MovementTypeOut",
    "WarehouseTypeCreate", "WarehouseTypeUpdate", "WarehouseTypeOut",
    "ProductTypeCreate", "ProductTypeUpdate", "ProductTypeOut",
    "OrderTypeCreate", "OrderTypeUpdate", "OrderTypeOut",
    "CustomFieldCreate", "CustomFieldUpdate", "CustomFieldOut",
    "SupplierTypeCreate", "SupplierTypeUpdate", "SupplierTypeOut",
    "CustomSupplierFieldCreate", "CustomSupplierFieldUpdate", "CustomSupplierFieldOut",
    "CustomWarehouseFieldCreate", "CustomWarehouseFieldUpdate", "CustomWarehouseFieldOut",
    "CustomMovementFieldCreate", "CustomMovementFieldUpdate", "CustomMovementFieldOut",
    "SerialStatusCreate", "SerialStatusUpdate", "SerialStatusOut",
    "EventTypeCreate", "EventTypeUpdate", "EventTypeOut",
    "EventSeverityCreate", "EventSeverityUpdate", "EventSeverityOut",
    "EventStatusCreate", "EventStatusUpdate", "EventStatusOut",
    # Analytics
    "MovementTrend", "AnalyticsOverview",
    # Events
    "EventCreate", "EventStatusChange", "EventImpactCreate",
    "EventOut", "EventImpactOut", "EventStatusLogOut", "PaginatedEvents",
    # Tracking
    "SerialCreate", "SerialUpdate", "SerialOut", "PaginatedSerials",
    "BatchCreate", "BatchUpdate", "BatchOut", "PaginatedBatches",
    "BatchDispatchEntry", "TraceForwardOut",
    "SOBatchEntry", "TraceBackwardOut",
    "BatchSearchResult",
    # Production
    "RecipeComponentCreate", "RecipeCreate", "RecipeUpdate",
    "RecipeComponentOut", "RecipeOut",
    "ProductionRunCreate", "ProductionRunUpdate", "ProductionRunOut", "ProductionRunReject", "PaginatedProductionRuns",
    "EmissionLineCreate", "EmissionCreate", "EmissionLineOut", "EmissionOut",
    "ReceiptLineCreate", "ReceiptCreate", "ReceiptLineOut", "ReceiptOut",
    "StockLayerOut",
    # Cycle Count
    "CycleCountCreate", "RecordCountIn", "RecountIn",
    "CycleCountItemOut", "CycleCountOut", "PaginatedCycleCounts",
    "IRASnapshotOut", "IRAComputeOut", "FeasibilityOut", "ProductDiscrepancyOut",
    # Audit
    "AuditLogOut", "PaginatedAuditLogs",
    # Pagination (new)
    "PaginatedRecipes", "PaginatedWarehouses",
    "PaginatedCustomerTypes", "PaginatedLocations",
    "PaginatedProductTypes", "PaginatedOrderTypes", "PaginatedSupplierTypes",
    "PaginatedMovementTypes", "PaginatedWarehouseTypes",
    "PaginatedEventTypes", "PaginatedEventSeverities", "PaginatedEventStatuses",
    "PaginatedSerialStatuses",
    "PaginatedCustomFields", "PaginatedCustomSupplierFields",
    "PaginatedCustomWarehouseFields", "PaginatedCustomMovementFields",
    # UoM
    "UoMCreate", "UoMOut", "UoMConversionCreate", "UoMConversionOut",
    "ConvertRequest", "ConvertResponse",
    # Cost History
    "ProductCostHistoryOut", "PaginatedCostHistory",
    # Pricing
    "ProductPricingOut", "MarginUpdateIn",
    "GlobalMarginOut", "GlobalMarginUpdateIn",
    # Partner
    "PartnerCreate", "PartnerUpdate", "PartnerOut", "PaginatedPartners",
]
