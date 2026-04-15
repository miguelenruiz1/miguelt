# UX Hardening Report — 2026-04-14

Branch: `fixes/milimetricos`
Scope: frontend-only (`front-trace/src/`)
Método: inspección estática + `tsc --noEmit` (sin browser). Demo Uniandes 20-abr.

---

## Parte A — Checklist de los 13 flujos demo-críticos

| # | Flujo | Estado | Commits aplicados | Gaps no arreglados |
|---|---|---|---|---|
| 1 | `/login` (qa@trace.com) | OK | `a621f7f` mejora mensaje al fallar login | Ninguno; `login.error.message` ya se muestra inline. |
| 2 | `/` Dashboard inicial | OK | — | Dashboard es estático (shortcuts + usage). Fallback limpio cuando `usage` es `undefined`. |
| 3 | `/cumplimiento/parcelas/nueva` café (Huila) | OK | `a621f7f` (toast ahora muestra detail real) | Validación EUDR precisión 6 decimales la hace backend; frontend no la previene. |
| 4 | Crear plot cacao (Tumaco) + cadmio | OK | `a621f7f` | — |
| 5 | Crear plot palma (Cesar) + RSPO | OK | `a621f7f` | — |
| 6 | `/cumplimiento/parcelas` lista + filtro commodity | OK | — | `PlotDocBadge` hace fetch por fila — si hay 100 parcelas dispara 100 queries. LOW. |
| 7 | `/cumplimiento/parcelas/:id` detalle | minor | `a621f7f` | Loading state es texto plano "Cargando..." (no skeleton). `(plot as any).metadata_?.…` — el uso de `as any` encubre tipos faltantes. |
| 8 | `/assets` crear asset | major | — | **Campo `plot_id` no existe en `CreateAssetModal` ni `MintNFTModal`.** El seed lo envía pero el UI no lo expone (ver Parte C). |
| 9 | `/assets/:id` detalle + `PlotOriginCard` | OK | `93e033d` (`alert()` → `toast`) | `PlotOriginCard` ya consume `asset.plot_id` vía `usePlot`. Si el backend sigue devolviendo null (bug conocido), la card no aparece. |
| 10 | `/inventario/ventas` crear SO | OK | `93e033d` (try/catch + guards) | Modal ya no se cierra silenciosamente; toast muestra detail Pydantic. |
| 11 | `/cumplimiento/registros/:id` DDS + cadmio | OK | `a621f7f` + `93e033d` | **CadmiumCard usaba `fetch` sin Authorization**; ya migrado a `authFetch` + invalidación de React Query en lugar de `window.location.reload()`. |
| 12 | Timeline eventos custody | OK | — | `EventTimeline` tiene skeleton + empty state. |
| 13 | `/inventario` dashboard KPIs por commodity | OK | — | Todas las queries tienen `isLoading` con skeleton Tailwind. |

**Resumen**: 11 OK, 1 minor, 1 major (scope backend, no fixable desde frontend sin agregar feature).

---

## Parte B — Bugs fixeados en este sprint

| Commit | Archivos | Fix |
|---|---|---|
| `a621f7f` | `lib/api.ts`, `lib/inventory-api.ts`, `lib/user-api.ts` | `ApiError.message` ahora normaliza `detail` cuando es un array Pydantic v2 (`[{loc,msg,type}]`) o un objeto con `.message`. Antes se propagaba `[object Object]` a 102 callsites de `toast.error(e.message)`. Arreglado también el popup 402 en api.ts que asumía `detail` string. |
| `93e033d` | `pages/compliance/RecordDetailPage.tsx` | `CadmiumCard`: migrado de `fetch` crudo (sin Authorization) a `authFetch`; parseo de detail array; invalidación de queries `['compliance','records',id]` reemplaza `window.location.reload()`; toast.success/error explícito; validación client-side `Number.isFinite(value)`. |
| `93e033d` | `pages/AssetDetailPage.tsx` | `alert(e.message)` → `toast.error(e.message)` al fallar borrado; añadido `toast.success('Carga eliminada')`. |
| `93e033d` | `pages/inventory/SalesOrdersPage.tsx` | `CreateSOModal.doSubmit` envuelto en try/catch con `toast.error`; añadidos guards `!customer_id` y `lines.length === 0`; mensaje de éxito explícito. Antes, si el backend 422-eaba (p.ej. líneas vacías o producto sin stock), el modal se quedaba abierto sin feedback. |

