# Trace — Pitch para Centro de Emprendimiento Uniandes

**Fecha:** 20 de abril de 2026
**Presenta:** Miguel Enrique Ruiz Aldana — MISO Uniandes, Senior Developer Uniandes (8 años)
**Demo en vivo:** http://62.238.5.1

---

## 1. ¿Qué es Trace?

**Plataforma SaaS multi-tenant modular para operaciones empresariales completas** — gestión de inventarios, producción, ventas, facturación, compliance, trazabilidad y más — en la que **cada empresa activa sólo los módulos que necesita** y paga por lo que usa.

Una empresa puede usar Trace únicamente para manejar su inventario, otra puede usar inventario + producción + facturación electrónica, y otra puede sumarle compliance EUDR si exporta. **Misma plataforma, configuraciones distintas.**

Una frase:

> *Trace es la infraestructura operativa digital que le faltaba a la empresa LatAm: modular, en español, integrada con las realidades locales (DIAN, IGAC, Salesforce), a precio accesible.*

---

## 2. La versatilidad es el producto

El insight que nos diferencia: **las empresas pequeñas y medianas en LatAm no pueden pagar 5 SaaS distintos** (uno de inventario, uno de facturación, uno de compliance, uno de CRM, uno de gestión de usuarios). Terminan operando con **Excel + WhatsApp + memoria**.

Trace es **una sola plataforma con 8 módulos** que se activan según el caso de uso. Una misma base, muchas verticales.

### Ejemplos reales de quién puede usar qué:

| Tipo de empresa | Módulos que necesita |
|---|---|
| **Panadería de barrio** | Inventario + Productos + Ventas + Usuarios |
| **Distribuidora de abarrotes** | Inventario + Órdenes de compra + Proveedores + Bodegas + Facturación DIAN |
| **Manufactura pequeña** (cosméticos, alimentos) | Producción + Recetas + Lotes + QC + Inventario + Facturación |
| **Cooperativa agrícola** | Todo lo anterior + **Trazabilidad blockchain + EUDR** |
| **E-commerce** | Inventario + Variantes + Pasarelas de pago + Customer Portal |
| **Restaurante/cadena** | Inventario + Recetas + Conteos cíclicos + Alertas de caducidad |
| **Consultora / empresa de servicios** | Facturación + Cliente Portal + Roles y permisos + Integraciones |
| **Importador/exportador** | Inventario + Aduana + Trazabilidad + Compliance |

Cada cliente **activa los módulos que necesita** desde un **Marketplace interno**. Si mañana cambia su negocio, activa o desactiva módulos en 1 clic.

---

## 3. ¿Qué hace Trace? — los 8 módulos

### 📦 **INVENTARIO** (módulo más robusto — funciona solo, sin otros módulos)
- Productos con variantes, lotes, seriales, impuestos, unidades de medida
- Bodegas + ubicaciones físicas (estantes, racks) con validación de capacidad
- Stock: entradas, salidas, transferencias, mermas, devoluciones, ajustes
- **Costeo FIFO + promedio ponderado (WAC)** automático
- **Alertas** de stock bajo, caducidad, reorden
- **Reorden automático** — cuando baja del punto mínimo, genera OC al proveedor preferente
- Conteos cíclicos con detección automática de discrepancias
- **Portal para clientes** (B2B): tus clientes ven su stock disponible, hacen pedidos
- **Verificación pública por QR** (B2C): consumidor final escanea y valida autenticidad/origen
- Reportes CSV, analíticos ABC, dashboards
- Importación masiva desde Excel con templates por industria

### 🏭 **PRODUCCIÓN**
- Recetas (Bill of Materials): productos compuestos con ingredientes y cantidades
- Corridas de producción: planeada → en progreso → liberada
- Consumo automático de materias primas
- Generación automática de producto terminado con costeo
- **Recursos** (máquinas, operarios) con capacidad por hora
- **Tests de calidad** con parámetros y valores esperados

