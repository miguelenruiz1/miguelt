import React, { Suspense, lazy } from 'react'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'

// Helper for named exports — avoids the verbose .then(m => ({default: m.X})) repetition.
const named = <K extends string>(loader: () => Promise<Record<K, React.ComponentType<unknown>>>, key: K) =>
  lazy(() => loader().then((m) => ({ default: m[key] })))

// ── Auth pages (lazy) ───────────────────────────────────────────────────────
const LoginPage = named(() => import('@/pages/LoginPage'), 'LoginPage')
const RegisterPage = named(() => import('@/pages/RegisterPage'), 'RegisterPage')
const AcceptInvitationPage = named(() => import('@/pages/AcceptInvitationPage'), 'AcceptInvitationPage')
const ForgotPasswordPage = named(() => import('@/pages/ForgotPasswordPage'), 'ForgotPasswordPage')
const ResetPasswordPage = named(() => import('@/pages/ResetPasswordPage'), 'ResetPasswordPage')
const ProfilePage = named(() => import('@/pages/ProfilePage'), 'ProfilePage')
const OnboardingPage = named(() => import('@/pages/OnboardingPage'), 'OnboardingPage')

// ── Logistics pages (lazy) ──────────────────────────────────────────────────
const DashboardPage = named(() => import('@/pages/DashboardPage'), 'DashboardPage')
const WalletsPage = named(() => import('@/pages/WalletsPage'), 'WalletsPage')
const WalletDetailPage = named(() => import('@/pages/WalletDetailPage'), 'WalletDetailPage')
const AssetsPage = named(() => import('@/pages/AssetsPage'), 'AssetsPage')
const AssetDetailPage = named(() => import('@/pages/AssetDetailPage'), 'AssetDetailPage')
const SystemPage = named(() => import('@/pages/SystemPage'), 'SystemPage')
const TaxonomyPage = named(() => import('@/pages/TaxonomyPage'), 'TaxonomyPage')
const OrganizationDetailPage = named(() => import('@/pages/OrganizationDetailPage'), 'OrganizationDetailPage')
const TrackingBoardPage = named(() => import('@/pages/TrackingBoardPage'), 'TrackingBoardPage')
const WorkflowBuilderPage = named(() => import('@/pages/WorkflowBuilderPage'), 'WorkflowBuilderPage')
const PublicVerifyPage = lazy(() => import('@/pages/PublicVerifyPage'))
const NotFoundPage = named(() => import('@/pages/NotFoundPage'), 'NotFoundPage')

// ── Admin pages (lazy) ──────────────────────────────────────────────────────
const UsersPage = named(() => import('@/pages/UsersPage'), 'UsersPage')
const RolesPage = named(() => import('@/pages/RolesPage'), 'RolesPage')
const AuditPage = named(() => import('@/pages/AuditPage'), 'AuditPage')
const EmailProvidersPage = named(() => import('@/pages/EmailProvidersPage'), 'EmailProvidersPage')

// ── Subscription / commerce pages (lazy) ────────────────────────────────────
const SubscriptionsPage = named(() => import('@/pages/SubscriptionsPage'), 'SubscriptionsPage')
const SubscriptionDetailPage = named(() => import('@/pages/SubscriptionDetailPage'), 'SubscriptionDetailPage')
const PlansPage = named(() => import('@/pages/PlansPage'), 'PlansPage')
const MarketplacePage = named(() => import('@/pages/MarketplacePage'), 'MarketplacePage')
const PaymentsPage = named(() => import('@/pages/PaymentsPage'), 'PaymentsPage')
const CheckoutPage = named(() => import('@/pages/CheckoutPage'), 'CheckoutPage')
const CheckoutResultPage = named(() => import('@/pages/CheckoutResultPage'), 'CheckoutResultPage')
const EInvoicingPage = named(() => import('@/pages/EInvoicingPage'), 'EInvoicingPage')
const EInvoicingSandboxPage = named(() => import('@/pages/EInvoicingSandboxPage'), 'EInvoicingSandboxPage')
const EInvoicingResolutionPage = named(() => import('@/pages/EInvoicingResolutionPage'), 'EInvoicingResolutionPage')

