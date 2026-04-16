# Phase 1 Testing Infrastructure Report

**Date:** 2026-04-15
**Scope:** inventory-service, subscription-service, trace-service

## TL;DR

**64 Phase 1 tests passing across 3 services.**

| Service               | Unit tests | Integration tests | Status  |
|-----------------------|-----------:|------------------:|---------|
| inventory-service     |         20 |                 — | PASS    |
| subscription-service  |         14 |                 4 | PASS    |
| trace-service         |         26 |                 — | PASS    |
| **total**             |     **60** |             **4** | **64 PASS** |

All tests are deterministic, run in under 5 seconds combined, and require no
external services (DB/Redis/network). The subscription-service integration
tests use an in-memory SQLite engine.

## Pre-existing state (correction to initial brief)

The Phase 1 brief stated "Trace no tiene ni un solo test automatizado". That's
inaccurate.

- `inventory-service/tests/` already contains **1655 test cases** across 50+
  files with a mature `conftest.py` (in-memory SQLite + JSONB patching +
  ASGITransport client + dep overrides). Many tests are currently failing
  (collection OK, execution fails on DB fixtures in some files), but the
  **infrastructure is there**.
- `trace-service/tests/` has a Postgres-backed integration suite
  (`test_custody_flow`, `test_allowlist`, `test_concurrency`,
  `test_idempotency`) with an autouse `_clean_tables` fixture that
  TRUNCATEs between tests. Requires a live test DB on port 5437.
- `subscription-service/tests/` did NOT exist. Created from scratch here.

Given this, Phase 1 in practice became:
1. **subscription-service**: greenfield test infra + 18 tests.
2. **inventory-service**: add `tests/unit/` bucket + 20 focused unit tests
   targeting areas the existing suite didn't cover (NIT validator, tax math,
   module cache contract).
3. **trace-service**: add `tests/unit/` bucket with sub-conftest override
   (no Postgres required) + 26 state-machine tests.

## Files created

### subscription-service (greenfield)

- `subscription-service/pytest.ini`
- `subscription-service/requirements-test.txt`
- `subscription-service/tests/__init__.py`
- `subscription-service/tests/conftest.py` — SQLite+JSONB patch, dep overrides,
  `make_plan` / `make_subscription` factories, Redis mock, superuser test user.
- `subscription-service/tests/unit/__init__.py`
- `subscription-service/tests/unit/test_platform_service.py` — MRR monthly,
  MRR annual (uses price_annual/12), canceled excluded, change_plan rejects
  canceled, change_plan unknown plan.
- `subscription-service/tests/unit/test_module_service.py` — catalog sanity,
  `list_tenant_modules` merges catalog + activations, `activate()` invalidates
  cache with the key contract `module:{tenant_id}:{slug}`.
- `subscription-service/tests/unit/test_invoice_service.py` — format contract,
  sequential mock, `generate_invoice` amount (pins current behavior),
  status transition invariants.
- `subscription-service/tests/integration/__init__.py`
- `subscription-service/tests/integration/test_api_plans.py` — list + get.
- `subscription-service/tests/integration/test_api_platform.py` — superuser
  allow + non-superuser 403.

### inventory-service (added)

- `inventory-service/app/utils/nit.py` — DIAN NIT check-digit validator
  (`compute_nit_check_digit`, `is_valid_nit`, `assert_valid_nit`).
- `inventory-service/requirements-test.txt`
- `inventory-service/tests/unit/__init__.py`
- `inventory-service/tests/unit/test_nit_validator.py` — 11 tests incl. known
  public NITs (Bancolombia 800197268-4), dot handling, invalid-DV rejection,
  assert variant.
- `inventory-service/tests/unit/test_tax_service.py` — 7 tests:
  `calculate_line_taxes` single IVA, IVA+Retefuente, multi-line, zero-exempt,
  half-up rounding, CO_ALLOWED_TAX_SLUGS sanity, `create_rate` ConflictError
  on non-CO slug (async with DB mock).
- `inventory-service/tests/unit/test_module_catalog.py` — 2 tests pinning the
  `module:{tenant_id}:{slug}` Redis key contract consumer-side.

### trace-service (added)

- `trace-service/requirements-test.txt`
- `trace-service/tests/unit/__init__.py`
- `trace-service/tests/unit/conftest.py` — overrides the parent's autouse
  `_clean_tables` fixture with a no-op so unit tests don't need Postgres.
- `trace-service/tests/unit/test_custody_state_machine.py` — 26 tests:
  HANDOFF valid origins + target state, RELEASED/BURNED terminal invariants,
  BURN from every non-terminal (parametrized, 9 cases) + rejected from every
  terminal (3), ARRIVED tight-only-from-IN_TRANSIT, informational events
  preserve state (6 parametrized).

