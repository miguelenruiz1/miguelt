# Fase 6 — UX Polish Report

Fecha: 2026-04-15
Scope: front-trace (React 19 + Vite + TS + Tailwind)
Verificación: `npx tsc --noEmit` OK (exit 0), `npm run build` OK (1m 4s)

---

## 1. Componentes nuevos

### 1.1 Skeleton family — `src/components/ui/skeleton.tsx`
Extendí el archivo existente (no roto, backward-compatible) con 4 variantes:

| Export        | Props                                                    | Uso típico                                    |
|---------------|----------------------------------------------------------|-----------------------------------------------|
| `Skeleton`    | `className`, `rows?`, `...divProps`                      | Placeholder genérico, tolera API shadcn vieja |
| `SkeletonTable` | `columns?=5`, `rows?=6`, `className?`                  | Tablas listadas antes de que llegue `data`    |
| `SkeletonCard`  | `lines?=3`, `className?`                               | Cards de detalle, paneles                     |
| `SkeletonGrid`  | `items?=4`, `columns?=4`, `className?`                 | Dashboards con KPIs                           |

Backward compat: el `<Skeleton className="h-4 w-24" />` de shadcn-style sigue funcionando (sin `rows` colapsa al comportamiento original).

### 1.2 EmptyState — `src/components/ui/EmptyState.tsx`
Nuevo componente reusable. API:
```ts
interface EmptyStateProps {
  icon: React.ElementType
  title: string
  description: string
  action?: { label: string; onClick?: () => void; to?: string; icon?: React.ElementType }
  secondaryAction?: EmptyStateAction
  illustration?: React.ReactNode
  compact?: boolean
  className?: string
}
```
Render: círculo con ícono (bg `muted/60`), `h3` título, `p` descripción `text-muted-foreground`, hasta 2 botones (default/outline) que aceptan `to` (react-router Link) u `onClick`. Nota: los botones con `to` no usan `<Button asChild>` porque el `Button` del repo (`@base-ui/react`) no expone esa prop; se renderiza como `<Link>` con clases equivalentes.

### 1.3 ErrorBoundary — `src/components/ErrorBoundary.tsx`
Class component React 19-compatible. Catch `getDerivedStateFromError` + `componentDidCatch`.
- Fallback por defecto: ícono `AlertTriangle`, título "Algo salió mal", descripción, y en dev se muestra el stack trace. Dos acciones: "Recargar página" (`window.location.reload()`) y "Reportar el problema" (mailto: a soporte@trace.log con URL y error pre-rellenos).
- Sentry: hook no-op si `window.Sentry.captureException` existe — evita dependencia dura; si se instala Sentry después, empieza a reportar sin más cambios.
- Props: `fallback` (node o `(err, reset) => node`), `onError`, `onReset`, `children`.

---

## 2. Wiring de ErrorBoundary

- `src/App.tsx` — envuelve todo el `<RouterProvider>` + `<PlanLimitModal>` en `<ErrorBoundary>` raíz (catch de último recurso).
- `src/components/layout/Layout.tsx` — envuelve el `<Outlet />` con `<ErrorBoundary key={pathname}>`. Clave: `key={pathname}` re-crea el boundary en cada cambio de ruta → un error en `/inventario/productos` no deja el boundary "atrapado" en estado error al navegar a `/dashboard`.

`QueryClientProvider` ya está en `main.tsx`; el `<App>` hijo ya queda bajo el ErrorBoundary.

---

## 3. Codemod i18n es-CO

**Resultado**: 59 replacements, 18 archivos modificados, 0 matches residuales.

Patrones reemplazados:
- `.toLocaleDateString('es'` → `.toLocaleDateString('es-CO'`
- `.toLocaleString('es'` → `.toLocaleString('es-CO'`
- `.toLocaleTimeString('es',` → `.toLocaleTimeString('es-CO',`

Archivos tocados (verificados uno a uno para evitar falsos positivos en `lang="es"` o similares):
```
src/pages/DashboardPage.tsx
src/pages/UsersPage.tsx
src/pages/SettingsPage.tsx
src/pages/TrackingBoardPage.tsx
src/pages/settings/BillingPage.tsx
src/pages/inventory/BatchesPage.tsx
src/pages/inventory/EventsPage.tsx
src/pages/inventory/InventoryDashboardPage.tsx
src/pages/inventory/MovementsPage.tsx
src/pages/inventory/PickingPage.tsx
src/pages/inventory/ProductsPage.tsx
src/pages/inventory/PurchaseOrderDetailPage.tsx
src/pages/inventory/PurchaseOrdersPage.tsx
src/pages/inventory/ScannerPage.tsx
src/pages/inventory/SerialsPage.tsx
src/pages/platform/PlatformAnalyticsPage.tsx
src/pages/platform/PlatformSalesPage.tsx
src/pages/platform/PlatformTenantDetailPage.tsx
src/pages/platform/PlatformTenantsPage.tsx
```

Verificación final (grep):
```
Pattern: \.toLocale(Date|Time)?String\('es'[,)]
Matches: 0 (en 0 archivos)
```

