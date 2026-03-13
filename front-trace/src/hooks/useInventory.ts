import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  inventoryAnalyticsApi,
  inventoryAuditApi,
  inventoryBatchesApi,
  inventoryCategoriesApi,
  inventoryConfigApi,
  inventoryCycleCountsApi,
  inventoryEventConfigApi,
  inventoryEventsApi,
  inventoryImportsApi,
  inventoryLocationsApi,
  inventoryMovementTypesApi,
  inventoryMovementsApi,
  inventoryPOApi,
  inventoryProductionApi,
  inventoryProductsApi,
  inventoryRecipesApi,
  inventoryReportsApi,
  inventorySerialsApi,
  inventoryStockApi,
  inventorySuppliersApi,
  inventoryWarehouseTypesApi,
  inventoryWarehousesApi,
  inventoryCustomersApi,
  inventoryCustomerTypesApi,
  inventorySalesOrdersApi,
  inventoryVariantAttributesApi,
  inventoryVariantsApi,
  inventoryAlertsApi,
  inventoryKardexApi,
  inventoryPortalApi,
  inventoryReorderApi,
  inventoryCustomerPricesApi,
  inventoryTaxApi,
} from '@/lib/inventory-api'
import type {
  Category,
  CustomField,
  CustomMovementField,
  CustomSupplierField,
  CustomWarehouseField,
  DynamicMovementType,
  DynamicWarehouseType,
  EventSeverity,
  EventStatus,
  EventType,
  OrderType,
  Product,
  ProductType,
  SerialStatus,
  Supplier,
  SupplierType,
  Warehouse,
  WarehouseLocation,
} from '@/types/inventory'

// ─── Categories ──────────────────────────────────────────────────────────────

export function useCategories(params?: Parameters<typeof inventoryCategoriesApi.list>[0]) {
  return useQuery({
    queryKey: ['inventory', 'categories', params],
    queryFn: () => inventoryCategoriesApi.list(params),
  })
}

export function useCategory(id: string) {
  return useQuery({
    queryKey: ['inventory', 'categories', id],
    queryFn: () => inventoryCategoriesApi.get(id),
    enabled: !!id,
  })
}

export function useCreateCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryCategoriesApi.create>[0]) =>
      inventoryCategoriesApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'categories'] })
    },
  })
}

export function useUpdateCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof inventoryCategoriesApi.update>[1] }) =>
      inventoryCategoriesApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'categories'] })
    },
  })
}

export function useDeleteCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryCategoriesApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'categories'] })
    },
  })
}

// ─── Products ─────────────────────────────────────────────────────────────────

export function useProducts(params?: Parameters<typeof inventoryProductsApi.list>[0]) {
  return useQuery({
    queryKey: ['inventory', 'products', params],
    queryFn: () => inventoryProductsApi.list(params),
  })
}

export function useProduct(id: string) {
  return useQuery({
    queryKey: ['inventory', 'products', id],
    queryFn: () => inventoryProductsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Product>) => inventoryProductsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'products'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useUpdateProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Product> }) =>
      inventoryProductsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'products'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useDeleteProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryProductsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'products'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useUploadProductImage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ productId, file }: { productId: string; file: File }) =>
      inventoryProductsApi.uploadImage(productId, file),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['inventory', 'products'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'products', vars.productId] })
    },
  })
}

export function useDeleteProductImage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ productId, imageUrl }: { productId: string; imageUrl: string }) =>
      inventoryProductsApi.deleteImage(productId, imageUrl),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['inventory', 'products'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'products', vars.productId] })
    },
  })
}

// ─── Warehouses ───────────────────────────────────────────────────────────────

export function useWarehouses() {
  return useQuery({
    queryKey: ['inventory', 'warehouses'],
    queryFn: () => inventoryWarehousesApi.list(),
  })
}

export function useCreateWarehouse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Warehouse>) => inventoryWarehousesApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'warehouses'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useUpdateWarehouse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Warehouse> }) =>
      inventoryWarehousesApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'warehouses'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useDeleteWarehouse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryWarehousesApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'warehouses'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

// ─── Stock ────────────────────────────────────────────────────────────────────

export function useStockLevels(params?: Parameters<typeof inventoryStockApi.list>[0]) {
  return useQuery({
    queryKey: ['inventory', 'stock', params],
    queryFn: () => inventoryStockApi.list(params),
  })
}

export function useAssignStockLocation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ levelId, locationId }: { levelId: string; locationId: string | null }) =>
      inventoryStockApi.assignLocation(levelId, locationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'config', 'locations'] })
    },
  })
}

export function useStockByProduct(productId: string) {
  return useQuery({
    queryKey: ['inventory', 'stock', 'product', productId],
    queryFn: () => inventoryStockApi.list({ product_id: productId }),
    enabled: !!productId,
  })
}

export function useReceiveStock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryStockApi.receive>[0]) =>
      inventoryStockApi.receive(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useIssueStock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryStockApi.issue>[0]) =>
      inventoryStockApi.issue(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useTransferStock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryStockApi.transfer>[0]) =>
      inventoryStockApi.transfer(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useAdjustStock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryStockApi.adjust>[0]) =>
      inventoryStockApi.adjust(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useAdjustInStock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryStockApi.adjust_in>[0]) =>
      inventoryStockApi.adjust_in(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useAdjustOutStock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryStockApi.adjust_out>[0]) =>
      inventoryStockApi.adjust_out(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useReturnStock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryStockApi.return_stock>[0]) =>
      inventoryStockApi.return_stock(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useWasteStock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryStockApi.waste>[0]) =>
      inventoryStockApi.waste(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useInitiateTransfer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryStockApi.initiateTransfer>[0]) =>
      inventoryStockApi.initiateTransfer(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useCompleteTransfer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (movementId: string) =>
      inventoryStockApi.completeTransfer(movementId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
    onError: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
    },
  })
}