### repo root

- `qa/run-tests.sh` — local runner (`unit` default, `all` adds integration).
- `qa/PHASE1_TESTING_REPORT.md` — this file.
- `cloudbuild.tests.yaml` — parallel Cloud Build step running all three
  services' unit suites; designed to be hooked via `waitFor` from existing
  per-service deploy pipelines.

## Files modified

None. All additions are in new files, minimizing risk of side-effects on the
existing test and deploy pipelines. `requirements-test.txt` files are new and
do not affect production builds (not referenced in any Dockerfile).

## Bugs / rough edges discovered

### BUG-01 (medium) — `SubscriptionService.generate_invoice` ignores billing_cycle

**File:** `subscription-service/app/services/subscription_service.py:159`

```python
amount = sub.plan.price_monthly if sub.plan else Decimal("0")
```

For annual subscriptions the generated invoice should bill `price_annual`, not
`price_monthly`. The PlatformService MRR code correctly branches on
`billing_cycle` but `generate_invoice` does not. Documented in
`test_generate_invoice_uses_price_monthly` (pins current behavior; a follow-up
PR should flip the test and fix the service).

### BUG-02 (low) — legacy trace-service unit tests coupled to Postgres

The parent `trace-service/tests/conftest.py` has `_clean_tables` as an
autouse session fixture hitting `TEST_DATABASE_URL`. This forces every test
in that directory to require a real Postgres test DB on port 5437, even pure
domain-logic tests. Worked around here with a `tests/unit/conftest.py`
no-op override, but a larger cleanup should split that file into
`_common` + `_integration` fixtures.

### BUG-03 (low) — `inventory-service/pytest.ini` lacks `python_classes = Test*`

Existing config only collects `test_*` functions. The new tests use
`class Test*:` containers (modern convention). Worked because pytest's
default still matches `Test*` when `python_classes` is unset, but the
inventory pytest.ini explicitly lists `python_files` + `python_functions`
without `python_classes`, so a future tightening of that config would break
the new tests. Safer: add `python_classes = Test*` explicitly. Left alone
in this phase to stay within scope.

### Observation — existing inventory suite has ~flaky/broken tests

`pytest tests/test_pricing.py` fails with `sqlalchemy.exc.OperationalError`
at collection. Did not investigate (out of Phase 1 scope), but the "all
existing tests green" premise doesn't hold: only the new `tests/unit/`
bucket is guaranteed green. Phase 2 should fix or quarantine the broken
files.

## Initial coverage

Not measured formally in this phase — `--cov-fail-under=0` is effectively
the policy today. The rationale: turning coverage on while the existing
inventory suite is partially broken would produce misleading numbers. Once
Phase 2 fixes/quarantines those tests, enable coverage with a floor of 20%
initially and ratchet up.

## How to run

Locally:

```bash
# Default: unit tests only (fast, no DB)
bash qa/run-tests.sh

# With integration tests (in-memory SQLite)
bash qa/run-tests.sh all
```

Per-service:

```bash
cd inventory-service    && python -m pytest tests/unit -x --tb=short
cd subscription-service && python -m pytest tests       -x --tb=short
cd trace-service        && python -m pytest tests/unit  -x --tb=short
```

Docker / CI:

```bash
gcloud builds submit --config cloudbuild.tests.yaml --project trace-log
```

## Next steps (Phase 2)

1. **Fix BUG-01** in `SubscriptionService.generate_invoice` and flip the
   pinning test. Same class of bug likely in `LicenseService` —
   audit all currency/cycle-dependent math.
2. **Quarantine or fix** the failing tests in `inventory-service/tests/*`.
   Move pure unit tests into `tests/unit/` so they can run without Postgres.
3. **Add testcontainers-python** to the stack for Postgres-dependent tests
   that need JSONB / CTE / UPSERT / ON CONFLICT semantics. SQLite isn't
   sufficient for the UPSERT-based `next_invoice_number`.
4. **Enable coverage** with a floor:
   `--cov=app --cov-fail-under=20` in each pytest.ini, ratcheting upward.
5. **End-to-end billing flow test** in subscription-service:
   onboard_tenant → activate module → generate_invoice →
   mark_invoice_paid → events show up in platform dashboard.
6. **State-machine guard tests in trace-service** via the actual service
   layer (not just the domain mappings tested here) — i.e. call
   `custody_service.register_event()` and assert the service raises for
   illegal transitions, not just that the mapping table contains them.
7. **Hook `cloudbuild.tests.yaml`** as a `waitFor` prerequisite on the
   per-service deploy pipelines so a red test blocks deploy.
