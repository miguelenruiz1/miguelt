"""
CASO DE USO: Exportación de Café Orgánico -- Finca La Esperanza (Colombia) -> Miami (EEUU)

Flujo completo:
1. Proveedor + Producto con track_on_chain
2. OC internacional (PO) con incoterm FOB, USD
3. Recepción en bodega con lote trazable -> anchor en Solana
4. Documentos de comercio exterior (cert origen, fitosanitario, DEX)
5. Guía de remisión terrestre (Bogotá -> Cartagena)
6. BL marítimo (Cartagena -> Miami)
7. Pedido de venta (SO) internacional CIF
8. Verificación pública del lote
"""
import pytest
from unittest.mock import AsyncMock, patch


# -- Helpers para crear maestros -----------------------------------------------

async def _create_warehouse(c):
    r = await c.post("/api/v1/warehouses", json={
        "name": "Bodega Bogotá ZF", "code": "BOG-ZF", "warehouse_type": "main",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_category(c):
    r = await c.post("/api/v1/categories", json={"name": "Café", "slug": "cafe"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_supplier(c):
    r = await c.post("/api/v1/suppliers", json={
        "name": "Finca La Esperanza", "code": "FLE-001",
        "contact_name": "Carlos Rodríguez", "email": "carlos@finca.co",
        "phone": "+57 310 555 1234",
        "address": {"city": "Huila", "country": "CO"},
        "lead_time_days": 7, "payment_terms_days": 30,
    })
    assert r.status_code == 201, r.text
    return r.json()


async def _create_product(c, cat_id):
    r = await c.post("/api/v1/products", json={
        "sku": "CAFE-ORG-500", "name": "Café Orgánico Huila 500g",
        "description": "Café de origen, 1800 msnm, certificado orgánico",
        "unit_of_measure": "kg", "track_batches": True, "track_on_chain": True,
        "category_id": cat_id, "weight_per_unit": "0.5",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _create_customer(c):
    r = await c.post("/api/v1/customers", json={
        "name": "Miami Specialty Coffee LLC", "code": "MSC-001",
        "contact_name": "John Smith", "email": "john@miamicoffee.com",
        "address": {"city": "Miami", "state": "FL", "country": "US"},
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


# -- TEST PRINCIPAL ------------------------------------------------------------

@pytest.mark.anyio
@patch("app.clients.trace_client.anchor_event_background", new_callable=AsyncMock)
@patch("app.clients.trace_client.anchor_event", new_callable=AsyncMock)
async def test_exportacion_cafe_colombia_miami(mock_anchor, mock_bg, client):
    c = client
    mock_anchor.return_value = {"id": "a1", "anchor_status": "pending", "payload_hash": "abc"}
    mock_bg.return_value = None

    print("\n" + "=" * 70)
    print("  CASO DE USO: Café Orgánico Colombia -> Miami")
    print("=" * 70)

    # -- 1. Maestros ---------------------------------------------------
    print("\n[BOX] 1. MAESTROS")
    wh_id = await _create_warehouse(c)
    cat_id = await _create_category(c)
    sup = await _create_supplier(c)
    prod_id = await _create_product(c, cat_id)
    cust_id = await _create_customer(c)
    print(f"   [OK] Bodega: Bogotá ZF")
    print(f"   [OK] Proveedor: Finca La Esperanza")
    print(f"   [OK] Producto: Café Orgánico Huila (track_on_chain=true)")
    print(f"   [OK] Cliente: Miami Specialty Coffee LLC")

    # -- 2. OC Internacional -------------------------------------------
    print("\n[DOC] 2. ORDEN DE COMPRA INTERNACIONAL")
    r = await c.post("/api/v1/purchase-orders", json={
        "supplier_id": sup["id"], "warehouse_id": wh_id,
        "currency": "USD", "exchange_rate": "4150.50",
        "incoterm": "FOB",
        "origin_country": "CO", "destination_country": "US",
        "port_of_loading": "Cartagena", "port_of_discharge": "Miami",
        "is_international": True,
        "lines": [{"product_id": prod_id, "qty_ordered": "1000", "unit_cost": "8.50"}],
    })
    assert r.status_code == 201, r.text
    po = r.json()
    po_id = po["id"]
    print(f"   [OK] {po['po_number']} -- 1000 kg × $8.50 USD = $8,500 FOB")
    print(f"   [OK] Incoterm: FOB Cartagena -> Miami | TRM: $4,150.50")

    # Enviar + Confirmar
    r = await c.post(f"/api/v1/purchase-orders/{po_id}/send")
    assert r.status_code == 200
    po = r.json()
    chain_len = len(po.get("anchor_chain") or [])
    print(f"   [OK] Enviada -> chain: {chain_len} hash(es)")

    r = await c.post(f"/api/v1/purchase-orders/{po_id}/confirm")
    assert r.status_code == 200
    po = r.json()
    chain_len = len(po.get("anchor_chain") or [])
    print(f"   [OK] Confirmada -> chain: {chain_len} hash(es)")

    # -- 3. Lote + Recepción -------------------------------------------
    print("\n[FAC] 3. LOTE TRAZABLE + RECEPCIÓN")
    r = await c.post("/api/v1/batches", json={
        "entity_id": prod_id,
        "batch_number": "LOT-CAFE-2026-Q1",
        "manufacture_date": "2026-01-15",
        "expiration_date": "2027-01-15",
        "quantity": "1000",
        "metadata": {
            "origin": "Huila, Colombia", "altitude": "1800 msnm",
            "variety": "Caturra", "process": "Lavado",
            "certification": ["Orgánico", "Rainforest Alliance"],
            "cupping_score": 86,
        },
    })
    assert r.status_code == 201, r.text
    batch = r.json()
    print(f"   [OK] Lote: {batch['batch_number']} -- Huila 1800msnm, cupping 86pts")

    # Recibir
    line_id = po["lines"][0]["id"]
    r = await c.post(f"/api/v1/purchase-orders/{po_id}/receive", json={
        "lines": [{"line_id": line_id, "qty_received": "1000"}],
    })
    assert r.status_code == 200, r.text
    po = r.json()
    print(f"   [OK] 1000 kg recibidos -- OC estado: {po['status']}")
    print(f"   [OK] anchor_hash: {(po.get('anchor_hash') or 'N/A')[:20]}...")

    # -- 4. Documentos de Comercio Exterior ----------------------------
    print("\n[PAP] 4. DOCUMENTOS DE COMERCIO EXTERIOR")

    docs = [
        ("cert_origen", "CO-2026-EXP-00142", "Certificado de Origen TLC CO-US", "Cámara de Comercio de Bogotá", "0901.21.10", "8500"),
        ("fitosanitario", "ICA-FITO-2026-08834", "Certificado Fitosanitario", "ICA", None, None),
        ("dex", "DEX-2026-CO-0039281", "Declaración de Exportación DIAN", "DIAN", "0901.21.10", "8500"),
    ]
    trade_doc_ids = []
    for dtype, dnum, title, auth, hs, fob in docs:
        body = {
            "document_type": dtype, "document_number": dnum,
            "purchase_order_id": po_id, "title": title,
            "issuing_authority": auth, "issuing_country": "CO",
        }
        if hs:
            body["hs_code"] = hs
        if fob:
            body["fob_value"] = fob
            body["currency"] = "USD"
        r = await c.post("/api/v1/trade-documents", json=body)
        assert r.status_code == 201, r.text
        td = r.json()
        trade_doc_ids.append(td["id"])
        print(f"   [OK] [{dtype.upper()}] {dnum} -- {auth}")

    # Aprobar todos
    for tid in trade_doc_ids:
        r = await c.post(f"/api/v1/trade-documents/{tid}/approve")
        assert r.status_code == 200
    print(f"   [OK] {len(trade_doc_ids)} documentos APROBADOS (anclados en blockchain)")

    # -- 5. Guía de Remisión Terrestre ---------------------------------
    print("\n[TRK] 5. GUÍA DE REMISIÓN (Bogotá -> Cartagena)")
    r = await c.post("/api/v1/shipments", json={
        "document_type": "remision", "document_number": "REM-2026-00891",
        "purchase_order_id": po_id,
        "carrier_name": "Transportes del Café SAS",
        "vehicle_plate": "ABC-123", "driver_name": "Miguel Torres",
        "driver_id_number": "79.543.210",
        "origin_city": "Bogotá", "destination_city": "Cartagena",
        "origin_country": "CO", "destination_country": "CO",
        "total_packages": 50, "total_weight_kg": "1050",
        "cargo_description": "50 sacos café orgánico × 20kg",
        "declared_value": "8500", "declared_currency": "USD",
    })
    assert r.status_code == 201, r.text
    rem = r.json()
    print(f"   [OK] {rem['document_number']} -- Placa: ABC-123, Conductor: Miguel Torres")

    r = await c.post(f"/api/v1/shipments/{rem['id']}/status", json={"status": "in_transit"})
    assert r.status_code == 200
    print(f"   [OK] EN TRÁNSITO")

    r = await c.post(f"/api/v1/shipments/{rem['id']}/status", json={"status": "delivered"})
    assert r.status_code == 200
    print(f"   [OK] ENTREGADO en Puerto de Cartagena")

    # -- 6. BL Marítimo ------------------------------------------------
    print("\n[SHP] 6. BILL OF LADING (Cartagena -> Miami)")
    r = await c.post("/api/v1/shipments", json={
        "document_type": "bl", "document_number": "MAEU-CTG-MIA-04521",
        "purchase_order_id": po_id,
        "carrier_name": "Maersk Line", "carrier_code": "MAEU",
        "vessel_name": "Maersk Cartagena", "voyage_number": "VY-2026-0312",
        "container_number": "MAEU-7234521", "container_type": "20ft",
        "seal_number": "SEAL-CO-98231",
        "origin_city": "Cartagena", "destination_city": "Miami",
        "origin_country": "CO", "destination_country": "US",
        "total_packages": 50, "total_weight_kg": "1050",
        "cargo_description": "50 bags green coffee organic -- HS 0901.21.10",
        "declared_value": "8500", "declared_currency": "USD",
        "tracking_number": "MAEU-7234521",
    })
    assert r.status_code == 201, r.text
    bl = r.json()
    print(f"   [OK] {bl['document_number']} -- Maersk Cartagena")
    print(f"   [OK] Contenedor: MAEU-7234521 (20ft) -- Sello: SEAL-CO-98231")

    # -- 7. SO Internacional -------------------------------------------
    print("\n[USD] 7. PEDIDO DE VENTA CIF Miami")
    r = await c.post("/api/v1/sales-orders", json={
        "customer_id": cust_id, "warehouse_id": wh_id,
        "currency": "USD", "incoterm": "CIF",
        "origin_country": "CO", "destination_country": "US",
        "is_international": True, "carrier_name": "Maersk Line",
        "tracking_number": "MAEU-7234521",
        "shipping_address": {"city": "Miami", "state": "FL", "country": "US"},
        "lines": [{"product_id": prod_id, "qty_ordered": "1000", "unit_price": "12.50"}],
    })
    assert r.status_code == 201, r.text
    so = r.json()
    print(f"   [OK] {so['order_number']} -- 1000 kg × $12.50 = $12,500 CIF Miami")

    # -- 8. Verificación Pública ---------------------------------------
    print("\n[QR] 8. VERIFICACIÓN PÚBLICA DEL LOTE (QR)")
    r = await c.get("/api/v1/public/batch/LOT-CAFE-2026-Q1/verify?tenant_id=test-tenant")
    assert r.status_code == 200, r.text
    v = r.json()
    print(f"   [OK] Producto: {v['product_name']}")
    print(f"   [OK] SKU: {v['product_sku']}")
    print(f"   [OK] Lote: {v['batch_number']}")
    print(f"   [OK] Vencimiento: {v['expiration_date']} ({v['expiration_status']})")
    print(f"   [OK] Proveedor: {v.get('origin_supplier') or 'N/A'}")
    print(f"   [OK] Eventos blockchain: {v['total_events_anchored']}")

    # -- 9. Resumen Documental -----------------------------------------
    print("\n[DIR] 9. RESUMEN DOCUMENTAL")
    r = await c.get(f"/api/v1/shipments?po_id={po_id}")
    assert r.status_code == 200
    for s in r.json():
        print(f"   [VAN] [{s['document_type'].upper():10s}] {s['document_number']:30s} {s['status']:12s} anchor:{s.get('anchor_status','none')}")

    r = await c.get(f"/api/v1/trade-documents?po_id={po_id}")
    assert r.status_code == 200
    for t in r.json():
        print(f"   [SCR] [{t['document_type'].upper():15s}] {(t.get('document_number') or 'N/A'):30s} {t['status']:12s} anchor:{t.get('anchor_status','none')}")

    # -- Resumen Final -------------------------------------------------
    print(f"""
{'='*70}
  CADENA COMPLETA DE TRAZABILIDAD
{'='*70}

  [PLT] Origen:  Finca La Esperanza, Huila 1800msnm
  [BOX] Lote:    LOT-CAFE-2026-Q1 (cupping 86, Caturra lavado)
  [FAC] Bodega:  Bogotá Zona Franca

  Cadena documentaria anclada en Solana:
  +------------------------------------------------------+
  | OC {po['po_number']:15s} FOB $8,500 USD (TRM 4150.50)|
  | |- Cert. Origen    CO-2026-EXP-00142   [OK] blockchain |
  | |- Fitosanitario   ICA-FITO-2026-08834 [OK] blockchain |
  | |- DEX DIAN        DEX-2026-CO-0039281 [OK] blockchain |
  | |- Remisión        REM-2026-00891      [OK] blockchain |
  | |- BL Marítimo     MAEU-CTG-MIA-04521  [OK] blockchain |
  |                                                      |
  | SO {so['order_number']:15s} CIF $12,500 USD            |
  | [SHP] Maersk Cartagena -> Miami (MAEU-7234521)          |
  |------------------------------------------------------+

  Verificación: GET /api/v1/public/batch/LOT-CAFE-2026-Q1/verify
  -> Consumidor escanea QR -> ve origen, certificados y blockchain

{'='*70}
""")
    print("[PASS] Caso de uso completado exitosamente\n")