export function usePendingTransfers() {
  return useQuery({
    queryKey: ['inventory', 'movements', { movement_type: 'transfer', status: 'in_transit' }],
    queryFn: () => inventoryMovementsApi.list({ movement_type: 'transfer', status: 'in_transit' }),
  })
}

// ─── Movements ────────────────────────────────────────────────────────────────

export function useMovements(params?: Parameters<typeof inventoryMovementsApi.list>[0]) {
  return useQuery({
    queryKey: ['inventory', 'movements', params],
    queryFn: () => inventoryMovementsApi.list(params),
  })
}

// ─── Suppliers ────────────────────────────────────────────────────────────────

export function useSuppliers() {
  return useQuery({
    queryKey: ['inventory', 'suppliers'],
    queryFn: () => inventorySuppliersApi.list(),
    select: (data) => data.items,
  })
}

export function useCreateSupplier() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Supplier>) => inventorySuppliersApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'suppliers'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useUpdateSupplier() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Supplier> }) =>
      inventorySuppliersApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'suppliers'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useDeleteSupplier() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventorySuppliersApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'suppliers'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

// ─── Purchase Orders ──────────────────────────────────────────────────────────

export function usePurchaseOrders(params?: Parameters<typeof inventoryPOApi.list>[0]) {
  return useQuery({
    queryKey: ['inventory', 'pos', params],
    queryFn: () => inventoryPOApi.list(params),
  })
}

export function usePO(id: string) {
  return useQuery({
    queryKey: ['inventory', 'pos', id],
    queryFn: () => inventoryPOApi.get(id),
    enabled: !!id,
  })
}

export function useCreatePO() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryPOApi.create>[0]) =>
      inventoryPOApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'pos'] }),
  })
}

export function useUpdatePO() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      inventoryPOApi.update(id, data as Partial<import('@/types/inventory').PurchaseOrder>),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'pos'] }),
  })
}

export function useSendPO() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryPOApi.send(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'pos'] }),
  })
}

export function useConfirmPO() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryPOApi.confirm(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'pos'] }),
  })
}

export function useCancelPO() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryPOApi.cancel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'pos'] }),
  })
}

export function useReceivePO() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, lines }: { id: string; lines: Parameters<typeof inventoryPOApi.receive>[1] }) =>
      inventoryPOApi.receive(id, lines),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'pos'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useDeletePO() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryPOApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'pos'] }),
  })
}

export function useConsolidatePOs() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (po_ids: string[]) => inventoryPOApi.consolidate(po_ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'pos'] }),
  })
}

export function useConsolidationCandidates() {
  return useQuery({
    queryKey: ['inventory', 'pos', 'consolidation-candidates'],
    queryFn: () => inventoryPOApi.consolidationCandidates(),
  })
}

export function useConsolidationInfo(poId: string) {
  return useQuery({
    queryKey: ['inventory', 'pos', 'consolidation-info', poId],
    queryFn: () => inventoryPOApi.consolidationInfo(poId),
    enabled: !!poId,
  })
}

export function useDeconsolidatePO() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (poId: string) => inventoryPOApi.deconsolidate(poId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'pos'] }),
  })
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export function useInventoryAnalytics() {
  return useQuery({
    queryKey: ['inventory', 'analytics', 'overview'],
    queryFn: () => inventoryAnalyticsApi.overview(),
    staleTime: 60_000,
  })
}

// ─── Config: Product Types ────────────────────────────────────────────────────

export function useProductTypes() {
  return useQuery({
    queryKey: ['inventory', 'config', 'product-types'],
    queryFn: () => inventoryConfigApi.listProductTypes(),
    staleTime: 5 * 60_000,
  })
}

export function useCreateProductType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<ProductType>) => inventoryConfigApi.createProductType(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'config', 'product-types'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useUpdateProductType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ProductType> }) =>
      inventoryConfigApi.updateProductType(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'config', 'product-types'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useDeleteProductType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryConfigApi.deleteProductType(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'config', 'product-types'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

// ─── Config: Order Types ──────────────────────────────────────────────────────

export function useOrderTypes() {
  return useQuery({
    queryKey: ['inventory', 'config', 'order-types'],
    queryFn: () => inventoryConfigApi.listOrderTypes(),
    staleTime: 5 * 60_000,
  })
}

export function useCreateOrderType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<OrderType>) => inventoryConfigApi.createOrderType(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'order-types'] }),
  })
}

export function useUpdateOrderType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<OrderType> }) =>
      inventoryConfigApi.updateOrderType(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'order-types'] }),
  })
}

export function useDeleteOrderType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryConfigApi.deleteOrderType(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'order-types'] }),
  })
}

// ─── Config: Custom Fields ────────────────────────────────────────────────────

export function useCustomFields(productTypeId?: string) {
  return useQuery({
    queryKey: ['inventory', 'config', 'custom-fields', productTypeId],
    queryFn: () => inventoryConfigApi.listCustomFields(productTypeId),
    staleTime: 5 * 60_000,
  })
}

export function useCreateCustomField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<CustomField>) => inventoryConfigApi.createCustomField(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'custom-fields'] }),
  })
}

