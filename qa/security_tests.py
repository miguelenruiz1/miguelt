"""Targeted security tests for the 2 critical bugs found in agent audit.

Bug 1: Taxonomy cross-tenant write — Bob should NOT be able to mutate
  resources belonging to Alice's tenant by flipping X-Tenant-Id.

Bug 2: user-api roles.py 500s — admin RBAC flow should return 200, not 500.
"""
from __future__ import annotations

import os
import secrets
import subprocess
import sys

import httpx

GATEWAY = "http://localhost:9000"
USER_API = "http://localhost:9001"
PASS = "[PASS]"
FAIL = "[FAIL]"


def flush_redis():
    subprocess.run(["docker", "exec", "trace-redis", "redis-cli", "-n", "2", "FLUSHDB"],
                   capture_output=True)
    subprocess.run(["docker", "exec", "trace-redis", "redis-cli", "-n", "3", "FLUSHDB"],
                   capture_output=True)


def register(client, suffix, company):
    r = client.post(f"{USER_API}/api/v1/auth/register", json={
        "email": f"sec{suffix}@test.com",
        "username": f"sec{suffix}",
        "full_name": f"Sec {suffix}",
        "password": "TracePwd2026!",
        "company": company,
    })
    r.raise_for_status()
    return r.json()["id"], r.json()["tenant_id"]