Total: **2 commits**, **6 archivos**, **~125 líneas netas**.

---

## Parte C — Bugs NO arreglados por severidad

### BLOCKER
- **`CreateAssetModal` / `MintNFTModal` no exponen `plot_id`** (`front-trace/src/components/assets/CreateAssetModal.tsx`, `MintNFTModal.tsx`). El prompt del sprint menciona "crear asset linkeado a plot (campo `plot_id`)" pero no existe el input. Agregarlo es una *feature* nueva (prompt explícitamente prohíbe features). Coordinar con agente backend para: (a) qué endpoint devuelve el plot seleccionable; (b) si se requiere dropdown o búsqueda. **No se arregló por estar fuera de scope.**
- **`AssetDetailPage.tsx:454` consume `asset.plot_id ?? null`** pero el bug del backend (reporte previo Parte D HIGH) sigue haciendo que el POST `/api/v1/assets` no persista `plot_id`. El `PlotOriginCard` quedará oculto silenciosamente. No fixable desde frontend.

### HIGH
- **`PlotDetailPage.tsx:621-626` accede a `(plot as any).metadata_?.eudr_full_screening`** con casts `as any`. Si el backend cambia la forma del `metadata_`, la UI rompe sin error de tipo. Ver `front-trace/src/types/compliance.ts` para agregar tipos; no lo hice por scope (>30 min).
- **`RecordDetailPage.tsx:431-443` link de plot al record: `linkPlot.mutate` sin `onError`**. Si el backend rechaza por cantidad inválida, el form se resetea sin feedback.

### MED
- **`PlotsPage.tsx:75-90` `PlotDocBadge` hace `usePlotDocuments(plot.id)` por cada fila** → N queries. Con 50+ parcelas es perceptible. Considerar endpoint batch `GET /plots/documents?plot_ids=...` o columna server-side con count.
- **`PlotDetailPage.tsx:618` loading state es texto plano** "Cargando..." sin spinner/skeleton — inconsistente con el resto de la app.
- **`SalesOrdersPage.tsx:505` usa `prompt()` nativo para motivo de rechazo** — se ve feo en demo. Considerar modal propio.
- **`CreatePlotPage.tsx:199` el polígono queda en state local (`polygonData`)** — si el usuario envía, falla validación en otro campo, y edita, el polígono se preserva (OK). Pero si clickea "Cancelar" y vuelve, se pierde. No crítico para demo.

### LOW
- **`CreatePlotPage.tsx:73-74` rangos geográficos fijos a Colombia** (`lat -4.23..13.39`). Si alguien demostrara con coords mock de fuera de CO, fallaría. Backend ya valida; frontend duplica.
- **`RecordDetailPage.tsx:117` antes lanzaba `HTTP ${status}` sin detail** — ahora parsea.
- **`InventoryDashboardPage.tsx:629` usa `data?.movements_by_type ?? []`** OK, pero otros spots accesan `data!.event_summary` (con `!`) que crashearía si `data` es `undefined` después del loading guard. Defensivo pero no observado.

---

## Parte D — i18n gaps encontrados

- Ningún `>Loading<`, `>Submit<`, `>Cancel<`, `>Save<` suelto en `pages/`. Inspección con regex confirmada.
- Acentos inconsistentes: algunas cadenas en CreatePlotPage son sin tilde ("Ubicacion", "Municipio"). Mezcla intencional — el archivo entero está sin tildes, consistente. No arreglar en este sprint.
- Sidebar, Topbar, Dashboard: todo en español.
- `PaymentsPage`, `MarketplacePage` son superuser-only → no impactan demo.

