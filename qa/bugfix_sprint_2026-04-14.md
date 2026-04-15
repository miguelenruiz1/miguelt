# Bugfix sprint — 2026-04-14

Branch: `fixes/milimetricos`

## Commits

| Hash | Scope | Description |
|------|-------|-------------|
| `1ea4a01` | i18n + UX | Consistent `es-CO` formatting for numbers/dates across 35 files; added `fmtNumber`/`fmtMoney` helpers. Also contains skeleton loading states for PlotDetailPage, RecordDetailPage, PurchaseOrderDetailPage, SalesOrderDetailPage, AssetDetailPage (bundled because the same files had both changes). |

Only 1 commit created this sprint. Items 1 and 2 produced no fixes (see below).

## Item 1 — trace-bridge E2E validation

**Result: Auth-probe only (not full E2E).**

What was verified:
- S2S call from `inventory-api` container → `trace-api:8000/api/v1/internal/assets/from-production-receipt` resolves, auth token accepted, endpoint returns `422` with the expected "no active wallet" detail when posting placeholder payload. Confirms routing + auth + payload shape are wired correctly.
- `inventory-service/app/clients/trace_client.py:notify_production_completed` matches the trace-service Pydantic request schema (`ProductionReceiptRequest`).
- `production_service.create_receipt` gathers `input_batch_ids` and `plot_ids` inside a SAVEPOINT (regla #2 applied) and calls `notify_production_completed_background` fire-and-forget.

What was NOT verified end-to-end:
- No production run exists in the QA tenant. Creating one requires: wallet generation, product + recipe (with `output_entity_id`), inputs stock, emissions, then a receipt. That setup is ~1-2 h of data prep and is out of scope for a bugfix sprint (rule #8 of prompt: "if item exceeds 2x estimated time → document and skip").
- The `BatchPlotOrigin` insert path was not re-verified with real data.

**Recommendation**: spin up a short seed script that provisions (wallet + product + recipe + stock + run + emission + receipt) for the QA tenant, so this endpoint can be smoke-tested after every trace-bridge change. Left as pending — no commit.

Honest rating per rule #10: the bridge **probably** works end-to-end, but nobody has run it against live input batches + plot origins in this environment. Do not claim "verified".

## Item 2 — Browser console audit

**Result: no bugs fixed; false positives only.**

Checked:
- `key={index}` / `key={i}`: all occurrences are on static arrays, skeleton loaders, or string lists where React's reconciler cannot misbehave (no reorder/delete operations). Not worth changing.
- `{x.length && <..>}` numeric-falsy-renders-"0": **zero** matches in JSX (the 2 results were `!length &&` which is safe).
- `.map` on possibly-undefined: all audited call sites guard with `if (!data) return <Spinner/>` before rendering.
- `defaultProps` on function components: zero matches.
- `async` directly passed to `useEffect`: zero matches.
- Untranslated English in user-visible JSX text: only `<span className="sr-only">Close</span>` in shadcn `dialog.tsx`/`sheet.tsx` (screen-reader only, low priority, skipped).

No commit produced. The codebase is already hygienic in these categories.

## Item 3 — i18n / es-CO consistency

**Result: 35 files swept. 1 commit (`1ea4a01`).**

Problem: 128 bare `.toLocaleString()` / `.toLocaleDateString()` calls across 31 files. Browser default locale → inconsistent output depending on OS language (Colombian user sees `1,000,000` on a Windows-EN install).

Fix:
- `sed` replace of `.toLocaleString()` → `.toLocaleString('es-CO')` and `.toLocaleDateString()` → `.toLocaleDateString('es-CO')` in all `.tsx`.
- Added `fmtNumber(value, opts?)` and `fmtMoney(value, currency='COP')` in `src/lib/utils.ts`. `fmtMoney` drops decimals for COP (whole pesos) and uses 2 decimals otherwise.

Not touched (out of scope for this sprint):
- Hard-coded prefix `${amount}` → should migrate to `fmtMoney(amount, currency)` per-page when their currency is known. Left as follow-up. Current behavior is unchanged for those call sites — no regression.
- String `kg` / `ha` units in labels.

TypeScript: `npx tsc --noEmit` passes clean after the sweep.

## Item 4 — Detail page skeleton loading

**Result: 5 detail pages upgraded (bundled into `1ea4a01`).**

Replaced flat `"Cargando..."` / centered spinner with shape-preserving skeleton layouts (title bar + KPI cards + main content area) in:

- `PlotDetailPage.tsx`
- `AssetDetailPage.tsx`
- `PurchaseOrderDetailPage.tsx`
- `SalesOrderDetailPage.tsx` (main one; the batches-used sub-component still has a small inline "Cargando..." — low priority)
- `RecordDetailPage.tsx`

Skeleton uses `animate-pulse` + `bg-muted` to match the existing `Skeleton` utility.

## Effectiveness delta

Baseline: ~95-96% (prior sprint).

Honest assessment after this sprint: **~96%**.

Rationale:
- i18n sweep is a real fix but low-visibility for dev-running-in-Spanish-locale.
- Skeletons are polish — UX feel improves but no behavior change.
- No new bugs uncovered that required fixes in code (Item 2).
- Item 1 remains at "wired, auth OK, E2E not driven". Same state as end of prior sprint, not worse.

## Pending / follow-ups

1. **Trace-bridge E2E**: write a seed script that provisions a complete production run with emissions + receipt for the QA tenant, then `curl` the receipt endpoint and assert an asset appears in trace-service with `event_type=transformation` and `BatchPlotOrigin` rows exist. ~1 h of work, but blocked by needing a reusable seed/fixture.
2. **Migrate `$${x.toLocaleString('es-CO')} COP`** call sites to `fmtMoney(x, 'COP')` — cosmetic, cleaner.
3. **`sr-only` strings** `"Close"` in dialog.tsx/sheet.tsx — translate for Spanish screen-reader users.
4. Pre-existing working-tree changes (CLAUDE.md, front-trace/cloudbuild.yaml, qa_test.sh, pitch/, qa/) were left untouched per scope rule 4.

## Verification

```
cd front-trace && npx tsc --noEmit   # pass, 0 errors
git log --oneline -2                 # 1ea4a01 + ac607d9 (baseline)
```