export function useUpdateCustomField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CustomField> }) =>
      inventoryConfigApi.updateCustomField(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'custom-fields'] }),
  })
}

export function useDeleteCustomField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryConfigApi.deleteCustomField(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'custom-fields'] }),
  })
}

// ─── Config: Supplier Types ───────────────────────────────────────────────────

export function useSupplierTypes() {
  return useQuery({
    queryKey: ['inventory', 'config', 'supplier-types'],
    queryFn: () => inventoryConfigApi.listSupplierTypes(),
    staleTime: 5 * 60_000,
  })
}

export function useCreateSupplierType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<SupplierType>) => inventoryConfigApi.createSupplierType(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'supplier-types'] }),
  })
}

export function useUpdateSupplierType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<SupplierType> }) =>
      inventoryConfigApi.updateSupplierType(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'supplier-types'] }),
  })
}

export function useDeleteSupplierType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryConfigApi.deleteSupplierType(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'supplier-types'] }),
  })
}

// ─── Config: Custom Supplier Fields ──────────────────────────────────────────

export function useSupplierFields(supplierTypeId?: string) {
  return useQuery({
    queryKey: ['inventory', 'config', 'supplier-fields', supplierTypeId],
    queryFn: () => inventoryConfigApi.listSupplierFields(supplierTypeId),
    staleTime: 5 * 60_000,
  })
}

export function useCreateSupplierField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<CustomSupplierField>) => inventoryConfigApi.createSupplierField(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'supplier-fields'] }),
  })
}

export function useUpdateSupplierField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CustomSupplierField> }) =>
      inventoryConfigApi.updateSupplierField(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'supplier-fields'] }),
  })
}

export function useDeleteSupplierField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryConfigApi.deleteSupplierField(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'supplier-fields'] }),
  })
}

// ─── Config: Custom Warehouse Fields ────────────────────────────────────────

export function useWarehouseFields(warehouseTypeId?: string) {
  return useQuery({
    queryKey: ['inventory', 'config', 'warehouse-fields', warehouseTypeId],
    queryFn: () => inventoryConfigApi.listWarehouseFields(warehouseTypeId),
    staleTime: 5 * 60_000,
  })
}

export function useCreateWarehouseField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<CustomWarehouseField>) => inventoryConfigApi.createWarehouseField(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'warehouse-fields'] }),
  })
}

export function useUpdateWarehouseField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CustomWarehouseField> }) =>
      inventoryConfigApi.updateWarehouseField(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'warehouse-fields'] }),
  })
}

export function useDeleteWarehouseField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryConfigApi.deleteWarehouseField(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'warehouse-fields'] }),
  })
}

// ─── Config: Custom Movement Fields ─────────────────────────────────────────

export function useMovementFields(movementTypeId?: string) {
  return useQuery({
    queryKey: ['inventory', 'config', 'movement-fields', movementTypeId],
    queryFn: () => inventoryConfigApi.listMovementFields(movementTypeId),
    staleTime: 5 * 60_000,
  })
}

export function useCreateMovementField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<CustomMovementField>) => inventoryConfigApi.createMovementField(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'movement-fields'] }),
  })
}

export function useUpdateMovementField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CustomMovementField> }) =>
      inventoryConfigApi.updateMovementField(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'movement-fields'] }),
  })
}

export function useDeleteMovementField() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryConfigApi.deleteMovementField(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'movement-fields'] }),
  })
}

// ─── Reports ──────────────────────────────────────────────────────────────────

export function useDownloadReport() {
  return useMutation({
    mutationFn: async ({
      type,
      dateFrom,
      dateTo,
    }: {
      type: 'products' | 'stock' | 'movements' | 'suppliers' | 'events' | 'serials' | 'batches' | 'purchase-orders'
      dateFrom?: string
      dateTo?: string
    }) => {
      let res: Response
      if (type === 'products') res = await inventoryReportsApi.downloadProducts()
      else if (type === 'stock') res = await inventoryReportsApi.downloadStock()
      else if (type === 'suppliers') res = await inventoryReportsApi.downloadSuppliers()
      else if (type === 'events') res = await inventoryReportsApi.downloadEvents(dateFrom, dateTo)
      else if (type === 'serials') res = await inventoryReportsApi.downloadSerials()
      else if (type === 'batches') res = await inventoryReportsApi.downloadBatches()
      else if (type === 'purchase-orders') res = await inventoryReportsApi.downloadPurchaseOrders(dateFrom, dateTo)
      else res = await inventoryReportsApi.downloadMovements(dateFrom, dateTo)

      if (!res.ok) throw new Error('Error descargando reporte')

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${type}-${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      URL.revokeObjectURL(url)
    },
  })
}

// ─── Imports (CSV + Demo) ────────────────────────────────────────────────────

export function useImportProductsCsv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => inventoryImportsApi.uploadCsv(file),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['inventory'] }) },
  })
}

export function useImportDemo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (industries: string[]) => inventoryImportsApi.importDemo(industries),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['inventory'] }) },
  })
}

export function useDeleteDemo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (industries: string[]) => inventoryImportsApi.deleteDemo(industries),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['inventory'] }) },
  })
}

export function useDownloadTemplate() {
  return useMutation({
    mutationFn: async (name: string) => {
      const res = await inventoryImportsApi.downloadTemplate(name)
      if (!res.ok) throw new Error('Error descargando template')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `template_${name}.csv`
      a.click()
      URL.revokeObjectURL(url)
    },
  })
}

// ─── Movement Types ──────────────────────────────────────────────────────────

