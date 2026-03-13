"""Hardcoded demo data for 3 industries."""

from __future__ import annotations

# ─── Shared event config (seeded once, shared across all industries) ──────────

SHARED_EVENT_CONFIG: dict = {
    "event_types": [
        {"name": "Daño en almacén", "slug": "dano-almacen", "color": "#ef4444", "icon": "alert-triangle"},
        {"name": "Robo / Pérdida", "slug": "robo-perdida", "color": "#dc2626", "icon": "shield-alert"},
        {"name": "Producto vencido", "slug": "producto-vencido", "color": "#f59e0b", "icon": "clock"},
        {"name": "Error de conteo", "slug": "error-conteo", "color": "#6366f1", "icon": "hash"},
        {"name": "Devolución de cliente", "slug": "devolucion-cliente", "color": "#0ea5e9", "icon": "undo-2"},
    ],
    "event_severities": [
        {"name": "Baja", "slug": "baja", "weight": 1, "color": "#22c55e"},
        {"name": "Media", "slug": "media", "weight": 2, "color": "#f59e0b"},
        {"name": "Alta", "slug": "alta", "weight": 3, "color": "#ef4444"},
        {"name": "Crítica", "slug": "critica", "weight": 4, "color": "#dc2626"},
    ],
    "event_statuses": [
        {"name": "Abierto", "slug": "abierto", "is_final": False, "color": "#ef4444", "sort_order": 0},
        {"name": "En investigación", "slug": "en-investigacion", "is_final": False, "color": "#f59e0b", "sort_order": 1},
        {"name": "Resuelto", "slug": "resuelto", "is_final": True, "color": "#22c55e", "sort_order": 2},
        {"name": "Cerrado", "slug": "cerrado", "is_final": True, "color": "#94a3b8", "sort_order": 3},
    ],
}