### 🧾 **FACTURACIÓN Y VENTAS**
- Órdenes de compra con flujo draft → enviada → confirmada → recibida
- Órdenes de venta con reserva de stock → picking → envío → entregado → facturado
- **Facturación electrónica DIAN** (Factus, Nubefact, Siigo)
- **Clientes** con precios especiales automáticos
- **Integración con Salesforce** (CRM)
- Socios (supplier + customer en el mismo modelo si aplica)

### 💳 **SUSCRIPCIONES Y COBROS**
- 4 planes (free / starter / professional / enterprise) totalmente configurables
- Facturas PDF numeradas
- **7 pasarelas de pago latinoamericanas**: ePayco, PayU, Wompi, MercadoPago, Bold, Kushki, OpenPay
- License keys con validación pública
- **Marketplace de módulos** (1 clic para activar/desactivar)

### 🔐 **GESTIÓN DE USUARIOS Y PERMISOS**
- Multi-tenant: cada empresa es aislada, su data jamás se cruza con otra
- Registro con **2FA (TOTP)** opcional
- **136 permisos granulares** en 27 módulos
- Roles custom con matriz visual (estilo Drupal)
- Invitaciones de equipo por email
- **Auditoría completa** (quién hizo qué, cuándo)
- Proveedores de email configurables (Resend, SMTP, Mailhog)

### 🔗 **TRAZABILIDAD Y CUSTODIA** (el diferenciador)
- Registro de activos con metadata rica (fotos, documentos, origen)
- **Anclaje en blockchain Solana** (cNFTs comprimidos → $0.0001 por evento)
- Cadena de custodia con 6 eventos: entrega, llegada, carga, QC, liberación, destrucción
- Tablero Kanban en vivo (7 estados)
- Wallets del sistema con airdrop automático
- Multi-actor: productor + transportista + bodega + cliente ven lo mismo en tiempo real

### 📋 **COMPLIANCE / REGULATORIO** (EUDR, FSC, USDA Organic, lo que venga)
- Framework EUDR completo: 7 commodities, geolocalización, DDS, retención 5 años
- **Parcelas con validación GeoJSON estricta** (rechaza polígonos mal formados)
- Detección de solapamiento entre parcelas
- **Records DDS** con envío automático a TRACES NT (UE)
- **Certificados PDF** auto-generados
- Extensible a cualquier framework regulatorio futuro (FSC, USDA, RSPO, Rainforest Alliance…)

### 🤖 **INTELIGENCIA ARTIFICIAL**
- Análisis narrativo de P&L con Claude
- Recomendaciones automáticas de gestión
- Generación asistida de reportes
- Rate limits y costo controlado por plan

---

## 4. ¿A quién le sirve?

### Empresas que operan con inventario físico (es decir, casi todas)
- **Tiendas, distribuidoras, mayoristas** — necesitan saber cuánto tienen, dónde y cuánto cuesta
- **Manufactura pequeña y mediana** — necesitan producción + inventario + facturación en un solo lugar
- **E-commerce** — necesitan stock + variantes + pasarelas + cliente portal
- **Restaurantes y cadenas** — necesitan inventario + recetas + alertas de caducidad
- **Agroindustria** — necesitan **todo lo anterior + trazabilidad + compliance** si exportan

### Empresas de servicios que necesitan gestión ordenada
- **Consultoras** — facturación + clientes + usuarios y roles + auditoría
- **Agencias** — proyectos como "productos" + facturación + permisos de equipo
- **SaaS pequeños** — pueden usar Trace como backend de su propio producto

### Organizaciones que necesitan prueba de origen
- **Cooperativas** que exportan a Europa (EUDR obliga)
- **Marcas premium** que quieren diferenciar con trazabilidad verificable
- **Auditores y certificadoras** que necesitan plataforma estándar de consulta

### Usuario final (consumidor)
- Cualquier persona que **escanee un QR** en un producto y quiera verificar autenticidad, origen o legalidad.

---

## 5. ¿Por qué es innovador?

### 5.1 Innovación de producto