export function useMovementTypes() {
  return useQuery({
    queryKey: ['inventory', 'config', 'movement-types'],
    queryFn: () => inventoryMovementTypesApi.list(),
    staleTime: 5 * 60_000,
  })
}

export function useCreateMovementType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<DynamicMovementType>) => inventoryMovementTypesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'movement-types'] }),
  })
}

export function useUpdateMovementType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<DynamicMovementType> }) =>
      inventoryMovementTypesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'movement-types'] }),
  })
}

export function useDeleteMovementType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryMovementTypesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'movement-types'] }),
  })
}

// ─── Warehouse Types ─────────────────────────────────────────────────────────

export function useWarehouseTypes() {
  return useQuery({
    queryKey: ['inventory', 'config', 'warehouse-types'],
    queryFn: () => inventoryWarehouseTypesApi.list(),
    staleTime: 5 * 60_000,
  })
}

export function useCreateWarehouseType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<DynamicWarehouseType>) => inventoryWarehouseTypesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'warehouse-types'] }),
  })
}

export function useUpdateWarehouseType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<DynamicWarehouseType> }) =>
      inventoryWarehouseTypesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'warehouse-types'] }),
  })
}

export function useDeleteWarehouseType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryWarehouseTypesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'warehouse-types'] }),
  })
}

// ─── Warehouse Locations ─────────────────────────────────────────────────────

export function useLocations(warehouseId?: string) {
  return useQuery({
    queryKey: ['inventory', 'config', 'locations', warehouseId],
    queryFn: () => inventoryLocationsApi.list(warehouseId),
    staleTime: 5 * 60_000,
  })
}

export function useCreateLocation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<WarehouseLocation>) => inventoryLocationsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'locations'] }),
  })
}

export function useUpdateLocation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<WarehouseLocation> }) =>
      inventoryLocationsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'locations'] }),
  })
}

export function useDeleteLocation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryLocationsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'locations'] }),
  })
}

// ─── Event Config: Event Types ───────────────────────────────────────────────

export function useEventTypes() {
  return useQuery({
    queryKey: ['inventory', 'config', 'event-types'],
    queryFn: () => inventoryEventConfigApi.listEventTypes(),
    staleTime: 5 * 60_000,
  })
}

export function useCreateEventType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<EventType>) => inventoryEventConfigApi.createEventType(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'event-types'] }),
  })
}

export function useUpdateEventType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<EventType> }) =>
      inventoryEventConfigApi.updateEventType(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'event-types'] }),
  })
}

export function useDeleteEventType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryEventConfigApi.deleteEventType(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'event-types'] }),
  })
}

// ─── Event Config: Severities ────────────────────────────────────────────────

export function useEventSeverities() {
  return useQuery({
    queryKey: ['inventory', 'config', 'event-severities'],
    queryFn: () => inventoryEventConfigApi.listSeverities(),
    staleTime: 5 * 60_000,
  })
}

export function useCreateEventSeverity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<EventSeverity>) => inventoryEventConfigApi.createSeverity(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'event-severities'] }),
  })
}

export function useUpdateEventSeverity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<EventSeverity> }) =>
      inventoryEventConfigApi.updateSeverity(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'event-severities'] }),
  })
}

export function useDeleteEventSeverity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryEventConfigApi.deleteSeverity(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'event-severities'] }),
  })
}

// ─── Event Config: Statuses ──────────────────────────────────────────────────

export function useEventStatuses() {
  return useQuery({
    queryKey: ['inventory', 'config', 'event-statuses'],
    queryFn: () => inventoryEventConfigApi.listStatuses(),
    staleTime: 5 * 60_000,
  })
}

export function useCreateEventStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<EventStatus>) => inventoryEventConfigApi.createStatus(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'event-statuses'] }),
  })
}

export function useUpdateEventStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<EventStatus> }) =>
      inventoryEventConfigApi.updateStatus(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'event-statuses'] }),
  })
}

export function useDeleteEventStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryEventConfigApi.deleteStatus(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'event-statuses'] }),
  })
}

// ─── Event Config: Serial Statuses ───────────────────────────────────────────

export function useSerialStatuses() {
  return useQuery({
    queryKey: ['inventory', 'config', 'serial-statuses'],
    queryFn: () => inventoryEventConfigApi.listSerialStatuses(),
    staleTime: 5 * 60_000,
  })
}

export function useCreateSerialStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<SerialStatus>) => inventoryEventConfigApi.createSerialStatus(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'serial-statuses'] }),
  })
}

export function useUpdateSerialStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<SerialStatus> }) =>
      inventoryEventConfigApi.updateSerialStatus(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'serial-statuses'] }),
  })
}

export function useDeleteSerialStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryEventConfigApi.deleteSerialStatus(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'serial-statuses'] }),
  })
}

// ─── Events ──────────────────────────────────────────────────────────────────

export function useEvents(params?: Parameters<typeof inventoryEventsApi.list>[0]) {
  return useQuery({
    queryKey: ['inventory', 'events', params],
    queryFn: () => inventoryEventsApi.list(params),
  })
}

export function useEvent(id: string) {
  return useQuery({
    queryKey: ['inventory', 'events', id],
    queryFn: () => inventoryEventsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateEvent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => inventoryEventsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'events'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useChangeEventStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { status_id: string; notes?: string; changed_by?: string; resolved_at?: string } }) =>
      inventoryEventsApi.changeStatus(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'events'] }),
  })
}

export function useAddEventImpact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ eventId, data }: { eventId: string; data: Record<string, unknown> }) =>
      inventoryEventsApi.addImpact(eventId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'events'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
    },
  })
}