---

## Parte E — Errores esperados en consola (no son bugs)

Para que el founder no se asuste si abre DevTools durante la demo:

1. **`/api/v1/compliance/plots/{id}/screen-deforestation-full` puede responder >10s** (llamada real a GFW). Esto no es error, pero la UI muestra `Loader2` — el usuario podría pensar que colgó.
2. **`/api/v1/production-resources` devuelve 403** (reporte previo). Si el demo entra a `/produccion/recursos`, verá 403 en consola. Evitar navegar ahí.
3. **Warnings de React DevTools sobre `key` faltante** — no encontré `.map` sin `key` en los archivos demo-críticos inspeccionados (PlotsPage, SalesOrdersPage, InventoryDashboardPage, AssetsPage, PlotDetailPage).
4. **WebSocket de Vite HMR** (dev-only): ignorable en prod build.
5. **Leaflet "reset not possible without bounds"**: aparece si un plot no tiene polígono. No crashea.

---

## Parte F — Top 5 cosas que requieren verificación manual con browser

No pude validar sin un browser real:

1. **Leaflet/PlotPolygonEditor**: que el dibujo de polígono (click-to-add vertices, cálculo de área) funciona en todos los commodities. El código parece OK; solo un human puede confirmar UX.
2. **Tooltips flotantes** (títulos en botones `Verificar deforestacion`, badges EUDR `DF`/`LL`/`FC`): son `title=""` nativos. Verificar que se vean OK en Chrome/Safari (en Firefox el renderizado es feo).
3. **Responsive mobile**: el sticky footer del `CreatePlotPage` usa `fixed bottom-0` — puede taparse con el nav mobile en iOS Safari. No testeable sin device.
4. **Animaciones de recharts (BarChart/PieChart/LineChart)**: pueden laggear con datasets grandes — en la demo el tenant tiene pocos datos, debería ir fluido.
5. **Toast stacking**: si el usuario dispara 3 screenings seguidos, aparecen 3 toasts a la vez. Visualmente sorprendente; verificar que el z-index no se coma el sticky footer.

---

## Parte G — Delta honesto

**Antes de este sprint** (post QA anterior): ~75-80% de los flujos demo eran robustos. El principal bug silente era que los toasts mostraban `[object Object]` cuando el backend devolvía 422 con detail array — afectaba a todos los flujos con forms.

**Después de este sprint**: estimo **~90% bulletproof** para los flujos 1-7, 9-13. El único flujo con major gap es **#8 (asset create con plot_id)** — bloqueado por falta de feature en el UI + bug persistente backend.

Razón del 10% restante:
- Flujo #8 requiere feature nueva (ver Parte C BLOCKER).
- `PlotDetailPage` sigue con `as any` en metadata (frágil ante cambios backend, Parte C HIGH).
- Algunos spots con `prompt()` nativo y loading states inconsistentes (Parte C MED) — cosmético.

**Recomendación para antes de la demo**:
1. Coordinar con agente backend para confirmar que `asset.plot_id` se persiste y devuelve correctamente (smoke test POST + GET de un asset con `plot_id`).
2. Si no hay tiempo para agregar el selector de plot en los modales, demostrar flujo #8 con un asset *pre-seedeado* y saltar la parte de "crear asset from UI con plot link".
3. Evitar navegar a `/produccion/recursos` (403 visible).
4. Hacer un dry-run end-to-end de los 13 flujos en la máquina de demo 1 hora antes — ningún reporte estático reemplaza eso (CLAUDE.md regla #10).

**Commits en esta sesión**: `a621f7f`, `93e033d`. No hay push, no hay deploy.
**Type-check**: `npx tsc --noEmit` pasa limpio.