| Aspecto | Software tradicional | Trace |
|---|---|---|
| **Modularidad** | Vendés 1 producto con features fijos | **Marketplace modular**: activás lo que necesitás, pagás por eso |
| **Multi-tenancy** | Una instancia por cliente (deploy dedicado, caro) | **SaaS multi-tenant nativo** con aislamiento estricto por diseño |
| **Precio accesible** | $100-500 USD/mes por usuario | Desde **$0 (free tier) a ~$50 USD/mes** para empresas pequeñas |
| **Localización LatAm** | Hecha en US/EU con traducción al español | **Hecho en Colombia, para LatAm** — DIAN, IGAC, NIT, pasarelas locales |
| **Experiencia de usuario** | Interfaces cargadas, curva de aprendizaje alta | UI React moderna, sidebar adaptativa por módulos activos |
| **Un solo stack** | 5 SaaS distintos = 5 logins, 5 facturas, 5 APIs | **Una plataforma** con 8 módulos integrados |

### 5.2 Innovación técnica

| | Competencia | Trace |
|---|---|---|
| **Prueba de inmutabilidad** | DB centralizada (modificable) | **Blockchain Solana** con cNFTs |
| **Costo por evento blockchain** | $0.50-2.00 USD | **$0.0001 USD** (compressed NFTs) |
| **Multi-usuario en tiempo real** | Requiere integraciones custom | **Nativo**: productor+transportista+bodega coordinados |
| **IA integrada** | Módulo aparte o no existe | **Claude integrado** para análisis P&L |
| **Compliance regulatorio** | Manual + Excel | **Automático**, validado en tiempo real |
| **Verificación pública** | No existe | **QR → URL pública** sin login |

### 5.3 Innovación de mercado

- **Precio LatAm-friendly**: una PYME colombiana con 5 empleados paga $50/mes por lo que en US cuesta $500.
- **Modelo freemium real**: cualquier negocio arranca gratis con módulos básicos; solo paga cuando crece.
- **Integración con realidades locales**: DIAN, IGAC, NIT, pasarelas LatAm. Las soluciones importadas **no tienen eso**.
- **Portabilidad**: si el cliente crece o cambia de rubro, activa más módulos. No tiene que migrar a otro SaaS.

---

## 6. Casos de uso concretos

### Caso 1: Panadería "Don Pedro" (5 empleados, Bogotá)
- **Problema**: vende 30 productos en 2 locales, no sabe cuánto le queda de harina y cuánto vende por día
- **Usa**: Inventario + Productos + Ventas + Usuarios
- **Costo**: free tier (hasta 3 usuarios) → $20/mes cuando crezca
- **Beneficio**: deja de perder producto por caducidad + sabe su utilidad por día

### Caso 2: Fábrica de cosméticos "Natur" (15 empleados)
- **Problema**: produce 8 productos, cada uno con receta, no hace costeo real
- **Usa**: Inventario + Producción + Recetas + Facturación DIAN
- **Costo**: $50-80/mes
- **Beneficio**: conoce costo real por producto, factura legalmente, controla caducidad

### Caso 3: Cooperativa cafetera (200 socios)
- **Problema**: exportan a Europa, **EUDR los obliga** a probar origen y legalidad o pierden el mercado
- **Usa**: todo (Inventario + Producción + Trazabilidad blockchain + Compliance EUDR + Facturación)
- **Costo**: $200-500/mes (enterprise)
- **Beneficio**: cumplen EUDR sin pagar $5.000/mes a solución europea

### Caso 4: Restaurante mediano (2 locales, 25 empleados)
- **Problema**: pierde plata en caducidad, no sabe qué plato le deja más margen
- **Usa**: Inventario + Recetas (del menú) + Conteos cíclicos + Alertas caducidad + Analítica
- **Costo**: $50-100/mes
- **Beneficio**: reduce mermas 30-50%, optimiza menú con data real

### Caso 5: Importador de electrónicos
- **Problema**: 20 SKUs, 5 proveedores en China, 3 bodegas en Colombia, sin visibilidad
- **Usa**: Inventario + Órdenes de compra + Proveedores + Bodegas múltiples + Transferencias
- **Costo**: $80/mes
- **Beneficio**: sabe stock consolidado, controla lead times, evita stockouts