// ─── Serials ─────────────────────────────────────────────────────────────────

export function useSerials(params?: Parameters<typeof inventorySerialsApi.list>[0]) {
  return useQuery({
    queryKey: ['inventory', 'serials', params],
    queryFn: () => inventorySerialsApi.list(params),
  })
}

export function useCreateSerial() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => inventorySerialsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'serials'] }),
  })
}

export function useUpdateSerial() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      inventorySerialsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'serials'] }),
  })
}

export function useDeleteSerial() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventorySerialsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'serials'] }),
  })
}

// ─── Batches ─────────────────────────────────────────────────────────────────

export function useBatches(params?: Parameters<typeof inventoryBatchesApi.list>[0]) {
  return useQuery({
    queryKey: ['inventory', 'batches', params],
    queryFn: () => inventoryBatchesApi.list(params),
  })
}

export function useCreateBatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => inventoryBatchesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'batches'] }),
  })
}

export function useUpdateBatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      inventoryBatchesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'batches'] }),
  })
}

export function useDeleteBatch() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryBatchesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'batches'] }),
  })
}

// ─── Recipes ─────────────────────────────────────────────────────────────────

export function useRecipes() {
  return useQuery({
    queryKey: ['inventory', 'recipes'],
    queryFn: () => inventoryRecipesApi.list(),
  })
}

export function useRecipe(id: string) {
  return useQuery({
    queryKey: ['inventory', 'recipes', id],
    queryFn: () => inventoryRecipesApi.get(id),
    enabled: !!id,
  })
}

export function useCreateRecipe() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => inventoryRecipesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'recipes'] }),
  })
}

export function useUpdateRecipe() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      inventoryRecipesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'recipes'] }),
  })
}

export function useDeleteRecipe() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryRecipesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'recipes'] }),
  })
}

// ─── Production Runs ─────────────────────────────────────────────────────────

export function useProductionRuns(params?: Parameters<typeof inventoryProductionApi.list>[0]) {
  return useQuery({
    queryKey: ['inventory', 'production', params],
    queryFn: () => inventoryProductionApi.list(params),
  })
}

export function useProductionRun(id: string) {
  return useQuery({
    queryKey: ['inventory', 'production', id],
    queryFn: () => inventoryProductionApi.get(id),
    enabled: !!id,
  })
}

export function useCreateProductionRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryProductionApi.create>[0]) =>
      inventoryProductionApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'production'] }),
  })
}

export function useExecuteProductionRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryProductionApi.execute(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'production'] })
    },
  })
}

export function useFinishProductionRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryProductionApi.finish(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'production'] })
    },
  })
}

export function useApproveProductionRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryProductionApi.approve(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'production'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useRejectProductionRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, rejection_notes }: { id: string; rejection_notes: string }) =>
      inventoryProductionApi.reject(id, rejection_notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'production'] })
    },
  })
}

export function useDeleteProductionRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryProductionApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'production'] }),
  })
}

// ─── Cycle Counts ───────────────────────────────────────────────────────────

export function useCycleCounts(params?: Parameters<typeof inventoryCycleCountsApi.list>[0]) {
  return useQuery({
    queryKey: ['inventory', 'cycle-counts', params],
    queryFn: () => inventoryCycleCountsApi.list(params),
  })
}

export function useCycleCount(id: string) {
  return useQuery({
    queryKey: ['inventory', 'cycle-counts', id],
    queryFn: () => inventoryCycleCountsApi.get(id),
    enabled: !!id,
  })
}

export function useCreateCycleCount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: inventoryCycleCountsApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'cycle-counts'] }),
  })
}

export function useStartCycleCount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryCycleCountsApi.start(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'cycle-counts'] }),
  })
}

export function useRecordCount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ccId, itemId, data }: { ccId: string; itemId: string; data: { counted_qty: string; notes?: string } }) =>
      inventoryCycleCountsApi.recordCount(ccId, itemId, data),
    onSuccess: (_d, vars) => qc.invalidateQueries({ queryKey: ['inventory', 'cycle-counts', vars.ccId] }),
  })
}

export function useRecountItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ccId, itemId, data }: { ccId: string; itemId: string; data: { recount_qty: string; root_cause?: string; notes?: string } }) =>
      inventoryCycleCountsApi.recount(ccId, itemId, data),
    onSuccess: (_d, vars) => qc.invalidateQueries({ queryKey: ['inventory', 'cycle-counts', vars.ccId] }),
  })
}

export function useCompleteCycleCount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryCycleCountsApi.complete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'cycle-counts'] }),
  })
}

export function useApproveCycleCount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryCycleCountsApi.approve(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'cycle-counts'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'movements'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'analytics'] })
    },
  })
}

export function useCancelCycleCount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryCycleCountsApi.cancel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'cycle-counts'] }),
  })
}

/**
 * @todo Connect in CycleCountDetailPage IRA tab
 * Endpoint: GET /api/v1/cycle-counts/{id}/ira
 * Feature: IRA (Item Record Accuracy) metrics for a specific cycle count
 * Status: Pending UI implementation (analytics phase)
 */
export function useCycleCountIRA(id: string) {
  return useQuery({
    queryKey: ['inventory', 'cycle-counts', id, 'ira'],
    queryFn: () => inventoryCycleCountsApi.getIRA(id),
    enabled: !!id,
  })
}

/**
 * @todo Connect in new AnalyticsPage or CycleCountsPage dashboard
 * Endpoint: GET /api/v1/cycle-counts/analytics/ira-trend
 * Feature: IRA trend over time (chart data) with optional warehouse filter
 * Status: Pending UI implementation (analytics phase)
 */
