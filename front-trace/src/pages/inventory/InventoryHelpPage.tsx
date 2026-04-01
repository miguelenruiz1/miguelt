import { useParams, NavLink } from 'react-router-dom'
import {
  BookOpen, Package, Warehouse, Boxes, ArrowLeftRight, Truck, ShoppingCart,
  ClipboardCheck, ClipboardList, AlertTriangle, Hash, Layers, Factory, FileDown,
  Settings2, ArrowRight, Info, AlertCircle, CheckCircle2,
  GitBranch, BarChart3, RefreshCw, Search, Calendar, Shield,
  Users, Receipt, DollarSign, SplitSquareVertical, Bell, BookMarked, Upload,
  Eye, ShieldCheck, Activity, Calculator, Target, Building,
  ScanBarcode, ListChecks, BadgeCheck, FolderTree, FlaskConical, FileText, CreditCard, Merge,
} from 'lucide-react'
import { Topbar } from '@/components/layout/Topbar'

// ─── Shared UI helpers (same pattern as HelpPage) ────────────────────────────

function SectionHeader({ icon: Icon, title, subtitle }: { icon: React.ElementType; title: string; subtitle: string }) {
  return (
    <div className="flex items-start gap-4 mb-8 pb-6 border-b border-border">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20/50 shrink-0">
        <Icon className="h-6 w-6 text-primary" />
      </div>
      <div>
        <h1 className="text-xl font-bold text-foreground">{title}</h1>
        <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
      </div>
    </div>
  )
}