### Caso 6: Productor de chocolate premium (marca)
- **Problema**: quiere diferenciar su producto con "prueba de origen" en el empaque
- **Usa**: Inventario + Lotes + Trazabilidad blockchain + **QR público**
- **Costo**: $100/mes
- **Beneficio**: premium pricing 20-30% por producto verificable

---

## 7. Tecnología

### Stack

- **Frontend**: React 18 + Vite + TypeScript + Tailwind + React Query
- **Backend**: 8 microservicios en FastAPI (Python 3.11) con SQLAlchemy async
- **Bases de datos**: 8 PostgreSQL independientes (una por servicio) + Redis
- **Blockchain**: Solana con cNFTs vía Helius
- **IA**: Claude API (Anthropic)
- **Contenedores**: Docker Compose en producción
- **CI/CD**: GitFlow estricto (feature → develop → staging → main)

### Números del proyecto

| Métrica | Valor |
|---|---|
| Líneas de código | **~190.000** |
| Microservicios | **8 + frontend + gateway** |
| Endpoints REST | **681** |
| Modelos de datos | **73+** |
| Migraciones de BD | **187** |
| Páginas de frontend | **113** |
| Tests automatizados | **40+** (E2E + seguridad, 100% passing) |
| Containers en producción | **20 healthy 24/7** |
| Bugs de seguridad auditados y fixeados | **17 críticos** |

### Seguridad

- JWT con audience/issuer, blacklist Redis, 2FA opcional
- Multi-tenant enforced en **todos** los endpoints de mutación
- S2S con `compare_digest` timing-safe
- Encriptación Fernet de secretos (API keys, credenciales email/pago)
- Rate limiting + HMAC en webhooks
- Password policy (12+ chars, complejidad)
- Auditoría completa

### Costo de infraestructura

- **$5.49 USD/mes** en Hetzner Cloud — escalable hasta ~5.000 usuarios con un solo nodo
- Migración a cluster cuando haya >10 clientes pagantes
- **97% más barato** que GCP equivalente

---

## 8. Estado actual

- **Producto en producción desde 17 de abril de 2026** — http://62.238.5.1
- 20 containers corriendo 24/7, sin downtime
- Todas las funcionalidades descritas **existen y funcionan hoy**, no son promesas
- 3 rondas de QA completadas con 17 bugs críticos cerrados
- **Ningún cliente pagante aún** — es lo que queremos cambiar con apoyo del Centro

---

## 9. Qué pedimos del Centro de Emprendimiento

**NO pedimos dinero.** Ya tenemos la plataforma construida y la infraestructura pagada.

Lo que necesitamos es **acompañamiento experto para validar el negocio y encontrar los primeros clientes**:

### 🎯 Validación de modelo de negocio
- **Pricing**: ¿los $0-500 USD/mes escalonados tienen sentido para el mercado LatAm? ¿Cobrar por módulos, por transacción, por usuarios?
- **Propuesta de valor**: ¿qué módulo es **el gancho**? ¿Inventario? ¿Producción? ¿Compliance?
- **Posicionamiento**: ¿nos vendemos como "ERP modular" o como "plataforma de trazabilidad"? ¿Cambia el mensaje por vertical?
- **Competencia real**: ¿quién está resolviendo esto en LatAm? ¿Loggro, Defontana, Alegra, Siigo? ¿Dónde nos diferenciamos?
- **Canal**: ¿directo? ¿Vía gremios (Fenalco, ACOPI)? ¿Vía contadores que recomiendan software?

### 🤝 Conexiones a clientes potenciales
- Introducciones a **PYMES** que estén con Excel y necesiten digitalizarse
- Conexiones con **Fenalco, ACOPI, Propaís** para pilotos
- Contactos con **cooperativas agrícolas** (Fedecafé, Fedecacao, Fedepalma) para el uso EUDR
- Contactos con **agrupaciones de restaurantes** (ACODRES)
- Contactos con **emprendedores** del ecosistema Uniandes que ya tengan operación
- **3-5 pilotos reales** con descuento o gratis a cambio de feedback + case studies