export function useIRATrend(params?: { warehouse_id?: string }) {
  return useQuery({
    queryKey: ['inventory', 'cycle-counts', 'ira-trend', params],
    queryFn: () => inventoryCycleCountsApi.iraTrend(params),
    staleTime: 60_000,
  })
}

/**
 * @todo Connect in CycleCountDetailPage
 * Endpoint: GET /api/v1/cycle-counts/product-history/{productId}
 * Feature: Product-level discrepancy history across cycle counts
 * Status: Pending UI implementation (analytics phase)
 */
export function useProductDiscrepancyHistory(productId: string) {
  return useQuery({
    queryKey: ['inventory', 'cycle-counts', 'product-history', productId],
    queryFn: () => inventoryCycleCountsApi.productHistory(productId),
    enabled: !!productId,
  })
}

// ─── Audit ──────────────────────────────────────────────────────────────────

export function useInventoryAudit(params?: Parameters<typeof inventoryAuditApi.list>[0]) {
  return useQuery({
    queryKey: ['inventory', 'audit', params],
    queryFn: () => inventoryAuditApi.list(params),
  })
}

export function useEntityTimeline(resourceType: string, resourceId: string, params?: { offset?: number; limit?: number }) {
  return useQuery({
    queryKey: ['inventory', 'audit', 'timeline', resourceType, resourceId, params],
    queryFn: () => inventoryAuditApi.entityTimeline(resourceType, resourceId, params),
    enabled: !!resourceType && !!resourceId,
  })
}

// ─── Customers ────────────────────────────────────────────────────────────────

export function useCustomers(params?: Parameters<typeof inventoryCustomersApi.list>[0]) {
  return useQuery({ queryKey: ['inventory', 'customers', params], queryFn: () => inventoryCustomersApi.list(params) })
}
export function useCustomer(id: string) {
  return useQuery({ queryKey: ['inventory', 'customers', id], queryFn: () => inventoryCustomersApi.get(id), enabled: !!id })
}
export function useCustomerPrices(customerId: string | undefined) {
  return useQuery({
    queryKey: ['inventory', 'customers', customerId, 'prices'],
    queryFn: () => inventoryCustomersApi.prices(customerId!),
    enabled: !!customerId,
  })
}
export function useCreateCustomer() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryCustomersApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'customers'] }) })
}
export function useUpdateCustomer() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: ({ id, data }: { id: string; data: Partial<import('@/types/inventory').Customer> }) => inventoryCustomersApi.update(id, data), onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'customers'] }) })
}
export function useDeleteCustomer() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryCustomersApi.delete, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'customers'] }) })
}

export function useCustomerTypes() {
  return useQuery({ queryKey: ['inventory', 'customer-types'], queryFn: () => inventoryCustomerTypesApi.list() })
}
export function useCreateCustomerType() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryCustomerTypesApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'customer-types'] }) })
}
export function useUpdateCustomerType() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: ({ id, data }: { id: string; data: Partial<import('@/types/inventory').CustomerType> }) => inventoryCustomerTypesApi.update(id, data), onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'customer-types'] }) })
}
export function useDeleteCustomerType() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryCustomerTypesApi.delete, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'customer-types'] }) })
}

// ─── Sales Orders ─────────────────────────────────────────────────────────────

export function useSalesOrders(params?: Parameters<typeof inventorySalesOrdersApi.list>[0]) {
  return useQuery({ queryKey: ['inventory', 'sales-orders', params], queryFn: () => inventorySalesOrdersApi.list(params) })
}
export function useSalesOrder(id: string) {
  return useQuery({ queryKey: ['inventory', 'sales-orders', id], queryFn: () => inventorySalesOrdersApi.get(id), enabled: !!id })
}
export function useSalesOrderSummary() {
  return useQuery({ queryKey: ['inventory', 'sales-orders', 'summary'], queryFn: () => inventorySalesOrdersApi.summary() })
}
export function useCreateSalesOrder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}
export function useConfirmSalesOrder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.confirm, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}
export function usePickSalesOrder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.pick, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}
export function useShipSalesOrder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: ({ id, body }: { id: string; body?: { line_shipments?: Array<{ line_id: string; qty_shipped: number }>; shipping_info?: Record<string, unknown> } }) => inventorySalesOrdersApi.ship(id, body), onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory'] }) })
}
export function useDeliverSalesOrder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.deliver, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}
export function useReturnSalesOrder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.returnOrder, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory'] }) })
}
export function useCancelSalesOrder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.cancel, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}
export function useDeleteSalesOrder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.delete, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}
export function useRetryInvoice() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.retryInvoice, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}
export function useRetryCreditNote() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.retryCreditNote, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}
export function useStockCheck(orderId: string | undefined) {
  return useQuery({ queryKey: ['inventory', 'sales-orders', orderId, 'stock-check'], queryFn: () => inventorySalesOrdersApi.stockCheck(orderId!), enabled: !!orderId })
}
export function useUpdateLineWarehouse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, lineId, warehouseId }: { orderId: string; lineId: string; warehouseId: string }) =>
      inventorySalesOrdersApi.updateLineWarehouse(orderId, lineId, warehouseId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }),
  })
}
export function useSOReservations(orderId: string | undefined) {
  return useQuery({ queryKey: ['inventory', 'sales-orders', orderId, 'reservations'], queryFn: () => inventorySalesOrdersApi.listReservations(orderId!), enabled: !!orderId })
}
export function useApplyDiscount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { discount_pct: number; discount_reason?: string | null } }) =>
      inventorySalesOrdersApi.applyDiscount(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }),
  })
}
export function useBackorders(orderId: string | undefined) {
  return useQuery({ queryKey: ['inventory', 'sales-orders', orderId, 'backorders'], queryFn: () => inventorySalesOrdersApi.listBackorders(orderId!), enabled: !!orderId })
}
export function useConfirmBackorder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.confirmBackorder, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}