// ── Inventory pages (lazy) ──────────────────────────────────────────────────
const InventoryDashboardPage = named(() => import('@/pages/inventory/InventoryDashboardPage'), 'InventoryDashboardPage')
const ProductsPage = named(() => import('@/pages/inventory/ProductsPage'), 'ProductsPage')
const WarehousesPage = named(() => import('@/pages/inventory/WarehousesPage'), 'WarehousesPage')
const WarehouseDetailPage = named(() => import('@/pages/inventory/WarehouseDetailPage'), 'WarehouseDetailPage')
const MovementsPage = named(() => import('@/pages/inventory/MovementsPage'), 'MovementsPage')
const PurchaseOrdersPage = named(() => import('@/pages/inventory/PurchaseOrdersPage'), 'PurchaseOrdersPage')
const PurchaseOrderDetailPage = named(() => import('@/pages/inventory/PurchaseOrderDetailPage'), 'PurchaseOrderDetailPage')
const InventoryConfigPage = named(() => import('@/pages/inventory/InventoryConfigPage'), 'InventoryConfigPage')
const ConfigSectionPage = named(() => import('@/pages/inventory/ConfigSectionPage'), 'ConfigSectionPage')
const ProductTypeListPage = named(() => import('@/pages/inventory/ProductTypeListPage'), 'ProductTypeListPage')
const ProductTypeDetailPage = named(() => import('@/pages/inventory/ProductTypeDetailPage'), 'ProductTypeDetailPage')
const SupplierTypeListPage = named(() => import('@/pages/inventory/SupplierTypeListPage'), 'SupplierTypeListPage')
const SupplierTypeDetailPage = named(() => import('@/pages/inventory/SupplierTypeDetailPage'), 'SupplierTypeDetailPage')
const WarehouseTypeListPage = named(() => import('@/pages/inventory/WarehouseTypeListPage'), 'WarehouseTypeListPage')
const WarehouseTypeDetailPage = named(() => import('@/pages/inventory/WarehouseTypeDetailPage'), 'WarehouseTypeDetailPage')
const MovementTypeListPage = named(() => import('@/pages/inventory/MovementTypeListPage'), 'MovementTypeListPage')
const MovementTypeDetailPage = named(() => import('@/pages/inventory/MovementTypeDetailPage'), 'MovementTypeDetailPage')
const InventoryReportsPage = named(() => import('@/pages/inventory/InventoryReportsPage'), 'InventoryReportsPage')
const EventsPage = named(() => import('@/pages/inventory/EventsPage'), 'EventsPage')
const SerialsPage = named(() => import('@/pages/inventory/SerialsPage'), 'SerialsPage')
const BatchesPage = named(() => import('@/pages/inventory/BatchesPage'), 'BatchesPage')
const RecipesPage = named(() => import('@/pages/inventory/RecipesPage'), 'RecipesPage')
const ProductionPage = named(() => import('@/pages/inventory/ProductionPage'), 'ProductionPage')
const CycleCountsPage = named(() => import('@/pages/inventory/CycleCountsPage'), 'CycleCountsPage')
const CycleCountDetailPage = named(() => import('@/pages/inventory/CycleCountDetailPage'), 'CycleCountDetailPage')
const InventoryHelpPage = named(() => import('@/pages/inventory/InventoryHelpPage'), 'InventoryHelpPage')
const InventoryAuditPage = named(() => import('@/pages/inventory/InventoryAuditPage'), 'InventoryAuditPage')
const SalesOrdersPage = named(() => import('@/pages/inventory/SalesOrdersPage'), 'SalesOrdersPage')
const PendingApprovalsPage = named(() => import('@/pages/inventory/PendingApprovalsPage'), 'PendingApprovalsPage')
const SalesOrderDetailPage = named(() => import('@/pages/inventory/SalesOrderDetailPage'), 'SalesOrderDetailPage')
const AlertsPage = named(() => import('@/pages/inventory/AlertsPage'), 'AlertsPage')
const KardexPage = named(() => import('@/pages/inventory/KardexPage'), 'KardexPage')
const VariantsPage = named(() => import('@/pages/inventory/VariantsPage'), 'VariantsPage')
const ScannerPage = named(() => import('@/pages/inventory/ScannerPage'), 'ScannerPage')
const PickingPage = named(() => import('@/pages/inventory/PickingPage'), 'PickingPage')
const CustomerDetailPage = named(() => import('@/pages/inventory/CustomerDetailPage'), 'CustomerDetailPage')
const CustomerPortalPage = named(() => import('@/pages/inventory/CustomerPortalPage'), 'CustomerPortalPage')
const CategoriesPage = named(() => import('@/pages/inventory/CategoriesPage'), 'CategoriesPage')
const TaxRatesPage = named(() => import('@/pages/inventory/TaxRatesPage'), 'TaxRatesPage')
const ReorderConfigPage = named(() => import('@/pages/inventory/ReorderConfigPage'), 'ReorderConfigPage')
const CustomerPricesPage = named(() => import('@/pages/inventory/CustomerPricesPage'), 'CustomerPricesPage')
const PnLPage = named(() => import('@/pages/inventory/PnLPage'), 'PnLPage')
const UoMPage = named(() => import('@/pages/inventory/UoMPage'), 'UoMPage')
const PartnersPage = named(() => import('@/pages/inventory/PartnersPage'), 'PartnersPage')
const PartnerDetailPage = named(() => import('@/pages/inventory/PartnerDetailPage'), 'PartnerDetailPage')

