# TraceLog — Servicios para Clientes

**Fecha:** 31 de marzo de 2026

---

## Resumen Ejecutivo

TraceLog es una plataforma SaaS que ofrece 6 modulos activables para empresas exportadoras, fabricantes y comercializadoras. Cada modulo funciona independiente y se conecta con los demas. El cliente activa lo que necesita y paga solo por lo que usa.

---

## Modulo 1: Inventario

**Precio:** Desde $29 USD/mes
**Para quien:** Cualquier empresa que maneje productos fisicos

### Que incluye:

**Productos**
- Catalogo de productos con SKU, categorias, imagenes y variantes
- Lotes (EntityBatch) con fecha de fabricacion, vencimiento y costo
- Seriales (EntitySerial) con estado individual por unidad
- Campos personalizados por tipo de producto

**Stock**
- Control de stock por producto + bodega + ubicacion
- Movimientos: compra, venta, traslado, ajuste, devolucion, merma
- Reservas automaticas al confirmar ordenes de venta
- Valorizacion: FIFO, FEFO, LIFO, promedio ponderado
- Kardex (historial valorizado de cada movimiento)
- Clasificacion ABC por valor y rotacion
- Alertas de stock bajo y punto de reorden
- Auto-reorden configurable

**Bodegas**
- Multi-bodega con tipos configurables (principal, secundaria, transito, virtual)
- Ubicaciones jerarquicas (pasillo, estante, posicion)
- Area, costo por m2, capacidad maxima
- Conteo ciclico (CycleCount) con aprobacion
- Scanner de codigo de barras para movimientos rapidos
- Picking de pedidos

**Compras**
- Ordenes de compra con flujo: borrador → enviada → confirmada → parcial → recibida
- Recepcion parcial de ordenes
- Aprobaciones por monto
- Consolidacion de ordenes
- Historial de precios de compra por proveedor

**Ventas**
- Ordenes de venta con flujo: borrador → confirmada → picking → despachada → entregada
- Remision fiscal con impuestos
- Notas credito y debito
- Backorders y devoluciones
- Precios especiales por cliente
- Portal de autoservicio del cliente

**Socios Comerciales**
- Registro maestro de proveedores y clientes (BusinessPartner)
- Datos fiscales: NIT, contacto, terminos de pago, credito
- Evaluacion y scoring de proveedores
- Tipos configurables (distribuidor, fabricante, importador, etc.)

**Impuestos y Medidas**
- Tasas de impuesto: IVA, retencion, ICA (seed Colombia)
- Unidades de medida con conversiones (kg, lb, ton, etc.)

**Reportes**
- Descarga CSV: productos, stock, movimientos, proveedores
- Rentabilidad (P&L) por producto
- Rotacion por tipo y top 10 por valor
- Ocupacion de bodegas

---

## Modulo 2: Produccion

**Precio:** Desde $39 USD/mes
**Requiere:** Inventario
**Para quien:** Fabricantes, procesadores de alimentos, laboratorios

### Que incluye:

**Recetas (BOM)**
- Bill of Materials con componentes y cantidades
- Versiones de receta (v1, v2, v3) con fecha de vigencia
- Sub-ensambles recursivos (receta dentro de receta)
- Costo estandar calculado automaticamente
- Porcentaje de desperdicio configurable
- Tamano de produccion planificado

**Corridas de Produccion**
- Flujo completo: planeada → liberada → en proceso → completada → cerrada
- Al liberar: reserva automatica de materiales en bodega
- Emisiones: consumo FIFO de componentes del inventario
- Recibos: generacion de producto terminado con capas de costo
- Cierre: calculo de varianza real vs estandar
- Soporte de desensamble (proceso inverso)

**Recursos**
- Maquinas, mano de obra y equipos con tarifa por hora
- Capacidad disponible por recurso
- Costo de recursos asignado a cada corrida
- Verificacion de capacidad antes de liberar

**MRP (Planificacion de Requerimientos)**
- Explosion recursiva de BOM
- Calculo de necesidades netas (demanda - stock - en proceso)
- Generacion automatica de ordenes de compra para faltantes
- Soporte de sub-ensambles en la explosion

---

## Modulo 3: Logistica + Blockchain

**Precio:** Incluido en todos los planes
**Para quien:** Transportistas, operadores logisticos, exportadores

