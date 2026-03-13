import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { DashboardPage } from '@/pages/DashboardPage'
import { WalletsPage } from '@/pages/WalletsPage'
import { AssetsPage } from '@/pages/AssetsPage'
import { AssetDetailPage } from '@/pages/AssetDetailPage'
import { SystemPage } from '@/pages/SystemPage'
import { TaxonomyPage } from '@/pages/TaxonomyPage'
import { OrganizationDetailPage } from '@/pages/OrganizationDetailPage'
import { TrackingBoardPage } from '@/pages/TrackingBoardPage'
import { WalletDetailPage } from '@/pages/WalletDetailPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { HelpPage } from '@/pages/HelpPage'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { UsersPage } from '@/pages/UsersPage'
import { RolesPage } from '@/pages/RolesPage'
import { AuditPage } from '@/pages/AuditPage'
import { SubscriptionsPage } from '@/pages/SubscriptionsPage'
import { SubscriptionDetailPage } from '@/pages/SubscriptionDetailPage'
import { PlansPage } from '@/pages/PlansPage'
import { MarketplacePage } from '@/pages/MarketplacePage'
import { PaymentsPage } from '@/pages/PaymentsPage'
import { CheckoutPage } from '@/pages/CheckoutPage'
import { AcceptInvitationPage } from '@/pages/AcceptInvitationPage'
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage'
import { ResetPasswordPage } from '@/pages/ResetPasswordPage'
import { EmailTemplatesPage } from '@/pages/EmailTemplatesPage'
import { EmailProvidersPage } from '@/pages/EmailProvidersPage'
import { InventoryDashboardPage } from '@/pages/inventory/InventoryDashboardPage'
import { ProductsPage } from '@/pages/inventory/ProductsPage'
import { WarehousesPage } from '@/pages/inventory/WarehousesPage'
import { WarehouseDetailPage } from '@/pages/inventory/WarehouseDetailPage'
import { MovementsPage } from '@/pages/inventory/MovementsPage'
import { SuppliersPage } from '@/pages/inventory/SuppliersPage'
import { PurchaseOrdersPage } from '@/pages/inventory/PurchaseOrdersPage'
import { InventoryConfigPage } from '@/pages/inventory/InventoryConfigPage'
import { ConfigSectionPage } from '@/pages/inventory/ConfigSectionPage'
import { ProductTypeListPage } from '@/pages/inventory/ProductTypeListPage'
import { ProductTypeDetailPage } from '@/pages/inventory/ProductTypeDetailPage'
import { SupplierTypeListPage } from '@/pages/inventory/SupplierTypeListPage'
import { SupplierTypeDetailPage } from '@/pages/inventory/SupplierTypeDetailPage'
import { WarehouseTypeListPage } from '@/pages/inventory/WarehouseTypeListPage'
import { WarehouseTypeDetailPage } from '@/pages/inventory/WarehouseTypeDetailPage'
import { MovementTypeListPage } from '@/pages/inventory/MovementTypeListPage'
import { MovementTypeDetailPage } from '@/pages/inventory/MovementTypeDetailPage'
import { InventoryReportsPage } from '@/pages/inventory/InventoryReportsPage'
import { EventsPage } from '@/pages/inventory/EventsPage'
import { SerialsPage } from '@/pages/inventory/SerialsPage'
import { BatchesPage } from '@/pages/inventory/BatchesPage'
import { RecipesPage } from '@/pages/inventory/RecipesPage'
import { ProductionPage } from '@/pages/inventory/ProductionPage'
import { PurchaseOrderDetailPage } from '@/pages/inventory/PurchaseOrderDetailPage'
import { CycleCountsPage } from '@/pages/inventory/CycleCountsPage'
import { CycleCountDetailPage } from '@/pages/inventory/CycleCountDetailPage'
import { InventoryHelpPage } from '@/pages/inventory/InventoryHelpPage'
import { InventoryAuditPage } from '@/pages/inventory/InventoryAuditPage'
import { CustomersPage } from '@/pages/inventory/CustomersPage'
import { SalesOrdersPage } from '@/pages/inventory/SalesOrdersPage'
import { PendingApprovalsPage } from '@/pages/inventory/PendingApprovalsPage'
import { SalesOrderDetailPage } from '@/pages/inventory/SalesOrderDetailPage'
import { AlertsPage } from '@/pages/inventory/AlertsPage'
import { KardexPage } from '@/pages/inventory/KardexPage'
import { VariantsPage } from '@/pages/inventory/VariantsPage'
import { ScannerPage } from '@/pages/inventory/ScannerPage'
import { PickingPage } from '@/pages/inventory/PickingPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { CustomerDetailPage } from '@/pages/inventory/CustomerDetailPage'
import { CustomerPortalPage } from '@/pages/inventory/CustomerPortalPage'
import { EInvoicingPage } from '@/pages/EInvoicingPage'
import { EInvoicingSandboxPage } from '@/pages/EInvoicingSandboxPage'
import { EInvoicingResolutionPage } from '@/pages/EInvoicingResolutionPage'
import { CategoriesPage } from '@/pages/inventory/CategoriesPage'
import { TaxRatesPage } from '@/pages/inventory/TaxRatesPage'
import { ReorderConfigPage } from '@/pages/inventory/ReorderConfigPage'
import { CustomerPricesPage } from '@/pages/inventory/CustomerPricesPage'
import { ModuleGuard } from '@/components/inventory/ModuleGuard'
import { PlatformDashboardPage } from '@/pages/platform/PlatformDashboardPage'
import { PlatformTenantsPage } from '@/pages/platform/PlatformTenantsPage'
import { PlatformTenantDetailPage } from '@/pages/platform/PlatformTenantDetailPage'
import { PlatformAnalyticsPage } from '@/pages/platform/PlatformAnalyticsPage'
import { PlatformMarketplacePage } from '@/pages/platform/PlatformMarketplacePage'
import { PlatformSalesPage } from '@/pages/platform/PlatformSalesPage'
import { PlatformTeamPage } from '@/pages/platform/PlatformTeamPage'
import { PlatformOnboardPage } from '@/pages/platform/PlatformOnboardPage'
import { PlatformUsersPage } from '@/pages/platform/PlatformUsersPage'

