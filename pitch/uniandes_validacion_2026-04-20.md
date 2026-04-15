# TRACE — Pitch de validación
**Centro de Innovación y Emprendimiento, Universidad de los Andes**
Lunes 20 de abril de 2026

---

## 1. Quiénes somos

TRACE es una plataforma SaaS multi-tenant para que **exportadores agrícolas colombianos cumplan con el Reglamento de Deforestación de la Unión Europea (EUDR 2023/1115)** sin armar Excels paralelos ni contratar consultoras de USD 30k/año. Hoy soporta café, cacao y aceite de palma. Equipo técnico fundador, 3 meses de desarrollo, MVP funcional.

---

## 2. El problema (urgencia regulatoria real)

A partir del **30 de diciembre de 2025**, ningún operador europeo puede importar café, cacao, palma, soya, madera, caucho ni carne sin presentar una **Due Diligence Statement (DDS)** en el sistema oficial **TRACES NT** de la Comisión Europea con:

- Polígono GeoJSON de cada finca de origen (precisión ≥6 decimales WGS84).
- Prueba satelital de no-deforestación post-31-dic-2020 (Hansen GFC, JRC TMF, GFW).
- Trazabilidad documental de cada eslabón de la cadena (productor → cooperativa → exportador → naviera → importador EU).

**Quien no cumple, no pasa aduana.** Multas hasta el 4% del facturado anual europeo + retiro de mercancía + prohibición de comercializar 12 meses.

**Mercado afectado en Colombia (2026)**:
- Café: USD 3.500M / 12M sacos / 545.000 caficultores
- Cacao: USD 250M creciendo 15%/año
- Aceite de palma: USD 1.200M (Colombia es 4° productor mundial)
- **Total: ~USD 5.000M/año en exportaciones agrícolas a la UE**

El 90% de esos exportadores **no tiene cómo cumplir** y está dependiendo de Excel + consultoras puntuales.

---

## 3. Quién paga el dolor (ICP)

Tres perfiles validables:

| Perfil | Cantidad CO | Dolor | Disposición a pagar (hipótesis) |
|---|---|---|---|
| **Exportadores grandes** (Carcafé, Banexport, Casa Luker, Daabon, Indupalma) | ~80 | Miles de DDS/año, miles de fincas, multas potenciales millonarias | USD 500-3000/mes SaaS + setup |
| **Cooperativas** (Cadefihuila, APROCASUR, Red Ecolsierra) | ~200 | Agregar a smallholders sin GPS, certificar como un solo operador | USD 100-500/mes |
| **Importadores europeos** (InterAmerican, Daarnhouwer, Touton) | ~50 con foco LATAM | Verificar DDS upstream de sus proveedores colombianos | USD 1000-5000/mes |

**Hipótesis a validar**: el dolor es real, urgente, y están dispuestos a pagar más que el costo del Excel + consultora.

---

## 4. Qué construimos (estado actual)

**Plataforma SaaS multi-tenant** con 8 microservicios:

- **Compliance EUDR**: gestión de fincas (plots), polígonos GeoJSON con validación topológica, screening satelital multi-fuente, decision tree de riesgo, generación de DDS, anclaje hash en blockchain Solana (cNFT compressed), integración TRACES NT.
- **Trace (custodia)**: chain-of-custody con state machine, eventos jerárquicos, multi-actor (productor → cooperativa → exportador → naviera → importador).
- **Inventory + Production**: productos, almacenes, movimientos, transformaciones (cereza→pergamino→verde, mazorca→fermentado, RFF→CPO+PKO), recetas BOM, UoM con conversiones, taxes con IVA exportación + retenciones.
- **User/Auth**: RBAC granular, audit log, JWT + refresh + Redis blacklist.
- **Subscription**: planes, módulos toggle-ables, marketplace, 7 pasarelas de pago integradas.
- **Frontend**: React 18 + Vite + TS + Tailwind + React Query, ~30 pantallas operativas.
- **Deploy**: Cloud Run (Google Cloud), gateway nginx, Cloud Build CI.

**3 casos semilla end-to-end**:
- Café Huila → Hamburgo (lote HU-2026-042, finca El Mirador, Pitalito)
- Cacao Tumaco → Amsterdam (lote LT-APRO-2026-042, APROCASUR)
- Palma Cesar → Rotterdam (lote CPO-CES-2026-088, Indupalma RSPO IP)

---

## 5. Estado honesto: dónde estamos en serio

Auditoría interna (10 agentes QA, abril 2026):

- **Completitud técnica**: ~38% para "producto productivo cobrable".
- **Funcionalidad efectiva probada**: ~55% (lo que existe y funciona end-to-end).
- **Validación con cliente real**: **0%**. Cero pilotos firmados, cero usuarios reales en producción.

Lo que SÍ funciona: arquitectura sólida, multi-commodity, EUDR domain profundo, anclaje blockchain, multi-tenant en producción.