function InfoBox({ type = 'info', children }: { type?: 'info' | 'warning' | 'success'; children: React.ReactNode }) {
  const styles = {
    info:    'bg-blue-50 border-blue-200 text-blue-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  }
  const icons = {
    info:    <Info className="h-4 w-4 shrink-0 mt-0.5" />,
    warning: <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />,
    success: <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />,
  }
  return (
    <div className={`flex gap-2.5 rounded-xl border p-3.5 text-sm ${styles[type]}`}>
      {icons[type]}
      <div>{children}</div>
    </div>
  )
}

function H2({ children }: { children: React.ReactNode }) {
  return <h2 className="text-base font-bold text-foreground mt-7 mb-3 flex items-center gap-2">{children}</h2>
}

function Pill({ children, color = 'slate' }: { children: React.ReactNode; color?: string }) {
  const colors: Record<string, string> = {
    indigo:  'bg-primary/15 text-primary',
    emerald: 'bg-emerald-100 text-emerald-700',
    amber:   'bg-amber-100 text-amber-700',
    red:     'bg-red-100 text-red-700',
    blue:    'bg-blue-100 text-blue-700',
    purple:  'bg-purple-100 text-purple-700',
    slate:   'bg-secondary text-muted-foreground',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${colors[color] ?? colors.slate}`}>
      {children}
    </span>
  )
}

// ─── Section: Overview ───────────────────────────────────────────────────────

function OverviewSection() {
  const modules = [
    { to: '/inventario/ayuda/productos',      icon: Package,              label: 'Productos',         desc: 'Crear, editar, SKU, precios, variantes y atributos custom' },
    { to: '/inventario/ayuda/variantes',       icon: SplitSquareVertical, label: 'Variantes',         desc: 'Talla, color, presentacion — variantes de producto' },
    { to: '/inventario/ayuda/bodegas',         icon: Warehouse,           label: 'Bodegas',           desc: 'Tipos de bodega, zonas, pasillos, racks y bins' },
    { to: '/inventario/ayuda/stock',           icon: Boxes,               label: 'Stock y Niveles',   desc: 'Recibir, despachar, transferir, ajustar y formulas' },
    { to: '/inventario/ayuda/movimientos',     icon: ArrowLeftRight,      label: 'Movimientos',       desc: 'Tipos, filtros, historial y reportes' },
    { to: '/inventario/ayuda/proveedores',     icon: Truck,               label: 'Proveedores',       desc: 'CRUD, tipos, campos custom y lead time' },
    { to: '/inventario/ayuda/compras',         icon: ShoppingCart,        label: 'Ordenes de Compra', desc: 'Crear OC, lineas, flujo de estados y recepcion parcial' },
    { to: '/inventario/ayuda/clientes',        icon: Users,               label: 'Clientes',          desc: 'CRUD, tipos de cliente y datos de contacto' },
    { to: '/inventario/ayuda/ventas',          icon: Receipt,             label: 'Ordenes de Venta',  desc: 'Ciclo completo: confirmar, picking, despacho, entrega' },
    { to: '/inventario/ayuda/precios',         icon: DollarSign,          label: 'Precios Especiales', desc: 'Precios especiales por cliente con vigencia y tiers' },
    { to: '/inventario/ayuda/conteo-ciclico',  icon: ClipboardCheck,      label: 'Conteo Ciclico',    desc: '6 metodologias, IRA, reconteo y causa raiz' },
    { to: '/inventario/ayuda/eventos',         icon: AlertTriangle,       label: 'Eventos',           desc: 'Crear eventos, severidades, impactos y estados' },
    { to: '/inventario/ayuda/alertas',         icon: Bell,                label: 'Alertas de Stock',  desc: 'Alertas de minimo, maximo y reorden automatico' },
    { to: '/inventario/ayuda/kardex',          icon: BookMarked,          label: 'Kardex',            desc: 'Historial valorizado de entradas y salidas por producto' },
    { to: '/inventario/ayuda/seriales',        icon: Hash,                label: 'Seriales',          desc: 'Trazabilidad unitaria, estados y ciclo de vida' },
    { to: '/inventario/ayuda/lotes',           icon: Layers,              label: 'Lotes',             desc: 'Fabricacion, vencimiento y trazabilidad por lote' },
    { to: '/inventario/ayuda/produccion',      icon: Factory,             label: 'Produccion',        desc: 'Recetas (BOM), corridas, aprobacion y costos FIFO' },
    { to: '/inventario/ayuda/control-calidad',  icon: ShieldCheck,         label: 'Control de Calidad', desc: 'Bloqueo QC, aprobacion/rechazo y flujo automatico' },
    { to: '/inventario/ayuda/ocupacion',       icon: Activity,            label: 'Ocupacion',         desc: 'KPIs de ocupacion de bodegas, ubicaciones y stock estancado' },
    { to: '/inventario/ayuda/portal-cliente',   icon: Eye,                label: 'Portal de Cliente', desc: 'Vista de solo lectura para clientes: stock y pedidos' },
    { to: '/inventario/ayuda/clasificacion-abc', icon: BarChart3,          label: 'Clasificacion ABC', desc: 'Analisis 80/15/5 por valor y rotacion de productos' },
    { to: '/inventario/ayuda/eoq',              icon: Calculator,         label: 'EOQ',               desc: 'Cantidad optima de pedido (formula de Wilson)' },
    { to: '/inventario/ayuda/politica-stock',   icon: Target,             label: 'Politica de Stock', desc: 'Meses de rotacion objetivo por tipo de producto' },
    { to: '/inventario/ayuda/costo-almacen',    icon: Building,           label: 'Costo de Almacen',  desc: 'Valuacion de costo por m², ubicacion y bodega' },
    { to: '/inventario/ayuda/impuestos',        icon: Receipt,             label: 'Impuestos',         desc: 'IVA, retención en la fuente, ICA y códigos DIAN' },
    { to: '/inventario/ayuda/precios-clientes', icon: CreditCard,         label: 'Precios Especiales', desc: 'Precios preferenciales por cliente con vigencia' },
    { to: '/inventario/ayuda/escaner',         icon: ScanBarcode,         label: 'Escáner',           desc: 'Lectura de código de barras y acciones rápidas de stock' },
    { to: '/inventario/ayuda/picking',         icon: ListChecks,          label: 'Picking',           desc: 'Cola de preparación, verificación línea por línea' },
    { to: '/inventario/ayuda/aprobaciones',    icon: BadgeCheck,          label: 'Aprobaciones',      desc: 'Aprobación de OV por monto, principio 4 ojos' },
    { to: '/inventario/ayuda/reorden',         icon: RefreshCw,           label: 'Reorden Automático', desc: 'Generación automática de POs al bajar del punto de reorden' },
    { to: '/inventario/ayuda/recetas',         icon: FlaskConical,        label: 'Recetas (BOM)',     desc: 'Composición de productos, disponibilidad de componentes' },
    { to: '/inventario/ayuda/categorias',      icon: FolderTree,          label: 'Categorías',        desc: 'Árbol jerárquico de categorías de producto' },
    { to: '/inventario/ayuda/facturacion',     icon: FileText,            label: 'Facturación Electrónica', desc: 'CUFE, DIAN, sandbox, notas crédito y remisiones' },
    { to: '/inventario/ayuda/reportes',        icon: FileDown,            label: 'Reportes',          desc: 'Descargas CSV de productos, stock, movimientos y más' },
    { to: '/inventario/ayuda/importacion',     icon: Upload,              label: 'Importacion',       desc: 'Carga masiva de productos y datos demo' },
    { to: '/inventario/ayuda/auditoria',       icon: ClipboardList,       label: 'Auditoria',         desc: 'Log de acciones, timeline por entidad y trazabilidad' },
    { to: '/inventario/ayuda/configuracion',   icon: Settings2,           label: 'Configuracion',     desc: 'Tipos, campos custom, reglas de entrada y despacho' },
  ]
  return (
    <div>
      <SectionHeader icon={BookOpen} title="Ayuda del Modulo de Inventario" subtitle="Documentacion completa de todas las funcionalidades" />
      <p className="text-sm text-muted-foreground mb-6">
        El modulo de <strong>Inventario</strong> gestiona productos, bodegas, stock, movimientos, proveedores, ordenes de compra y venta,
        clientes, precios especiales, conteo ciclico, seriales, lotes, produccion, alertas y kardex. Selecciona una seccion para ver la documentacion detallada.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {modules.map(({ to, icon: Icon, label, desc }) => (
          <NavLink
            key={to}
            to={to}
            className="flex items-start gap-3 p-4 rounded-2xl border border-border bg-card hover:border-primary/50 hover:shadow-md transition-all group"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 shrink-0">
              <Icon className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-foreground group-hover:text-primary">{label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
            </div>
            <ArrowRight className="h-4 w-4 text-slate-300 group-hover:text-primary/70 mt-1 shrink-0" />
          </NavLink>
        ))}
      </div>
    </div>
  )
}

// ─── Section: Productos ──────────────────────────────────────────────────────

function ProductosSection() {
  return (
    <div>
      <SectionHeader icon={Package} title="Productos" subtitle="Catalogo maestro de productos del inventario" />

      <InfoBox type="info">
        Cada producto tiene un <strong>SKU unico</strong> que lo identifica en todo el sistema. El SKU no puede modificarse una vez creado.
      </InfoBox>

      <H2>Crear un producto</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Inventario > Productos',
          'Click en "Nuevo producto"',
          'Completar los campos obligatorios: nombre, SKU y unidad de medida',
          'Opcionalmente asignar tipo de producto, precio, codigo de barras y limites de stock',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Campos del producto</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Tipo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['name', 'texto', 'Nombre del producto'],
              ['sku', 'texto', 'Codigo unico (no editable)'],
              ['barcode', 'texto', 'Codigo de barras (EAN, UPC, etc.)'],
              ['description', 'texto', 'Descripcion opcional'],
              ['unit_of_measure', 'texto', 'Unidad: kg, unidad, litro, caja, etc.'],
              ['price', 'decimal', 'Precio unitario (para valoracion de stock)'],
              ['cost', 'decimal', 'Costo unitario (para calculos de margen)'],
              ['min_stock', 'entero', 'Stock minimo — alerta de reabastecimiento'],
              ['max_stock', 'entero', 'Stock maximo — limite de capacidad'],
              ['reorder_point', 'entero', 'Punto de reorden — nivel para generar sugerencia de compra'],
              ['is_active', 'boolean', 'Si el producto esta activo (default: true)'],
              ['product_type_id', 'UUID', 'Tipo de producto (configurable)'],
              ['custom_attributes', 'JSONB', 'Campos personalizados segun tipo de producto'],
            ].map(([field, type, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 pr-4"><Pill>{type}</Pill></td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Tipos de producto</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Los tipos de producto permiten categorizar productos y definir <strong>campos custom</strong> por tipo.
        Se configuran en <strong>Inventario &gt; Configuracion &gt; Tipos de producto</strong>.
      </p>
      <InfoBox type="success">
        Los campos custom definidos en un tipo de producto aparecen automaticamente en el formulario de creacion/edicion
        de los productos que pertenecen a ese tipo.
      </InfoBox>

      <H2>Variantes</H2>
      <p className="text-xs text-muted-foreground">
        Un producto puede tener <strong>variantes</strong> (talla, color, presentacion). Cada variante tiene su propio SKU,
        precio y stock independiente. Ver la seccion <strong>Variantes</strong> para mas detalles.
      </p>

      <H2>Unidades de medida</H2>
      <p className="text-xs text-muted-foreground">
        Las unidades de medida mas comunes son: <Pill>kg</Pill> <Pill>unidad</Pill> <Pill>litro</Pill> <Pill>caja</Pill> <Pill>metro</Pill> <Pill>par</Pill>.
        El campo es libre — puedes escribir cualquier unidad que necesites.
      </p>
    </div>
  )
}

// ─── Section: Variantes ─────────────────────────────────────────────────────

function VariantesSection() {
  return (
    <div>
      <SectionHeader icon={SplitSquareVertical} title="Variantes de Producto" subtitle="Talla, color, presentacion y mas — variaciones de un mismo producto" />

      <InfoBox type="info">
        Las variantes permiten gestionar diferentes presentaciones de un mismo producto (ej: Camiseta Roja M, Camiseta Azul L)
        sin crear productos separados. Cada variante tiene su propio <strong>SKU, precio y stock</strong>.
      </InfoBox>

      <H2>Crear variantes</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir al detalle de un producto',
          'En la seccion "Variantes", click en "Nueva variante"',
          'Definir nombre de la variante (ej: "Rojo / M")',
          'Asignar SKU unico, precio y opcionalmente codigo de barras',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Campos de la variante</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['variant_name', 'Nombre descriptivo (ej: "500ml", "Rojo / XL")'],
              ['sku', 'SKU unico de la variante'],
              ['barcode', 'Codigo de barras de la variante'],
              ['price', 'Precio unitario (sobreescribe el del producto padre)'],
              ['cost', 'Costo unitario de la variante'],
              ['attributes', 'Atributos clave-valor (ej: { color: "rojo", talla: "M" })'],
              ['is_active', 'Si la variante esta activa'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Stock por variante</H2>
      <p className="text-xs text-muted-foreground mb-3">
        El stock se gestiona <strong>a nivel de variante</strong>. Al recibir, despachar o transferir stock,
        puedes seleccionar la variante especifica. Esto permite saber exactamente cuantas unidades
        de cada variante hay en cada bodega.
      </p>
      <InfoBox type="warning">
        Si un producto tiene variantes, los movimientos de stock deben especificar la variante.
        El stock total del producto es la suma de todas sus variantes.
      </InfoBox>

      <H2>Integracion con otros modulos</H2>
      <div className="space-y-2">
        {[
          { module: 'Ordenes de Compra', desc: 'Las lineas de OC pueden especificar variante para recibir stock correcto' },
          { module: 'Ordenes de Venta', desc: 'Cada linea de venta puede indicar variante; el stock se reserva por variante' },
          { module: 'Precios Especiales', desc: 'Los precios especiales por cliente pueden ser por variante, con precios diferenciados' },
          { module: 'Conteo Ciclico', desc: 'El conteo puede incluir variantes para verificar stock a nivel granular' },
        ].map(({ module, desc }) => (
          <div key={module} className="rounded-xl border border-border p-3">
            <p className="text-xs font-bold text-foreground">{module}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Section: Bodegas ────────────────────────────────────────────────────────

function BodegasSection() {
  return (
    <div>
      <SectionHeader icon={Warehouse} title="Bodegas" subtitle="Ubicaciones de almacenamiento del inventario" />

      <InfoBox type="info">
        Cada bodega tiene un <strong>tipo</strong> que determina su uso. La bodega principal (<Pill color="indigo">main</Pill>) es la principal
        de operaciones. Al crear el tenant, se genera automaticamente una bodega principal.
      </InfoBox>

      <H2>Tipos de bodega</H2>
      <div className="grid grid-cols-2 gap-2 mb-4">
        {[
          { type: 'main', label: 'Principal', desc: 'Bodega central de operaciones', color: 'indigo' },
          { type: 'secondary', label: 'Secundaria', desc: 'Bodega auxiliar o de apoyo', color: 'slate' },
          { type: 'virtual', label: 'Virtual', desc: 'Sin ubicacion fisica (ej: dropship)', color: 'purple' },
          { type: 'transit', label: 'Transito', desc: 'Productos en movimiento entre bodegas', color: 'amber' },
        ].map(({ type, label, desc, color }) => (
          <div key={type} className="rounded-xl border border-border p-3">
            <Pill color={color}>{type}</Pill>
            <p className="text-xs font-bold text-foreground mt-1">{label}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Crear una bodega</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Inventario > Bodegas',
          'Click en "Nueva bodega"',
          'Ingresar nombre, tipo y direccion',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Ubicaciones (zonas, pasillos, racks, bins)</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Dentro de cada bodega se pueden definir ubicaciones jerarquicas para localizar productos con mayor precision:
      </p>
      <div className="space-y-2">
        {[
          { level: 'Zona', desc: 'Area general (ej: Zona A, Zona Frio, Zona Peligrosos)', example: 'ZONA-A' },
          { level: 'Pasillo', desc: 'Pasillo dentro de la zona', example: 'ZONA-A-P01' },
          { level: 'Rack', desc: 'Estanteria dentro del pasillo', example: 'ZONA-A-P01-R03' },
          { level: 'Bin', desc: 'Posicion exacta dentro del rack', example: 'ZONA-A-P01-R03-B02' },
        ].map(({ level, desc, example }) => (
          <div key={level} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color="indigo">{level}</Pill>
            <div>
              <p className="text-xs text-muted-foreground">{desc}</p>
              <p className="text-[11px] text-muted-foreground font-mono mt-0.5">{example}</p>
            </div>
          </div>
        ))}
      </div>

      <H2><Activity className="h-4 w-4 text-primary/70" /> Ocupacion de bodega</H2>
      <p className="text-xs text-muted-foreground mb-3">
        El dashboard muestra KPIs de ocupacion para cada bodega basados en las ubicaciones definidas
        y el stock almacenado en cada una:
      </p>
      <div className="space-y-2 mb-4">
        {[
          { kpi: 'Ubicaciones totales', desc: 'Cantidad total de ubicaciones (hojas) definidas en la bodega.', color: 'slate' },
          { kpi: 'Ubicaciones ocupadas', desc: 'Ubicaciones que tienen al menos un registro de stock.', color: 'blue' },
          { kpi: 'Ubicaciones libres', desc: 'Ubicaciones sin stock asignado, disponibles para recepcion.', color: 'emerald' },
          { kpi: '% Ocupacion', desc: 'Porcentaje de ubicaciones ocupadas sobre el total. Se muestra como barra de progreso.', color: 'indigo' },
          { kpi: 'Stock estancado', desc: 'Ubicaciones con stock sin movimiento en los ultimos 90 dias.', color: 'amber' },
        ].map(({ kpi, desc, color }) => (
          <div key={kpi} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{kpi}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
      <InfoBox type="info">
        Los KPIs de ocupacion se muestran en el <strong>Dashboard de Inventario</strong> y tambien
        en la vista de detalle de cada bodega. La ocupacion por tipo de ubicacion se desglosa en barras individuales.
      </InfoBox>
    </div>
  )
}

// ─── Section: Stock ──────────────────────────────────────────────────────────

function StockSection() {
  return (
    <div>
      <SectionHeader icon={Boxes} title="Stock y Niveles" subtitle="Gestion de cantidades y niveles de inventario" />

      <InfoBox type="info">
        El stock de cada producto se calcula por bodega (y opcionalmente por variante). Un mismo producto puede tener
        cantidades diferentes en cada bodega. El stock total es la suma de todas las bodegas.
      </InfoBox>

      <H2>Operaciones de stock</H2>
      <div className="space-y-3">
        {[
          { op: 'Recibir', desc: 'Ingreso de producto a bodega (compra, devolucion, transferencia entrante)', pill: 'emerald', movement: 'receive' },
          { op: 'Despachar', desc: 'Salida de producto de bodega (venta, envio)', pill: 'red', movement: 'issue' },
          { op: 'Transferir', desc: 'Mover stock de una bodega a otra. Genera 2 movimientos: salida + entrada', pill: 'amber', movement: 'transfer' },
          { op: 'Ajustar (absoluto)', desc: 'Establecer la cantidad exacta de un producto en bodega', pill: 'purple', movement: 'adjust' },
          { op: 'Ajustar entrada', desc: 'Incrementar stock por sobrante encontrado', pill: 'blue', movement: 'adjust_in' },
          { op: 'Ajustar salida', desc: 'Decrementar stock por faltante o merma', pill: 'red', movement: 'adjust_out' },
          { op: 'Devolucion', desc: 'Ingreso por devolucion de cliente o proveedor', pill: 'slate', movement: 'return' },
          { op: 'Desperdicio', desc: 'Baja de producto danado, vencido o inutilizable', pill: 'red', movement: 'waste' },
        ].map(({ op, desc, pill, movement }) => (
          <div key={op} className="rounded-xl border border-border p-4">
            <p className="text-sm font-bold text-foreground mb-1">{op} <Pill color={pill}>{movement}</Pill></p>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2><BarChart3 className="h-4 w-4 text-primary/70" /> Niveles de stock</H2>
      <div className="space-y-2 mt-2">
        {[
          { level: 'Stock minimo', desc: 'Nivel por debajo del cual se genera alerta de reabastecimiento.', color: 'amber' },
          { level: 'Punto de reorden', desc: 'Nivel donde se sugiere crear una orden de compra al proveedor.', color: 'blue' },
          { level: 'Stock maximo', desc: 'Limite superior de almacenamiento. Evita sobre-stock.', color: 'red' },
          { level: 'Stock actual', desc: 'Cantidad real disponible en bodega.', color: 'emerald' },
          { level: 'Stock reservado', desc: 'Cantidad comprometida en ordenes de venta confirmadas.', color: 'purple' },
        ].map(({ level, desc, color }) => (
          <div key={level} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{level}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Formulas</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`Stock disponible = Stock actual - Stock reservado
Stock valorizado  = Stock actual x Precio unitario
Rotacion          = Unidades vendidas / Stock promedio`}
      </div>

      <InfoBox type="warning">
        Los ajustes de stock generados por <strong>conteo ciclico</strong> se aplican como delta (no absoluto),
        para no sobreescribir movimientos que ocurrieron entre el conteo y la aprobacion.
      </InfoBox>

      <H2><ShieldCheck className="h-4 w-4 text-primary/70" /> Bloqueo por Control de Calidad (QC)</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Cuando un tipo de producto tiene activado <Pill color="indigo">requires_qc</Pill>, todo stock recibido
        entra automaticamente en estado <Pill color="amber">pending_qc</Pill> y no puede ser despachado hasta
        que un usuario lo apruebe o rechace.
      </p>
      <div className="space-y-2 mb-4">
        {[
          { state: 'pending_qc', desc: 'Stock recibido pendiente de inspeccion. No se puede despachar.', color: 'amber' },
          { state: 'approved', desc: 'Stock aprobado y disponible para despacho normal.', color: 'emerald' },
          { state: 'rejected', desc: 'Stock rechazado. Se puede ajustar o dar de baja como desperdicio.', color: 'red' },
        ].map(({ state, desc, color }) => (
          <div key={state} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{state}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
      <InfoBox type="info">
        Los botones de <strong>Aprobar</strong> y <strong>Rechazar</strong> aparecen en la tabla de stock de cada bodega
        cuando hay registros con estado <Pill color="amber">pending_qc</Pill>.
      </InfoBox>

      <H2>Reglas de despacho (FIFO / FEFO / LIFO)</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Cada tipo de producto puede configurar una <strong>regla de despacho</strong> que determina
        el orden en que se consumen los lotes al despachar:
      </p>
      <div className="space-y-2 mb-4">
        {[
          { rule: 'FIFO', desc: 'First In, First Out — despacha primero el stock mas antiguo (por fecha de ingreso). Es la regla por defecto.', color: 'blue' },
          { rule: 'FEFO', desc: 'First Expired, First Out — despacha primero el stock con fecha de vencimiento mas cercana. Ideal para perecederos, farmaceuticos y quimicos.', color: 'emerald' },
          { rule: 'LIFO', desc: 'Last In, First Out — despacha primero el stock mas reciente. Usado en materiales donde el orden inverso es preferible.', color: 'purple' },
        ].map(({ rule, desc, color }) => (
          <div key={rule} className="rounded-xl border border-border p-4">
            <p className="text-sm font-bold text-foreground mb-1"><Pill color={color}>{rule}</Pill></p>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
      <InfoBox type="warning">
        La regla FEFO requiere que los lotes tengan <strong>fecha de vencimiento</strong> registrada.
        Si un lote no tiene fecha, se ubica al final de la cola de despacho.
      </InfoBox>
    </div>
  )
}

// ─── Section: Movimientos ────────────────────────────────────────────────────

function MovimientosSection() {
  return (
    <div>
      <SectionHeader icon={ArrowLeftRight} title="Movimientos" subtitle="Historial de todos los cambios de stock" />

      <p className="text-sm text-muted-foreground mb-5">
        Cada cambio de stock genera un <strong>movimiento</strong> que queda registrado permanentemente.
        Los movimientos son inmutables — no se pueden editar ni eliminar.
      </p>

      <H2>Tipos de movimiento</H2>
      <div className="grid grid-cols-2 gap-2 mb-4">
        {[
          { type: 'purchase', label: 'Compra', desc: 'Ingreso por recepcion de OC', color: 'emerald' },
          { type: 'sale', label: 'Venta', desc: 'Salida por orden de venta', color: 'red' },
          { type: 'transfer', label: 'Transferencia', desc: 'Movimiento entre bodegas', color: 'amber' },
          { type: 'adj_in', label: 'Ajuste entrada', desc: 'Ajuste positivo (sobrante)', color: 'blue' },
          { type: 'adj_out', label: 'Ajuste salida', desc: 'Ajuste negativo (merma)', color: 'purple' },
          { type: 'return', label: 'Devolucion', desc: 'Devolucion de cliente', color: 'slate' },
          { type: 'waste', label: 'Desperdicio', desc: 'Producto danado o vencido', color: 'red' },
        ].map(({ type, label, desc, color }) => (
          <div key={type} className="rounded-lg border border-border p-3">
            <Pill color={color}>{type}</Pill>
            <p className="text-xs font-bold text-foreground mt-1">{label}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">{desc}</p>
          </div>
        ))}
      </div>

      <H2><Search className="h-4 w-4 text-primary/70" /> Filtros</H2>
      <p className="text-xs text-muted-foreground mb-3">
        La tabla de movimientos permite filtrar por:
      </p>
      <div className="flex flex-wrap gap-2">
        {['Producto', 'Bodega', 'Tipo de movimiento', 'Rango de fechas', 'Referencia', 'Variante'].map(f => (
          <Pill key={f} color="slate">{f}</Pill>
        ))}
      </div>

      <H2>Datos del movimiento</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['movement_type', 'Tipo: purchase, sale, transfer, adj_in, adj_out, return, waste'],
              ['quantity', 'Cantidad movida (siempre positiva)'],
              ['product', 'Producto afectado'],
              ['variant', 'Variante especifica (si aplica)'],
              ['warehouse', 'Bodega origen o destino'],
              ['unit_cost', 'Costo unitario del movimiento'],
              ['reference', 'Referencia externa (ej: numero de OC o OV)'],
              ['batch_number', 'Numero de lote (si aplica)'],
              ['notes', 'Notas adicionales del operador'],
              ['performed_by', 'Usuario que realizo el movimiento'],
              ['created_at', 'Fecha y hora del movimiento'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Section: Proveedores ────────────────────────────────────────────────────

function ProveedoresSection() {
  return (
    <div>
      <SectionHeader icon={Truck} title="Proveedores" subtitle="Gestion de proveedores y datos de contacto" />

      <H2>Crear un proveedor</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Inventario > Proveedores',
          'Click en "Nuevo proveedor"',
          'Completar nombre, email y telefono',
          'Opcionalmente asignar tipo de proveedor',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Campos del proveedor</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['name', 'Nombre o razon social'],
              ['email', 'Correo de contacto'],
              ['phone', 'Telefono de contacto'],
              ['address', 'Direccion fisica'],
              ['supplier_type_id', 'Tipo de proveedor (configurable)'],
              ['lead_time_days', 'Tiempo de entrega en dias'],
              ['custom_attributes', 'Campos personalizados segun tipo'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Tipos de proveedor</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Los tipos de proveedor se configuran en <strong>Inventario &gt; Configuracion &gt; Tipos de proveedor</strong>.
        Cada tipo puede tener <strong>campos custom</strong> propios que aparecen en el formulario del proveedor.
      </p>
      <InfoBox type="success">
        El <strong>lead time</strong> (tiempo de entrega) se usa para estimar fechas de recepcion al crear ordenes de compra.
      </InfoBox>
    </div>
  )
}

// ─── Section: Ordenes de Compra ──────────────────────────────────────────────

function ComprasSection() {
  return (
    <div>
      <SectionHeader icon={ShoppingCart} title="Ordenes de Compra" subtitle="Gestion del ciclo de compras y recepcion" />

      <InfoBox type="info">
        Las ordenes de compra (OC) gestionan el ciclo completo desde el pedido al proveedor hasta la recepcion
        en bodega. Cada OC recibe un numero automatico con formato <Pill color="indigo">PO-YYYY-NNNN</Pill>.
      </InfoBox>

      <H2><GitBranch className="h-4 w-4 text-primary/70" /> Flujo de estados</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`draft → sent → confirmed → partial → received
  |                              |
  +------------------------------+→ canceled

draft ─┐
draft ─┤→ consolidated (merge)
draft ─┘`}
      </div>

      <div className="space-y-2 mt-3">
        {[
          { state: 'draft', desc: 'Borrador — en preparacion, editable', color: 'slate' },
          { state: 'sent', desc: 'Enviada al proveedor, esperando confirmacion', color: 'amber' },
          { state: 'confirmed', desc: 'Confirmada por el proveedor', color: 'blue' },
          { state: 'partial', desc: 'Recepcion parcial — algunas lineas recibidas', color: 'purple' },
          { state: 'received', desc: 'Totalmente recibida — stock actualizado', color: 'emerald' },
          { state: 'consolidated', desc: 'Consolidada — fusionada con otras OC del mismo proveedor', color: 'indigo' },
          { state: 'canceled', desc: 'Cancelada — sin efecto en stock', color: 'red' },
        ].map(({ state, desc, color }) => (
          <div key={state} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{state}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Crear una orden de compra</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Inventario > Ordenes de Compra',
          'Click en "Nueva OC"',
          'Seleccionar proveedor y bodega destino',
          'Agregar lineas: producto (y variante si aplica), cantidad, precio unitario',
          'Click en "Crear" (queda en estado draft)',
          'Enviar al proveedor cuando este lista',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2><RefreshCw className="h-4 w-4 text-primary/70" /> Recepcion parcial</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Si el proveedor envia la mercancia en multiples envios, puedes registrar cada recepcion parcial:
      </p>
      <div className="space-y-2">
        <div className="rounded-xl border border-border p-4">
          <p className="text-xs text-muted-foreground">
            1. La OC pasa a estado <Pill color="purple">partial</Pill> al registrar la primera recepcion parcial.<br/>
            2. Cada recepcion genera un movimiento de stock tipo <Pill color="emerald">purchase</Pill>.<br/>
            3. Cuando todas las lineas esten completas, la OC pasa a <Pill color="emerald">received</Pill>.
          </p>
        </div>
      </div>

      <H2><Merge className="h-4 w-4 text-primary/70" /> Consolidacion de OC</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Cuando tienes multiples OC en estado <Pill color="slate">draft</Pill> para el <strong>mismo proveedor</strong>,
        puedes fusionarlas en una sola OC consolidada:
      </p>
      <div className="space-y-2">
        <div className="rounded-xl border border-border p-4">
          <p className="text-xs text-muted-foreground">
            1. Seleccionar 2 o mas OC borrador del mismo proveedor.<br/>
            2. Click en "Consolidar" — se crea una nueva OC con todas las lineas combinadas.<br/>
            3. Las OC originales pasan a estado <Pill color="indigo">consolidated</Pill> y quedan inactivas.<br/>
            4. La nueva OC consolida los productos (sumando cantidades si coincide el producto/variante).<br/>
            5. La OC consolidada se puede editar, enviar y recibir normalmente.
          </p>
        </div>
      </div>
      <InfoBox type="warning">
        Solo se pueden consolidar OC en estado <Pill color="slate">draft</Pill> del mismo proveedor.
        El endpoint es <code className="bg-amber-100 rounded px-1">POST /api/v1/purchase-orders/consolidate</code>.
      </InfoBox>
    </div>
  )
}

// ─── Section: Clientes ──────────────────────────────────────────────────────

function ClientesSection() {
  return (
    <div>
      <SectionHeader icon={Users} title="Clientes" subtitle="Gestion de clientes, tipos y datos de contacto" />

      <InfoBox type="info">
        Los clientes son las personas o empresas a quienes vendes. Cada cliente puede tener un <strong>tipo</strong> asignado
        y <strong>precios especiales</strong> personalizados.
      </InfoBox>

      <H2>Crear un cliente</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Inventario > Clientes',
          'Click en "Nuevo cliente"',
          'Completar nombre, email, telefono y direccion',
          'Opcionalmente seleccionar tipo de cliente',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Campos del cliente</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['name', 'Nombre o razon social del cliente'],
              ['code', 'Codigo unico del cliente (ej: CLI-001)'],
              ['email', 'Correo electronico de contacto'],
              ['phone', 'Telefono de contacto'],
              ['address', 'Direccion de envio o facturacion'],
              ['tax_id', 'NIT o identificacion fiscal'],
              ['customer_type_id', 'Tipo de cliente (configurable)'],
              ['credit_limit', 'Limite de credito en la moneda del tenant'],
              ['discount_pct', 'Descuento global (%) que aplica a todas las OV del cliente'],
              ['is_active', 'Si el cliente esta activo'],
              ['notes', 'Notas internas sobre el cliente'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Tipos de cliente</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Los tipos de cliente se configuran en <strong>Inventario &gt; Configuracion &gt; Tipos de cliente</strong>.
        Permiten segmentar clientes por naturaleza: mayorista, minorista, distribuidor, etc.
      </p>

      <H2>Precios por cliente</H2>
      <p className="text-xs text-muted-foreground mb-4">
        Cada cliente puede tener <strong>precios especiales</strong> asignados. Al crear una orden de venta para ese cliente,
        los precios se resuelven automaticamente. Ver la seccion <strong>Precios Especiales</strong>.
      </p>

      <H2><Eye className="h-4 w-4 text-primary/70" /> Portal de cliente</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Desde la pagina de detalle de un cliente, el boton <Pill color="indigo">Ver Portal</Pill> abre
        una vista de solo lectura con la informacion relevante para ese cliente:
      </p>
      <div className="space-y-2 mb-4">
        {[
          { tab: 'Stock', desc: 'Stock disponible de los productos asociados al cliente, con cantidades y ubicaciones.' },
          { tab: 'Pedidos', desc: 'Listado de ordenes de venta del cliente con estado, fecha y total. Click para ver detalle.' },
        ].map(({ tab, desc }) => (
          <div key={tab} className="rounded-xl border border-border p-4">
            <p className="text-sm font-bold text-foreground mb-1">{tab}</p>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
      <InfoBox type="success">
        El portal de cliente es de <strong>solo lectura</strong>. En el futuro, se podra compartir
        un enlace directo para que el cliente consulte sus pedidos sin necesidad de credenciales internas.
      </InfoBox>
    </div>
  )
}

// ─── Section: Ordenes de Venta ──────────────────────────────────────────────

function VentasSection() {
  return (
    <div>
      <SectionHeader icon={Receipt} title="Ordenes de Venta" subtitle="Ciclo completo de venta: desde pedido hasta entrega" />

      <InfoBox type="info">
        Las ordenes de venta (OV) gestionan el ciclo de venta al cliente. Cada OV recibe un numero automatico
        con formato <Pill color="indigo">SO-YYYY-NNNN</Pill> y soporta el flujo completo de picking, despacho y entrega.
      </InfoBox>

      <H2><GitBranch className="h-4 w-4 text-primary/70" /> Flujo de estados</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`draft → pending_approval → confirmed → picking → shipped → delivered
  |         |                  |           |         |
  |         +→ rejected        |           |         +→ returned
  +---------+------------------+-----------+---------+→ canceled`}
      </div>

      <div className="space-y-2 mt-3">
        {[
          { state: 'draft', desc: 'Borrador — en preparacion, editable. No reserva stock.', color: 'slate' },
          { state: 'pending_approval', desc: 'Pendiente de aprobacion — el total supera el umbral del tenant', color: 'amber' },
          { state: 'rejected', desc: 'Rechazada — un aprobador rechazo la OV con motivo', color: 'red' },
          { state: 'confirmed', desc: 'Confirmada — stock reservado para las lineas de la orden', color: 'blue' },
          { state: 'picking', desc: 'En picking — operador preparando el pedido en bodega', color: 'amber' },
          { state: 'shipped', desc: 'Despachada — enviada al cliente, en transito', color: 'purple' },
          { state: 'delivered', desc: 'Entregada — cliente recibio la mercancia', color: 'emerald' },
          { state: 'returned', desc: 'Devuelta — stock reingresado, nota credito emitida si aplica', color: 'slate' },
          { state: 'canceled', desc: 'Cancelada — stock liberado, sin efecto', color: 'red' },
        ].map(({ state, desc, color }) => (
          <div key={state} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{state}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Crear una orden de venta</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Inventario > Ordenes de Venta',
          'Click en "Nueva OV"',
          'Seleccionar cliente, bodega de despacho y moneda',
          'Agregar lineas: producto (y variante), cantidad, precio unitario, tarifa IVA y retención',
          'Los precios se resuelven automaticamente si el cliente tiene un precio especial vigente',
          'Aplicar descuento global (%) y/o descuento por linea si corresponde',
          'Click en "Crear" (queda en draft)',
          'Confirmar — si el total supera el umbral de aprobacion, va a pending_approval',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2><BadgeCheck className="h-4 w-4 text-primary/70" /> Aprobacion por monto</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Si el tenant configura un umbral de aprobacion (<code className="bg-secondary rounded px-1">so_approval_threshold</code>),
        las OV cuyo total supere ese monto requieren aprobacion antes de confirmar:
      </p>
      <div className="space-y-2 mb-3">
        <div className="rounded-xl border border-border p-4">
          <p className="text-xs text-muted-foreground">
            1. Al confirmar, si <strong>total &gt; umbral</strong>, la OV pasa a <Pill color="amber">pending_approval</Pill>.<br/>
            2. Un usuario diferente al creador aprueba o rechaza en <strong>Inventario &gt; Aprobaciones</strong>.<br/>
            3. El <strong>principio de 4 ojos</strong> impide que el creador apruebe su propia OV.<br/>
            4. Al aprobar, la OV pasa a <Pill color="blue">confirmed</Pill> y reserva stock.
          </p>
        </div>
      </div>
      <InfoBox type="warning">
        El umbral se configura en <strong>Inventario &gt; Configuracion &gt; Inventario (tenant)</strong>.
        Si no se configura, la aprobacion no es requerida y la OV pasa directo a confirmed.
      </InfoBox>

      <H2>Impuestos en la OV</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Cada linea de la OV puede tener una <strong>tarifa de IVA</strong> y una <strong>retención en la fuente</strong>:
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['tax_rate_id', 'Tarifa de IVA (referencia a tabla de impuestos)'],
              ['tax_rate_pct', 'Porcentaje de IVA efectivo (ej: 0.19)'],
              ['tax_amount', 'Monto de IVA calculado por linea'],
              ['retention_pct', 'Porcentaje de retencion en la fuente'],
              ['retention_amount', 'Monto de retencion calculado por linea'],
              ['discount_pct', 'Descuento % por linea'],
              ['discount_amount', 'Monto de descuento calculado'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Totales de la OV</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`subtotal         = Σ (qty × precio - descuento_linea)
discount_amount  = subtotal × discount_pct (global)
tax_amount       = Σ tax_amount por linea
total_retention  = Σ retention_amount por linea
total_with_tax   = subtotal - discount_amount + tax_amount
total_payable    = total_with_tax - total_retention`}
      </div>

      <H2>Reserva de stock</H2>
      <InfoBox type="warning">
        Al <strong>confirmar</strong> una OV, el sistema reserva stock para cada linea (optimistic locking).
        Si no hay stock suficiente en la bodega, se genera un <strong>backorder</strong> automatico con las lineas faltantes.
      </InfoBox>

      <H2>Backorders</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Cuando al confirmar una OV no hay stock suficiente para alguna linea:
      </p>
      <div className="space-y-2 mb-3">
        <div className="rounded-xl border border-border p-4">
          <p className="text-xs text-muted-foreground">
            1. La OV original se confirma solo con las cantidades disponibles.<br/>
            2. Se crea automaticamente una nueva OV hija (backorder) con las cantidades pendientes.<br/>
            3. El backorder queda en estado <Pill color="slate">draft</Pill> y referencia la OV padre.<br/>
            4. Numero de backorder: <Pill color="indigo">SO-YYYY-NNNN (BO-1)</Pill>.
          </p>
        </div>
      </div>

      <H2>Despacho y picking</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Al despachar, puedes especificar cantidades por linea (despacho parcial) o despachar la orden completa.
        Cada despacho genera movimientos de stock tipo <Pill color="red">sale</Pill>. La pagina de <strong>Picking</strong> permite
        verificar linea por linea desde bodega.
      </p>

      <H2><FileText className="h-4 w-4 text-primary/70" /> Remision de entrega</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Al despachar, se puede generar una <strong>remision</strong> (guia de despacho) en PDF que incluye:
        numero de remision, datos del cliente, productos, cantidades y firma de recibido.
        Se genera con <Pill color="indigo">POST /sales-orders/&#123;id&#125;/remission</Pill>.
      </p>

      <H2>Resumen y KPIs</H2>
      <p className="text-xs text-muted-foreground">
        El dashboard de ventas muestra un resumen de ordenes por estado (draft, pending_approval, confirmed, shipped, etc.)
        con conteo y totales. Accesible desde <strong>Inventario &gt; Ventas</strong>.
      </p>
    </div>
  )
}

// ─── Section: Precios (now redirects to Precios Especiales) ─────────────────

function PreciosSection() {
  return (
    <div>
      <SectionHeader icon={DollarSign} title="Precios Especiales" subtitle="Precios diferenciados por cliente con vigencia" />

      <InfoBox type="info">
        Los precios se resuelven con una jerarquia de 2 niveles: <strong>precio especial del cliente</strong> y <strong>precio base del producto</strong>.
        Si el cliente tiene un precio especial vigente para un producto, se usa ese precio. De lo contrario, se usa el precio base del producto.
      </InfoBox>

      <H2>Jerarquia de resolucion</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          '1. Precio especial del cliente (customer_special) — si existe y esta vigente',
          '2. Precio base del producto (product_base) — precio de venta configurado en el producto',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <p className="text-xs text-muted-foreground mt-4">
        Para gestionar precios especiales, ve a <strong>Inventario &gt; Precios Especiales</strong>.
        Ahi puedes crear, editar y ver el historial de precios por cliente y producto.
      </p>
    </div>
  )
}

// ─── Section: Conteo Ciclico ─────────────────────────────────────────────────

function ConteoCliclicoSection() {
  return (
    <div>
      <SectionHeader icon={ClipboardCheck} title="Conteo Ciclico" subtitle="Verificacion sistematica del inventario fisico" />

      <InfoBox type="info">
        El conteo ciclico es un metodo de verificacion que cuenta una porcion del inventario de forma regular,
        en lugar de un inventario fisico completo. Su objetivo es mantener el <strong>IRA por encima del 95%</strong>.
      </InfoBox>

      <H2>Ventajas sobre el inventario anual</H2>
      <div className="flex flex-wrap gap-2 mb-4">
        {[
          'No detiene operaciones',
          'Detecta errores temprano',
          'Correccion continua',
          'Menor costo operativo',
          'Precision en tiempo real',
        ].map(v => <Pill key={v} color="emerald">{v}</Pill>)}
      </div>

      {/* IRA */}
      <H2><BarChart3 className="h-4 w-4 text-primary/70" /> IRA (Inventory Record Accuracy)</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`IRA = (items sin discrepancia / total items) x 100

IRA Valor = (1 - |sumatoria(discrepancia x costo)| / sumatoria(sistema x costo)) x 100`}
      </div>
      <div className="grid grid-cols-3 gap-2 mb-4">
        {[
          { range: '>= 95%', label: 'Verde (meta)', color: 'emerald' },
          { range: '90% - 95%', label: 'Ambar (alerta)', color: 'amber' },
          { range: '< 90%', label: 'Rojo (critico)', color: 'red' },
        ].map(({ range, label, color }) => (
          <div key={range} className="rounded-xl border border-border p-3 text-center">
            <Pill color={color}>{range}</Pill>
            <p className="text-[11px] text-muted-foreground mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Discrepancia */}
      <H2>Discrepancia y ajuste por delta</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`Discrepancia    = Cantidad contada - Cantidad en sistema
Stock ajustado  = Stock actual + Discrepancia  (delta, no absoluto)`}
      </div>
      <div className="space-y-2 mb-4">
        {[
          { sign: 'Positiva', desc: 'Sobrante — hay mas producto del que dice el sistema', color: 'blue' },
          { sign: 'Negativa', desc: 'Faltante — hay menos producto del que dice el sistema', color: 'red' },
          { sign: 'Cero', desc: 'Item exacto — el sistema y el fisico coinciden', color: 'emerald' },
        ].map(({ sign, desc, color }) => (
          <div key={sign} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{sign}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
      <InfoBox type="warning">
        Al aprobar, el sistema aplica la discrepancia como <strong>delta</strong> al stock actual, no reemplaza el valor.
        Esto evita borrar movimientos legitimos que ocurrieron entre el conteo y la aprobacion.
      </InfoBox>

      {/* 6 Metodologias */}
      <H2>6 metodologias de conteo</H2>
      <div className="space-y-3">
        {[
          {
            name: 'Grupo de Control',
            desc: 'Grupo fijo y representativo que se cuenta repetidamente. Sirve para medir confiabilidad del proceso, detectar errores sistematicos y entrenar personal.',
            when: 'Al inicio de un programa de conteo ciclico, o para validar el proceso.',
          },
          {
            name: 'Auditoria por Ubicacion',
            desc: 'Se cuentan todos los productos de una ubicacion especifica (pasillo, estanteria, zona). Rapido y eficiente, detecta productos mal ubicados.',
            when: 'Bodegas con ubicaciones bien definidas (estanterias, racks, bins).',
          },
          {
            name: 'Seleccion Aleatoria',
            desc: 'Productos elegidos al azar. Elimina sesgos de seleccion y da una muestra representativa.',
            when: 'Cuando no hay informacion sobre que productos tienen mas problemas.',
          },
          {
            name: 'Poblacion Decreciente',
            desc: 'Se inicia con el inventario completo. Los productos que pasan 2 conteos sin discrepancia se retiran. El esfuerzo se enfoca en los problematicos.',
            when: 'Cuando se quiere reducir progresivamente el volumen de conteo.',
          },
          {
            name: 'Categoria de Producto',
            desc: 'Se agrupan por categoria (tipo, familia, proveedor) y se programa el conteo por grupo.',
            when: 'Categorias con mayor riesgo de discrepancia (productos pequenos, alto valor).',
          },
          {
            name: 'Clasificacion ABC',
            desc: 'Basado en Pareto (80/20). A (alto valor) se cuenta semanal/mensual, B (medio) trimestral, C (bajo) semestral.',
            when: 'Metodologia mas recomendada. Prioriza el esfuerzo en productos de mayor impacto.',
          },
        ].map(({ name, desc, when }, i) => (
          <div key={name} className="rounded-xl border border-border p-4">
            <p className="text-sm font-bold text-foreground mb-1">
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold text-[10px] mr-2">{i + 1}</span>
              {name}
            </p>
            <p className="text-xs text-muted-foreground mb-2">{desc}</p>
            <p className="text-[11px] text-muted-foreground"><strong>Cuando usar:</strong> {when}</p>
          </div>
        ))}
      </div>

      {/* Flujo paso a paso */}
      <H2>Flujo de trabajo paso a paso</H2>
      <div className="space-y-3">
        {[
          { title: 'Crear el conteo', desc: 'Inventario > Conteo Ciclico > "Nuevo conteo". Seleccionar bodega, productos (opcional), metodologia, contadores y minutos por conteo. El sistema toma un snapshot de cantidades en sistema.' },
          { title: 'Verificar factibilidad', desc: 'Revisar la tarjeta de Factibilidad: tiempo total estimado, horas por contador, si es completable en una jornada (7h). Si no es factible: agregar contadores, reducir productos o dividir en multiples conteos.' },
          { title: 'Iniciar el conteo', desc: 'Click "Iniciar" — cambia de Borrador a En Progreso. Se habilita el registro de cantidades.' },
          { title: 'Registrar 1er conteo', desc: 'Para cada producto: click en el campo "1er Conteo", ingresar cantidad fisica, click "OK". El sistema calcula la discrepancia automaticamente.' },
          { title: 'Recontar (2do intento)', desc: 'Para items con discrepancia: click "Recontar", ingresar nueva cantidad, documentar causa raiz. El reconteo se convierte en el conteo autoritativo.' },
          { title: 'Completar el conteo', desc: 'Verificar que todos los items tengan conteo registrado. Click "Completar". El sistema valida que no queden items sin contar.' },
          { title: 'Aprobar el conteo', desc: 'Revisar discrepancias e IRA. Click "Aprobar". Se aplican ajustes de stock (delta), se crean movimientos, se calcula IRA y se actualiza la fecha de ultimo conteo.' },
        ].map(({ title, desc }, i) => (
          <div key={i} className="flex items-start gap-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            <div>
              <p className="text-xs font-bold text-foreground">{title}</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">{desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Causas raiz */}
      <H2>Causas raiz de discrepancia</H2>
      <div className="flex flex-wrap gap-2 mb-4">
        {[
          'Error de conteo inicial',
          'Producto mal ubicado',
          'Robo/merma no registrada',
          'Error de recepcion',
          'Error de despacho',
          'Dano no reportado',
          'Error de sistema',
        ].map(c => <Pill key={c} color="red">{c}</Pill>)}
      </div>

      {/* Estados */}
      <H2><GitBranch className="h-4 w-4 text-primary/70" /> Estados del conteo</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`Borrador → En Progreso → Completado → Aprobado
    |             |              |
    +-------------+--------------+→ Cancelado`}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Estado</th>
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Descripcion</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['Borrador', 'Recien creado, snapshot tomado', 'Iniciar, Cancelar'],
              ['En Progreso', 'Conteo activo, registro de cantidades', 'Contar, Recontar, Completar, Cancelar'],
              ['Completado', 'Todos los items contados', 'Aprobar, Cancelar'],
              ['Aprobado', 'Ajustes aplicados al stock', '(estado final)'],
              ['Cancelado', 'Descartado, sin efecto', '(estado final)'],
            ].map(([state, desc, actions]) => (
              <tr key={state}>
                <td className="py-2 pr-4 font-semibold text-foreground">{state}</td>
                <td className="py-2 pr-4 text-muted-foreground">{desc}</td>
                <td className="py-2 text-muted-foreground">{actions}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Permisos */}
      <H2><Shield className="h-4 w-4 text-primary/70" /> Permisos requeridos</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Accion</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Permiso</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['Ver conteos y analiticas', 'inventory.view'],
              ['Iniciar, contar, completar', 'inventory.manage'],
              ['Crear, aprobar, cancelar', 'inventory.admin'],
            ].map(([action, perm]) => (
              <tr key={action}>
                <td className="py-2 pr-4 text-foreground">{action}</td>
                <td className="py-2"><Pill color="indigo">{perm}</Pill></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mejores practicas */}
      <H2>Mejores practicas</H2>
      <div className="space-y-2">
        {[
          'Contar regularmente — poco y frecuente es mejor que mucho y raro',
          'Meta IRA >= 95% — estandar de la industria',
          'Documentar causas raiz — siempre registrar por que hubo discrepancia',
          'Usar el reconteo — ante una discrepancia, recontar antes de completar',
          'Revisar factibilidad — no crear conteos imposibles de completar en una jornada',
          'Metodologia ABC — contar productos A con mayor frecuencia',
          'Aprobar oportunamente — no dejar conteos completados sin aprobar',
        ].map((tip, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
            {tip}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Section: Eventos ────────────────────────────────────────────────────────

function EventosSection() {
  return (
    <div>
      <SectionHeader icon={AlertTriangle} title="Eventos" subtitle="Registro de incidencias y eventos operativos" />

      <p className="text-sm text-muted-foreground mb-5">
        Los eventos registran incidencias, alertas y sucesos relevantes que afectan al inventario.
        Cada evento queda asociado a un producto, bodega o movimiento.
      </p>

      <H2>Crear un evento</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Inventario > Eventos',
          'Click en "Nuevo evento"',
          'Seleccionar tipo, severidad y producto/bodega afectado',
          'Describir el evento en detalle',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Severidades</H2>
      <div className="space-y-2">
        {[
          { level: 'low', desc: 'Informativo — no requiere accion inmediata', color: 'slate' },
          { level: 'medium', desc: 'Alerta — requiere atencion pero no es urgente', color: 'amber' },
          { level: 'high', desc: 'Importante — requiere accion pronta', color: 'red' },
          { level: 'critical', desc: 'Critico — requiere accion inmediata', color: 'red' },
        ].map(({ level, desc, color }) => (
          <div key={level} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{level}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Estados del evento</H2>
      <div className="space-y-2">
        {[
          { state: 'open', desc: 'Evento abierto, pendiente de resolucion', color: 'amber' },
          { state: 'in_progress', desc: 'En proceso de investigacion o correccion', color: 'blue' },
          { state: 'resolved', desc: 'Resuelto — accion correctiva aplicada', color: 'emerald' },
          { state: 'closed', desc: 'Cerrado — sin accion requerida', color: 'slate' },
        ].map(({ state, desc, color }) => (
          <div key={state} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{state}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Impactos</H2>
      <p className="text-xs text-muted-foreground">
        Un evento puede tener multiples <strong>impactos</strong> que detallan las consecuencias sobre productos
        o bodegas especificas: cantidad afectada, costo estimado y descripcion del dano.
      </p>
    </div>
  )
}

// ─── Section: Alertas de Stock ──────────────────────────────────────────────

function AlertasSection() {
  return (
    <div>
      <SectionHeader icon={Bell} title="Alertas de Stock" subtitle="Notificaciones automaticas de niveles de inventario" />

      <InfoBox type="info">
        El sistema genera alertas automaticas cuando el stock de un producto alcanza niveles criticos,
        basandose en los umbrales configurados en cada producto.
      </InfoBox>

      <H2>Tipos de alerta</H2>
      <div className="space-y-3">
        {[
          { type: 'Stock bajo minimo', desc: 'El stock actual esta por debajo del min_stock configurado en el producto. Indica riesgo de desabasto.', color: 'red', action: 'Crear orden de compra al proveedor' },
          { type: 'Punto de reorden', desc: 'El stock ha alcanzado el reorder_point. Es momento de generar un pedido de reabastecimiento.', color: 'amber', action: 'Revisar lead time del proveedor y crear OC' },
          { type: 'Stock sobre maximo', desc: 'El stock supera el max_stock configurado. Hay riesgo de sobre-stock y costos de almacenaje.', color: 'purple', action: 'Evaluar transferencias o ajustar compras futuras' },
          { type: 'Sin stock', desc: 'El producto tiene stock cero en una o mas bodegas. Hay riesgo de no poder cumplir pedidos.', color: 'red', action: 'Accion urgente: recibir stock o redirigir pedidos' },
        ].map(({ type, desc, color, action }) => (
          <div key={type} className="rounded-xl border border-border p-4">
            <p className="text-sm font-bold text-foreground mb-1"><Pill color={color}>{type}</Pill></p>
            <p className="text-xs text-muted-foreground mb-2">{desc}</p>
            <p className="text-[11px] text-muted-foreground"><strong>Accion sugerida:</strong> {action}</p>
          </div>
        ))}
      </div>

      <H2>Configurar umbrales</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Los umbrales de alerta se configuran en cada producto individual:
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['min_stock', 'Umbral minimo — alerta de stock bajo'],
              ['max_stock', 'Umbral maximo — alerta de sobre-stock'],
              ['reorder_point', 'Punto de reorden — sugerencia de reabastecimiento'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <InfoBox type="success">
        Las alertas se visualizan en el <strong>Dashboard de Inventario</strong> como indicadores de productos
        bajo minimo y sobre maximo. Tambien se reflejan en el reporte de stock.
      </InfoBox>
    </div>
  )
}

// ─── Section: Kardex ────────────────────────────────────────────────────────

function KardexSection() {
  return (
    <div>
      <SectionHeader icon={BookMarked} title="Kardex" subtitle="Historial valorizado de entradas y salidas por producto" />

      <InfoBox type="info">
        El <strong>Kardex</strong> es un registro contable que detalla cronologicamente cada entrada y salida de un producto,
        mostrando la cantidad, el costo unitario y el saldo acumulado. Es esencial para la valoracion de inventario.
      </InfoBox>

      <H2>Que muestra el Kardex</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Para cada producto, el Kardex presenta una tabla cronologica con:
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Columna</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['Fecha', 'Fecha y hora del movimiento'],
              ['Tipo', 'Tipo de movimiento (entrada, salida, ajuste)'],
              ['Referencia', 'Numero de OC, OV o referencia del movimiento'],
              ['Entrada (qty)', 'Cantidad ingresada (si aplica)'],
              ['Entrada (costo)', 'Costo total de la entrada'],
              ['Salida (qty)', 'Cantidad despachada (si aplica)'],
              ['Salida (costo)', 'Costo total de la salida'],
              ['Saldo (qty)', 'Cantidad acumulada despues del movimiento'],
              ['Saldo (costo)', 'Valor total acumulado del inventario'],
              ['Costo unitario', 'Costo promedio o FIFO segun metodo'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Metodo de costeo</H2>
      <div className="space-y-2">
        {[
          { method: 'Costo promedio', desc: 'El costo unitario se recalcula con cada entrada como promedio ponderado de todas las unidades en inventario.' },
          { method: 'FIFO', desc: 'First In, First Out — las salidas se valoran al costo de las unidades mas antiguas. Usado en produccion para calcular costo de componentes.' },
        ].map(({ method, desc }) => (
          <div key={method} className="rounded-xl border border-border p-4">
            <p className="text-sm font-bold text-foreground mb-1">{method}</p>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Acceso al Kardex</H2>
      <p className="text-xs text-muted-foreground">
        El Kardex se accede desde el detalle de cada producto, en la pestana "Kardex".
        Tambien puedes filtrar por rango de fechas y bodega para ver movimientos especificos.
        El endpoint es <code className="bg-secondary rounded px-1">GET /api/v1/products/&#123;id&#125;/kardex</code>.
      </p>

      <InfoBox type="warning">
        El Kardex refleja todos los movimientos reales de stock. Si hay discrepancias entre el Kardex y el stock
        fisico, usa el <strong>conteo ciclico</strong> para identificar y corregir las diferencias.
      </InfoBox>
    </div>
  )
}

// ─── Section: Seriales ───────────────────────────────────────────────────────

function SerialesSection() {
  return (
    <div>
      <SectionHeader icon={Hash} title="Seriales" subtitle="Trazabilidad unitaria por numero de serie" />

      <InfoBox type="info">
        Los seriales permiten hacer seguimiento de <strong>unidades individuales</strong> de un producto.
        Cada serial tiene un numero unico e irrepetible dentro del tenant.
      </InfoBox>

      <H2>Crear un serial</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Inventario > Seriales',
          'Click en "Nuevo serial"',
          'Seleccionar el producto asociado',
          'Ingresar el numero de serie (unico)',
          'Opcionalmente asignar a una bodega',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Estados del serial</H2>
      <div className="space-y-2">
        {[
          { state: 'available', desc: 'Disponible en bodega, listo para venta o despacho', color: 'emerald' },
          { state: 'reserved', desc: 'Reservado para un pedido o proceso', color: 'amber' },
          { state: 'sold', desc: 'Vendido al cliente final', color: 'blue' },
          { state: 'in_transit', desc: 'En movimiento entre bodegas', color: 'purple' },
          { state: 'damaged', desc: 'Danado — no disponible para venta', color: 'red' },
          { state: 'returned', desc: 'Devuelto por el cliente', color: 'slate' },
        ].map(({ state, desc, color }) => (
          <div key={state} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{state}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Trazabilidad</H2>
      <p className="text-xs text-muted-foreground">
        Cada serial mantiene un historial completo de movimientos: desde su creacion, pasando por transferencias
        entre bodegas, hasta su venta o baja. Esto permite rastrear la ubicacion y el estado de cada unidad
        individual en cualquier momento.
      </p>

      <InfoBox type="success">
        Los estados de serial son <strong>configurables por tenant</strong>. Puedes agregar estados custom
        en <strong>Configuracion &gt; Estados de serial</strong> segun tu flujo de trabajo.
      </InfoBox>
    </div>
  )
}

// ─── Section: Lotes ──────────────────────────────────────────────────────────

function LotesSection() {
  return (
    <div>
      <SectionHeader icon={Layers} title="Lotes" subtitle="Trazabilidad por lote de fabricacion" />

      <InfoBox type="info">
        Los lotes agrupan unidades de un mismo producto fabricadas en el mismo ciclo.
        Son esenciales para control de <strong>vencimiento</strong> y trazabilidad de origen.
      </InfoBox>

      <H2>Crear un lote</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Inventario > Lotes',
          'Click en "Nuevo lote"',
          'Seleccionar el producto',
          'Ingresar numero de lote (unico por producto)',
          'Establecer fecha de fabricacion y fecha de vencimiento',
          'Ingresar cantidad del lote',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Campos del lote</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['batch_number', 'Numero de lote unico por producto'],
              ['product', 'Producto asociado'],
              ['quantity', 'Cantidad de unidades en el lote'],
              ['manufactured_date', 'Fecha de fabricacion'],
              ['expiry_date', 'Fecha de vencimiento'],
              ['notes', 'Notas adicionales (proveedor, condiciones, etc.)'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2><Calendar className="h-4 w-4 text-primary/70" /> Control de vencimiento</H2>
      <p className="text-xs text-muted-foreground">
        Los lotes con fecha de vencimiento permiten aplicar politicas <strong>FEFO</strong> (First Expired, First Out)
        para despachar primero los productos mas proximos a vencer. El sistema puede alertar sobre lotes
        proximos a vencimiento.
      </p>
    </div>
  )
}

// ─── Section: Produccion ─────────────────────────────────────────────────────

function ProduccionSection() {
  return (
    <div>
      <SectionHeader icon={Factory} title="Produccion" subtitle="Recetas (BOM), corridas de produccion, aprobacion y costos FIFO" />

      <H2>Recetas (Bill of Materials)</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Una receta define los componentes necesarios para fabricar un producto terminado.
        Cada receta tiene un producto resultado, una cantidad de rendimiento y una lista de componentes.
      </p>
      <div className="rounded-xl border border-primary/30 bg-primary/5 p-4">
        <p className="text-sm font-bold text-primary mb-2">Ejemplo de receta</p>
        <div className="text-xs text-muted-foreground space-y-1">
          <p><strong>Producto resultado:</strong> Caja de regalo premium (rinde 1 unidad)</p>
          <p><strong>Componentes:</strong></p>
          <div className="ml-4 space-y-0.5">
            <p>- Caja carton decorada x 1 unidad</p>
            <p>- Papel seda x 2 hojas</p>
            <p>- Cinta de raso x 0.5 metros</p>
            <p>- Tarjeta personalizada x 1 unidad</p>
          </div>
        </div>
      </div>

      <H2>Crear una receta</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Inventario > Recetas',
          'Click en "Nueva receta"',
          'Seleccionar el producto resultado',
          'Agregar componentes con sus cantidades',
          'Establecer la cantidad de producto resultante (yield)',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2><GitBranch className="h-4 w-4 text-primary/70" /> Corridas de produccion</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Una <strong>corrida de produccion</strong> es la ejecucion real de una receta. El flujo incluye aprobacion:
      </p>

      <H2>Flujo de estados</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`pending → in_progress → awaiting_approval → completed
    |          |                |
    +----------+----------------+→ rejected`}
      </div>

      <div className="space-y-2 mt-3">
        {[
          { state: 'pending', desc: 'Creada — pendiente de iniciar. Verifica disponibilidad de componentes.', color: 'slate' },
          { state: 'in_progress', desc: 'En ejecucion — componentes consumidos, produccion en curso.', color: 'amber' },
          { state: 'awaiting_approval', desc: 'Esperando aprobacion del supervisor antes de ingresar producto terminado.', color: 'blue' },
          { state: 'completed', desc: 'Aprobada y completada — stock de producto resultado incrementado.', color: 'emerald' },
          { state: 'rejected', desc: 'Rechazada — el supervisor no aprobo la corrida. Los componentes ya consumidos no se revierten automaticamente.', color: 'red' },
        ].map(({ state, desc, color }) => (
          <div key={state} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{state}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Proceso de ejecucion</H2>
      <div className="space-y-2">
        <div className="rounded-xl border border-border p-4">
          <p className="text-xs text-muted-foreground">
            1. Se verifica que haya stock suficiente de todos los componentes en la bodega.<br/>
            2. Se descuenta el stock de cada componente (movimientos <Pill color="red">adj_out</Pill>).<br/>
            3. El costo de produccion se calcula por capas <strong>FIFO</strong> (costo real de los componentes consumidos).<br/>
            4. La corrida pasa a <Pill color="blue">awaiting_approval</Pill>.<br/>
            5. Al aprobar, se incrementa el stock del producto resultado (movimiento <Pill color="emerald">adj_in</Pill>).<br/>
            6. El costo unitario del producto resultante = suma de costos FIFO de componentes / cantidad producida.
          </p>
        </div>
      </div>

      <H2>Costeo FIFO en produccion</H2>
      <InfoBox type="success">
        El sistema calcula el costo de produccion usando capas <strong>FIFO</strong>: consume primero las unidades
        mas antiguas de cada componente y suma su costo real. Esto da un costo de produccion preciso,
        no un promedio estimado.
      </InfoBox>
    </div>
  )
}

// ─── Section: Reportes ───────────────────────────────────────────────────────

function ReportesSection() {
  return (
    <div>
      <SectionHeader icon={FileDown} title="Reportes" subtitle="Exportacion de datos en formato CSV" />

      <p className="text-sm text-muted-foreground mb-5">
        La seccion de reportes permite descargar datos del inventario en formato CSV para analisis externo
        en Excel, Google Sheets u otras herramientas.
      </p>

      <H2>Reportes disponibles</H2>
      <div className="space-y-3">
        {[
          { name: 'Productos', desc: 'Lista completa de productos con SKU, precio, stock minimo/maximo, tipo y atributos.', endpoint: 'GET /api/v1/reports/products' },
          { name: 'Stock', desc: 'Niveles de stock actuales por producto y bodega. Incluye valoracion.', endpoint: 'GET /api/v1/reports/stock' },
          { name: 'Movimientos', desc: 'Historial de movimientos con filtro por rango de fechas. Tipo, cantidad, referencia y notas.', endpoint: 'GET /api/v1/reports/movements' },
          { name: 'Proveedores', desc: 'Directorio de proveedores con tipo, contacto y lead time.', endpoint: 'GET /api/v1/reports/suppliers' },
          { name: 'Eventos', desc: 'Eventos de inventario con tipo, severidad, estado e impacto.', endpoint: 'GET /api/v1/reports/events' },
          { name: 'Seriales', desc: 'Listado de numeros de serie con estado, producto y bodega.', endpoint: 'GET /api/v1/reports/serials' },
          { name: 'Lotes', desc: 'Lotes con fecha de fabricacion, vencimiento y cantidades.', endpoint: 'GET /api/v1/reports/batches' },
          { name: 'Ordenes de compra', desc: 'OC con estado, proveedor, total y fecha.', endpoint: 'GET /api/v1/reports/purchase-orders' },
        ].map(({ name, desc, endpoint }) => (
          <div key={name} className="rounded-xl border border-border p-4">
            <p className="text-sm font-bold text-foreground mb-1">{name} <Pill color="slate">{endpoint}</Pill></p>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Filtros de fechas</H2>
      <p className="text-xs text-muted-foreground">
        El reporte de movimientos acepta <Pill>fecha_inicio</Pill> y <Pill>fecha_fin</Pill> como parametros
        opcionales para limitar el rango de datos exportados.
      </p>

      <InfoBox type="info">
        Los archivos CSV se descargan directamente al navegador. El nombre del archivo incluye la fecha
        de generacion para facilitar el control de versiones.
      </InfoBox>
    </div>
  )
}

// ─── Section: Importacion ───────────────────────────────────────────────────

function ImportacionSection() {
  return (
    <div>
      <SectionHeader icon={Upload} title="Importacion y Datos Demo" subtitle="Carga masiva de productos y generacion de datos de prueba" />

      <H2>Importacion de productos</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Puedes importar productos de forma masiva via la API. El endpoint acepta un arreglo de productos
        y los crea en lote:
      </p>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`POST /api/v1/products/import
Content-Type: application/json

[
  { "name": "Producto A", "sku": "PROD-001", "unit_of_measure": "unidad", "price": 10000 },
  { "name": "Producto B", "sku": "PROD-002", "unit_of_measure": "kg", "price": 5000 },
  ...
]`}
      </div>

      <H2>Datos demo</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Para probar el sistema rapidamente, puedes generar datos de prueba que incluyen productos,
        bodegas, proveedores y movimientos de stock de ejemplo:
      </p>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`POST /api/v1/demo/seed`}
      </div>

      <InfoBox type="warning">
        Los datos demo son para <strong>entornos de prueba</strong> unicamente. No los uses en produccion
        ya que generan registros ficticios que pueden confundir la operacion real.
      </InfoBox>

      <H2>Formato CSV para importacion</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Si prefieres preparar los datos en una hoja de calculo, el formato CSV esperado es:
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Columna</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['name *', 'Nombre del producto (obligatorio)'],
              ['sku *', 'SKU unico (obligatorio)'],
              ['unit_of_measure *', 'Unidad de medida (obligatorio)'],
              ['price', 'Precio unitario'],
              ['cost', 'Costo unitario'],
              ['min_stock', 'Stock minimo'],
              ['max_stock', 'Stock maximo'],
              ['barcode', 'Codigo de barras'],
              ['description', 'Descripcion del producto'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Section: Configuracion ─────────────────────────────────────────────────

function ConfiguracionSection() {
  return (
    <div>
      <SectionHeader icon={Settings2} title="Configuracion" subtitle="Tipos, campos custom, estados y parametros del inventario" />

      <InfoBox type="warning">
        La seccion de configuracion requiere el permiso <Pill color="indigo">inventory.admin</Pill>.
        Los cambios aqui afectan a todos los usuarios del tenant.
      </InfoBox>

      <H2>Tipos configurables</H2>
      <div className="space-y-3">
        {[
          { name: 'Tipos de producto', desc: 'Categorias de producto con campos custom propios. Cada producto puede pertenecer a un tipo.', path: 'Configuracion > Tipos de producto' },
          { name: 'Tipos de proveedor', desc: 'Categorias de proveedor con campos custom. Permite diferenciar proveedores por naturaleza.', path: 'Configuracion > Tipos de proveedor' },
          { name: 'Tipos de cliente', desc: 'Categorias de cliente: mayorista, minorista, distribuidor, etc.', path: 'Configuracion > Tipos de cliente' },
          { name: 'Tipos de bodega', desc: 'Clasificacion de bodegas: principal, secundaria, virtual, transito.', path: 'Configuracion > Tipos de bodega' },
          { name: 'Tipos de movimiento', desc: 'Tipos de movimiento de stock: compra, venta, transferencia, ajuste, devolucion, desperdicio.', path: 'Configuracion > Tipos de movimiento' },
          { name: 'Tipos de orden', desc: 'Clasificacion de ordenes de compra para segmentar por prioridad o naturaleza.', path: 'Configuracion > Tipos de orden' },
          { name: 'Tipos de evento', desc: 'Clasificacion de eventos de inventario: robo, dano, merma, etc.', path: 'Configuracion > Tipos de evento' },
          { name: 'Severidades de evento', desc: 'Niveles de urgencia: low, medium, high, critical.', path: 'Configuracion > Severidades' },
          { name: 'Estados de evento', desc: 'Flujo de estados de eventos: open, in_progress, resolved, closed.', path: 'Configuracion > Estados de evento' },
        ].map(({ name, desc, path }) => (
          <div key={name} className="rounded-xl border border-border p-4">
            <p className="text-sm font-bold text-foreground mb-1">{name}</p>
            <p className="text-xs text-muted-foreground mb-1">{desc}</p>
            <p className="text-[11px] text-muted-foreground"><strong>Ruta:</strong> Inventario &gt; {path}</p>
          </div>
        ))}
      </div>

      <H2>Reglas de tipo de producto</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Cada tipo de producto puede configurar reglas avanzadas que automatizan el comportamiento del inventario:
      </p>
      <div className="space-y-3 mb-4">
        {[
          { name: 'Requiere QC', field: 'requires_qc', desc: 'Cuando esta activado, todo stock recibido de productos de este tipo entra en estado pending_qc y no puede despacharse hasta ser aprobado.' },
          { name: 'Regla de despacho', field: 'dispatch_rule', desc: 'Define el orden de consumo de lotes: FIFO (por defecto), FEFO (por vencimiento) o LIFO (ultimo en entrar, primero en salir).' },
          { name: 'Ubicacion de entrada', field: 'entry_rule_location_id', desc: 'Ubicacion predeterminada donde se almacena automaticamente el stock al recibirlo. Si se configura, no es necesario seleccionar ubicacion manualmente en cada recepcion.' },
        ].map(({ name, field, desc }) => (
          <div key={field} className="rounded-xl border border-border p-4">
            <p className="text-sm font-bold text-foreground mb-1">{name} <span className="text-xs font-mono text-muted-foreground ml-1">{field}</span></p>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
      <InfoBox type="info">
        Estas reglas se configuran en <strong>Inventario &gt; Configuracion &gt; Tipos de producto</strong>,
        tanto al crear un nuevo tipo como al editar uno existente.
      </InfoBox>

      <H2>Campos custom</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Los campos custom permiten extender los formularios de productos, proveedores y bodegas con campos adicionales
        especificos del tipo. Tipos de campo disponibles:
      </p>
      <div className="flex flex-wrap gap-2 mb-4">
        {['text', 'number', 'date', 'boolean', 'select', 'url', 'email'].map(t => (
          <Pill key={t} color="indigo">{t}</Pill>
        ))}
      </div>

      <InfoBox type="success">
        Los campos custom definidos en un tipo aparecen automaticamente en los formularios de creacion y edicion
        de las entidades que pertenecen a ese tipo. Los valores se guardan en el campo <code className="bg-emerald-100 rounded px-1">custom_attributes</code> (JSONB).
      </InfoBox>

      <H2>Estados de serial</H2>
      <p className="text-xs text-muted-foreground">
        Los estados de serial son configurables por tenant. Los estados por defecto son:
        <Pill color="emerald">available</Pill> <Pill color="amber">reserved</Pill> <Pill color="blue">sold</Pill>{' '}
        <Pill color="purple">in_transit</Pill> <Pill color="red">damaged</Pill> <Pill color="slate">returned</Pill>.
        Puedes agregar estados custom segun tu flujo de trabajo.
      </p>

      <H2>Configuracion de eventos</H2>
      <p className="text-xs text-muted-foreground">
        Los tipos de evento, severidades e impactos son configurables para adaptar el sistema de eventos
        a las necesidades de tu operacion. Los cambios se aplican en tiempo real.
      </p>

      <H2>Campos de bodega y movimiento</H2>
      <p className="text-xs text-muted-foreground">
        Tambien puedes definir campos custom para <strong>bodegas</strong> (ej: responsable, horario) y
        <strong> movimientos</strong> (ej: numero de guia, transportadora). Se configuran en las pestanas correspondientes.
      </p>
    </div>
  )
}

// ─── Section: Control de Calidad ────────────────────────────────────────────

function ControlCalidadSection() {
  return (
    <div>
      <SectionHeader icon={ShieldCheck} title="Control de Calidad (QC)" subtitle="Bloqueo automatico, inspeccion y aprobacion de stock" />

      <p className="text-sm text-muted-foreground mb-4">
        El sistema de control de calidad permite bloquear automaticamente el stock recibido hasta que pase una inspeccion.
        Esto evita que productos no verificados sean despachados a clientes.
      </p>

      <H2>Como funciona</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'Un tipo de producto tiene activada la opcion "Requiere QC" en Configuracion > Tipos de producto',
          'Al recibir stock de ese producto, el sistema asigna automaticamente el estado pending_qc',
          'El stock pendiente de QC aparece resaltado en la tabla de stock de la bodega',
          'Un usuario con permisos aprueba o rechaza el stock desde los botones de accion',
          'Solo el stock aprobado queda disponible para despacho',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Estados de QC</H2>
      <div className="space-y-2 mb-4">
        {[
          { state: 'pending_qc', desc: 'Stock recibido pendiente de inspeccion. No puede ser despachado ni transferido.', color: 'amber' },
          { state: 'approved', desc: 'Stock inspeccionado y aprobado. Disponible para todas las operaciones.', color: 'emerald' },
          { state: 'rejected', desc: 'Stock rechazado por calidad. Se recomienda ajustar como desperdicio o devolucion.', color: 'red' },
        ].map(({ state, desc, color }) => (
          <div key={state} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{state}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <InfoBox type="warning">
        Intentar despachar stock con estado <Pill color="amber">pending_qc</Pill> genera un error.
        El sistema bloquea la operacion hasta que el stock sea aprobado.
      </InfoBox>

      <H2>Endpoints</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`POST /api/v1/stock/qc-approve   { stock_level_id }
POST /api/v1/stock/qc-reject    { stock_level_id }`}
      </div>
    </div>
  )
}

// ─── Section: Ocupacion ─────────────────────────────────────────────────────

function OcupacionSection() {
  return (
    <div>
      <SectionHeader icon={Activity} title="Ocupacion de Bodegas" subtitle="KPIs de capacidad, ocupacion y stock estancado" />

      <p className="text-sm text-muted-foreground mb-4">
        Los indicadores de ocupacion permiten monitorear el uso real de las bodegas y detectar
        problemas como sobre-almacenamiento o stock sin rotacion.
      </p>

      <H2>KPIs principales</H2>
      <div className="space-y-2 mb-4">
        {[
          { kpi: 'Ubicaciones totales', desc: 'Numero total de ubicaciones hoja (bins) definidas en todas las bodegas.', color: 'slate' },
          { kpi: 'Ubicaciones ocupadas', desc: 'Ubicaciones que contienen al menos un registro de stock activo.', color: 'blue' },
          { kpi: 'Ubicaciones libres', desc: 'Ubicaciones disponibles para recibir mercancia.', color: 'emerald' },
          { kpi: '% Ocupacion global', desc: 'Porcentaje de ocupacion total. Se muestra como barra de progreso en el dashboard.', color: 'indigo' },
          { kpi: 'Stock estancado', desc: 'Cantidad de ubicaciones con stock que no ha tenido movimiento en 90+ dias.', color: 'amber' },
        ].map(({ kpi, desc, color }) => (
          <div key={kpi} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{kpi}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Desglose por bodega</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Ademas del KPI global, el dashboard muestra una barra de ocupacion individual para cada bodega,
        permitiendo identificar rapidamente cuales estan al limite y cuales tienen capacidad disponible.
      </p>

      <H2>Desglose por tipo de ubicacion</H2>
      <p className="text-xs text-muted-foreground mb-3">
        La ocupacion se desglosa por tipo de ubicacion (zona, pasillo, rack, bin) para entender
        en que nivel de la jerarquia se concentra el uso del espacio.
      </p>

      <InfoBox type="info">
        Los KPIs de ocupacion se encuentran en <strong>Inventario &gt; Dashboard</strong> en la seccion
        "Ocupacion de Bodegas". Los datos se actualizan en tiempo real con cada operacion de stock.
      </InfoBox>

      <H2>Endpoint</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`GET /api/v1/analytics/occupation
→ { total_locations, occupied, free, occupation_pct, by_type, by_warehouse, stale_stock }`}
      </div>
    </div>
  )
}

// ─── Section: Portal de Cliente ─────────────────────────────────────────────

function PortalClienteSection() {
  return (
    <div>
      <SectionHeader icon={Eye} title="Portal de Cliente" subtitle="Vista de solo lectura para clientes: stock y pedidos" />

      <p className="text-sm text-muted-foreground mb-4">
        El portal de cliente ofrece una vista de solo lectura donde los clientes pueden consultar
        el stock disponible de sus productos y el estado de sus pedidos.
      </p>

      <H2>Acceder al portal</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'Ir a Inventario > Clientes y seleccionar un cliente',
          'En la pagina de detalle del cliente, click en el boton "Ver Portal"',
          'Se abre la vista de portal con dos pestanas: Stock y Pedidos',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Pestanas del portal</H2>
      <div className="space-y-3 mb-4">
        {[
          { tab: 'Stock', desc: 'Muestra los productos y cantidades disponibles asociados al cliente. Incluye SKU, nombre del producto, bodega y cantidad.' },
          { tab: 'Pedidos', desc: 'Lista las ordenes de venta del cliente con numero, fecha, estado y total. Click en una orden para ver el detalle con sus lineas.' },
        ].map(({ tab, desc }) => (
          <div key={tab} className="rounded-xl border border-border p-4">
            <p className="text-sm font-bold text-foreground mb-1">{tab}</p>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <InfoBox type="success">
        El portal es de <strong>solo lectura</strong> — no permite modificar stock ni crear ordenes.
        Es una herramienta de transparencia para que los clientes puedan consultar su informacion.
      </InfoBox>

      <H2>Endpoints del portal</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`GET /api/v1/portal/stock?customer_id={id}
GET /api/v1/portal/orders?customer_id={id}
GET /api/v1/portal/orders/{order_id}`}
      </div>

      <InfoBox type="info">
        La ruta del portal es <code className="bg-blue-100 rounded px-1">/inventario/portal/:customerId</code>.
        En una futura version se podra compartir un enlace publico para acceso directo del cliente.
      </InfoBox>
    </div>
  )
}

// ─── Section: Clasificacion ABC ─────────────────────────────────────────────

function ClasificacionABCSection() {
  return (
    <div>
      <SectionHeader icon={BarChart3} title="Clasificacion ABC" subtitle="Analisis de Pareto: 80/15/5 por valor de movimiento" />

      <p className="text-sm text-muted-foreground mb-4">
        La clasificacion ABC agrupa automaticamente todos los productos con movimiento
        segun el valor total que representan. Se basa en el principio de Pareto: pocos productos
        concentran la mayor parte del valor.
      </p>

      <H2>Clases</H2>
      <div className="grid grid-cols-3 gap-3 mb-4">
        {[
          { cls: 'A', pct: '~80%', items: '~20%', desc: 'Productos de mayor valor. Requieren control estricto, conteo frecuente y negociacion prioritaria con proveedores.', color: 'red' },
          { cls: 'B', pct: '~15%', items: '~30%', desc: 'Valor intermedio. Control moderado, conteo trimestral.', color: 'amber' },
          { cls: 'C', pct: '~5%', items: '~50%', desc: 'Bajo valor unitario. Control ligero, conteo semestral. Muchos articulos pero poco impacto economico.', color: 'emerald' },
        ].map(({ cls, pct, items, desc, color }) => (
          <div key={cls} className="rounded-xl border border-border p-4">
            <Pill color={color}>Clase {cls}</Pill>
            <p className="text-xs text-muted-foreground mt-2">{desc}</p>
            <p className="text-[11px] text-muted-foreground mt-1">{pct} del valor, {items} de los articulos</p>
          </div>
        ))}
      </div>

      <H2>Como se calcula</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'Se suman los movimientos de cada producto en los ultimos 12 meses (cantidad x costo unitario)',
          'Los productos se ordenan de mayor a menor por valor total',
          'Se calcula el porcentaje acumulado del valor',
          'A = acumulado hasta 80%, B = 80-95%, C = 95-100%',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <InfoBox type="info">
        La clasificacion ABC se muestra en el <strong>Dashboard de Inventario</strong> con una barra apilada
        de colores, resumen por clase y tabla de los 15 productos principales.
      </InfoBox>

      <H2>Aplicaciones practicas</H2>
      <div className="space-y-2">
        {[
          { use: 'Conteo ciclico', desc: 'Productos A se cuentan mensual, B trimestral, C semestral.' },
          { use: 'Negociacion', desc: 'Enfoca esfuerzos de compras y descuentos en productos A.' },
          { use: 'Seguridad', desc: 'Productos A en areas de acceso restringido.' },
          { use: 'Reabastecimiento', desc: 'Pronosticos mas detallados para productos A.' },
        ].map(({ use, desc }) => (
          <div key={use} className="rounded-xl border border-border p-3">
            <p className="text-xs font-bold text-foreground">{use}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Endpoint</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`GET /api/v1/analytics/abc?months=12
→ { period_months, total_products, grand_total_value, summary: { A, B, C }, items[] }`}
      </div>
    </div>
  )
}

// ─── Section: EOQ ───────────────────────────────────────────────────────────

function EOQSection() {
  return (
    <div>
      <SectionHeader icon={Calculator} title="EOQ — Cantidad Optima de Pedido" subtitle="Formula de Wilson para minimizar costos de inventario" />

      <p className="text-sm text-muted-foreground mb-4">
        El EOQ (Economic Order Quantity) calcula la cantidad optima a pedir de cada producto
        para minimizar la suma de costos de pedido y costos de almacenamiento.
      </p>

      <H2>Formula</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`EOQ = √(2 × D × S / H)

D = Demanda anual (unidades vendidas/despachadas en 12 meses)
S = Costo por pedido (costo administrativo de colocar una orden)
H = Costo de mantenimiento por unidad/año = Precio × (% costo mantenimiento)`}
      </div>

      <H2>Parametros de entrada</H2>
      <div className="space-y-2 mb-4">
        {[
          { param: 'Costo por pedido (S)', desc: 'Costo administrativo de generar una orden de compra: horas-hombre, comunicacion, recepcion. Por defecto $50.', color: 'blue' },
          { param: '% Costo mantenimiento (H%)', desc: 'Porcentaje anual del valor del producto que cuesta almacenarlo: espacio, seguros, obsolescencia. Por defecto 25%.', color: 'purple' },
        ].map(({ param, desc, color }) => (
          <div key={param} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{param}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Resultados</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Para cada producto con historial de movimientos, el sistema calcula:
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['eoq', 'Cantidad optima a pedir por orden'],
              ['annual_demand', 'Demanda anual calculada'],
              ['orders_per_year', 'Numero de ordenes optimas al año'],
              ['current_reorder_qty', 'Cantidad actual de reorden (para comparar)'],
              ['total_annual_cost', 'Costo total anual optimo (pedido + almacenamiento)'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <InfoBox type="warning">
        El EOQ asume demanda constante y no considera descuentos por volumen ni lead times variables.
        Usalo como referencia para ajustar tus cantidades de reorden, no como valor absoluto.
      </InfoBox>

      <H2>Endpoint</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`GET /api/v1/analytics/eoq?ordering_cost=50&holding_cost_pct=25
→ { ordering_cost, holding_cost_pct, total_products, items[] }`}
      </div>
    </div>
  )
}

// ─── Section: Politica de Stock ─────────────────────────────────────────────

function PoliticaStockSection() {
  return (
    <div>
      <SectionHeader icon={Target} title="Politica de Stock" subtitle="Control de meses de rotacion por tipo de producto" />

      <p className="text-sm text-muted-foreground mb-4">
        Cada tipo de producto puede tener un <strong>objetivo de meses de rotacion</strong> que define
        cuantos meses de inventario es aceptable mantener. El sistema compara el stock actual contra
        el consumo mensual para detectar excesos.
      </p>

      <H2>Configurar la politica</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'Ir a Inventario > Configuracion > Tipos de producto',
          'Editar un tipo de producto',
          'Establecer el campo "Meses de rotacion objetivo" (ej: 3)',
          'Los productos de ese tipo seran evaluados automaticamente',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Como se calcula</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`Meses en mano = Valor stock actual / Consumo mensual promedio (12 meses)

Estado:
  ok     → Meses en mano <= Objetivo
  excess → Meses en mano > Objetivo (sobre-stock)
  no_data → Sin consumo registrado`}
      </div>

      <H2>Estados</H2>
      <div className="space-y-2 mb-4">
        {[
          { status: 'ok', desc: 'El stock esta dentro del objetivo. Barra de progreso verde.', color: 'emerald' },
          { status: 'excess', desc: 'Sobre-stock detectado. Barra roja con indicacion del exceso en meses.', color: 'red' },
          { status: 'no_data', desc: 'No hay consumo registrado para calcular. Revisar si hay movimientos de salida.', color: 'slate' },
        ].map(({ status, desc, color }) => (
          <div key={status} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{status}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <InfoBox type="info">
        La politica de rotacion se muestra en el <strong>Dashboard de Inventario</strong> como barras
        de progreso por cada tipo de producto que tenga objetivo configurado.
      </InfoBox>
    </div>
  )
}

// ─── Section: Costo de Almacen ──────────────────────────────────────────────

function CostoAlmacenSection() {
  return (
    <div>
      <SectionHeader icon={Building} title="Costo de Almacenamiento" subtitle="Valuacion del costo de almacenar por bodega, m² y ubicacion" />

      <p className="text-sm text-muted-foreground mb-4">
        El modulo calcula el costo mensual de almacenamiento por bodega basado en el costo por metro cuadrado
        y el area total. Permite comparar el costo de almacenamiento contra el valor del inventario almacenado.
      </p>

      <H2>Configurar costos de bodega</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'Ir a Inventario > Bodegas y editar una bodega',
          'Ingresar el "Costo por m²" (costo mensual por metro cuadrado)',
          'Ingresar el "Area total (m²)" de la bodega',
          'El sistema calcula automaticamente el costo mensual y por ubicacion',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>KPIs calculados</H2>
      <div className="space-y-2 mb-4">
        {[
          { kpi: 'Costo mensual', desc: 'Costo por m² × Area total. Costo fijo mensual de la bodega.', color: 'indigo' },
          { kpi: 'Valor en stock', desc: 'Suma del valor (qty × costo) de todo el inventario en la bodega.', color: 'purple' },
          { kpi: 'Almacenamiento/Valor', desc: 'Porcentaje del costo mensual respecto al valor almacenado. Menor es mejor.', color: 'amber' },
          { kpi: 'Costo por ubicacion', desc: 'Costo mensual dividido entre el numero de ubicaciones de la bodega.', color: 'blue' },
        ].map(({ kpi, desc, color }) => (
          <div key={kpi} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{kpi}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <InfoBox type="success">
        Puedes comparar tu costo por m² con operadores logisticos del mercado para evaluar si es mas
        eficiente tener bodega propia o tercerizar el almacenamiento.
      </InfoBox>

      <H2>Endpoint</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`GET /api/v1/analytics/storage-valuation
→ { total_monthly_cost, total_stock_value, storage_to_value_pct, items[] }`}
      </div>
    </div>
  )
}

// ─── Section: Auditoria ─────────────────────────────────────────────────────

function AuditoriaSection() {
  return (
    <div>
      <SectionHeader icon={ClipboardList} title="Auditoria" subtitle="Log de acciones, timeline de actividad y trazabilidad de usuario" />

      <p className="text-sm text-muted-foreground mb-4">
        El sistema de auditoria registra automaticamente cada accion de mutacion (crear, editar, eliminar)
        realizada en el modulo de inventario. Esto incluye quien realizo la accion, cuando, desde que IP
        y los datos anteriores y nuevos del recurso afectado.
      </p>

      <InfoBox type="info">
        La pagina de auditoria esta en <strong>Inventario &gt; Auditoria</strong> y requiere el permiso{' '}
        <Pill color="indigo">inventory.admin</Pill>. El timeline por entidad esta disponible con{' '}
        <Pill color="blue">inventory.view</Pill>.
      </InfoBox>

      <H2>Acciones auditadas</H2>
      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="w-full text-xs">
          <thead className="bg-muted">
            <tr>
              <th className="text-left px-3 py-2 font-semibold text-muted-foreground">Accion</th>
              <th className="text-left px-3 py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['inventory.product.create/update/delete', 'Productos'],
              ['inventory.warehouse.create/update/delete', 'Bodegas'],
              ['inventory.supplier.create/update/delete', 'Proveedores'],
              ['inventory.stock.receive/issue/transfer/adjust/...', 'Movimientos de stock (8 tipos)'],
              ['inventory.po.create/update/send/confirm/cancel/receive', 'Ordenes de compra'],
              ['inventory.so.create/update/confirm/pick/ship/deliver/return/cancel', 'Ordenes de venta'],
              ['inventory.customer.create/update/delete', 'Clientes'],
              ['inventory.customer_type.create/update/delete', 'Tipos de cliente'],
              ['inventory.event.create/update_status/add_impact', 'Eventos e impactos'],
              ['inventory.serial.create/update/delete', 'Seriales'],
              ['inventory.batch.create/update/delete', 'Lotes'],
              ['inventory.recipe.create/update/delete', 'Recetas (BOM)'],
              ['inventory.production.create/execute/finish/approve/reject', 'Corridas de produccion'],
              ['inventory.cycle_count.*', 'Conteos ciclicos (7 acciones)'],
              ['inventory.config.*', 'Configuracion (tipos, campos, estados)'],
            ].map(([action, desc]) => (
              <tr key={action}>
                <td className="px-3 py-2 font-mono text-foreground">{action}</td>
                <td className="px-3 py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Descripciones legibles</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Cada registro de auditoria incluye una <strong>descripcion en espanol</strong> generada automaticamente
        con contexto relevante:
      </p>
      <div className="space-y-2">
        {[
          'Registro entrada de stock — 100 uds, de "Leche", en "Bodega Principal"',
          'Creo orden de venta "SO-2026-0001" — para "Cliente ABC"',
          'Transfirio stock entre bodegas — 50 uds, de "Bodega A" a "Bodega B"',
          'Aprobo conteo ciclico',
        ].map((example, i) => (
          <div key={i} className="rounded-xl bg-muted border border-border px-3 py-2 text-xs text-muted-foreground font-mono">
            {example}
          </div>
        ))}
      </div>

      <H2>Pagina de auditoria</H2>
      <p className="text-xs text-muted-foreground mb-3">
        La pagina principal de auditoria (<strong>Inventario &gt; Auditoria</strong>) permite:
      </p>
      <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1 mb-4">
        <li>Buscar por accion (texto libre)</li>
        <li>Filtrar por tipo de recurso (producto, bodega, proveedor, stock, orden de compra, orden de venta, cliente, etc.)</li>
        <li>Filtrar por rango de fechas</li>
        <li>Expandir cada fila para ver el diff visual (datos anteriores vs nuevos)</li>
        <li>Paginacion de 25 registros por pagina</li>
      </ul>

      <H2>Timeline de actividad</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Cada entidad del inventario tiene un timeline de actividad que muestra el historial completo
        de acciones realizadas sobre ella. Este timeline se encuentra disponible en las paginas de detalle
        y se alimenta del endpoint <code className="bg-secondary rounded px-1">GET /api/v1/audit/entity/&#123;tipo&#125;/&#123;id&#125;</code>.
      </p>

      <H2>Campos created_by / updated_by</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Todas las tablas principales del inventario incluyen los campos <code className="bg-secondary rounded px-1">created_by</code> y{' '}
        <code className="bg-secondary rounded px-1">updated_by</code> que guardan el ID del usuario que realizo la accion.
        Estos campos se muestran en las tablas de listado como columna "Creado por" con el nombre completo del usuario resuelto.
      </p>

      <InfoBox type="success">
        Los nombres de usuario se resuelven automaticamente mediante el user-service. Si el usuario no se encuentra,
        se muestra un ID truncado como fallback.
      </InfoBox>
    </div>
  )
}

// ─── Section: Impuestos ─────────────────────────────────────────────────────

function ImpuestosSection() {
  return (
    <div>
      <SectionHeader icon={Receipt} title="Impuestos" subtitle="IVA, retención en la fuente, ICA y códigos DIAN" />

      <InfoBox type="info">
        Las tarifas de impuesto son configurables por tenant. Se usan en las ordenes de venta para calcular
        automaticamente el IVA y la retencion en la fuente de cada linea.
      </InfoBox>

      <H2>Tipos de impuesto</H2>
      <div className="space-y-2 mb-4">
        {[
          { type: 'IVA', desc: 'Impuesto al Valor Agregado. Tarifas tipicas Colombia: 0%, 5%, 19%.', color: 'indigo' },
          { type: 'Retención', desc: 'Retención en la fuente. Varía según actividad economica del proveedor/cliente.', color: 'purple' },
          { type: 'ICA', desc: 'Impuesto de Industria y Comercio. Tarifa municipal.', color: 'blue' },
        ].map(({ type, desc, color }) => (
          <div key={type} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{type}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Campos de una tarifa</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['name', 'Nombre descriptivo (ej: "IVA 19%")'],
              ['tax_type', 'Tipo: iva, retention o ica'],
              ['rate', 'Tarifa decimal (ej: 0.19 = 19%)'],
              ['dian_code', 'Codigo DIAN asociado (opcional)'],
              ['is_default', 'Si es la tarifa por defecto para su tipo'],
              ['description', 'Descripcion adicional'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Inicializar tarifas Colombia</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Si no hay tarifas configuradas, el boton <Pill color="emerald">Inicializar Colombia</Pill> crea las tarifas
        estandar colombianas: IVA 0%, 5%, 19% y retenciones comunes.
      </p>

      <H2>Uso en ordenes de venta</H2>
      <InfoBox type="success">
        Al agregar una linea a una OV, puedes seleccionar la tarifa de IVA y la retencion.
        El sistema calcula automaticamente los montos de impuesto y los totales.
        Los productos pueden tener un <code className="bg-emerald-100 rounded px-1">tax_rate_id</code> por defecto
        y la marca <code className="bg-emerald-100 rounded px-1">is_tax_exempt</code>.
      </InfoBox>
    </div>
  )
}

// ─── Section: Precios Especiales ────────────────────────────────────────────

function PreciosClientesSection() {
  return (
    <div>
      <SectionHeader icon={CreditCard} title="Precios Especiales por Cliente" subtitle="Precios preferenciales individuales con vigencia" />

      <InfoBox type="info">
        Los <strong>precios especiales</strong> permiten definir un precio preferencial para un cliente y producto especifico,
        con fecha de vigencia. Es el unico mecanismo de precios diferenciados: si existe un precio especial vigente, se usa;
        de lo contrario, se aplica el precio base del producto.
      </InfoBox>

      <H2>Crear un precio especial</H2>
      <div className="flex flex-col gap-2 mt-1">
        {[
          'Ir a Inventario > Precios Especiales',
          'Click en "Nuevo Precio"',
          'Seleccionar cliente y producto',
          'Ingresar precio unitario especial',
          'Establecer fechas de vigencia (válido desde / hasta)',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>KPIs de la pagina</H2>
      <div className="space-y-2 mb-4">
        {[
          { kpi: 'Total activos', desc: 'Numero de precios especiales vigentes.', color: 'emerald' },
          { kpi: 'Clientes con precio', desc: 'Cantidad de clientes que tienen al menos un precio especial.', color: 'blue' },
          { kpi: 'Vence pronto', desc: 'Precios que vencen en los proximos 30 dias.', color: 'amber' },
        ].map(({ kpi, desc, color }) => (
          <div key={kpi} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{kpi}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Renovar un precio</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Cuando un precio especial esta proximo a vencer, puedes <strong>renovarlo</strong> desde el icono de
        renovacion. Se crea un nuevo registro con el mismo precio y nuevas fechas de vigencia.
      </p>

      <H2>Prioridad de precios</H2>
      <InfoBox type="success">
        Al crear una OV, el sistema resuelve el precio en este orden de prioridad:<br/>
        1. <strong>Precio especial</strong> vigente para ese cliente y producto (customer_special)<br/>
        2. <strong>Precio base</strong> del producto (product_base)
      </InfoBox>
    </div>
  )
}

// ─── Section: Escaner ───────────────────────────────────────────────────────

function EscanerSection() {
  return (
    <div>
      <SectionHeader icon={ScanBarcode} title="Escáner" subtitle="Lectura de código de barras y acciones rápidas de stock" />

      <p className="text-sm text-muted-foreground mb-4">
        La pagina de escaner permite buscar productos por codigo de barras (o SKU) y ejecutar
        operaciones de stock de forma rapida sin navegar por multiples paginas.
      </p>

      <H2>Como funciona</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'Ir a Inventario > Escáner',
          'Enfocar el campo de busqueda (auto-focus)',
          'Escanear un código de barras con lector físico o escribir el SKU',
          'El producto se identifica automáticamente y se muestra su info',
          'Elegir acción rápida: Recibir, Despachar o Transferir',
          'Completar cantidad y bodega, confirmar operación',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Acciones rapidas</H2>
      <div className="space-y-2 mb-4">
        {[
          { action: 'Recibir', desc: 'Ingresa stock del producto en una bodega seleccionada.', color: 'emerald' },
          { action: 'Despachar', desc: 'Saca stock de la bodega (movimiento de salida).', color: 'red' },
          { action: 'Transferir', desc: 'Mueve stock entre dos bodegas.', color: 'blue' },
        ].map(({ action, desc, color }) => (
          <div key={action} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{action}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Feedback auditivo</H2>
      <InfoBox type="success">
        El escaner emite un <strong>beep de exito</strong> (tono agudo) cuando identifica el producto correctamente,
        y un <strong>beep de error</strong> (tono grave) cuando no lo encuentra. Esto permite operar sin mirar la pantalla.
      </InfoBox>

      <H2>Historial de escaneos</H2>
      <p className="text-xs text-muted-foreground">
        Cada escaneo se registra en un historial en pantalla con timestamp, codigo y producto.
        El historial se mantiene durante la sesion y se reinicia al cambiar de pagina.
      </p>
    </div>
  )
}

// ─── Section: Picking ───────────────────────────────────────────────────────

function PickingSection() {
  return (
    <div>
      <SectionHeader icon={ListChecks} title="Picking" subtitle="Preparación de pedidos linea por linea desde bodega" />

      <p className="text-sm text-muted-foreground mb-4">
        La pagina de Picking es el centro de trabajo del operador de bodega. Muestra las ordenes
        de venta listas para preparar y permite verificar cada linea durante el alistamiento.
      </p>

      <H2>Cola de picking</H2>
      <p className="text-xs text-muted-foreground mb-3">
        La cola muestra las OV en estado <Pill color="blue">confirmed</Pill> y <Pill color="amber">picking</Pill>.
        Las que ya estan en picking se muestran primero.
      </p>

      <H2>Flujo de picking</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'Seleccionar una OV confirmada de la cola',
          'Click en "Iniciar Picking" — la OV pasa a estado picking',
          'Para cada linea: verificar producto, ubicacion y cantidad',
          'Marcar cada linea como pickeada conforme se prepara',
          'Al completar todas las lineas, click en "Despachar"',
          'La OV pasa a shipped y el stock se descuenta de la bodega',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Informacion mostrada</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Dato</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['Producto + SKU', 'Nombre y SKU del producto a preparar'],
              ['Cantidad', 'Unidades a despachar segun la OV'],
              ['Bodega', 'Bodega de origen de la mercancia'],
              ['Ubicacion', 'Ubicacion exacta (zona/pasillo/rack/bin) si aplica'],
              ['Stock disponible', 'Stock actual vs cantidad solicitada'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <InfoBox type="warning">
        Solo los usuarios con permiso <Pill color="indigo">inventory.manage</Pill> pueden iniciar y completar el picking.
        Es importante verificar las cantidades fisicamente antes de marcar una linea como completa.
      </InfoBox>
    </div>
  )
}

// ─── Section: Aprobaciones ──────────────────────────────────────────────────

function AprobacionesSection() {
  return (
    <div>
      <SectionHeader icon={BadgeCheck} title="Aprobaciones Pendientes" subtitle="Aprobación de ordenes de venta por monto" />

      <p className="text-sm text-muted-foreground mb-4">
        Cuando una orden de venta supera el umbral de aprobacion configurado para el tenant,
        requiere aprobacion de un segundo usuario antes de poder confirmarla.
      </p>

      <H2>Principio de 4 ojos</H2>
      <InfoBox type="warning">
        El usuario que <strong>creo</strong> la OV no puede aprobarla. Esto garantiza que siempre
        haya dos personas involucradas en la aprobacion de ordenes grandes, previniendo fraude.
      </InfoBox>

      <H2>KPIs de la pagina</H2>
      <div className="space-y-2 mb-4">
        {[
          { kpi: 'Pendientes', desc: 'Total de OV esperando aprobacion', color: 'amber' },
          { kpi: 'Urgentes (>4h)', desc: 'Llevan mas de 4 horas esperando — requieren atencion inmediata', color: 'red' },
          { kpi: 'Demoradas (1-4h)', desc: 'Llevan entre 1 y 4 horas esperando', color: 'amber' },
          { kpi: 'Recientes (<1h)', desc: 'Solicitudes recientes, aun dentro del tiempo normal', color: 'emerald' },
        ].map(({ kpi, desc, color }) => (
          <div key={kpi} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{kpi}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Aprobar o rechazar</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'Ir a Inventario > Aprobaciones',
          'Ver la lista de OV pendientes con numero, cliente, total y tiempo de espera',
          'Para aprobar: click en el boton verde de check',
          'Para rechazar: click en el boton rojo, ingresar motivo de rechazo',
          'La OV aprobada pasa a confirmed; la rechazada pasa a rejected',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Log de aprobaciones</H2>
      <p className="text-xs text-muted-foreground">
        Cada accion de aprobacion o rechazo queda registrada en la tabla <code className="bg-secondary rounded px-1">so_approval_logs</code>
        con quien la ejecuto, cuando, el motivo (si fue rechazo) y el total de la OV al momento de la accion.
      </p>

      <H2>Configurar el umbral</H2>
      <InfoBox type="info">
        El umbral se configura por tenant en <strong>Inventario &gt; Configuracion</strong> como el campo
        <code className="bg-blue-100 rounded px-1 ml-1">so_approval_threshold</code>. Si no se configura o se deja en 0,
        la aprobacion no es requerida.
      </InfoBox>
    </div>
  )
}

// ─── Section: Reorden Automatico ────────────────────────────────────────────

function ReordenSection() {
  return (
    <div>
      <SectionHeader icon={RefreshCw} title="Reorden Automático" subtitle="Generación automática de OC cuando el stock baja del punto de reorden" />

      <p className="text-sm text-muted-foreground mb-4">
        El modulo de reorden automatico monitorea los productos que tienen configurado un punto de reorden
        y un proveedor preferido. Cuando el stock disponible cae por debajo del punto de reorden,
        genera automaticamente una orden de compra borrador.
      </p>

      <H2>Requisitos del producto</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Para que un producto participe en el reorden automatico, debe tener configurados:
      </p>
      <div className="space-y-2 mb-4">
        {[
          { field: 'reorder_point', desc: 'Nivel de stock que dispara la reorden (punto de pedido)', color: 'amber' },
          { field: 'auto_reorder', desc: 'Flag activado (true) — habilita el reorden automatico', color: 'emerald' },
          { field: 'preferred_supplier_id', desc: 'Proveedor preferido al que se enviara la OC', color: 'blue' },
        ].map(({ field, desc, color }) => (
          <div key={field} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{field}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Como funciona</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'Ir a Inventario > Reorden Automático',
          'Ver los productos con reorden configurado, su stock actual y punto de reorden',
          'Los productos bajo su punto de reorden aparecen resaltados',
          'Click en "Ejecutar Reorden" para verificar todos los productos y generar POs',
          'El sistema crea una PO borrador por cada proveedor que tenga productos pendientes',
          'Las POs creadas se pueden revisar y enviar desde Ordenes de Compra',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>KPIs</H2>
      <div className="space-y-2 mb-4">
        {[
          { kpi: 'Productos con reorden', desc: 'Total de productos que tienen reorden automatico activado', color: 'blue' },
          { kpi: 'Bajo punto de reorden', desc: 'Productos cuyo stock actual esta por debajo del reorder_point', color: 'red' },
          { kpi: 'En nivel normal', desc: 'Productos con stock por encima del punto de reorden', color: 'emerald' },
        ].map(({ kpi, desc, color }) => (
          <div key={kpi} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{kpi}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <InfoBox type="success">
        Tambien puedes ejecutar la verificacion para un <strong>producto individual</strong> haciendo click
        en el boton de reorden de cada fila. Esto es util para forzar una PO para un producto especifico.
      </InfoBox>

      <H2>Endpoints</H2>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`GET  /api/v1/reorder/config          → Lista productos con reorden configurado
POST /api/v1/reorder/check-all       → Ejecuta verificacion global y crea POs
POST /api/v1/reorder/check/{product_id} → Verifica un producto individual`}
      </div>
    </div>
  )
}

// ─── Section: Recetas ───────────────────────────────────────────────────────

function RecetasSection() {
  return (
    <div>
      <SectionHeader icon={FlaskConical} title="Recetas (BOM)" subtitle="Composición de productos y verificacion de disponibilidad" />

      <p className="text-sm text-muted-foreground mb-4">
        Las recetas (Bill of Materials) definen los componentes necesarios para fabricar un producto terminado.
        La pagina de recetas permite gestionar las recetas independientemente de la produccion.
      </p>

      <H2>Crear una receta</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'Ir a Inventario > Recetas',
          'Click en "Nueva receta"',
          'Seleccionar el producto resultado (terminado)',
          'Agregar componentes: producto, cantidad requerida',
          'Establecer la cantidad de rendimiento (yield)',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Disponibilidad de componentes</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Cada receta muestra en tiempo real si tiene todos los componentes disponibles en inventario:
      </p>
      <div className="space-y-2 mb-4">
        {[
          { status: 'Disponible', desc: 'Todos los componentes tienen stock suficiente para al menos una corrida.', color: 'emerald' },
          { status: 'N sin stock', desc: 'Uno o más componentes no tienen stock suficiente. Muestra cuántos faltan.', color: 'red' },
        ].map(({ status, desc, color }) => (
          <div key={status} className="flex gap-3 items-start rounded-xl border border-border p-3">
            <Pill color={color}>{status}</Pill>
            <p className="text-xs text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>

      <H2>Detalle de receta</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Al expandir o ver el detalle de una receta, se muestra:
      </p>
      <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1 mb-4">
        <li>Producto resultado y cantidad de rendimiento</li>
        <li>Lista de componentes con cantidad requerida y stock actual</li>
        <li>Disponibilidad por bodega (en que bodegas hay stock de cada componente)</li>
        <li>Indicador visual de componentes faltantes</li>
      </ul>

      <InfoBox type="info">
        Las recetas son la base para las <strong>corridas de produccion</strong>. Una corrida consume
        los componentes y genera el producto terminado. Ver la seccion <strong>Produccion</strong> para mas detalle.
      </InfoBox>
    </div>
  )
}

// ─── Section: Categorias ────────────────────────────────────────────────────

function CategoriasSection() {
  return (
    <div>
      <SectionHeader icon={FolderTree} title="Categorías" subtitle="Arbol jerarquico de categorias de producto" />

      <p className="text-sm text-muted-foreground mb-4">
        Las categorias permiten organizar los productos en una estructura jerarquica de arbol.
        Cada categoria puede tener sub-categorias, formando una taxonomia natural.
      </p>

      <H2>Crear una categoria</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'Ir a Inventario > Categorías',
          'Click en "Nueva categoría"',
          'Ingresar nombre y descripcion',
          'Opcionalmente seleccionar una categoria padre (para crear sub-categorias)',
          'Click en "Crear"',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Jerarquia</H2>
      <div className="rounded-xl border border-primary/30 bg-primary/5 p-4 mb-4">
        <p className="text-sm font-bold text-primary mb-2">Ejemplo de arbol</p>
        <div className="text-xs text-muted-foreground font-mono space-y-0.5">
          <p>Alimentos</p>
          <p className="ml-4">├─ Lacteos</p>
          <p className="ml-8">├─ Leches</p>
          <p className="ml-8">└─ Quesos</p>
          <p className="ml-4">├─ Carnes</p>
          <p className="ml-4">└─ Bebidas</p>
          <p>Aseo</p>
          <p className="ml-4">├─ Detergentes</p>
          <p className="ml-4">└─ Jabones</p>
        </div>
      </div>

      <H2>Campos</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['name', 'Nombre de la categoria'],
              ['description', 'Descripcion opcional'],
              ['parent_id', 'Categoria padre (null para raiz)'],
              ['is_active', 'Si la categoria esta activa'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <InfoBox type="success">
        Las categorias forman un arbol jerarquico para organizar productos. Un producto pertenece a una sola categoria.
      </InfoBox>
    </div>
  )
}

// ─── Section: Facturacion Electronica ───────────────────────────────────────

function FacturacionSection() {
  return (
    <div>
      <SectionHeader icon={FileText} title="Facturación Electrónica" subtitle="CUFE, DIAN, sandbox, notas crédito y remisiones" />

      <p className="text-sm text-muted-foreground mb-4">
        El modulo de facturacion electronica permite emitir facturas ante la DIAN (Colombia),
        generar notas credito para devoluciones y gestionar remisiones de entrega.
      </p>

      <H2>Flujo de facturacion</H2>
      <div className="flex flex-col gap-2 mt-1 mb-4">
        {[
          'La OV llega a estado shipped o delivered',
          'Desde el detalle de la OV, click en "Emitir Factura"',
          'El sistema envia la factura al proveedor de facturacion (ej: FacturAPI)',
          'La DIAN valida y retorna el CUFE (Codigo Unico de Factura Electronica)',
          'La factura queda registrada con numero, CUFE, URL del PDF y estado',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3 text-xs text-muted-foreground">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/15 text-primary font-bold shrink-0 text-[10px]">{i + 1}</span>
            {step}
          </div>
        ))}
      </div>

      <H2>Campos de factura en la OV</H2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['cufe', 'Codigo Unico de Factura Electronica (DIAN)'],
              ['invoice_number', 'Numero consecutivo de factura'],
              ['invoice_pdf_url', 'URL del PDF de la factura generada'],
              ['invoice_status', 'Estado: pending, sent, accepted, rejected'],
              ['invoice_remote_id', 'ID en el proveedor externo de facturacion'],
              ['invoice_provider', 'Proveedor usado (ej: facturapi, siigo)'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Notas credito</H2>
      <p className="text-xs text-muted-foreground mb-3">
        Cuando una OV se devuelve (estado <Pill color="slate">returned</Pill>), se puede emitir una
        <strong> nota credito</strong> que anula total o parcialmente la factura original:
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4 font-semibold text-muted-foreground">Campo</th>
              <th className="text-left py-2 font-semibold text-muted-foreground">Descripcion</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[
              ['credit_note_cufe', 'CUFE de la nota credito'],
              ['credit_note_number', 'Numero de la nota credito'],
              ['credit_note_remote_id', 'ID en el proveedor externo'],
              ['credit_note_status', 'Estado de la nota credito'],
            ].map(([field, desc]) => (
              <tr key={field}>
                <td className="py-2 pr-4 font-mono font-semibold text-foreground">{field}</td>
                <td className="py-2 text-muted-foreground">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <H2>Sandbox de facturacion</H2>
      <InfoBox type="info">
        La pagina <strong>Facturacion Electronica &gt; Sandbox</strong> permite generar facturas de prueba
        en formato PDF sin enviar a la DIAN. Es util para verificar que los datos son correctos antes de
        emitir facturas reales. Genera un PDF local usando <code className="bg-blue-100 rounded px-1">jsPDF</code>.
      </InfoBox>

      <H2>Resolución de facturación</H2>
      <p className="text-xs text-muted-foreground mb-3">
        La DIAN asigna resoluciones de facturacion a cada empresa. La pagina de <strong>Resolución</strong> permite
        configurar el prefijo, rango de numeracion (desde/hasta), fecha de vigencia y estado de la resolucion
        por tenant. Esto controla los consecutivos de las facturas emitidas.
      </p>

      <H2>Remision (guia de despacho)</H2>
      <p className="text-xs text-muted-foreground mb-3">
        La remision es el documento que acompana la mercancia durante el despacho. Se genera como PDF
        e incluye: numero de remision, fecha, datos del cliente, direccion de entrega, lista de productos
        con cantidades y espacio para firma de recibido.
      </p>
      <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-xs font-mono overflow-x-auto my-3 leading-relaxed">
        {`POST /api/v1/sales-orders/{id}/remission → Genera numero de remision
Frontend: generateRemissionPDF() → Genera PDF local con jsPDF`}
      </div>

      <H2>Paginas relacionadas</H2>
      <div className="space-y-2">
        {[
          { name: 'Facturación Electrónica', path: '/facturacion-electronica', desc: 'Lista de facturas emitidas, reintentos y estados' },
          { name: 'Sandbox', path: '/facturacion-electronica-sandbox', desc: 'Generador de facturas de prueba en PDF' },
          { name: 'Resolución', path: '/facturacion-electronica/resolucion', desc: 'Configuracion de resoluciones DIAN por tenant' },
        ].map(({ name, path, desc }) => (
          <div key={name} className="rounded-xl border border-border p-3">
            <p className="text-xs font-bold text-foreground">{name} <span className="text-[11px] text-muted-foreground ml-1">{path}</span></p>
            <p className="text-[11px] text-muted-foreground mt-0.5">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Nav sidebar ─────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { section: '',               icon: BookOpen,              label: 'Inicio' },
  { section: 'productos',      icon: Package,               label: 'Productos' },
  { section: 'variantes',      icon: SplitSquareVertical,  label: 'Variantes' },
  { section: 'bodegas',        icon: Warehouse,             label: 'Bodegas' },
  { section: 'stock',          icon: Boxes,                 label: 'Stock y Niveles' },
  { section: 'movimientos',    icon: ArrowLeftRight,        label: 'Movimientos' },
  { section: 'proveedores',    icon: Truck,                 label: 'Proveedores' },
  { section: 'compras',        icon: ShoppingCart,           label: 'Ordenes de Compra' },
  { section: 'clientes',       icon: Users,                 label: 'Clientes' },
  { section: 'ventas',         icon: Receipt,               label: 'Ordenes de Venta' },
  { section: 'precios',        icon: DollarSign,            label: 'Precios Especiales' },
  { section: 'conteo-ciclico', icon: ClipboardCheck,        label: 'Conteo Ciclico' },
  { section: 'eventos',        icon: AlertTriangle,         label: 'Eventos' },
  { section: 'alertas',        icon: Bell,                  label: 'Alertas de Stock' },
  { section: 'kardex',         icon: BookMarked,            label: 'Kardex' },
  { section: 'seriales',       icon: Hash,                  label: 'Seriales' },
  { section: 'lotes',          icon: Layers,                label: 'Lotes' },
  { section: 'produccion',     icon: Factory,               label: 'Produccion' },
  { section: 'control-calidad',  icon: ShieldCheck,           label: 'Control de Calidad' },
  { section: 'ocupacion',       icon: Activity,              label: 'Ocupacion' },
  { section: 'portal-cliente',  icon: Eye,                   label: 'Portal de Cliente' },
  { section: 'clasificacion-abc', icon: BarChart3,            label: 'Clasificacion ABC' },
  { section: 'eoq',             icon: Calculator,            label: 'EOQ' },
  { section: 'politica-stock',  icon: Target,                label: 'Politica de Stock' },
  { section: 'costo-almacen',   icon: Building,              label: 'Costo de Almacen' },
  { section: 'impuestos',         icon: Receipt,               label: 'Impuestos' },
  { section: 'precios-clientes', icon: CreditCard,            label: 'Precios Especiales' },
  { section: 'escaner',          icon: ScanBarcode,           label: 'Escáner' },
  { section: 'picking',          icon: ListChecks,            label: 'Picking' },
  { section: 'aprobaciones',     icon: BadgeCheck,            label: 'Aprobaciones' },
  { section: 'reorden',          icon: RefreshCw,             label: 'Reorden Automático' },
  { section: 'recetas',          icon: FlaskConical,          label: 'Recetas (BOM)' },
  { section: 'categorias',       icon: FolderTree,            label: 'Categorías' },
  { section: 'facturacion',      icon: FileText,              label: 'Facturación' },
  { section: 'reportes',       icon: FileDown,              label: 'Reportes' },
  { section: 'importacion',    icon: Upload,                label: 'Importacion' },
  { section: 'auditoria',      icon: ClipboardList,         label: 'Auditoria' },
  { section: 'configuracion',  icon: Settings2,             label: 'Configuracion' },
]

const SECTION_COMPONENTS: Record<string, React.ReactNode> = {
  '':               <OverviewSection />,
  'productos':      <ProductosSection />,
  'variantes':      <VariantesSection />,
  'bodegas':        <BodegasSection />,
  'stock':          <StockSection />,
  'movimientos':    <MovimientosSection />,
  'proveedores':    <ProveedoresSection />,
  'compras':        <ComprasSection />,
  'clientes':       <ClientesSection />,
  'ventas':         <VentasSection />,
  'precios':        <PreciosSection />,
  'conteo-ciclico': <ConteoCliclicoSection />,
  'eventos':        <EventosSection />,
  'alertas':        <AlertasSection />,
  'kardex':         <KardexSection />,
  'seriales':       <SerialesSection />,
  'lotes':          <LotesSection />,
  'produccion':     <ProduccionSection />,
  'control-calidad':  <ControlCalidadSection />,
  'ocupacion':        <OcupacionSection />,
  'portal-cliente':   <PortalClienteSection />,
  'clasificacion-abc': <ClasificacionABCSection />,
  'eoq':              <EOQSection />,
  'politica-stock':   <PoliticaStockSection />,
  'costo-almacen':    <CostoAlmacenSection />,
  'impuestos':         <ImpuestosSection />,
  'precios-clientes':  <PreciosClientesSection />,
  'escaner':           <EscanerSection />,
  'picking':           <PickingSection />,
  'aprobaciones':      <AprobacionesSection />,
  'reorden':           <ReordenSection />,
  'recetas':           <RecetasSection />,
  'categorias':        <CategoriasSection />,
  'facturacion':       <FacturacionSection />,
  'reportes':       <ReportesSection />,
  'importacion':    <ImportacionSection />,
  'auditoria':      <AuditoriaSection />,
  'configuracion':  <ConfiguracionSection />,
}

// ─── Page ────────────────────────────────────────────────────────────────────

export function InventoryHelpPage() {
  const { section = '' } = useParams<{ section?: string }>()
  const currentItem = NAV_ITEMS.find((n) => n.section === section) ?? NAV_ITEMS[0]
  const Content = SECTION_COMPONENTS[section] ?? SECTION_COMPONENTS['']

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <Topbar title="Inventario — Ayuda" subtitle={currentItem.label} />
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar nav */}
        <nav className="w-52 shrink-0 border-r border-border overflow-y-auto py-4 px-2 bg-muted/50">
          {NAV_ITEMS.map(({ section: s, icon: Icon, label }) => (
            <NavLink
              key={s}
              to={s ? `/inventario/ayuda/${s}` : '/inventario/ayuda'}
              end={!s}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-semibold transition-all mb-0.5 ${
                  isActive
                    ? 'text-primary bg-card  ring-1 ring-ring/20'
                    : 'text-muted-foreground hover:bg-card/70 hover:text-foreground'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-3xl">
            {Content}
          </div>
        </div>
      </div>
    </div>
  )
}