### Que incluye:

**Activos Trazables (Assets)**
- Cada carga es un activo con historial completo
- Estado: en custodia, en transito, cargado, QC, liberado, quemado
- Vinculo con productos de inventario (referencia logica)
- Minting de cNFT en Solana (opcional, para trazabilidad blockchain)

**Cadena de Custodia**
- Eventos: handoff, arrived, loaded, qc, release, burn
- Maquina de estados validada (no se puede saltar pasos)
- Timeline visual de quien tuvo el activo, cuando y donde
- Cada evento se ancla en blockchain (Solana) de forma inmutable

**Custodios (Wallets)**
- Registro de actores logisticos: finca, bodega, camion, aduana, distribuidor
- Generacion de keypair Solana para custodios
- Tipos de custodian configurables por empresa

**Organizaciones**
- Entidades en la cadena logistica (fabricante, transportista, distribuidor)
- Vinculo con socios comerciales de inventario

**Tracking Board**
- Kanban visual por estado del workflow
- Auto-refresh cada 30 segundos
- Filtro por organizacion

**Workflow Configurable**
- Estados y transiciones personalizables por empresa
- Tipos de evento renombrables
- Presets por industria: logistics, pharma, coldchain, retail, construction

**Documentos de Transporte**
- BL (Bill of Lading), AWB, carta de porte, guia terrestre
- Documentos de comercio exterior: cert. origen, fitosanitario, INVIMA, DEX, DIM
- Seguro de carga

**Verificacion Publica**
- Cualquier persona verifica un activo o certificado con un link publico
- No requiere cuenta ni login
- Muestra cadena completa con prueba blockchain

---

## Modulo 4: Cumplimiento EUDR

**Precio:** Desde $49 USD/mes
**Requiere:** Logistica
**Para quien:** Exportadores de cafe, cacao, madera, caucho, palma, soya, ganado a Europa

### Que incluye:

**Marcos Normativos**
- EUDR (Reglamento UE 2023/1115)
- USDA Organic
- FSSAI (India)
- Cada empresa activa los marcos que necesita

**Parcelas (Plots)**
- Registro de fincas con coordenadas GPS o poligono GeoJSON
- Area en hectareas
- Verificacion automatica contra datos satelitales de Global Forest Watch (GFW)
- Evaluacion de riesgo de deforestacion

**Registros (Records)**
- Declaracion de diligencia debida (DDS) por carga
- Asociacion de parcela + proveedor + lote + ruta
- Validacion automatica contra reglas del marco normativo
- Estado: borrador, pendiente, aprobado, rechazado

**Certificados**
- Generacion automatica en PDF con diseño profesional
- Codigo QR para verificacion instantanea
- Verificacion publica por URL (sin login)
- Anclaje en blockchain Solana para inmutabilidad
- Numeracion unica por certificado

**Evaluacion de Riesgo**
- Scoring por parcela y por proveedor
- Factores: deforestacion, documentacion, historial
- Recomendaciones de accion

**Cadena de Suministro**
- Modelado de nodos de la cadena (finca → acopio → beneficio → exportador)
- Trazabilidad de punta a punta

**Conexiones Externas**
- Global Forest Watch (GFW) — datos satelitales de deforestacion
- TRACES NT (sistema oficial de la UE) — conexion directa (credenciales configurables)

---

## Modulo 5: Facturacion Electronica DIAN

**Precio:** Desde $19 USD/mes
**Requiere:** Inventario
**Para quien:** Cualquier empresa colombiana que facture

### Que incluye:

**Facturas Electronicas**
- Emision ante la DIAN via proveedor MATIAS
- Numeracion automatica con resolucion
- Modo sandbox (pruebas) y modo produccion
- PDF de la factura generado automaticamente

**Notas Credito**
- Generacion desde una orden de venta
- Anulacion parcial o total
- Envio automatico a la DIAN

**Notas Debito**
- Generacion por ajustes de precio
- Envio automatico a la DIAN

**Resoluciones**
- Gestion de resoluciones de numeracion
- Prefijo, rango desde/hasta
- Fecha de vigencia
- Autoincremento dentro del rango

---

## Modulo 6: Inteligencia Artificial

