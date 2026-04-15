"""ORM models for inventory-service — re-exports from submodules."""
from app.db.models.enums import (
    WarehouseType, MovementType, POStatus, SalesOrderStatus,
    CycleCountStatus, CycleCountMethodology,
)
from app.db.models.config import (
    ProductType,
    OrderType,
    DynamicMovementType,
    DynamicWarehouseType,
    CustomProductField,
    SupplierType,
    CustomSupplierField,
    CustomWarehouseField,
    CustomMovementField,
)
from app.db.models.category import Category
from app.db.models.entity import Product
from app.db.models.tax import TaxRate, TaxCategory, SalesOrderLineTax
from app.db.models.warehouse import Warehouse, WarehouseLocation
from app.db.models.stock import StockLevel, StockMovement, StockReservation
from app.db.models.supplier import Supplier
from app.db.models.purchase_order import PurchaseOrder, PurchaseOrderLine, POApprovalLog
from app.db.models.goods_receipt import GoodsReceipt, GoodsReceiptLine
from app.db.models.customer import CustomerType, Customer
from app.db.models.customer_price import CustomerPrice, CustomerPriceHistory
from app.db.models.partner import BusinessPartner
from app.db.models.sales_order import SalesOrder, SalesOrderLine, SOApprovalLog, TenantInventoryConfig
from app.db.models.variant import VariantAttribute, VariantAttributeOption, ProductVariant
from app.db.models.alert import StockAlert
from app.db.models.events import (
    EventType,
    EventSeverity,
    EventStatus,
    InventoryEvent,
    EventImpact,
    EventStatusLog,
)
from app.db.models.tracking import SerialStatus, EntitySerial, EntityBatch
from app.db.models.production import (
    EntityRecipe,
    RecipeComponent,
    ProductionRun,
    ProductionEmission,
    ProductionEmissionLine,
    ProductionReceipt,
    ProductionReceiptLine,
    ProductionResource,
    RecipeResource,
    ProductionRunResourceCost,
    StockLayer,
)
from app.db.models.uom import UnitOfMeasure, UoMConversion
from app.db.models.cost_history import ProductCostHistory
from app.db.models.cycle_count import CycleCount, CycleCountItem, IRASnapshot
from app.db.models.audit import InventoryAuditLog

__all__ = [
    # Enums
    "WarehouseType", "MovementType", "POStatus", "SalesOrderStatus",
    "CycleCountStatus", "CycleCountMethodology",
    # Config
    "ProductType", "OrderType",
    "DynamicMovementType", "DynamicWarehouseType",
    "CustomProductField", "SupplierType", "CustomSupplierField",
    "CustomWarehouseField", "CustomMovementField",
    # Category
    "Category",
    # Entity
    "Product",
    # Tax
    "TaxRate", "TaxCategory", "SalesOrderLineTax",
    # Warehouse
    "Warehouse", "WarehouseLocation",
    # Stock
    "StockLevel", "StockMovement", "StockReservation",
    # Supplier
    "Supplier",
    # Purchase Order
    "PurchaseOrder", "PurchaseOrderLine", "POApprovalLog",
    "GoodsReceipt", "GoodsReceiptLine",
    # Customer & Pricing
    "CustomerType", "Customer",
    "CustomerPrice", "CustomerPriceHistory",
    # Sales Order
    "SalesOrder", "SalesOrderLine", "SOApprovalLog", "TenantInventoryConfig",
    # Variants
    "VariantAttribute", "VariantAttributeOption", "ProductVariant",
    # Alerts
    "StockAlert",
    # Events
    "EventType", "EventSeverity", "EventStatus",
    "InventoryEvent", "EventImpact", "EventStatusLog",
    # Tracking
    "SerialStatus", "EntitySerial", "EntityBatch",
    # Production
    "EntityRecipe", "RecipeComponent", "ProductionRun",
    "ProductionEmission", "ProductionEmissionLine",
    "ProductionReceipt", "ProductionReceiptLine",
    "ProductionResource", "RecipeResource", "ProductionRunResourceCost",
    "StockLayer",
    # Cycle Count
    "CycleCount", "CycleCountItem", "IRASnapshot",
    # Audit
    "InventoryAuditLog",
    # UoM
    "UnitOfMeasure", "UoMConversion",
    # Cost History
    "ProductCostHistory",
    # Business Partner
    "BusinessPartner",
]