---

## 4. Páginas migradas a Skeleton + EmptyState

Páginas convertidas del spinner/"Cargando..." a `SkeletonTable`/`SkeletonCard` + `EmptyState` con copy en español natural:

| Página                                           | Skeleton          | EmptyState                                      |
|--------------------------------------------------|-------------------|-------------------------------------------------|
| `platform/PlatformTenantsPage.tsx`               | SkeletonTable 6×6 | Empresas — CTA "Nueva empresa"                  |
| `platform/PlatformDashboardPage.tsx`             | SkeletonGrid+Card | — (no lista)                                    |
| `platform/PlatformUsersPage.tsx`                 | SkeletonTable 7×8 | Usuarios — copy dependiente de filtros          |
| `inventory/ProductsPage.tsx`                     | SkeletonTable 6×8 | Productos — CTA "Nuevo producto"                |
| `inventory/PurchaseOrdersPage.tsx`               | SkeletonTable 5×6 | Órdenes de compra                               |
| `inventory/SalesOrdersPage.tsx`                  | SkeletonTable 8×6 | Órdenes de venta                                |
| `inventory/MovementsPage.tsx`                    | SkeletonTable 6×6 | Movimientos — CTA "Nuevo movimiento"            |
| `compliance/RecordsPage.tsx`                     | SkeletonTable 8×6 | Registros — CTA "Nuevo registro"                |

Patrón aplicado: `{isLoading && !data ? <SkeletonTable .../> : data.length === 0 ? <EmptyState .../> : <table>...</table>}`.

**No migradas (DataTable ya maneja loading/empty internamente, evité double-wrap)**:
- `compliance/CertificatesPage.tsx` (usa `<DataTable isLoading emptyMessage>`)
- `compliance/PlotsPage.tsx` (usa `<DataTable isLoading emptyMessage>`)

**Pendientes identificadas (scope para fase 7)**:
- `inventory/BatchesPage.tsx`, `inventory/SerialsPage.tsx`, `inventory/WarehousesPage.tsx`, `inventory/CustomersPage.tsx`/`PartnersPage.tsx` — tienen `Cargando…` textual pero fuera del alcance pudimos testear; convertibles copy-paste al patrón.
- `platform/PlatformTenantDetailPage.tsx` — varias secciones con spinners pequeños (OK quedan, son sub-paneles dentro de una página ya cargada).

---

## 5. Forms migrados / auditados con RHF + zod

`zod@3.24` y `@hookform/resolvers@4.1` ya estaban en `package.json`. No se instaló nada.

| Form / Modal                                    | Estado inicial        | Acción tomada                                |
|-------------------------------------------------|-----------------------|----------------------------------------------|
| `components/assets/CreateAssetModal.tsx`        | Ya usaba RHF+zod      | Verificado, OK (es la referencia canónica)   |
| `components/wallets/GenerateWalletModal.tsx`    | Ya usaba RHF+zod      | Verificado, OK                               |
| `components/wallets/RegisterWalletModal.tsx`    | Ya usaba RHF+zod      | Verificado, OK                               |
| `pages/compliance/CreatePlotPage.tsx`           | Ya usaba RHF+zod      | Verificado (usa `Controller`), OK            |
| `components/assets/MintNFTModal.tsx`            | `useState` + manual   | **Migrado** — introducido schema zod, `safeParse` centraliza errores, mismo UI de errores inline |
| `pages/PlansPage.tsx` (crear/editar plan)       | `useState` + manual   | **No migrado** — flag para fase 7            |
| `pages/UsersPage.tsx` (CreateUserModal)         | `useState` + manual   | **No migrado** — flag para fase 7            |
| `pages/platform/PlatformOnboardPage.tsx`        | Wizard multi-step     | **No migrado** — requiere refactor de wizard, alto riesgo de regresión; flag para fase 7 |
| `pages/inventory/PartnerDetailPage.tsx` (NIT)   | `useState` + `required` HTML | **No migrado** — flag; sugerida regex NIT `/^\d{6,10}-?\d?$/` |

**Observación**: el proyecto ya tiene una buena base de RHF+zod; la brecha real es en modales viejos que siguen con `useState`. La migración completa de los 4 pendientes es 2-3 h adicionales.

---

## 6. Antes / Después (conceptual)

### Lista de productos (ProductsPage)
- **Antes**: `<div className="p-12 text-center text-muted-foreground">Cargando...</div>` — texto estático sin estructura, luego salto abrupto a la tabla.
- **Después**: skeleton con header y 8 filas fantasma de 6 columnas, misma anchura que la tabla real → transición visual continua, sin content shift.
- **Empty**: antes era `<Package /> + "No hay productos registrados"` con botón ad-hoc; ahora `<EmptyState icon={Package} title="Aún no tenés productos" description="Creá tu primer producto del catálogo..." action={{label:"Nuevo producto", onClick, icon: Plus}}/>` — consistente con el resto.

### Dashboard de plataforma
- **Antes**: centered spinner en `h-64` vacío.
- **Después**: skeleton de 4 KPI cards + 2 paneles + 1 tabla (forma 1:1 del layout final).