const router = createBrowserRouter([
  // ─── Public routes (no layout) ──────────────────────────────────────────────
  { path: '/login',              element: <LoginPage /> },
  { path: '/register',           element: <RegisterPage /> },
  { path: '/accept-invitation',  element: <AcceptInvitationPage /> },
  { path: '/forgot-password',    element: <ForgotPasswordPage /> },
  { path: '/reset-password',     element: <ResetPasswordPage /> },

  // ─── Protected routes (with layout) ─────────────────────────────────────────
  {
    path: '/',
    element: <ProtectedRoute><Layout /></ProtectedRoute>,
    children: [
      { index: true,                  element: <DashboardPage /> },
      { path: 'wallets',              element: <WalletsPage /> },
      { path: 'wallets/:id',          element: <WalletDetailPage /> },
      { path: 'assets',               element: <AssetsPage /> },
      { path: 'assets/:id',           element: <AssetDetailPage /> },
      { path: 'organizations',        element: <TaxonomyPage /> },
      { path: 'organizations/:id',    element: <OrganizationDetailPage /> },
      { path: 'tracking',             element: <TrackingBoardPage /> },
      {
        path: 'system',
        element: (
          <ProtectedRoute superuserOnly>
            <SystemPage />
          </ProtectedRoute>
        ),
      },
      { path: 'settings',             element: <Navigate to="/platform/blockchain" replace /> },
      { path: 'help',                 element: <HelpPage /> },
      { path: 'help/:section',        element: <HelpPage /> },
      { path: 'profile',              element: <ProfilePage /> },

      // ── Mi Equipo (tenant team admin) ──────────────────────────────────────
      {
        path: 'equipo/usuarios',
        element: (
          <ProtectedRoute permission="admin.users">
            <UsersPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'equipo/roles',
        element: (
          <ProtectedRoute permission="admin.roles">
            <RolesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'equipo/auditoria',
        element: (
          <ProtectedRoute permission="admin.audit">
            <AuditPage />
          </ProtectedRoute>
        ),
      },

      // ── Mi Empresa (tenant self-service) ───────────────────────────────────
      {
        path: 'empresa/suscripcion',
        element: (
          <ProtectedRoute permission="subscription.view">
            <SubscriptionDetailPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'empresa/plantillas',
        element: (
          <ProtectedRoute permission="email.view">
            <EmailTemplatesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'empresa/correo',
        element: (
          <ProtectedRoute permission="email.manage">
            <EmailProvidersPage />
          </ProtectedRoute>
        ),
      },

      // ── Backward-compat redirects ──────────────────────────────────────────
      { path: 'admin/users',            element: <Navigate to="/equipo/usuarios" replace /> },
      { path: 'admin/roles',            element: <Navigate to="/equipo/roles" replace /> },
      { path: 'admin/audit',            element: <Navigate to="/equipo/auditoria" replace /> },
      { path: 'admin/subscriptions',    element: <Navigate to="/empresa/suscripcion" replace /> },
      { path: 'admin/subscriptions/:tenantId', element: <Navigate to="/empresa/suscripcion" replace /> },
      { path: 'admin/plans',            element: <Navigate to="/platform/plans" replace /> },
      { path: 'admin/email-templates',  element: <Navigate to="/empresa/plantillas" replace /> },
      { path: 'admin/email-providers',  element: <Navigate to="/empresa/correo" replace /> },
      { path: 'pagos',                  element: <Navigate to="/platform/payments" replace /> },

      // ── Marketplace & checkout ─────────────────────────────────────────────
      { path: 'marketplace', element: <MarketplacePage /> },
      { path: 'checkout',    element: <CheckoutPage /> },

      // ── Facturación Electrónica (requires inventory + electronic-invoicing) ─
      {
        path: 'facturacion-electronica',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><EInvoicingPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'facturacion-electronica-sandbox',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><EInvoicingSandboxPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'facturacion-electronica/resolucion',
        element: (
          <ProtectedRoute permission="integrations.manage">
            <ModuleGuard><EInvoicingResolutionPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },

      // ── Plataforma (superuser only) ────────────────────────────────────────
      {
        path: 'platform',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformDashboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/tenants',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformTenantsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/tenants/:tenantId',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformTenantDetailPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/analytics',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformAnalyticsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/marketplace',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformMarketplacePage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/sales',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformSalesPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/team',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformTeamPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/onboard',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformOnboardPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/plans',
        element: (
          <ProtectedRoute superuserOnly>
            <PlansPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/subscriptions',
        element: (
          <ProtectedRoute superuserOnly>
            <SubscriptionsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/subscriptions/:tenantId',
        element: (
          <ProtectedRoute superuserOnly>
            <SubscriptionDetailPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/users',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformUsersPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/payments',
        element: (
          <ProtectedRoute superuserOnly>
            <PaymentsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/blockchain',
        element: (
          <ProtectedRoute superuserOnly>
            <SettingsPage />
          </ProtectedRoute>
        ),
      },

      // ── Inventario (module-gated) ──────────────────────────────────────────
      {
        path: 'inventario',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><InventoryDashboardPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/ayuda',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><InventoryHelpPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/ayuda/:section',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><InventoryHelpPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/productos',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><ProductsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/bodegas',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><WarehousesPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/bodegas/:id',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><WarehouseDetailPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/movimientos',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><MovementsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/proveedores',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><SuppliersPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/compras',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><PurchaseOrdersPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/compras/:id',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><PurchaseOrderDetailPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/categorias',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><CategoriesPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
{
        path: 'inventario/configuracion',
        element: (
          <ProtectedRoute permission="inventory.config">
            <ModuleGuard><InventoryConfigPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/configuracion/tipos-producto',
        element: (
          <ProtectedRoute permission="inventory.config">
            <ModuleGuard><ProductTypeListPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/configuracion/tipos-producto/:id',
        element: (
          <ProtectedRoute permission="inventory.config">
            <ModuleGuard><ProductTypeDetailPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/configuracion/tipos-proveedor',
        element: (
          <ProtectedRoute permission="inventory.config">
            <ModuleGuard><SupplierTypeListPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/configuracion/tipos-proveedor/:id',
        element: (
          <ProtectedRoute permission="inventory.config">
            <ModuleGuard><SupplierTypeDetailPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/configuracion/tipos-bodega',
        element: (
          <ProtectedRoute permission="inventory.config">
            <ModuleGuard><WarehouseTypeListPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/configuracion/tipos-bodega/:id',
        element: (
          <ProtectedRoute permission="inventory.config">
            <ModuleGuard><WarehouseTypeDetailPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/configuracion/tipos-movimiento',
        element: (
          <ProtectedRoute permission="inventory.config">
            <ModuleGuard><MovementTypeListPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/configuracion/tipos-movimiento/:id',
        element: (
          <ProtectedRoute permission="inventory.config">
            <ModuleGuard><MovementTypeDetailPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/configuracion/impuestos',
        element: (
          <ProtectedRoute permission="inventory.manage">
            <ModuleGuard><TaxRatesPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/configuracion/:section',
        element: (
          <ProtectedRoute permission="inventory.config">
            <ModuleGuard><ConfigSectionPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/eventos',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><EventsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/seriales',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><SerialsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/lotes',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><BatchesPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/recetas',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><RecipesPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/produccion',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><ProductionPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/conteos',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><CycleCountsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/conteos/:id',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><CycleCountDetailPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/clientes',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><CustomersPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/clientes/:id',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><CustomerDetailPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/portal/:customerId',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><CustomerPortalPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/escaner',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><ScannerPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/picking',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><PickingPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/aprobaciones',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><PendingApprovalsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/ventas',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><SalesOrdersPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/ventas/:id',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><SalesOrderDetailPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/precios-clientes',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><CustomerPricesPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/alertas',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><AlertsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/kardex',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><KardexPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/variantes',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><VariantsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/reorden',
        element: (
          <ProtectedRoute permission="inventory.manage">
            <ModuleGuard><ReorderConfigPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/reportes',
        element: (
          <ProtectedRoute permission="reports.view">
            <ModuleGuard><InventoryReportsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/auditoria',
        element: (
          <ProtectedRoute permission="admin.audit">
            <ModuleGuard><InventoryAuditPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },

  // ─── Global 404 (outside layout) ────────────────────────────────────────────
  { path: '*', element: <NotFoundPage /> },
])

export default function App() {
  return <RouterProvider router={router} />
}