// ─── SO Approval ─────────────────────────────────────────────────────────────

export function useApproveSalesOrder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.approve, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}
export function useRejectSalesOrder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: ({ id, reason }: { id: string; reason: string }) => inventorySalesOrdersApi.reject(id, reason), onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}
export function useResubmitSalesOrder() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventorySalesOrdersApi.resubmit, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'sales-orders'] }) })
}
export function usePendingApprovals(params?: { offset?: number; limit?: number }) {
  return useQuery({ queryKey: ['inventory', 'sales-orders', 'pending-approval', params], queryFn: () => inventorySalesOrdersApi.pendingApprovals(params) })
}
export function useApprovalLog(soId?: string) {
  return useQuery({ queryKey: ['inventory', 'sales-orders', soId, 'approval-log'], queryFn: () => inventorySalesOrdersApi.approvalLog(soId!), enabled: !!soId })
}
export function useApprovalThreshold() {
  return useQuery({ queryKey: ['inventory', 'config', 'approval-threshold'], queryFn: () => inventoryConfigApi.getApprovalThreshold() })
}
export function useUpdateApprovalThreshold() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: (threshold: number | null) => inventoryConfigApi.updateApprovalThreshold(threshold), onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'config', 'approval-threshold'] }) })
}

export function useSoBatches(soId: string) {
  return useQuery({
    queryKey: ['inventory', 'sales-orders', soId, 'batches'],
    queryFn: () => inventorySalesOrdersApi.batches(soId),
    enabled: !!soId,
  })
}

// ─── Variants ─────────────────────────────────────────────────────────────────

export function useVariantAttributes() {
  return useQuery({ queryKey: ['inventory', 'variant-attributes'], queryFn: () => inventoryVariantAttributesApi.list() })
}
export function useCreateVariantAttribute() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryVariantAttributesApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'variant-attributes'] }) })
}
export function useUpdateVariantAttribute() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) => inventoryVariantAttributesApi.update(id, data), onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'variant-attributes'] }) })
}
export function useDeleteVariantAttribute() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryVariantAttributesApi.delete, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'variant-attributes'] }) })
}
export function useAddVariantOption() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: ({ attrId, data }: { attrId: string; data: Record<string, unknown> }) => inventoryVariantAttributesApi.addOption(attrId, data), onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'variant-attributes'] }) })
}

export function useProductVariants(params?: Parameters<typeof inventoryVariantsApi.list>[0]) {
  return useQuery({ queryKey: ['inventory', 'variants', params], queryFn: () => inventoryVariantsApi.list(params) })
}
export function useProductVariantsForProduct(productId: string | undefined) {
  return useQuery({ queryKey: ['inventory', 'variants', 'by-product', productId], queryFn: () => inventoryVariantsApi.listForProduct(productId!), enabled: !!productId })
}
export function useCreateVariant() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryVariantsApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'variants'] }) })
}
export function useUpdateVariant() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) => inventoryVariantsApi.update(id, data), onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'variants'] }) })
}
export function useDeleteVariant() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryVariantsApi.delete, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'variants'] }) })
}

// ─── Stock Alerts ─────────────────────────────────────────────────────────────

export function useStockAlerts(params?: Parameters<typeof inventoryAlertsApi.list>[0]) {
  return useQuery({ queryKey: ['inventory', 'alerts', params], queryFn: () => inventoryAlertsApi.list(params) })
}
export function useUnreadAlertCount() {
  return useQuery({ queryKey: ['inventory', 'alerts', 'unread'], queryFn: () => inventoryAlertsApi.unreadCount(), refetchInterval: 30_000 })
}
export function useMarkAlertRead() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryAlertsApi.markRead, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'alerts'] }) })
}
export function useResolveAlert() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryAlertsApi.resolve, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'alerts'] }) })
}
export function useScanAlerts() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryAlertsApi.scan, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'alerts'] }) })
}

// ─── Kardex ───────────────────────────────────────────────────────────────────

export function useKardex(productId: string, warehouseId?: string) {
  return useQuery({ queryKey: ['inventory', 'kardex', productId, warehouseId], queryFn: () => inventoryKardexApi.get(productId, warehouseId), enabled: !!productId })
}

// ─── QC (Quality Control) ─────────────────────────────────────────────────────

export function useQCApprove() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryStockApi.qcApprove>[0]) =>
      inventoryStockApi.qcApprove(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
    },
  })
}

export function useQCReject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Parameters<typeof inventoryStockApi.qcReject>[0]) =>
      inventoryStockApi.qcReject(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'stock'] })
    },
  })
}

// ─── Warehouse Occupation ─────────────────────────────────────────────────────

export function useWarehouseOccupation(warehouseId?: string) {
  return useQuery({
    queryKey: ['analytics', 'occupation', warehouseId],
    queryFn: () => inventoryAnalyticsApi.occupation(warehouseId),
  })
}

export function useABCClassification(months = 12) {
  return useQuery({
    queryKey: ['inventory', 'analytics', 'abc', months],
    queryFn: () => inventoryAnalyticsApi.abc(months),
    staleTime: 60_000,
  })
}