Lo que NO está listo: integraciones reales con TRACES NT y GFW, test suite automatizado, monitoring/alerting, validación legal GDPR/DPA, **y sobre todo: no sabemos si esto resuelve el dolor real de un exportador real**.

**Esa última frase es por la que venimos al CIE.**

---

## 6. Qué validamos vs qué necesitamos validar

| Validado ✅ | NO validado ❓ |
|---|---|
| EUDR es regulación real con enforcement en 60 días | ¿Los exportadores colombianos lo perciben como urgente? |
| Hay tecnología satelital + blockchain para resolverlo | ¿Confían en nuestra implementación? |
| Mercado de USD 5.000M/año está expuesto | ¿Cuánto del problema es solucionable con SaaS vs consultoría? |
| El stack técnico funciona y escala | ¿Cuánto pagarían? ¿Por qué módulo? ¿Cómo descubren el producto? |

---

## 7. Lo que pedimos al CIE Uniandes

**No buscamos capital.** Buscamos validación + acceso. 5 pedidos concretos:

1. **Programa de validación temprana**: ingreso a *Apps.co* o equivalente para metodología de descubrimiento de cliente (Steve Blank, Lean Startup) aplicada a B2B agtech.
2. **Acceso a red de empresas socias**: introducciones formales a 5-10 cooperativas/exportadores (FNC, FEDECACAO, FEDEPALMA, Procolombia, ProColombia Trade) para hacer **20 entrevistas estructuradas de descubrimiento** en mayo-junio 2026.
3. **Mentor sectorial**: alguien con experiencia operativa en exportación agrícola colombiana (ex-trader, ex-compliance officer, ex-FNC). 2-4 horas/mes.
4. **Mentor regulatorio EUDR**: alguien que entienda EU customs, TRACES NT y due diligence regulatoria. Puede ser remoto (LiveEO, Satelligence, Carbon Trust tienen perfiles así).
5. **Espacio en demo days / pitch competitions** cuando tengamos primer piloto firmado (Q3 2026): la siguiente etapa, si la validación cierra.

**Lo que NO pedimos** (intencionalmente):
- Capital semilla (todavía no es el momento — sería levantar sobre supuestos).
- Infraestructura cloud (ya tenemos GCP credits).
- Mentor técnico (el equipo cubre el lado de código).

---

## 8. Riesgos que reconocemos

1. **Riesgo de mercado**: el dolor EUDR puede ser percibido pero no urgente. Los exportadores grandes pueden contratar consultoras (USD 30-80k) en lugar de SaaS. Validamos en mayo-junio.
2. **Riesgo de adopción**: smallholders no usan smartphones para georreferenciación; cooperativas tienen procesos arcaicos. La UI puede no ser apropiada. Validamos con piloto operativo.
3. **Riesgo regulatorio**: EUDR puede postergarse (ya pasó una vez) o relajarse. Hedge: el sistema sirve para otros frameworks (RSPO, ISCC EU, FairTrade, RA).
4. **Riesgo competitivo**: LiveEO, Satelligence, Meridia, GeoTraceability ya operan en LATAM con presupuestos de Series B. Diferenciador defendible: anclaje blockchain + multi-commodity nativo + foco Colombia + precio LATAM.
5. **Riesgo de equipo**: founder técnico solo. Necesita perfil comercial + GIS engineer en próximos 6 meses.

---

## 9. Próximos 90 días (con o sin CIE)

| Mes | Foco | Métrica de éxito |
|---|---|---|
| **Mayo** | 20 entrevistas de descubrimiento con exportadores/cooperativas | Identificar 3 segmentos con dolor caliente medible |
| **Junio** | 3 propuestas de piloto pago (USD 500-2000/mes × 3 meses) | 1 piloto firmado |
| **Julio** | Implementación de piloto + iteración rápida + cierre de gaps técnicos identificados en producción real | NPS > 30 del cliente piloto |

Si en 90 días no hay 1 piloto firmado, **pivot serio**: revisión de ICP, propuesta de valor o vertical.

---

## 10. Lo que demostraremos hoy (en vivo, 5 min)

- Demo en navegador de los 3 lotes seedeados (café Huila, cacao Tumaco, palma Cesar).
- Validación geoespacial de polígono real con multi-source satelital.
- Generación de DDS EUDR con anclaje hash en blockchain.
- Filtros multi-commodity en panel de control.
- *(Caveat honesto: el flujo TRACES NT real aún no está conectado; mostramos el payload que se enviaría.)*

---

**Equipo / contacto**: Miguel Ruiz Triana — miguelenruiz1@gmail.com
**Repositorio**: privado (acceso bajo NDA si interesa diligencia técnica)
**Stack**: FastAPI + React + PostgreSQL + Solana + Google Cloud Run

---

*Preferimos las preguntas duras hoy, antes que el silencio cortés.*
