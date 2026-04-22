"""Debug: reproduce los fallos del seed y muestra el body de error real."""
from __future__ import annotations

import secrets
import sys

import httpx

GATEWAY = "http://62.238.5.1:9000"
EMAIL = "miguelenruiz1@gmail.com"
PASSWORD = "TraceAdmin2026!"


def show(label: str, r: httpx.Response):
    print(f"\n--- {label} ---")
    print(f"HTTP {r.status_code}")
    try:
        print(r.json())
    except Exception:
        print(r.text[:500])


def main() -> int:
    c = httpx.Client(timeout=45.0, follow_redirects=True)
    r = c.post(f"{GATEWAY}/api/v1/auth/login",
               json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    d = r.json()
    me = c.get(f"{GATEWAY}/api/v1/auth/me",
               headers={"Authorization": f"Bearer {d['access_token']}"}).json()
    tok, uid, tid = d["access_token"], me["id"], me["tenant_id"]
    h = {"Authorization": f"Bearer {tok}", "X-Tenant-Id": tid,
         "Content-Type": "application/json"}
    hdr_user = {**h, "X-User-Id": uid}
    print(f"login OK tenant={tid}")

    # 1) Categoria fallo
    r = c.post(f"{GATEWAY}/api/v1/categories", headers=h,
               json={"name": "Cafe Premium", "slug": f"cat-{secrets.token_hex(2)}"})
    show("POST /categories", r)

    # 2) Mint NFT fallo
    # generamos wallet primero
    r = c.post(f"{GATEWAY}/api/v1/registry/wallets/generate", headers=hdr_user,
               json={"name": "Wallet debug"})
    show("POST /registry/wallets/generate", r)
    wallet_pub = r.json().get("wallet_pubkey") if r.status_code in (200, 201) else None

    if wallet_pub:
        r = c.post(f"{GATEWAY}/api/v1/assets/mint", headers=hdr_user, json={
            "product_type": "coffee",
            "metadata": {"origin": "Huila", "variety": "Caturra",
                         "lot_number": "LOT-DBG", "weight_kg": 500},
            "initial_custodian_wallet": wallet_pub,
        })
        show("POST /assets/mint", r)

    # 3) Compliance plot punto
    r = c.post(f"{GATEWAY}/api/v1/compliance/plots/", headers=h, json={
        "plot_code": f"PLOT-DBG-{secrets.token_hex(2).upper()}",
        "commodity_type": "coffee",
        "plot_area_ha": 2.35,
        "country_code": "CO",
        "geolocation_type": "point",
        "lat": 2.350123, "lng": -75.892456,
        "producer_name": "Juan Perez",
        "producer_identifier_type": "CC",
        "producer_identifier": "12345678",
    })
    show("POST /compliance/plots (point)", r)

    # 4) Receta
    # Crear 2 productos para la receta
    r = c.post(f"{GATEWAY}/api/v1/products", headers=h,
               json={"sku": f"MP-DBG-{secrets.token_hex(2).upper()}",
                     "name": "MP debug", "unit_of_measure": "unit"})
    mp_id = r.json().get("id") if r.status_code in (200, 201) else None
    r = c.post(f"{GATEWAY}/api/v1/products", headers=h,
               json={"sku": f"PT-DBG-{secrets.token_hex(2).upper()}",
                     "name": "PT debug", "unit_of_measure": "unit"})
    pt_id = r.json().get("id") if r.status_code in (200, 201) else None

    if mp_id and pt_id:
        r = c.post(f"{GATEWAY}/api/v1/recipes", headers=h, json={
            "name": "Receta debug",
            "output_product_id": pt_id, "output_quantity": 1,
            "ingredients": [{"product_id": mp_id, "quantity": 1}],
        })
        show("POST /recipes", r)

    return 0


if __name__ == "__main__":
    sys.exit(main())