/**
 * @todo Connect in ReorderConfigPage or new AnalyticsPage
 * Endpoint: GET /api/v1/analytics/eoq
 * Feature: Economic Order Quantity calculation for all products
 * Status: Pending UI implementation (analytics phase)
 */
export function useEOQ(orderingCost: number, holdingCostPct: number, enabled = true) {
  return useQuery({
    queryKey: ['inventory', 'analytics', 'eoq', orderingCost, holdingCostPct],
    queryFn: () => inventoryAnalyticsApi.eoq(orderingCost, holdingCostPct),
    staleTime: 60_000,
    enabled,
  })
}

export function useStockPolicy() {
  return useQuery({
    queryKey: ['inventory', 'analytics', 'stock-policy'],
    queryFn: () => inventoryAnalyticsApi.stockPolicy(),
    staleTime: 60_000,
  })
}

export function useStorageValuation() {
  return useQuery({
    queryKey: ['inventory', 'analytics', 'storage-valuation'],
    queryFn: () => inventoryAnalyticsApi.storageValuation(),
    staleTime: 60_000,
  })
}

// ─── Auto Reorder ────────────────────────────────────────────────────────────

export function useReorderConfig() {
  return useQuery({ queryKey: ['inventory', 'reorder', 'config'], queryFn: () => inventoryReorderApi.config() })
}
export function useCheckAllReorder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: inventoryReorderApi.checkAll,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'reorder'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'purchase-orders'] })
    },
  })
}
export function useCheckProductReorder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: inventoryReorderApi.checkProduct,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory', 'reorder'] })
      qc.invalidateQueries({ queryKey: ['inventory', 'purchase-orders'] })
    },
  })
}

// ─── Portal (customer-facing) ─────────────────────────────────────────────────

export function usePortalStock(customerId: string) {
  return useQuery({
    queryKey: ['inventory', 'portal', customerId, 'stock'],
    queryFn: () => inventoryPortalApi.getStock(customerId),
    enabled: !!customerId,
  })
}

export function usePortalOrders(customerId: string, status?: string) {
  return useQuery({
    queryKey: ['inventory', 'portal', customerId, 'orders', status],
    queryFn: () => inventoryPortalApi.getOrders(customerId, status),
    enabled: !!customerId,
  })
}

export function usePortalOrderDetail(orderId: string, customerId: string) {
  return useQuery({
    queryKey: ['inventory', 'portal', customerId, 'orders', orderId],
    queryFn: () => inventoryPortalApi.getOrderDetail(orderId, customerId),
    enabled: !!orderId && !!customerId,
  })
}

// ─── Customer Special Prices ──────────────────────────────────────────────────

export function useCustomerSpecialPrices(params?: { customer_id?: string; product_id?: string; is_active?: boolean }) {
  return useQuery({ queryKey: ['inventory', 'customer-prices', params], queryFn: () => inventoryCustomerPricesApi.list(params) })
}
export function useCustomerPriceDetail(id: string) {
  return useQuery({ queryKey: ['inventory', 'customer-prices', id], queryFn: () => inventoryCustomerPricesApi.get(id), enabled: !!id })
}
export function useCustomerPricesForCustomer(customerId: string) {
  return useQuery({ queryKey: ['inventory', 'customer-prices', 'customer', customerId], queryFn: () => inventoryCustomerPricesApi.forCustomer(customerId), enabled: !!customerId })
}
export function useCustomerPricesForProduct(productId: string) {
  return useQuery({ queryKey: ['inventory', 'customer-prices', 'product', productId], queryFn: () => inventoryCustomerPricesApi.forProduct(productId), enabled: !!productId })
}
export function usePriceLookup() {
  return useMutation({ mutationFn: inventoryCustomerPricesApi.lookup })
}
export function useCreateCustomerPrice() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryCustomerPricesApi.create, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'customer-prices'] }) })
}
export function useDeactivateCustomerPrice() {
  const qc = useQueryClient()
  return useMutation({ mutationFn: inventoryCustomerPricesApi.deactivate, onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'customer-prices'] }) })
}
export function useCustomerPriceHistory(params?: { customer_id?: string; product_id?: string }) {
  return useQuery({ queryKey: ['inventory', 'customer-prices', 'history', params], queryFn: () => inventoryCustomerPricesApi.history(params), enabled: !!(params?.customer_id || params?.product_id) })
}
export function useCustomerPriceMetrics() {
  return useQuery({ queryKey: ['inventory', 'customer-prices', 'metrics'], queryFn: () => inventoryCustomerPricesApi.metrics() })
}

// ─── Tax Rates ──────────────────────────────────────────────────────────────

export function useTaxRates(params?: { tax_type?: string; is_active?: boolean }) {
  return useQuery({
    queryKey: ['inventory', 'tax-rates', params],
    queryFn: () => inventoryTaxApi.list(params),
  })
}

export function useTaxSummary() {
  return useQuery({
    queryKey: ['inventory', 'tax-rates', 'summary'],
    queryFn: () => inventoryTaxApi.summary(),
  })
}

export function useCreateTaxRate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: inventoryTaxApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'tax-rates'] }),
  })
}

export function useUpdateTaxRate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      inventoryTaxApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'tax-rates'] }),
  })
}

export function useDeactivateTaxRate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => inventoryTaxApi.deactivate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'tax-rates'] }),
  })
}

export function useInitializeTaxRates() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => inventoryTaxApi.initialize(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inventory', 'tax-rates'] }),
  })
}
