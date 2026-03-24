"""Unified business_partners table — merges customers + suppliers.

Revision ID: 053
Revises: 052
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create unified table
    op.create_table(
        "business_partners",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("is_supplier", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_customer", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("supplier_type_id", sa.String(36), sa.ForeignKey("supplier_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_type_id", sa.String(36), sa.ForeignKey("customer_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tax_id", sa.String(50), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", sa.JSON, nullable=True),
        sa.Column("shipping_address", sa.JSON, nullable=True),
        sa.Column("credit_limit", sa.Integer, nullable=False, server_default="0"),
        sa.Column("discount_percent", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lead_time_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("payment_terms_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("custom_attributes", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_partner_tenant_code"),
    )
    op.create_index("ix_business_partners_tenant_id", "business_partners", ["tenant_id"])
    op.create_index("ix_business_partners_is_supplier", "business_partners", ["tenant_id", "is_supplier"])
    op.create_index("ix_business_partners_is_customer", "business_partners", ["tenant_id", "is_customer"])

    # 2. Migrate suppliers → business_partners
    op.execute("""
        INSERT INTO business_partners (
            id, tenant_id, name, code, is_supplier, is_customer,
            supplier_type_id, contact_name, email, phone, address,
            lead_time_days, payment_terms_days, is_active, notes,
            custom_attributes, created_by, updated_by, created_at, updated_at
        )
        SELECT
            id, tenant_id, name, code, true, false,
            supplier_type_id, contact_name, email, phone, address,
            lead_time_days, payment_terms_days, is_active, notes,
            custom_attributes, created_by, updated_by, created_at, updated_at
        FROM suppliers
    """)

    # 3. Migrate customers → business_partners (merge if same code+tenant exists)
    # First: customers whose code does NOT already exist in business_partners
    op.execute("""
        INSERT INTO business_partners (
            id, tenant_id, name, code, is_supplier, is_customer,
            customer_type_id, tax_id, contact_name, email, phone,
            address, shipping_address, credit_limit, discount_percent,
            payment_terms_days, is_active, notes, custom_attributes,
            created_by, updated_by, created_at, updated_at
        )
        SELECT
            c.id, c.tenant_id, c.name, c.code, false, true,
            c.customer_type_id, c.tax_id, c.contact_name, c.email, c.phone,
            c.address, c.shipping_address, c.credit_limit, c.discount_percent,
            c.payment_terms_days, c.is_active, c.notes, c.custom_attributes,
            c.created_by, c.updated_by, c.created_at, c.updated_at
        FROM customers c
        WHERE NOT EXISTS (
            SELECT 1 FROM business_partners bp
            WHERE bp.tenant_id = c.tenant_id AND bp.code = c.code
        )
    """)

    # Second: customers whose code ALREADY exists (same person is both) — update existing row
    op.execute("""
        UPDATE business_partners bp
        SET is_customer = true,
            customer_type_id = c.customer_type_id,
            tax_id = COALESCE(bp.tax_id, c.tax_id),
            shipping_address = c.shipping_address,
            credit_limit = c.credit_limit,
            discount_percent = c.discount_percent
        FROM customers c
        WHERE bp.tenant_id = c.tenant_id
          AND bp.code = c.code
          AND bp.is_customer = false
    """)

    # 4. Add partner_id FK columns to referencing tables
    op.add_column("purchase_orders", sa.Column("partner_id", sa.String(36), sa.ForeignKey("business_partners.id", ondelete="RESTRICT"), nullable=True))
    op.execute("UPDATE purchase_orders SET partner_id = supplier_id")

    op.add_column("sales_orders", sa.Column("partner_id", sa.String(36), sa.ForeignKey("business_partners.id", ondelete="RESTRICT"), nullable=True))
    # For sales_orders, customer_id maps to the business_partner that was created from the customer
    # If the customer code matched a supplier, the BP id is the supplier's id; otherwise it's the customer's id
    op.execute("""
        UPDATE sales_orders so
        SET partner_id = bp.id
        FROM business_partners bp
        JOIN customers c ON c.tenant_id = bp.tenant_id AND c.code = bp.code
        WHERE so.customer_id = c.id AND bp.is_customer = true
    """)

    op.add_column("customer_prices", sa.Column("partner_id", sa.String(36), sa.ForeignKey("business_partners.id", ondelete="CASCADE"), nullable=True))
    op.execute("""
        UPDATE customer_prices cp
        SET partner_id = bp.id
        FROM business_partners bp
        JOIN customers c ON c.tenant_id = bp.tenant_id AND c.code = bp.code
        WHERE cp.customer_id = c.id AND bp.is_customer = true
    """)

    op.add_column("product_cost_history", sa.Column("partner_id", sa.String(36), sa.ForeignKey("business_partners.id", ondelete="RESTRICT"), nullable=True))
    op.execute("UPDATE product_cost_history SET partner_id = supplier_id")

    # 5. Update Product.preferred_supplier_id → preferred_partner_id
    op.add_column("entities", sa.Column("preferred_partner_id", sa.String(36), sa.ForeignKey("business_partners.id", ondelete="SET NULL"), nullable=True))
    op.execute("UPDATE entities SET preferred_partner_id = preferred_supplier_id")

    # 6. Create indexes on new FK columns
    op.create_index("ix_po_partner_id", "purchase_orders", ["partner_id"])
    op.create_index("ix_so_partner_id", "sales_orders", ["partner_id"])


def downgrade() -> None:
    op.drop_index("ix_so_partner_id", table_name="sales_orders")
    op.drop_index("ix_po_partner_id", table_name="purchase_orders")

    op.drop_column("entities", "preferred_partner_id")
    op.drop_column("product_cost_history", "partner_id")
    op.drop_column("customer_prices", "partner_id")
    op.drop_column("sales_orders", "partner_id")
    op.drop_column("purchase_orders", "partner_id")

    op.drop_index("ix_business_partners_is_customer", table_name="business_partners")
    op.drop_index("ix_business_partners_is_supplier", table_name="business_partners")
    op.drop_index("ix_business_partners_tenant_id", table_name="business_partners")
    op.drop_table("business_partners")