// ── Production pages (lazy, default exports) ───────────────────────────────
const ProductionDashboardPage = lazy(() => import('@/pages/production/ProductionDashboardPage'))
const EmissionsPage = lazy(() => import('@/pages/production/EmissionsPage'))
const ReceiptsPage = lazy(() => import('@/pages/production/ReceiptsPage'))
const ProductionReportsPage = lazy(() => import('@/pages/production/ProductionReportsPage'))
const ResourcesPage = lazy(() => import('@/pages/production/ResourcesPage'))
const MRPPage = lazy(() => import('@/pages/production/MRPPage'))
const TransportAnalyticsPage = lazy(() => import('@/pages/logistics/TransportAnalyticsPage'))
// ── Misc lazy ───────────────────────────────────────────────────────────────
const MediaPage = lazy(() => import('@/pages/MediaPage'))
const WebhooksPage = lazy(() => import('@/pages/WebhooksPage'))

// Guards (synchronous — used as wrappers, not pages)
import { ModuleGuard } from '@/components/inventory/ModuleGuard'
import { ComplianceGuard } from '@/components/compliance/ComplianceGuard'
import { FeatureGuard } from '@/components/inventory/FeatureGuard'

// ── Compliance pages (lazy) ────────────────────────────────────────────────
const FrameworksPage = lazy(() => import('@/pages/compliance/FrameworksPage'))
const ActivationsPage = lazy(() => import('@/pages/compliance/ActivationsPage'))
const PlotsPage = lazy(() => import('@/pages/compliance/PlotsPage'))
const PlotDetailPage = named(() => import('@/pages/compliance/PlotDetailPage'), 'PlotDetailPage')
const RecordsPage = lazy(() => import('@/pages/compliance/RecordsPage'))
const RecordDetailPage = lazy(() => import('@/pages/compliance/RecordDetailPage'))
const CertificatesPage = lazy(() => import('@/pages/compliance/CertificatesPage'))
const VerifyCertificatePage = lazy(() => import('@/pages/compliance/VerifyCertificatePage'))
const ComplianceIntegrationsPage = named(() => import('@/pages/compliance/IntegrationsPage'), 'ComplianceIntegrationsPage')

// ── Platform pages (lazy) ──────────────────────────────────────────────────
const PlatformDashboardPage = named(() => import('@/pages/platform/PlatformDashboardPage'), 'PlatformDashboardPage')
const PlatformTenantsPage = named(() => import('@/pages/platform/PlatformTenantsPage'), 'PlatformTenantsPage')
const PlatformTenantDetailPage = named(() => import('@/pages/platform/PlatformTenantDetailPage'), 'PlatformTenantDetailPage')
const PlatformAnalyticsPage = named(() => import('@/pages/platform/PlatformAnalyticsPage'), 'PlatformAnalyticsPage')
const PlatformSalesPage = named(() => import('@/pages/platform/PlatformSalesPage'), 'PlatformSalesPage')
const PlatformTeamPage = named(() => import('@/pages/platform/PlatformTeamPage'), 'PlatformTeamPage')
const PlatformOnboardPage = named(() => import('@/pages/platform/PlatformOnboardPage'), 'PlatformOnboardPage')
const PlatformUsersPage = named(() => import('@/pages/platform/PlatformUsersPage'), 'PlatformUsersPage')
const PlatformAiSettingsPage = named(() => import('@/pages/platform/PlatformAiSettingsPage'), 'PlatformAiSettingsPage')
const PlatformCmsPage = named(() => import('@/pages/platform/PlatformCmsPage'), 'PlatformCmsPage')
const PlatformCmsEditorPage = named(() => import('@/pages/platform/PlatformCmsEditorPage'), 'PlatformCmsEditorPage')

