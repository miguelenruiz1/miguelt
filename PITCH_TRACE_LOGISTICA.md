# TRACE | Logistica Inteligente con Blockchain

## El problema

El 20% del costo del transporte internacional se debe a procesos fragmentados, documentacion en papel y falta de transparencia (Naciones Unidas).

En Colombia, un exportador de cafe, flores o frutas hoy:
- Maneja documentos en papel (cert origen, fitosanitario, DEX, BL)
- Coordina por email, WhatsApp y telefono
- No puede demostrar trazabilidad verificable al comprador internacional
- Pierde 2+ semanas rastreando un brote o problema de calidad
- Paga primas de seguro altas por falta de transparencia

## La solucion

**Trace** es la unica plataforma en Latinoamerica que integra inventario completo, documentos de comercio exterior y trazabilidad blockchain en un solo producto.

### Que hace Trace

**Inventario y operacion**
- Ordenes de compra internacionales con Incoterms (FOB, CIF, EXW)
- Multi-moneda (USD, EUR, COP) con tasa de cambio
- Recepcion en bodega con lotes trazables
- Pedidos de venta con facturacion electronica DIAN
- Stock por bodega, ubicacion, lote y serial
- Auto-reorder, alertas de vencimiento, ciclos de conteo

**Documentos de transporte**
- Guias de remision terrestre (conductor, placa, peso)
- Bill of Lading maritimo (buque, contenedor, sello)
- Air Waybill aereo (vuelo, paquetes)
- Carta porte, guia terrestre
- Tracking de cada envio

**Documentos de comercio exterior**
- Certificado de origen (Camara de Comercio)
- Certificado fitosanitario (ICA)
- Registro INVIMA
- DEX / DIM (DIAN)
- Factura comercial, packing list, certificado de seguro
- Codigo arancelario (HS), valores FOB/CIF

**Blockchain (Solana)**
- Cada evento critico se ancla en blockchain automaticamente
- Inmutable: nadie puede modificar lo que ya se registro
- Verificacion publica por QR: el comprador escanea y ve todo el origen
- cNFTs por lote para productos de alto valor
- Reglas configurables: usted decide que se ancla y que no
- Cadena de aprobacion verificable (enviado -> confirmado -> recibido)

## Diferenciacion

```
                    Inventario    Blockchain    Docs ComEx
                    completo      trazabilidad  (BL/AWB/DEX)

Farmer Connect         NO            SI            NO
iFinca                 NO            SI            NO
Safetrack              NO            SI            NO
Logimov                SI            NO            NO
Magaya                 NO            NO            SI
Siigo                  Basico        NO            NO

TRACE                  SI            SI            SI
```

**Nadie en LATAM ofrece las tres cosas juntas.**

## Caso de uso: Exportacion de cafe

```
Finca La Esperanza (Huila) -> Bodega Bogota -> Puerto Cartagena -> Miami

1. OC internacional FOB $8,500 USD (TRM $4,150)
2. Recepcion 1000 kg con lote LOT-CAFE-2026-Q1
   - Metadata: Huila 1800msnm, Caturra lavado, cupping 86pts
   - Certificaciones: Organico + Rainforest Alliance
3. Documentos: Cert Origen + Fitosanitario ICA + DEX DIAN
4. Guia remision Bogota -> Cartagena (placa, conductor)
5. BL maritimo Maersk (contenedor MAEU-7234521, sello SEAL-CO-98231)
6. SO internacional CIF $12,500 USD -> Miami Specialty Coffee LLC
7. El comprador en Miami escanea QR del lote:
   GET /api/v1/public/batch/LOT-CAFE-2026-Q1/verify
   -> Ve origen, certificados, y prueba blockchain de todo el recorrido
```

**Todo esto ya funciona. Lo probamos end-to-end.**

## Beneficios medibles

| Beneficio | Impacto |
|---|---|
| Reduccion de tiempo en gestion documental | -60% (benchmarked por Usyncro) |
| Reduccion de papel | -80% |
| Reduccion en prima de seguro por transparencia | Hasta -30% |
| Tiempo de rastreo ante brote/recall | De 2 semanas a 2 segundos (IBM Food Trust) |
| Diferenciacion para compradores internacionales | Trazabilidad verificable = acceso a mercados premium |

## Pricing

| Plan | Precio/mes | Incluye |
|---|---|---|
| **Starter** | $599,000 COP | 2 usuarios, 50 OC, 50 pedidos, 100 anchors blockchain |
| **Professional** | $1,449,000 COP | 10 usuarios, 500 OC, 500 pedidos, 1000 anchors |
| **Enterprise** | $3,299,000 COP | Ilimitado, API, soporte prioritario |

Mas barato que un SAP. Mas completo que un Siigo. Con blockchain real.

## Piloto gratuito

Ofrecemos un piloto de 30 dias sin costo para las primeras 5 empresas.

**Que incluye el piloto:**
- Configuracion completa del inventario y maestros
- Un envio real de exportacion con todos los documentos
- Anchoring en blockchain (Solana devnet)
- Verificacion publica del lote por QR
- Soporte directo del equipo tecnico

**Que necesitamos de usted:**
- Un envio real proximo (exportacion o distribucion nacional)
- Datos de proveedor, producto, cliente, transportista
- 2 horas para configuracion inicial

## Contacto

[Tu nombre]
[Tu email]
[Tu telefono]
[Website/landing page]

---

**Trace | Trazabilidad verificable para la cadena de suministro latinoamericana**

Inventario + Blockchain + Comercio Exterior = Una sola plataforma