### 🧭 Mentoría go-to-market
- Founders con experiencia en **SaaS B2B LatAm** (Siigo, Alegra, Nubank, Platzi, Rappi)
- Mentores en **pricing** SaaS modular (el más difícil de estimar)
- Veteranos en **ventas a PYMES** colombianas (ciclo de venta distinto a enterprise)
- Mentores en **product-led growth** vs sales-led
- Mentoría en captación de los **primeros 10 clientes** (la etapa más difícil de una startup)

### 🏛️ Acceso a recursos institucionales Uniandes
- **Sello "apoyado por Centro de Emprendimiento Uniandes"** como validación frente a clientes y, eventualmente, inversores
- Acceso a **eventos** donde haya empresarios y PYMES
- **Tesistas MISO/MAES** potenciales que ayuden con R&D en módulos específicos (blockchain, IA, GeoSpatial)
- Espacio de coworking / infraestructura si se necesita

### 📰 Amplificación
- Cobertura en **Uniandes Noticias** / redes de la universidad
- Participación en **Demo Days** del Centro
- Mención como case study de MISO aplicado a industria

### 🔗 Red académica adicional
- Vínculo activo con el **Software Design Lab (SWDL)** de Ingeniería — proyecto paralelo **Kraken 2.0** (revival de framework de testing hecho en Uniandes)
- Mentoría del Dr. **Mario Linares-Vásquez** ya iniciada
- Potencial de papers conjuntos (ICSE Demo, ISSTA Tools) con Trace como case study

---

## 10. ¿Por qué nosotros?

### El fundador

- **Miguel Enrique Ruiz Aldana**
- Egresado **MISO Uniandes**
- **8 años como Senior Developer en Uniandes** — conoce la casa por dentro
- Código verificable en git, producto funcional en producción (no en PowerPoint)
- Relación activa con SWDL y profesores referentes (Mario Linares)

### El equipo hoy

- Miguel + **Claude Opus como pair programmer** — desarrollo solo-founder potenciado con IA, sostenido y productivo.
- Sin inversores ni deuda — **máxima flexibilidad** para pivotar si la validación lo requiere.

### La ambición por fases

- **Q3 2026**: 5-10 clientes piloto en Colombia (agro, manufactura, retail)
- **Q4 2026**: 15-30 clientes pagantes, revenue inicial
- **2027**: Expansión a Perú, Ecuador, Chile (mismo stack, idioma, regulaciones similares)
- **2028**: Referente LatAm en plataforma operativa modular para PYMES + trazabilidad

### Lo que NO somos

- **No somos "otra cripto startup"**: blockchain es un medio para probar inmutabilidad en el módulo de trazabilidad, **no el producto**. Los otros 7 módulos no necesitan blockchain.
- **No somos un SAP para empresas grandes**: somos para **PYMES** (5-200 empleados) que hoy operan en Excel.
- **No somos un ERP rígido**: somos **modular**, la empresa paga solo por lo que usa.
- **No vivimos del hype**: stack sobrio (FastAPI + Postgres + React), decisiones defendibles, cero moda innecesaria.

---

## 11. En 3 frases

1. **Tenemos plataforma real**, en producción, modular — no es un MVP, son 8 módulos integrados funcionando.
2. **Atacamos un mercado enorme y desatendido** — PYMES LatAm que hoy operan con Excel y no tienen presupuesto para 5 SaaS distintos.
3. **Nos falta validar el negocio** — el pricing, el posicionamiento, el canal — y el Centro de Emprendimiento es el lugar exacto para hacerlo.

---

## Lo que queremos salir con

- [ ] Próxima sesión agendada con un mentor del Centro
- [ ] 3-5 contactos concretos de potenciales primeros clientes o aliados (PYMES, gremios, cooperativas)
- [ ] Criterios claros de qué necesitamos probar antes de escalar o pedir recursos adicionales
- [ ] Entender cómo el Centro puede acompañar a Trace los próximos 6-12 meses

---

**Contacto:** Miguel Enrique Ruiz Aldana · miguelenruiz1@gmail.com
**Demo live:** http://62.238.5.1
**Código verificable (bajo NDA):** github.com/miguelenruiz1/miguelt