// ── Other pages (lazy) ─────────────────────────────────────────────────────
const SettingsPage = named(() => import('@/pages/SettingsPage'), 'SettingsPage')
const BillingPage = named(() => import('@/pages/settings/BillingPage'), 'BillingPage')
const LandingPage = named(() => import('@/pages/LandingPage'), 'LandingPage')
const EudrLandingPage = named(() => import('@/pages/EudrLandingPage'), 'EudrLandingPage')
const CmsPublicPage = named(() => import('@/pages/CmsPublicPage'), 'CmsPublicPage')

// Critical synchronous imports (small + always needed at root)
import { PlanLimitModal } from '@/components/PlanLimitModal'

// Show landing if not logged in, dashboard if logged in
const router = createBrowserRouter([
  // ─── Landing (public) ───────────────────────────────────────────────────────
  { path: '/home',               element: <LandingPage /> },
  { path: '/eudr',               element: <EudrLandingPage /> },
  { path: '/landing',            element: <LandingPage /> },
  { path: '/p/:slug',            element: <CmsPublicPage /> },

  // ─── Public routes (no layout) ──────────────────────────────────────────────
  { path: '/login',              element: <LoginPage /> },
  { path: '/register',           element: <RegisterPage /> },
  { path: '/accept-invitation',  element: <AcceptInvitationPage /> },
  { path: '/forgot-password',    element: <ForgotPasswordPage /> },
  { path: '/reset-password',     element: <ResetPasswordPage /> },
  { path: '/verify/:certificateNumber', element: <React.Suspense fallback={null}><VerifyCertificatePage /></React.Suspense> },
  { path: '/verificar', element: <PublicVerifyPage /> },
  { path: '/verificar/:batchNumber', element: <PublicVerifyPage /> },

  // ─── Onboarding (protected, no layout) ──────────────────────────────────────
  { path: '/onboarding', element: <ProtectedRoute><OnboardingPage /></ProtectedRoute> },

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
      { path: 'media',                 element: <React.Suspense fallback={null}><MediaPage /></React.Suspense> },
      {
        path: 'system',
        element: (
          <ProtectedRoute superuserOnly>
            <SystemPage />
          </ProtectedRoute>
        ),
      },
      { path: 'settings',             element: <Navigate to="/dashboard" replace /> },
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
        path: 'empresa/correo',
        element: (
          <ProtectedRoute permission="email.manage">
            <EmailProvidersPage />
          </ProtectedRoute>
        ),
      },

      // ── Settings ───────────────────────────────────────────────────────────
      {
        path: 'settings/billing',
        element: (
          <ProtectedRoute permission="subscription.view">
            <BillingPage />
          </ProtectedRoute>
        ),
      },

      {
        path: 'empresa/webhooks',
        element: (
          <ProtectedRoute permission="subscription.view">
            <WebhooksPage />
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
      { path: 'admin/email-templates',  element: <Navigate to="/empresa/correo" replace /> },
      { path: 'admin/email-providers',  element: <Navigate to="/empresa/correo" replace /> },
      { path: 'pagos',                  element: <Navigate to="/platform/payments" replace /> },

      // ── Marketplace & checkout ─────────────────────────────────────────────
      { path: 'marketplace', element: <MarketplacePage /> },
      { path: 'checkout',        element: <CheckoutPage /> },
      { path: 'checkout/result', element: <CheckoutResultPage /> },

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
        path: 'platform/ai',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformAiSettingsPage />
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
      {
        path: 'platform/cms',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformCmsPage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'platform/cms/:pageId',
        element: (
          <ProtectedRoute superuserOnly>
            <PlatformCmsEditorPage />
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
            <ModuleGuard><FeatureGuard feature="eventos"><EventsPage /></FeatureGuard></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/seriales',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><FeatureGuard feature="seriales"><SerialsPage /></FeatureGuard></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/lotes',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><FeatureGuard feature="lotes"><BatchesPage /></FeatureGuard></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'produccion',
        element: (
          <ProtectedRoute permission="production.view">
            <ModuleGuard module="production"><ProductionDashboardPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'produccion/ordenes',
        element: (
          <ProtectedRoute permission="production.view">
            <ModuleGuard module="production"><ProductionPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'produccion/recetas',
        element: (
          <ProtectedRoute permission="production.view">
            <ModuleGuard module="production"><RecipesPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'produccion/recursos',
        element: (
          <ProtectedRoute permission="production.view">
            <ModuleGuard module="production"><ResourcesPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'produccion/mrp',
        element: (
          <ProtectedRoute permission="production.manage">
            <ModuleGuard module="production"><MRPPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'produccion/emisiones',
        element: (
          <ProtectedRoute permission="production.view">
            <ModuleGuard module="production"><EmissionsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'produccion/recibos',
        element: (
          <ProtectedRoute permission="production.view">
            <ModuleGuard module="production"><ReceiptsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'produccion/reportes',
        element: (
          <ProtectedRoute permission="production.view">
            <ModuleGuard module="production"><ProductionReportsPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/conteos',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><FeatureGuard feature="conteo"><CycleCountsPage /></FeatureGuard></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/conteos/:id',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><FeatureGuard feature="conteo"><CycleCountDetailPage /></FeatureGuard></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/socios',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><PartnersPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/socios/:id',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><PartnerDetailPage /></ModuleGuard>
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
            <ModuleGuard><FeatureGuard feature="escaner"><ScannerPage /></FeatureGuard></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/picking',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><FeatureGuard feature="picking"><PickingPage /></FeatureGuard></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/aprobaciones',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><FeatureGuard feature="aprobaciones"><PendingApprovalsPage /></FeatureGuard></ModuleGuard>
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
            <ModuleGuard><FeatureGuard feature="precios"><CustomerPricesPage /></FeatureGuard></ModuleGuard>
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
            <ModuleGuard><FeatureGuard feature="kardex"><KardexPage /></FeatureGuard></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/variantes',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><FeatureGuard feature="variantes"><VariantsPage /></FeatureGuard></ModuleGuard>
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
        path: 'inventario/rentabilidad',
        element: (
          <ProtectedRoute permission="inventory.view">
            <ModuleGuard><PnLPage /></ModuleGuard>
          </ProtectedRoute>
        ),
      },
      {
        path: 'inventario/unidades-medida',
        element: (
          <ProtectedRoute permission="inventory.manage">
            <ModuleGuard><UoMPage /></ModuleGuard>
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
      // ── Logistica (trace-service) ────────────────────────────────────────────
      {
        path: 'logistica/analiticas',
        element: <ProtectedRoute><TransportAnalyticsPage /></ProtectedRoute>,
      },
      {
        path: 'configuracion/flujo-de-trabajo',
        element: <ProtectedRoute><WorkflowBuilderPage /></ProtectedRoute>,
      },
      // ── Cumplimiento (compliance module-gated) ──────────────────────────────
      {
        path: 'cumplimiento/frameworks',
        element: (
          <React.Suspense fallback={null}>
            <ComplianceGuard><FrameworksPage /></ComplianceGuard>
          </React.Suspense>
        ),
      },
      {
        path: 'cumplimiento/activaciones',
        element: (
          <React.Suspense fallback={null}>
            <ComplianceGuard><ActivationsPage /></ComplianceGuard>
          </React.Suspense>
        ),
      },
      {
        path: 'cumplimiento/parcelas',
        element: (
          <React.Suspense fallback={null}>
            <ComplianceGuard><PlotsPage /></ComplianceGuard>
          </React.Suspense>
        ),
      },
      {
        path: 'cumplimiento/parcelas/:plotId',
        element: (
          <React.Suspense fallback={null}>
            <ComplianceGuard><PlotDetailPage /></ComplianceGuard>
          </React.Suspense>
        ),
      },
      {
        path: 'cumplimiento/registros',
        element: (
          <React.Suspense fallback={null}>
            <ComplianceGuard><RecordsPage /></ComplianceGuard>
          </React.Suspense>
        ),
      },
      {
        path: 'cumplimiento/registros/:id',
        element: (
          <React.Suspense fallback={null}>
            <ComplianceGuard><RecordDetailPage /></ComplianceGuard>
          </React.Suspense>
        ),
      },
      {
        path: 'cumplimiento/certificados',
        element: (
          <React.Suspense fallback={null}>
            <ComplianceGuard><CertificatesPage /></ComplianceGuard>
          </React.Suspense>
        ),
      },
      {
        path: 'cumplimiento/integraciones',
        element: (
          <React.Suspense fallback={null}>
            <ComplianceGuard><ComplianceIntegrationsPage /></ComplianceGuard>
          </React.Suspense>
        ),
      },

      { path: '*', element: <NotFoundPage /> },
    ],
  },

  // ─── Global 404 (outside layout) ────────────────────────────────────────────
  { path: '*', element: <NotFoundPage /> },
])

function PageFallback() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '60vh', color: '#888', fontSize: 14,
    }}>
      Cargando…
    </div>
  )
}

export default function App() {
  return (
    <>
      <Suspense fallback={<PageFallback />}>
        <RouterProvider router={router} />
      </Suspense>
      <PlanLimitModal />
    </>
  )
}