**Precio:** Desde $29 USD/mes
**Requiere:** Inventario
**Para quien:** Gerentes, directores financieros, analistas

### Que incluye:

**Analisis de Rentabilidad**
- Margen por producto calculado con datos reales de inventario
- Comparacion de costo vs precio de venta
- Identificacion de productos con margen negativo

**Alertas Automaticas**
- Notificacion cuando un producto pierde margen
- Deteccion de tendencias negativas
- Contador de alertas recurrentes

**Recomendaciones**
- Sugerencias accionables basadas en los datos
- Oportunidades de mejora de margen
- Analisis de que productos impulsar y cuales revisar

**Memoria Conversacional**
- El sistema recuerda el contexto de tu empresa
- Cada analisis es personalizado para tu operacion
- Mejora con el uso

**Motor IA**
- Powered by Claude (Anthropic)
- Limite diario configurable por plan
- Respuestas en espanol colombiano

---

## Servicios Transversales (incluidos en todos los planes)

### Autenticacion y Seguridad
- Registro e inicio de sesion con JWT
- Tokens de acceso (8h) + refresh (7d)
- Logout con blacklist en tiempo real
- Multi-tenant: cada empresa tiene su espacio aislado

### Roles y Permisos
- Roles configurables por empresa
- 10 grupos de permisos (Logistica, Inventario, Compras/Ventas, Produccion, Cumplimiento, Reportes, Equipo, Facturacion, Suscripcion, Correo)
- El primer usuario registrado recibe rol Administrador automaticamente
- Invitacion de usuarios por correo electronico

### Auditoria
- Log de todas las acciones administrativas
- Quien hizo que, cuando y desde donde
- Filtrable por usuario, accion y fecha

### Correo Electronico
- 9 plantillas de correo personalizables (bienvenida, reset password, factura, certificado, etc.)
- Envio via Resend (proveedor configurado a nivel plataforma)
- Variables dinamicas en plantillas ($user_name, $link, etc.)

### Media (Archivos)
- Almacenamiento centralizado de archivos
- Subida de imagenes, documentos y certificados
- Widget de seleccion de archivos integrado en toda la plataforma
- Categorias y referencias cruzadas (saber que archivo se usa donde)
- Soporte para almacenamiento local o AWS S3

### Webhooks
- Suscripciones a eventos por empresa
- Firma HMAC-SHA256 en cada entrega
- Retry automatico con backoff exponencial
- Catalogo de eventos disponibles
- Historial de entregas con estado

### Marketplace
- Catalogo de modulos activables
- Activacion/desactivacion inmediata
- Dependencias entre modulos (produccion requiere inventario, etc.)
- Sin contratos: activa hoy, desactiva manana

---

## Planes y Precios

| Plan | Precio | Modulos | Usuarios | Activos |
|---|---|---|---|---|
| **Starter** | $49 USD/mes | Logistica + Inventario + Facturacion DIAN | 10 | 1,000 |
| **Professional** | $99 USD/mes | Todo incluido (6 modulos) | 50 | 10,000 |
| **Enterprise** | A medida | Todo + ilimitado + soporte dedicado | Ilimitados | Ilimitados |

Descuento 20% en pago anual.

---

## Infraestructura

- Desplegado en Google Cloud Platform (Sao Paulo, Brasil)
- 10 containers en Cloud Run con auto-scaling
- PostgreSQL 16 gestionado (Cloud SQL) con backups diarios
- Redis para cache y colas en tiempo real
- HTTPS automatico en todos los endpoints
- Gateway Nginx como punto unico de entrada
- Tiempo de respuesta < 200ms en operaciones tipicas

---

## Diferenciadores Clave

1. **Unico en Latam** que integra inventario + produccion + logistica + EUDR en un solo SaaS
2. **Blockchain Solana** — cada certificado y movimiento de custodia es verificable publicamente
3. **Conexion directa** con TRACES NT (sistema oficial de la UE) y Global Forest Watch
4. **IA nativa** con Claude para analisis de rentabilidad
5. **Facturacion DIAN** incluida, no es un addon
6. **6x mas barato que SAP**, 3x mas barato que Odoo, con mas funcionalidad EUDR
7. **Implementacion en minutos**, no en meses
8. **Multi-tenant** — cada empresa tiene su espacio completamente aislado