DEMO_DATA: dict[str, dict] = {
    # ─── Pet Food Industry ─────────────────────────────────────────────────────
    "pet_food": {
        "label": "Comida para Mascotas",
        "product_types": [
            {"name": "Materia Prima", "color": "#f59e0b"},
            {"name": "Producto en Proceso", "color": "#3b82f6"},
            {"name": "Producto Terminado", "color": "#10b981"},
            {"name": "Empaque", "color": "#8b5cf6"},
        ],
        "supplier_types": [
            {"name": "Proveedor de Granos", "color": "#f59e0b"},
            {"name": "Proveedor de Proteínas", "color": "#ef4444"},
            {"name": "Proveedor de Empaque", "color": "#8b5cf6"},
        ],
        "order_types": [
            {"name": "Compra Regular", "color": "#10b981"},
            {"name": "Compra Urgente", "color": "#ef4444"},
        ],
        "warehouses": [
            {"name": "Almacén Materias Primas", "code": "MATERIAS-PRIMAS", "type": "main"},
            {"name": "Planta Producción", "code": "PRODUCCION", "type": "secondary"},
            {"name": "Bodega Producto Terminado", "code": "PT-BODEGA", "type": "main"},
            {"name": "Zona de Despacho", "code": "DESPACHO", "type": "transit"},
        ],
        "suppliers": [
            {"name": "Granos del Valle", "code": "GRANOS-VALLE", "type": "Proveedor de Granos", "contact": "Carlos Mendoza", "email": "ventas@granosvalle.com", "phone": "+57 310 555 1001", "lead_time": 5},
            {"name": "Proteínas del Sur", "code": "PROTEINAS-SUR", "type": "Proveedor de Proteínas", "contact": "Ana García", "email": "pedidos@proteinassur.com", "phone": "+57 310 555 1002", "lead_time": 7},
            {"name": "Empaques Express", "code": "EMPAQUES-EXP", "type": "Proveedor de Empaque", "contact": "Luis Ramírez", "email": "info@empaquesexp.com", "phone": "+57 310 555 1003", "lead_time": 3},
        ],
        "products": [
            {"sku": "MP-HPOLLO-001", "name": "Harina de pollo", "type": "Materia Prima", "wh": "MATERIAS-PRIMAS", "stock": 500, "cost": 3.50, "sale": 0, "unit": "kg"},
            {"sku": "MP-MAIZ-001", "name": "Maíz molido", "type": "Materia Prima", "wh": "MATERIAS-PRIMAS", "stock": 800, "cost": 1.20, "sale": 0, "unit": "kg"},
            {"sku": "MP-ARROZ-001", "name": "Arroz partido", "type": "Materia Prima", "wh": "MATERIAS-PRIMAS", "stock": 600, "cost": 0.90, "sale": 0, "unit": "kg"},
            {"sku": "MP-GRASA-001", "name": "Grasa animal", "type": "Materia Prima", "wh": "MATERIAS-PRIMAS", "stock": 200, "cost": 2.80, "sale": 0, "unit": "kg"},
            {"sku": "MP-VITAM-001", "name": "Vitaminas premix", "type": "Materia Prima", "wh": "MATERIAS-PRIMAS", "stock": 50, "cost": 15.00, "sale": 0, "unit": "kg"},
            {"sku": "EM-BOLSA1K-001", "name": "Bolsas 1kg", "type": "Empaque", "wh": "MATERIAS-PRIMAS", "stock": 2000, "cost": 0.15, "sale": 0, "unit": "un"},
            {"sku": "EM-BOLSA5K-001", "name": "Bolsas 5kg", "type": "Empaque", "wh": "MATERIAS-PRIMAS", "stock": 1000, "cost": 0.35, "sale": 0, "unit": "un"},
            {"sku": "EM-CAJAX12-001", "name": "Cajas x12", "type": "Empaque", "wh": "MATERIAS-PRIMAS", "stock": 500, "cost": 0.80, "sale": 0, "unit": "un"},
            {"sku": "PP-MEZCACH-001", "name": "Mezcla base cachorro", "type": "Producto en Proceso", "wh": "PRODUCCION", "stock": 100, "cost": 4.50, "sale": 0, "unit": "kg"},
            {"sku": "PP-MEZCADU-001", "name": "Mezcla base adulto", "type": "Producto en Proceso", "wh": "PRODUCCION", "stock": 150, "cost": 3.80, "sale": 0, "unit": "kg"},
            {"sku": "PT-CROQC1K-001", "name": "Croquetas Cachorro 1kg", "type": "Producto Terminado", "wh": "PT-BODEGA", "stock": 300, "cost": 5.20, "sale": 8.90, "unit": "un"},
            {"sku": "PT-CROQC5K-001", "name": "Croquetas Cachorro 5kg", "type": "Producto Terminado", "wh": "PT-BODEGA", "stock": 120, "cost": 22.00, "sale": 38.50, "unit": "un"},
            {"sku": "PT-CROQA1K-001", "name": "Croquetas Adulto 1kg", "type": "Producto Terminado", "wh": "PT-BODEGA", "stock": 400, "cost": 4.80, "sale": 7.90, "unit": "un"},
            {"sku": "PT-CROQA5K-001", "name": "Croquetas Adulto 5kg", "type": "Producto Terminado", "wh": "PT-BODEGA", "stock": 150, "cost": 20.00, "sale": 34.90, "unit": "un"},
            {"sku": "PT-SNKDNT-001", "name": "Snacks Dentales 200g", "type": "Producto Terminado", "wh": "PT-BODEGA", "stock": 600, "cost": 2.50, "sale": 5.90, "unit": "un"},
        ],
        "batches": [
            {"sku": "MP-HPOLLO-001", "batch": "LOT-HP-2026-01", "mfg": "2026-01-15", "exp": "2026-07-15", "qty": 250},
            {"sku": "MP-HPOLLO-001", "batch": "LOT-HP-2026-02", "mfg": "2026-02-10", "exp": "2026-08-10", "qty": 250},
            {"sku": "MP-MAIZ-001", "batch": "LOT-MZ-2026-01", "mfg": "2026-01-20", "exp": "2027-01-20", "qty": 800},
            {"sku": "PT-CROQC1K-001", "batch": "LOT-CC1K-2026-01", "mfg": "2026-02-01", "exp": "2027-02-01", "qty": 300},
            {"sku": "PT-CROQA1K-001", "batch": "LOT-CA1K-2026-01", "mfg": "2026-02-05", "exp": "2027-02-05", "qty": 400},
        ],
        "recipes": [
            {
                "name": "Mezcla Cachorro 1kg",
                "output_sku": "PP-MEZCACH-001",
                "output_qty": 100,
                "components": [
                    {"sku": "MP-HPOLLO-001", "qty": 30},
                    {"sku": "MP-MAIZ-001", "qty": 25},
                    {"sku": "MP-ARROZ-001", "qty": 20},
                    {"sku": "MP-GRASA-001", "qty": 15},
                    {"sku": "MP-VITAM-001", "qty": 10},
                ],
            },
            {
                "name": "Empaque Croquetas Cachorro 1kg",
                "output_sku": "PT-CROQC1K-001",
                "output_qty": 100,
                "components": [
                    {"sku": "PP-MEZCACH-001", "qty": 100},
                    {"sku": "EM-BOLSA1K-001", "qty": 100},
                ],
            },
        ],
        "purchase_orders": [
            {
                "supplier_code": "GRANOS-VALLE",
                "wh_code": "MATERIAS-PRIMAS",
                "status": "received",
                "notes": "Pedido mensual de granos",
                "lines": [
                    {"sku": "MP-MAIZ-001", "qty": 500, "cost": 1.20},
                    {"sku": "MP-ARROZ-001", "qty": 300, "cost": 0.90},
                ],
            },
            {
                "supplier_code": "PROTEINAS-SUR",
                "wh_code": "MATERIAS-PRIMAS",
                "status": "confirmed",
                "notes": "Reposición de harina de pollo",
                "lines": [
                    {"sku": "MP-HPOLLO-001", "qty": 200, "cost": 3.50},
                    {"sku": "MP-GRASA-001", "qty": 100, "cost": 2.80},
                ],
            },
        ],
        "production_runs": [
            {"recipe_name": "Mezcla Cachorro 1kg", "wh_code": "PRODUCCION", "multiplier": 1},
        ],
        "taxonomies": [
            {
                "name": "Etapa de vida",
                "slug": "etapa-vida",
                "product_type": "Producto Terminado",
                "terms": [
                    {"name": "Cachorro", "slug": "cachorro", "color": "#f59e0b"},
                    {"name": "Adulto", "slug": "adulto", "color": "#3b82f6"},
                    {"name": "Senior", "slug": "senior", "color": "#8b5cf6"},
                ],
            },
            {
                "name": "Especie",
                "slug": "especie",
                "terms": [
                    {"name": "Perro", "slug": "perro", "color": "#f97316"},
                    {"name": "Gato", "slug": "gato", "color": "#a855f7"},
                ],
            },
        ],
        "events": [
            {
                "title": "Bolsas con defecto de sellado",
                "event_type_slug": "dano-almacen",
                "severity_slug": "media",
                "status_slug": "abierto",
                "wh_code": "MATERIAS-PRIMAS",
                "description": "Lote de bolsas 1kg con sellado defectuoso, 50 unidades afectadas",
                "impacts": [{"sku": "EM-BOLSA1K-001", "qty": -50}],
            },
            {
                "title": "Harina de pollo próxima a vencer",
                "event_type_slug": "producto-vencido",
                "severity_slug": "alta",
                "status_slug": "en-investigacion",
                "wh_code": "MATERIAS-PRIMAS",
                "description": "Lote LOT-HP-2026-01 vence en 4 meses, priorizar uso",
                "impacts": [{"sku": "MP-HPOLLO-001", "qty": 0}],
            },
        ],
    },

    # ─── Technology / PC Industry ──────────────────────────────────────────────
    "technology": {
        "label": "Tecnología / PC",
        "product_types": [
            {"name": "Componente", "color": "#6366f1"},
            {"name": "Periférico", "color": "#ec4899"},
            {"name": "Equipo Armado", "color": "#059669"},
            {"name": "Accesorio", "color": "#f97316"},
        ],
        "supplier_types": [
            {"name": "Distribuidor Mayorista", "color": "#6366f1"},
            {"name": "Importador Directo", "color": "#059669"},
        ],
        "order_types": [
            {"name": "Compra Nacional", "color": "#10b981"},
            {"name": "Importación", "color": "#6366f1"},
        ],
        "warehouses": [
            {"name": "Almacén Componentes", "code": "COMPONENTES", "type": "main"},
            {"name": "Zona de Ensamble", "code": "ENSAMBLE", "type": "secondary"},
            {"name": "Vitrina / Showroom", "code": "VITRINA", "type": "secondary"},
            {"name": "Servicio Técnico", "code": "SERVICIO-TECNICO", "type": "secondary"},
        ],
        "suppliers": [
            {"name": "TechDistributor", "code": "TECHDIST", "type": "Distribuidor Mayorista", "contact": "David Park", "email": "orders@techdist.com", "phone": "+1 555 2001", "lead_time": 10},
            {"name": "PeripheralWorld", "code": "PERIPHWORLD", "type": "Distribuidor Mayorista", "contact": "Sara Kim", "email": "sales@periphworld.com", "phone": "+1 555 2002", "lead_time": 7},
            {"name": "AccessoryPlus", "code": "ACCPLUS", "type": "Importador Directo", "contact": "Mike Chen", "email": "info@accplus.com", "phone": "+1 555 2003", "lead_time": 14},
        ],
        "products": [
            {"sku": "COMP-I513400", "name": "Procesador Intel i5-13400", "type": "Componente", "wh": "COMPONENTES", "stock": 25, "cost": 189.00, "sale": 249.00, "unit": "un"},
            {"sku": "COMP-RAMD5-16", "name": "RAM DDR5 16GB", "type": "Componente", "wh": "COMPONENTES", "stock": 40, "cost": 45.00, "sale": 69.00, "unit": "un"},
            {"sku": "COMP-SSD1TB", "name": "SSD NVMe 1TB", "type": "Componente", "wh": "COMPONENTES", "stock": 35, "cost": 55.00, "sale": 85.00, "unit": "un"},
            {"sku": "COMP-PSU650", "name": "Fuente 650W 80+ Bronze", "type": "Componente", "wh": "COMPONENTES", "stock": 20, "cost": 50.00, "sale": 75.00, "unit": "un"},
            {"sku": "COMP-MBB660", "name": "Motherboard B660", "type": "Componente", "wh": "COMPONENTES", "stock": 15, "cost": 110.00, "sale": 155.00, "unit": "un"},
            {"sku": "COMP-CASEATX", "name": "Case ATX Gamer", "type": "Componente", "wh": "COMPONENTES", "stock": 18, "cost": 45.00, "sale": 69.00, "unit": "un"},
            {"sku": "COMP-RTX4060", "name": "GPU RTX 4060", "type": "Componente", "wh": "COMPONENTES", "stock": 12, "cost": 280.00, "sale": 389.00, "unit": "un"},
            {"sku": "PERI-MON24", "name": "Monitor 24\" FHD 75Hz", "type": "Periférico", "wh": "VITRINA", "stock": 10, "cost": 120.00, "sale": 179.00, "unit": "un"},
            {"sku": "PERI-KBMECH", "name": "Teclado mecánico RGB", "type": "Periférico", "wh": "VITRINA", "stock": 30, "cost": 35.00, "sale": 59.00, "unit": "un"},
            {"sku": "PERI-MOUSE", "name": "Mouse gaming 16000 DPI", "type": "Periférico", "wh": "VITRINA", "stock": 45, "cost": 18.00, "sale": 35.00, "unit": "un"},
            {"sku": "PERI-HEADSET", "name": "Headset USB 7.1", "type": "Periférico", "wh": "VITRINA", "stock": 20, "cost": 25.00, "sale": 45.00, "unit": "un"},
            {"sku": "EQ-PCGAMER", "name": "PC Gamer Básico", "type": "Equipo Armado", "wh": "ENSAMBLE", "stock": 5, "cost": 680.00, "sale": 999.00, "unit": "un"},
            {"sku": "EQ-PCOFI", "name": "PC Oficina Estándar", "type": "Equipo Armado", "wh": "ENSAMBLE", "stock": 8, "cost": 420.00, "sale": 649.00, "unit": "un"},
            {"sku": "ACC-HDMI2M", "name": "Cable HDMI 2m", "type": "Accesorio", "wh": "VITRINA", "stock": 100, "cost": 3.50, "sale": 8.00, "unit": "un"},
            {"sku": "ACC-PASTA", "name": "Pasta térmica 4g", "type": "Accesorio", "wh": "SERVICIO-TECNICO", "stock": 50, "cost": 4.00, "sale": 9.00, "unit": "un"},
            {"sku": "ACC-KITLIMP", "name": "Kit limpieza PC", "type": "Accesorio", "wh": "VITRINA", "stock": 25, "cost": 6.00, "sale": 14.00, "unit": "un"},
        ],
        "serials": [
            {"sku": "COMP-RTX4060", "numbers": ["RTX4060-SN-0001", "RTX4060-SN-0002", "RTX4060-SN-0003", "RTX4060-SN-0004", "RTX4060-SN-0005"]},
            {"sku": "COMP-I513400", "numbers": ["I5-13400-SN-001", "I5-13400-SN-002", "I5-13400-SN-003"]},
            {"sku": "PERI-MON24", "numbers": ["MON24-SN-001", "MON24-SN-002", "MON24-SN-003", "MON24-SN-004"]},
            {"sku": "EQ-PCGAMER", "numbers": ["PCG-2026-001", "PCG-2026-002", "PCG-2026-003"]},
        ],
        "recipes": [
            {
                "name": "Ensamble PC Gamer Básico",
                "output_sku": "EQ-PCGAMER",
                "output_qty": 1,
                "components": [
                    {"sku": "COMP-I513400", "qty": 1},
                    {"sku": "COMP-RAMD5-16", "qty": 1},
                    {"sku": "COMP-SSD1TB", "qty": 1},
                    {"sku": "COMP-PSU650", "qty": 1},
                    {"sku": "COMP-MBB660", "qty": 1},
                    {"sku": "COMP-CASEATX", "qty": 1},
                    {"sku": "COMP-RTX4060", "qty": 1},
                    {"sku": "ACC-PASTA", "qty": 1},
                ],
            },
            {
                "name": "Ensamble PC Oficina",
                "output_sku": "EQ-PCOFI",
                "output_qty": 1,
                "components": [
                    {"sku": "COMP-I513400", "qty": 1},
                    {"sku": "COMP-RAMD5-16", "qty": 1},
                    {"sku": "COMP-SSD1TB", "qty": 1},
                    {"sku": "COMP-PSU650", "qty": 1},
                    {"sku": "COMP-MBB660", "qty": 1},
                    {"sku": "COMP-CASEATX", "qty": 1},
                ],
            },
        ],
        "purchase_orders": [
            {
                "supplier_code": "TECHDIST",
                "wh_code": "COMPONENTES",
                "status": "confirmed",
                "notes": "Restock trimestral de componentes",
                "lines": [
                    {"sku": "COMP-I513400", "qty": 20, "cost": 189.00},
                    {"sku": "COMP-RAMD5-16", "qty": 30, "cost": 45.00},
                    {"sku": "COMP-RTX4060", "qty": 10, "cost": 280.00},
                ],
            },
            {
                "supplier_code": "PERIPHWORLD",
                "wh_code": "VITRINA",
                "status": "draft",
                "notes": "Pedido de periféricos para temporada",
                "lines": [
                    {"sku": "PERI-MON24", "qty": 15, "cost": 120.00},
                    {"sku": "PERI-KBMECH", "qty": 20, "cost": 35.00},
                    {"sku": "PERI-MOUSE", "qty": 30, "cost": 18.00},
                ],
            },
        ],
        "production_runs": [
            {"recipe_name": "Ensamble PC Gamer Básico", "wh_code": "ENSAMBLE", "multiplier": 2},
            {"recipe_name": "Ensamble PC Oficina", "wh_code": "ENSAMBLE", "multiplier": 3},
        ],
        "taxonomies": [
            {
                "name": "Marca",
                "slug": "marca",
                "product_type": "Componente",
                "terms": [
                    {"name": "Intel", "slug": "intel", "color": "#0071c5"},
                    {"name": "AMD", "slug": "amd", "color": "#ed1c24"},
                    {"name": "NVIDIA", "slug": "nvidia", "color": "#76b900"},
                    {"name": "Corsair", "slug": "corsair", "color": "#f1c40f"},
                ],
            },
            {
                "name": "Factor de forma",
                "slug": "factor-forma",
                "terms": [
                    {"name": "ATX", "slug": "atx", "color": "#6366f1"},
                    {"name": "Micro-ATX", "slug": "micro-atx", "color": "#8b5cf6"},
                    {"name": "Mini-ITX", "slug": "mini-itx", "color": "#a855f7"},
                ],
            },
        ],
        "events": [
            {
                "title": "GPU DOA en envío de TechDistributor",
                "event_type_slug": "dano-almacen",
                "severity_slug": "alta",
                "status_slug": "abierto",
                "wh_code": "COMPONENTES",
                "description": "2 RTX 4060 llegaron con daño en el PCB, notificar proveedor",
                "impacts": [{"sku": "COMP-RTX4060", "qty": -2}],
            },
            {
                "title": "Discrepancia en conteo de RAM",
                "event_type_slug": "error-conteo",
                "severity_slug": "baja",
                "status_slug": "resuelto",
                "wh_code": "COMPONENTES",
                "description": "Se encontraron 2 unidades extra de RAM DDR5 en conteo cíclico",
                "impacts": [{"sku": "COMP-RAMD5-16", "qty": 2}],
            },
        ],
    },

    # ─── Cleaning Products Industry ────────────────────────────────────────────
    "cleaning": {
        "label": "Productos de Aseo",
        "product_types": [
            {"name": "Limpieza Hogar", "color": "#0ea5e9"},
            {"name": "Cuidado Personal", "color": "#a855f7"},
            {"name": "Industrial", "color": "#64748b"},
            {"name": "Desechable", "color": "#22c55e"},
        ],
        "supplier_types": [
            {"name": "Fabricante", "color": "#64748b"},
            {"name": "Distribuidor Regional", "color": "#0ea5e9"},
        ],
        "order_types": [
            {"name": "Pedido Semanal", "color": "#10b981"},
            {"name": "Pedido Especial", "color": "#f59e0b"},
        ],
        "warehouses": [
            {"name": "Almacén Central", "code": "ALMACEN-CENTRAL", "type": "main"},
            {"name": "Tienda Norte", "code": "TIENDA-NORTE", "type": "secondary"},
            {"name": "Tienda Sur", "code": "TIENDA-SUR", "type": "secondary"},
        ],
        "suppliers": [
            {"name": "QuímicosNacionales", "code": "QUIMICOS-NAC", "type": "Fabricante", "contact": "Roberto Díaz", "email": "ventas@quimicosnac.com", "phone": "+57 310 555 3001", "lead_time": 4},
            {"name": "HigieneTotal", "code": "HIGIENE-TOT", "type": "Distribuidor Regional", "contact": "María Torres", "email": "pedidos@higienetotal.com", "phone": "+57 310 555 3002", "lead_time": 3},
            {"name": "DesechablesCo", "code": "DESECHABLES-CO", "type": "Distribuidor Regional", "contact": "Jorge Ruiz", "email": "info@desechablesco.com", "phone": "+57 310 555 3003", "lead_time": 5},
        ],
        "products": [
            {"sku": "LH-DETLIQ1L", "name": "Detergente líquido 1L", "type": "Limpieza Hogar", "wh": "ALMACEN-CENTRAL", "stock": 200, "cost": 1.80, "sale": 3.50, "unit": "un"},
            {"sku": "LH-SUAV1L", "name": "Suavizante 1L", "type": "Limpieza Hogar", "wh": "ALMACEN-CENTRAL", "stock": 150, "cost": 2.00, "sale": 3.90, "unit": "un"},
            {"sku": "LH-CLORO1L", "name": "Cloro 1L", "type": "Limpieza Hogar", "wh": "ALMACEN-CENTRAL", "stock": 300, "cost": 0.80, "sale": 1.90, "unit": "un"},
            {"sku": "LH-LIMPISO1L", "name": "Limpia pisos 1L", "type": "Limpieza Hogar", "wh": "ALMACEN-CENTRAL", "stock": 180, "cost": 1.50, "sale": 3.20, "unit": "un"},
            {"sku": "LH-DESENG500", "name": "Desengrasante 500ml", "type": "Limpieza Hogar", "wh": "ALMACEN-CENTRAL", "stock": 120, "cost": 1.20, "sale": 2.80, "unit": "un"},
            {"sku": "LH-JABBAR3", "name": "Jabón en barra x3", "type": "Limpieza Hogar", "wh": "ALMACEN-CENTRAL", "stock": 250, "cost": 0.90, "sale": 2.20, "unit": "un"},
            {"sku": "CP-JABLIQ500", "name": "Jabón líquido manos 500ml", "type": "Cuidado Personal", "wh": "TIENDA-NORTE", "stock": 100, "cost": 1.50, "sale": 3.50, "unit": "un"},
            {"sku": "CP-GELANTI250", "name": "Gel antibacterial 250ml", "type": "Cuidado Personal", "wh": "TIENDA-NORTE", "stock": 80, "cost": 1.80, "sale": 4.20, "unit": "un"},
            {"sku": "CP-SHAMP400", "name": "Shampoo 400ml", "type": "Cuidado Personal", "wh": "TIENDA-SUR", "stock": 90, "cost": 2.20, "sale": 5.50, "unit": "un"},
            {"sku": "IND-DESENG5L", "name": "Desengrasante industrial 5L", "type": "Industrial", "wh": "ALMACEN-CENTRAL", "stock": 40, "cost": 8.00, "sale": 15.00, "unit": "un"},
            {"sku": "IND-CLORO5L", "name": "Cloro concentrado 5L", "type": "Industrial", "wh": "ALMACEN-CENTRAL", "stock": 50, "cost": 4.50, "sale": 9.00, "unit": "un"},
            {"sku": "DES-BOLBAS10", "name": "Bolsas basura 10un", "type": "Desechable", "wh": "TIENDA-NORTE", "stock": 300, "cost": 0.60, "sale": 1.50, "unit": "un"},
            {"sku": "DES-GUANLAT100", "name": "Guantes látex x100", "type": "Desechable", "wh": "ALMACEN-CENTRAL", "stock": 60, "cost": 4.00, "sale": 8.50, "unit": "un"},
            {"sku": "DES-TOALPAP3", "name": "Toallas papel x3", "type": "Desechable", "wh": "TIENDA-SUR", "stock": 150, "cost": 1.80, "sale": 4.00, "unit": "un"},
        ],
        "batches": [
            {"sku": "LH-CLORO1L", "batch": "LOT-CL-2026-01", "mfg": "2026-01-10", "exp": "2027-01-10", "qty": 300},
            {"sku": "CP-GELANTI250", "batch": "LOT-GA-2026-01", "mfg": "2026-02-01", "exp": "2027-08-01", "qty": 80},
            {"sku": "IND-CLORO5L", "batch": "LOT-CL5-2026-01", "mfg": "2026-01-20", "exp": "2027-01-20", "qty": 50},
        ],
        "purchase_orders": [
            {
                "supplier_code": "QUIMICOS-NAC",
                "wh_code": "ALMACEN-CENTRAL",
                "status": "received",
                "notes": "Pedido semanal productos hogar",
                "lines": [
                    {"sku": "LH-DETLIQ1L", "qty": 100, "cost": 1.80},
                    {"sku": "LH-CLORO1L", "qty": 200, "cost": 0.80},
                    {"sku": "IND-DESENG5L", "qty": 20, "cost": 8.00},
                ],
            },
            {
                "supplier_code": "DESECHABLES-CO",
                "wh_code": "ALMACEN-CENTRAL",
                "status": "draft",
                "notes": "Reposición de desechables",
                "lines": [
                    {"sku": "DES-BOLBAS10", "qty": 200, "cost": 0.60},
                    {"sku": "DES-GUANLAT100", "qty": 30, "cost": 4.00},
                    {"sku": "DES-TOALPAP3", "qty": 100, "cost": 1.80},
                ],
            },
        ],
        "taxonomies": [
            {
                "name": "Fragancia",
                "slug": "fragancia",
                "product_type": "Limpieza Hogar",
                "terms": [
                    {"name": "Lavanda", "slug": "lavanda", "color": "#a855f7"},
                    {"name": "Limón", "slug": "limon", "color": "#eab308"},
                    {"name": "Pino", "slug": "pino", "color": "#22c55e"},
                    {"name": "Sin fragancia", "slug": "sin-fragancia", "color": "#94a3b8"},
                ],
            },
        ],
        "events": [
            {
                "title": "Derrame de cloro en almacén",
                "event_type_slug": "dano-almacen",
                "severity_slug": "alta",
                "status_slug": "en-investigacion",
                "wh_code": "ALMACEN-CENTRAL",
                "description": "Derrame de 10 unidades de cloro 1L por estiba mal apilada",
                "impacts": [{"sku": "LH-CLORO1L", "qty": -10}],
            },
        ],
    },
}