### Error en ruta
- **Antes**: crash → pantalla en blanco, usuario ve React overlay (dev) o nada (prod).
- **Después**: tarjeta con ícono amarillo, título "Algo salió mal", CTA "Recargar página" y "Reportar el problema" (mailto pre-rellenado). En dev se muestra stack trace.

---

## 7. Bugs visuales descubiertos (regla #9 — flag only, no arreglar)

1. **`ProductsPage.tsx`** (línea ~2472): el skeleton migrado reemplaza `Cargando...` del `totalEntries === 0` branch, pero fuera de la tabla principal hay un segundo `<LowStockTable>` interno que todavía tiene su propio "Cargando..." hardcodeado. No crítico, pero inconsistente.
2. **`PlatformUsersPage.tsx`**: el título de página no aparece en el código leído (¿eliminado en branch previo?) — el EmptyState asume que el usuario tiene contexto por el breadcrumb.
3. **`PlatformTenantsPage.tsx`**: al filtrar con `statusFilter` y recibir 0 resultados, el EmptyState muestra CTA "Nueva empresa" sólo si no hay filtro; cuando hay filtros, se oculta. Comportamiento correcto pero el texto genérico "Sin resultados" podría ser más específico ("Sin empresas con estado X").
4. **`MovementsPage.tsx`**: el botón de "Nuevo movimiento" dentro del EmptyState usa `onClick={() => setShowCreate(true)}` pero el modal abre siempre en el tab `purchase` — si el usuario venía filtrando por `sale`, podría confundir. Menor.
5. **`compliance/CertificatesPage.tsx` y `PlotsPage.tsx`**: siguen usando `<DataTable emptyMessage="string">` plano; no se migraron a `EmptyState` rico porque requeriría cambiar la API de `DataTable` (fuera de alcance). La UX de empty allí sigue siendo un string centrado.
6. **`Button` component del repo no soporta `asChild`** — `@base-ui/react/button`. Si se quiere consistencia total, habría que envolverlo en un wrapper que sí lo haga. Workaround usado en EmptyState: render directo de `<Link>` con clases mirror.

---

## 8. Verificación ejecutada

| Check                                                              | Resultado             |
|--------------------------------------------------------------------|-----------------------|
| `npx tsc --noEmit`                                                 | exit 0, 0 errores     |
| `npm run build` (Vite)                                             | success, 1m 4s        |
| grep `.toLocale*('es'[,)]` en `src/`                               | 0 matches             |
| ErrorBoundary wiring en App + Layout                               | OK, `key={pathname}`  |
| Smoke visual de 3 páginas (recomendado antes de merge)             | **pendiente de QA manual** (regla #10) |

---

## 9. Archivos creados / modificados

### Creados
- `front-trace/src/components/ui/EmptyState.tsx` (NEW)
- `front-trace/src/components/ErrorBoundary.tsx` (NEW)

### Modificados (componentes foundation)
- `front-trace/src/components/ui/skeleton.tsx` — extendido con `SkeletonTable`, `SkeletonCard`, `SkeletonGrid` (backward-compatible)
- `front-trace/src/App.tsx` — wrap `<ErrorBoundary>` raíz
- `front-trace/src/components/layout/Layout.tsx` — wrap `<ErrorBoundary key={pathname}>` alrededor del `<Outlet />`

### Modificados (migraciones de página + codemod i18n)
- Los 18 archivos del codemod (listados arriba en §3)
- `front-trace/src/pages/platform/PlatformTenantsPage.tsx`
- `front-trace/src/pages/platform/PlatformDashboardPage.tsx`
- `front-trace/src/pages/platform/PlatformUsersPage.tsx`
- `front-trace/src/pages/inventory/ProductsPage.tsx`
- `front-trace/src/pages/inventory/PurchaseOrdersPage.tsx`
- `front-trace/src/pages/inventory/SalesOrdersPage.tsx`
- `front-trace/src/pages/inventory/MovementsPage.tsx`
- `front-trace/src/pages/compliance/RecordsPage.tsx`
- `front-trace/src/components/assets/MintNFTModal.tsx` — zod schema + `safeParse`

---

## 10. Recomendaciones para Fase 7

1. Migrar los 4 forms pendientes (`PlansPage`, `UsersPage::CreateUserModal`, `PlatformOnboardPage`, `PartnerDetailPage`) a RHF+zod — el patrón ya está establecido.
2. Extender `DataTable` para aceptar un `emptyState?: ReactNode` prop → permite usar `EmptyState` rico en `CertificatesPage`, `PlotsPage` y cualquier otra que use DataTable.
3. Añadir wrapper `Button.asChild` sobre `@base-ui/react/button` para no duplicar clases entre `<Button>` y `<Link>`.
4. Instalar `@sentry/react` y `Sentry.init` en `main.tsx` — el ErrorBoundary ya tiene el hook listo.
5. Aplicar el patrón skeleton+empty a las ~15 páginas pendientes (Batches, Serials, Warehouses, Customers, Partners, etc.) — es puramente mecánico.
