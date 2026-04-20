"""Broad reachability scan of ALL inventory-service routers.

Counts each router as:
- PASS = GET returns 2xx or 307 with auth
- AUTH = 401/403 without auth (router is protected — good)
- DEGRADED = 5xx or 404 on a GET we expected to resolve
"""
from __future__ import annotations

import os
import subprocess
import sys

import httpx

GATEWAY = "http://localhost:9000"
USER_API = "http://localhost:9001"


def flush():
    subprocess.run(["docker", "exec", "trace-redis", "redis-cli", "-n", "2", "FLUSHDB"], capture_output=True)
    subprocess.run(["docker", "exec", "trace-redis", "redis-cli", "-n", "3", "FLUSHDB"], capture_output=True)
    subprocess.run(["docker", "exec", "trace-redis", "redis-cli", "-n", "4", "FLUSHDB"], capture_output=True)


def main() -> int:
    flush()
    import secrets as _s
    suf = _s.token_hex(3)
    c = httpx.Client(timeout=20.0, follow_redirects=False)

    r = c.post(f"{USER_API}/api/v1/auth/register", json={
        "email": f"invscan{suf}@t.com", "username": f"invscan{suf}",
        "full_name": "scan", "password": "TracePwd2026!",
        "company": f"InvScanCo{suf}",
    })
    r.raise_for_status()
    uid = r.json()["id"]
    tid = r.json()["tenant_id"]
    subprocess.run([
        "docker", "exec", "user-postgres", "psql", "-U", "user_svc", "-d", "userdb", "-c",
        f"UPDATE users SET is_superuser=true WHERE email='invscan{suf}@t.com';"
    ], capture_output=True)
    flush()
    tok = c.post(f"{USER_API}/api/v1/auth/login", json={
        "email": f"invscan{suf}@t.com", "password": "TracePwd2026!"
    }).json()["access_token"]
    # Activate inventory module
    c.post(f"{GATEWAY}/api/v1/modules/{tid}/inventory/activate",
           headers={"Authorization": f"Bearer {tok}", "X-Tenant-Id": tid})
    h = {"Authorization": f"Bearer {tok}", "X-Tenant-Id": tid, "X-User-Id": uid}

    # Each tuple: (router_label, list_endpoint).
    # Using GET probes because we mostly care about REACHABILITY + 2xx/3xx contract.
    endpoints = [
        ("categories",       "/api/v1/categories"),
        ("products",         "/api/v1/products"),
        ("warehouses",       "/api/v1/warehouses"),
        ("suppliers",        "/api/v1/suppliers"),
        ("purchase-orders",  "/api/v1/purchase-orders"),
        ("sales-orders",     "/api/v1/sales-orders"),
        ("movements",        "/api/v1/movements"),
        ("stock",            "/api/v1/stock?product_id=00000000-0000-0000-0000-000000000000"),
        ("batches",          "/api/v1/batches"),
        ("batch-origins",    "/api/v1/batch-origins"),
        ("customers",        "/api/v1/customers"),
        ("customer-prices",  "/api/v1/customer-prices"),
        ("cycle-counts",     "/api/v1/cycle-counts"),
        ("partners",         "/api/v1/partners"),
        ("production",       "/api/v1/production"),
        ("quality-tests",    "/api/v1/quality-tests"),
        ("recipes",          "/api/v1/recipes"),
        ("reorder",          "/api/v1/reorder"),
        ("serials",          "/api/v1/serials"),
        ("shipments",        "/api/v1/shipments"),
        ("tax-categories",   "/api/v1/tax-categories"),
        ("tax-rates",        "/api/v1/tax-rates"),
        ("uom",              "/api/v1/uom"),
        ("variants",         "/api/v1/variants"),
        ("variant-attrs",    "/api/v1/variant-attributes"),
        ("alerts",           "/api/v1/alerts"),
        ("audit",            "/api/v1/audit"),
        ("events",           "/api/v1/events"),
        ("imports",          "/api/v1/imports"),
        ("resources",        "/api/v1/resources"),
        ("portal",           "/api/v1/portal"),
        ("public-verify",    "/api/v1/public-verify"),
        ("analytics/overview","/api/v1/analytics/overview"),
        ("analytics/abc",    "/api/v1/analytics/abc"),
        ("reports/products", "/api/v1/reports/products"),
        ("reports/stock",    "/api/v1/reports/stock"),
        ("reports/movements","/api/v1/reports/movements"),
        ("reports/suppliers","/api/v1/reports/suppliers"),
        ("config/product-types",   "/api/v1/config/product-types"),
        ("config/order-types",     "/api/v1/config/order-types"),
        ("config/custom-fields",   "/api/v1/config/custom-fields"),
        ("config/supplier-types",  "/api/v1/config/supplier-types"),
    ]

    pass_, degraded, notfound = 0, 0, 0
    detail = []
    for name, path in endpoints:
        try:
            r = c.get(f"{GATEWAY}{path}", headers=h)
            code = r.status_code
        except Exception as e:
            code = 599
        if 200 <= code < 300 or code in (307,):
            pass_ += 1
            status = "PASS"
        elif code == 404:
            notfound += 1
            status = "404"
        elif 400 <= code < 500:
            notfound += 1
            status = f"{code}"
        else:
            degraded += 1
            status = f"FAIL {code}"
        detail.append((status, code, name, path))

    total = len(endpoints)
    for s, code, name, path in sorted(detail, key=lambda x: (x[0] != "PASS", x[0])):
        print(f"  {s:>5}  {code:>3}  {name:<22} {path}")
    print()
    print(f"TOTAL: {total}  PASS: {pass_}  NOT-FOUND/CLIENT: {notfound}  5xx: {degraded}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
