"""WM module validation: smoke-test all endpoints + reproduce confirm_line P0.

Run: python qa/wm_validation.py
"""
from __future__ import annotations
import secrets as _s
import subprocess
import sys
import httpx

GATEWAY = "http://localhost:9000"
USER_API = "http://localhost:9001"


def flush():
    for n in ("2", "3", "4"):
        subprocess.run(["docker", "exec", "trace-redis", "redis-cli", "-n", n, "FLUSHDB"],
                       capture_output=True)


def main() -> int:
    flush()
    suf = _s.token_hex(3)
    c = httpx.Client(timeout=30.0, follow_redirects=False)

    r = c.post(f"{USER_API}/api/v1/auth/register", json={
        "email": f"wm{suf}@t.com", "username": f"wm{suf}", "full_name": "wm",
        "password": "TracePwd2026!", "company": f"WMco{suf}",
    })
    r.raise_for_status()
    uid, tid = r.json()["id"], r.json()["tenant_id"]
    subprocess.run(["docker", "exec", "user-postgres", "psql", "-U", "user_svc", "-d", "userdb",
                    "-c", f"UPDATE users SET is_superuser=true WHERE email='wm{suf}@t.com';"],
                   capture_output=True)
    flush()
    tok = c.post(f"{USER_API}/api/v1/auth/login",
                 json={"email": f"wm{suf}@t.com", "password": "TracePwd2026!"}).json()["access_token"]
    c.post(f"{GATEWAY}/api/v1/modules/{tid}/inventory/activate",
           headers={"Authorization": f"Bearer {tok}", "X-Tenant-Id": tid})
    h = {"Authorization": f"Bearer {tok}", "X-Tenant-Id": tid, "X-User-Id": uid}

    def g(path):
        return c.get(f"{GATEWAY}{path}", headers=h)

    def p(path, body=None):
        return c.post(f"{GATEWAY}{path}", headers=h, json=body or {})

    # Need a warehouse id. Default tenant auto-seeds MAIN warehouse.
    whs = g("/api/v1/warehouses").json()
    wh_id = (whs[0]["id"] if isinstance(whs, list) and whs else None)
    if not wh_id:
        wh_id = p("/api/v1/warehouses", {"name": "WM-WH", "code": "WMWH",
                                          "warehouse_type": "main"}).json()["id"]
    print(f"warehouse={wh_id}")

    # ── 1. SMOKE TEST: all WM GET endpoints + seeds ───────────────────────────
    print("\n=== SMOKE TEST WM ENDPOINTS ===")
    fails = []
    smoke = [
        ("GET", "/api/v1/wm/storage-types"),
        ("GET", "/api/v1/wm/storage-sections"),
        ("GET", "/api/v1/wm/package-types"),
        ("GET", "/api/v1/wm/operation-types"),
        ("POST", "/api/v1/wm/operation-types/seed"),
        ("GET", "/api/v1/wm/putaway-rules"),
        ("GET", "/api/v1/wm/routes?warehouse_id=" + wh_id),
        ("GET", "/api/v1/wm/movement-orders"),
        ("GET", "/api/v1/wm/movement-orders?warehouse_id=" + wh_id),
        ("GET", f"/api/v1/wm/warehouses/{wh_id}/config"),
        ("GET", "/api/v1/wm/stock-status?warehouse_id=" + wh_id),
        ("GET", "/api/v1/wm/eri?warehouse_id=" + wh_id),
        ("GET", "/api/v1/wm/bins/empty-report?warehouse_id=" + wh_id),
    ]
    for method, path in smoke:
        try:
            r = g(path) if method == "GET" else p(path)
            tag = "OK " if r.status_code < 400 else ("AUTH" if r.status_code in (401, 403) else "FAIL")
            if r.status_code >= 500:
                tag = "FAIL-5xx"
                fails.append((method, path, r.status_code, r.text[:200]))
            print(f"  {tag:9} {r.status_code} {method} {path}")
        except Exception as e:
            print(f"  ERROR     {method} {path} -> {e}")
            fails.append((method, path, "EXC", str(e)))

    # ── 2. P0 REPRO: confirm_line relocates arbitrary/whole quant ─────────────
    print("\n=== P0 REPRO: confirm_line stock relocation ===")
    # Create 3 bins A,B,C via bulk (codes A-01, A-02, A-03 style won't matter; use prefix)
    binr = p("/api/v1/wm/bins/bulk", {
        "warehouse_id": wh_id, "location_kind": "physical",
        "separator": "-", "prefix": "WMT",
        "segments": [{"start": 1, "end": 3, "step": 1, "pad": 2}],
    })
    print(f"  bins/bulk -> {binr.status_code} {binr.text[:150]}")
    # Fetch location ids by listing config locations
    locs = g("/api/v1/config/locations?warehouse_id=" + wh_id).json()
    locs = locs if isinstance(locs, list) else locs.get("items", [])
    wmt = sorted([l for l in locs if str(l.get("code", "")).startswith("WMT")],
                 key=lambda l: l["code"])
    if len(wmt) < 3:
        print(f"  !! expected >=3 WMT bins, got {len(wmt)}: {[l.get('code') for l in wmt]}")
        return _summary(fails, None)
    A, B, C = wmt[0]["id"], wmt[1]["id"], wmt[2]["id"]
    print(f"  bins A={wmt[0]['code']} B={wmt[1]['code']} C={wmt[2]['code']}")

    # Product
    pid = p("/api/v1/products", {"sku": f"WMP{suf}", "name": "WM test prod",
                                  "unit_of_measure": "un"}).json()["id"]
    # Receive 100 into A, 100 into B  -> two quants
    r1 = p("/api/v1/stock/receive", {"product_id": pid, "warehouse_id": wh_id,
                                      "quantity": 100, "location_id": A, "unit_cost": 5})
    r2 = p("/api/v1/stock/receive", {"product_id": pid, "warehouse_id": wh_id,
                                      "quantity": 100, "location_id": B, "unit_cost": 5})
    print(f"  receive A -> {r1.status_code}, receive B -> {r2.status_code}")
    if r1.status_code >= 400:
        print(f"    receive err: {r1.text[:400]}")

    def quants():
        out = subprocess.run(["docker", "exec", "inventory-postgres", "psql", "-U", "inv_svc",
                              "-d", "inventorydb", "-At", "-F", ",", "-c",
                              f"SELECT location_id, qty_on_hand FROM stock_levels "
                              f"WHERE product_id='{pid}' ORDER BY qty_on_hand DESC;"],
                             capture_output=True, text=True)
        return out.stdout.strip()

    print("  quants BEFORE:")
    for ln in quants().splitlines():
        loc, q = ln.split(",")
        name = {A: "A", B: "B", C: "C"}.get(loc, loc[:8])
        print(f"    bin {name}: {q}")

    # Movement order: move 10 units from A -> C
    mo = p("/api/v1/wm/movement-orders", {
        "warehouse_id": wh_id,
        "lines": [{"product_id": pid, "quantity": 10,
                   "source_location_id": A, "dest_location_id": C}],
    })
    print(f"  create movement-order -> {mo.status_code}")
    if mo.status_code >= 400:
        print(f"    {mo.text[:300]}")
        return _summary(fails, "could not create movement order")
    moj = mo.json()
    oid, lid = moj["id"], moj["lines"][0]["id"]
    cf = p(f"/api/v1/wm/movement-orders/{oid}/lines/{lid}/confirm",
           {"confirm_source": True, "confirm_dest": True, "confirmed_qty": 10})
    print(f"  confirm line (qty=10, A->C) -> {cf.status_code}")
    if cf.status_code >= 500:
        fails.append(("POST", "confirm", cf.status_code, cf.text[:200]))

    print("  quants AFTER:")
    after = {}
    for ln in quants().splitlines():
        loc, q = ln.split(",")
        name = {A: "A", B: "B", C: "C"}.get(loc, loc[:8])
        after[name] = q
        print(f"    bin {name}: {q}")

    # Expected (correct): A=90, B=100, C=10. Bug => whole quant (100) moved, B touched, etc.
    # ── 3. Over-draw guard: confirm a move bigger than available must be rejected
    #        cleanly (ValidationError, no corruption). ──
    print("\n=== over-draw guard (move 1000 from A, only 90 available) ===")
    mo2 = p("/api/v1/wm/movement-orders", {
        "warehouse_id": wh_id,
        "lines": [{"product_id": pid, "quantity": 1000,
                   "source_location_id": A, "dest_location_id": C}],
    }).json()
    cf2 = p(f"/api/v1/wm/movement-orders/{mo2['id']}/lines/{mo2['lines'][0]['id']}/confirm",
            {"confirm_source": True, "confirm_dest": True, "confirmed_qty": 1000})
    print(f"  confirm overdraw -> {cf2.status_code} (expect 4xx, NOT 5xx)")
    if cf2.status_code >= 500:
        fails.append(("POST", "confirm-overdraw", cf2.status_code, cf2.text[:200]))
    # A must still be 90 (unchanged by the rejected move)
    a_now = [l.split(",") for l in quants().splitlines()]
    a_qty = next((q for loc, q in a_now if loc == A), "0")
    print(f"  bin A after rejected overdraw: {a_qty} (expect 90)")

    # ── 4. removal/plan must not crash and must respect the warehouse ──
    print("\n=== removal/plan sanity ===")
    rp = p("/api/v1/wm/removal/plan", {"warehouse_id": wh_id, "product_id": pid, "quantity": 5})
    print(f"  removal/plan -> {rp.status_code}")
    if rp.status_code >= 500:
        fails.append(("POST", "removal/plan", rp.status_code, rp.text[:200]))

    from decimal import Decimal as D
    if D(a_qty or "0") != D("90"):
        fails.append(("STATE", "overdraw-corruption", a_qty, "bin A changed after rejected move"))
    dA = D(after.get("A") or "0")
    dB = D(after.get("B") or "0")
    dC = D(after.get("C") or "0")
    if dA == D("90") and dB == D("100") and dC == D("10"):
        bug = None  # correct: exactly 10 moved A->C, A keeps 90, B untouched
    elif dC == D("100") or dA == 0:
        bug = "WHOLE quant relocated to C — partial qty ignored."
    elif dB != D("100"):
        bug = "B quant touched though line moved A->C — arbitrary quant selected."
    else:
        bug = f"unexpected state A={dA} B={dB} C={dC}"
    return _summary(fails, bug)


def _summary(fails, bug):
    print("\n=== SUMMARY ===")
    if fails:
        print(f"  {len(fails)} endpoint failures (5xx/exc):")
        for f in fails:
            print(f"    {f}")
    else:
        print("  no 5xx on smoke endpoints")
    if bug:
        print(f"  P0 CONFIRMED: {bug}")
    elif bug is None:
        print("  confirm_line moved stock correctly (A=90, C=10) — P0 NOT reproduced")
    return 1 if (fails or bug) else 0


if __name__ == "__main__":
    sys.exit(main())