def login(client, suffix):
    r = client.post(f"{USER_API}/api/v1/auth/login", json={
        "email": f"sec{suffix}@test.com", "password": "TracePwd2026!",
    })
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> int:
    flush_redis()
    client = httpx.Client(timeout=30.0, follow_redirects=False)
    fails: list[str] = []

    # ── Setup: Alice + Bob in distinct tenants, Alice as superuser ──────────
    sa, sb = secrets.token_hex(3), secrets.token_hex(3)
    a_id, a_tid = register(client, sa, f"ACorp{sa}")
    b_id, b_tid = register(client, sb, f"BCorp{sb}")
    subprocess.run([
        "docker", "exec", "user-postgres", "psql", "-U", "user_svc", "-d", "userdb", "-c",
        f"UPDATE users SET is_superuser=true WHERE email='sec{sa}@test.com';"
    ], capture_output=True)
    flush_redis()
    tA = login(client, sa)
    tB = login(client, sb)
    print(f"Alice tenant: {a_tid}  Bob tenant: {b_tid}")

    # ── BUG 1 reproduction: Bob tries to read / mutate Alice's taxonomy ─────
    print("\n=== BUG 1: Taxonomy cross-tenant access ===")

    # List custodian types (seeded) in default tenant to get an id
    r = client.get(f"{GATEWAY}/api/v1/taxonomy/custodian-types",
                   headers={"Authorization": f"Bearer {tA}",
                            "X-Tenant-Id": "00000000-0000-0000-0000-000000000001"})
    if r.status_code != 200:
        print(f"{FAIL}  setup: alice list types default failed {r.status_code}")
        return 1
    farm_id = next((c["id"] for c in r.json() if c["slug"] == "farm"), r.json()[0]["id"])

    # Alice (superuser) creates an org in the default tenant so she has a
    # known resource that Bob (non-superuser) should NOT be able to touch.
    default_tid = "00000000-0000-0000-0000-000000000001"
    r = client.post(
        f"{GATEWAY}/api/v1/taxonomy/organizations",
        headers={"Authorization": f"Bearer {tA}", "X-Tenant-Id": default_tid,
                 "X-User-Id": a_id, "Content-Type": "application/json"},
        json={"name": "Alice's Farm", "custodian_type_id": farm_id,
              "description": "Should belong only to default tenant"},
    )
    if r.status_code not in (200, 201):
        print(f"{FAIL}  setup: Alice create org in her tenant -> {r.status_code} {r.text[:200]}")
        return 1
    alice_org_id = r.json()["id"]
    print(f"  (setup) Alice org_id={alice_org_id}")

    # Now Bob (token of B) tries to read the default-tenant org via header flip
    r = client.get(
        f"{GATEWAY}/api/v1/taxonomy/organizations/{alice_org_id}",
        headers={"Authorization": f"Bearer {tB}", "X-Tenant-Id": default_tid},
    )
    if r.status_code == 200 and r.json().get("id") == alice_org_id:
        print(f"{FAIL}  Bob GET alice org via header flip returns 200 — isolation broken")
        fails.append("GET cross-tenant still allowed")
    elif r.status_code in (403, 404):
        print(f"{PASS}  Bob GET alice org rejected -- status={r.status_code}")
    else:
        print(f"[WARN]  unexpected status {r.status_code}")

    # Bob tries to PATCH (rename)
    r = client.patch(
        f"{GATEWAY}/api/v1/taxonomy/organizations/{alice_org_id}",
        headers={"Authorization": f"Bearer {tB}", "X-Tenant-Id": default_tid,
                 "X-User-Id": b_id, "Content-Type": "application/json"},
        json={"name": "HACKED_BY_BOB"},
    )
    if r.status_code in (403, 404):
        print(f"{PASS}  Bob PATCH alice org rejected -- status={r.status_code}")
    else:
        print(f"{FAIL}  Bob PATCH alice org status={r.status_code} body={r.text[:200]}")
        fails.append("PATCH cross-tenant still allowed")

    # Bob tries to DELETE
    r = client.delete(
        f"{GATEWAY}/api/v1/taxonomy/organizations/{alice_org_id}",
        headers={"Authorization": f"Bearer {tB}", "X-Tenant-Id": a_tid,
                 "X-User-Id": b_id},
    )
    if r.status_code in (403, 404):
        print(f"{PASS}  Bob DELETE alice org rejected -- status={r.status_code}")
    else:
        print(f"{FAIL}  Bob DELETE alice org status={r.status_code}")
        fails.append("DELETE cross-tenant still allowed")

    # Verify Alice's org still exists and was not modified
    r = client.get(
        f"{GATEWAY}/api/v1/taxonomy/organizations/{alice_org_id}",
        headers={"Authorization": f"Bearer {tA}", "X-Tenant-Id": default_tid},
    )
    if r.status_code == 200 and r.json().get("name") == "Alice's Farm":
        print(f"{PASS}  Alice's org intact: name='{r.json()['name']}'")
    else:
        print(f"{FAIL}  Alice's org corrupted or missing: {r.status_code} {r.text[:200]}")
        fails.append("alice org compromised")

    # ── BUG 2 reproduction: admin RBAC no longer 500s ────────────────────────
    print("\n=== BUG 2: user-api admin RBAC flow ===")

    # GET /roles/{id}/permissions — first list roles to get the admin role id
    r = client.get(
        f"{GATEWAY}/api/v1/roles",
        headers={"Authorization": f"Bearer {tA}", "X-Tenant-Id": a_tid},
    )
    roles = r.json() if r.status_code == 200 else []
    admin_role = next((x for x in roles if x.get("slug") == "administrador" or "admin" in x.get("slug", "")), roles[0] if roles else None)
    if admin_role:
        r = client.get(
            f"{GATEWAY}/api/v1/roles/{admin_role['id']}/permissions",
            headers={"Authorization": f"Bearer {tA}", "X-Tenant-Id": a_tid},
        )
        if r.status_code == 200:
            print(f"{PASS}  GET /roles/{{id}}/permissions -- status=200 perms={len(r.json())}")
        else:
            print(f"{FAIL}  GET /roles/{{id}}/permissions -- status={r.status_code} body={r.text[:200]}")
            fails.append("roles/{id}/permissions 500")

    # PATCH /users/{id} — Alice updates her own full_name
    r = client.patch(
        f"{GATEWAY}/api/v1/users/{a_id}",
        headers={"Authorization": f"Bearer {tA}", "X-Tenant-Id": a_tid,
                 "Content-Type": "application/json"},
        json={"full_name": "Alice Updated"},
    )
    if r.status_code in (200, 204):
        print(f"{PASS}  PATCH /users/{{id}} -- status={r.status_code}")
    else:
        print(f"{FAIL}  PATCH /users/{{id}} -- status={r.status_code} body={r.text[:200]}")
        fails.append("PATCH users 500")

    print("\n" + "=" * 55)
    if fails:
        print(f"FAILURES ({len(fails)}):")
        for f in fails:
            print(f"  - {f}")
        return 2
    print("ALL SECURITY TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
