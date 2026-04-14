import { useMemo, useState } from 'react'
import { BookOpen, ExternalLink, Globe, Scale } from 'lucide-react'

type Resource = {
  title: string
  description: string
  url: string
  tags: string[]   // country code or 'global'
  commodities: string[] // or 'all'
  category: 'database' | 'methodology' | 'platform' | 'official'
}

const RESOURCES: Resource[] = [
  // Global databases
  {
    title: 'Forest Legality Initiative — WRI',
    description:
      'Base de datos abierta del World Resources Institute sobre legalidad forestal por pais. Incluye mapeos legales detallados para operadores de madera — util para cruzar con otros commodities del mismo pais.',
    url: 'https://forestlegality.org/',
    tags: ['global'],
    commodities: ['all'],
    category: 'database',
  },
  {
    title: 'Timber Lex — base legal madera',
    description:
      'Repositorio de leyes aplicables a la produccion y exportacion de madera. Dos secciones relevantes para otros commodities: conversion de bosques y consulta previa.',
    url: 'https://www.timberlex.org/',
    tags: ['global'],
    commodities: ['all'],
    category: 'database',
  },
  {
    title: 'EU Forest Observatory (DG ENV / JRC)',
    description:
      'Plataforma oficial de la Comision Europea con mapas de cobertura forestal 2020, alertas y datos del JRC. Punto de partida para screening EUDR.',
    url: 'https://forest-observatory.ec.europa.eu/',
    tags: ['global', 'eu'],
    commodities: ['all'],
    category: 'official',
  },
  {
    title: 'Global Forest Watch (WRI)',
    description:
      'Alertas de deforestacion casi en tiempo real (GLAD, RADD), mapas historicos (Hansen) y dashboards por pais. Reconocido por la Comision Europea como referencia.',
    url: 'https://www.globalforestwatch.org/',
    tags: ['global'],
    commodities: ['all'],
    category: 'platform',
  },
  {
    title: 'WISP — What Is In that Plot (FAO)',
    description:
      'Herramienta gratuita y anonima de la FAO que consolida todos los datos globales de cobertura forestal y devuelve un veredicto de riesgo por parcela. Codigo fuente abierto, puede self-hostearse.',
    url: 'https://openforis.org/solutions/wisp/',
    tags: ['global'],
    commodities: ['coffee', 'cocoa', 'palm_oil', 'soy', 'wood'],
    category: 'platform',
  },
  {
    title: 'WDPA — World Database on Protected Areas',
    description:
      'Base de datos mundial de areas protegidas (parques, reservas, territorios indigenas reconocidos). Gestionada por UNEP-WCMC + IUCN.',
    url: 'https://www.protectedplanet.net/',
    tags: ['global'],
    commodities: ['all'],
    category: 'database',
  },
  {
    title: 'Transparency International — CPI',
    description:
      'Indice de Percepcion de Corrupcion por pais. Usado por la Comision Europea como insumo de benchmarking bajo EUTR; probablemente aplicable a EUDR una vez salgan las orientaciones.',
    url: 'https://www.transparency.org/en/cpi',
    tags: ['global'],
    commodities: ['all'],
    category: 'database',
  },
  // Initiative Española
  {
    title: 'Iniciativa Española Empresa y Biodiversidad (IEEB) — MITECO',
    description:
      'Ciclo formativo oficial sobre EUDR dirigido a sectores regulados espanoles. Webinarios grabados + preguntas frecuentes.',
    url: 'https://www.miteco.gob.es/',
    tags: ['global', 'eu', 'es'],
    commodities: ['all'],
    category: 'official',
  },
  {
    title: 'EFI — European Forest Institute (Barcelona)',
    description:
      'Programa de asistencia tecnica para implementacion EUDR en paises productores. Publica metodologias de due diligence para cacao (CIV, GHA, CMR), cafe y otros.',
    url: 'https://efi.int/',
    tags: ['global', 'eu'],
    commodities: ['coffee', 'cocoa', 'wood'],
    category: 'methodology',
  },
  // Colombia
  {
    title: 'SINAP + RUNAP — Parques Nacionales Colombia',
    description:
      'Sistema Nacional de Areas Protegidas y Registro Unico. Capa oficial para cruzar polígonos contra areas protegidas colombianas.',
    url: 'https://runap.parquesnacionales.gov.co/',
    tags: ['CO'],
    commodities: ['all'],
    category: 'official',
  },
  {
    title: 'ANT — Agencia Nacional de Tierras',
    description:
      'Registro de baldios adjudicados, titulacion colectiva y procesos agrarios. Fuente oficial de evidencia de tenencia de la tierra en Colombia.',
    url: 'https://www.agenciadetierras.gov.co/',
    tags: ['CO'],
    commodities: ['all'],
    category: 'official',
  },
  // Peru
  {
    title: 'geoSERNANP — Areas Naturales Protegidas Peru',
    description:
      'Visor geografico oficial de SERNANP con limites de ANP, ACR y ACP. Requisito para EUDR en operadores peruanos.',
    url: 'https://geo.sernanp.gob.pe/',
    tags: ['PE'],
    commodities: ['all'],
    category: 'official',
  },
  {
    title: 'GeoBosque — MINAM Peru',
    description:
      'Mapas nacionales de cobertura forestal peruana (amazonia) con alertas tempranas. Mas fino que los datasets globales para la region.',
    url: 'https://geobosques.minam.gob.pe/',
    tags: ['PE'],
    commodities: ['all'],
    category: 'official',
  },
  // Ecuador
  {
    title: 'MAATE — Patrimonio Nacional de Areas Protegidas',
    description:
      'Ministerio de Ambiente ecuatoriano — datos oficiales del SNAP y categorias de manejo.',
    url: 'https://www.ambiente.gob.ec/',
    tags: ['EC'],
    commodities: ['all'],
    category: 'official',
  },
  // Brasil
  {
    title: 'SICAR — Cadastro Ambiental Rural',
    description:
      'Registro federal brasileño de todos los inmuebles rurales. Incluye georreferenciacion publica — fuente #1 para EUDR en Brasil.',
    url: 'https://www.car.gov.br/',
    tags: ['BR'],
    commodities: ['soy', 'beef', 'coffee', 'cocoa'],
    category: 'official',
  },
  {
    title: 'IBAMA — Lista de areas embargadas',
    description:
      'Embargos por desmatamento ilegal. Cruzar obligatoriamente contra esta lista antes de exportar commodities brasileños.',
    url: 'https://www.ibama.gov.br/',
    tags: ['BR'],
    commodities: ['soy', 'beef'],
    category: 'official',
  },
  {
    title: 'Lista Suja do Trabalho — MTE Brasil',
    description:
      'Cadastro oficial de empleadores que sometieron trabajadores a condiciones analogas a la esclavitud. Cruce obligatorio para EUDR.',
    url: 'https://www.gov.br/trabalho-e-emprego/',
    tags: ['BR'],
    commodities: ['all'],
    category: 'official',
  },
  // Côte d'Ivoire
  {
    title: 'SODEFOR — forets classees Cote d\'Ivoire',
    description:
      'Societe ivoirienne responsable de las 234 forets classees. Fuente oficial de limites y parcelas legalmente admitidas dentro de forets.',
    url: 'https://www.sodefor.ci/',
    tags: ['CI'],
    commodities: ['cocoa', 'wood'],
    category: 'official',
  },
  {
    title: 'ICI — International Cocoa Initiative (CLMRS)',
    description:
      'Child Labour Monitoring and Remediation System. Referencia para demostrar due diligence de trabajo infantil en cacao africano.',
    url: 'https://cocoainitiative.org/',
    tags: ['CI', 'GH'],
    commodities: ['cocoa'],
    category: 'methodology',
  },
  // Ghana
  {
    title: 'Forestry Commission — Ghana',
    description:
      'Lista de parcelas de cacao legalmente admitidas dentro de forest reserves ghaneanas. Sin esta lista, todas las parcelas intersectadas con areas protegidas se rechazan.',
    url: 'https://www.fcghana.org/',
    tags: ['GH'],
    commodities: ['cocoa'],
    category: 'official',
  },
  // Asia
  {
    title: 'MSPO Dashboard — Malaysia',
    description:
      'Malaysian Sustainable Palm Oil, dashboard publico con coordenadas de parcelas certificadas. Certificacion obligatoria nacional.',
    url: 'https://www.mpocc.org.my/',
    tags: ['MY'],
    commodities: ['palm_oil'],
    category: 'platform',
  },
  {
    title: 'Satu Data — Indonesia',
    description:
      'Portal nacional indonesio de datos geoespaciales con capas de uso de suelo. Util para operadores de palma y caucho.',
    url: 'https://www.satudata.go.id/',
    tags: ['ID'],
    commodities: ['palm_oil', 'rubber'],
    category: 'official',
  },
]

const CATEGORY_LABELS: Record<string, string> = {
  database: 'Base de datos',
  methodology: 'Metodologia',
  platform: 'Plataforma',
  official: 'Fuente oficial',
}

const CATEGORY_COLORS: Record<string, string> = {
  database: 'bg-blue-50 text-blue-700 border-blue-200',
  methodology: 'bg-purple-50 text-purple-700 border-purple-200',
  platform: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  official: 'bg-emerald-50 text-emerald-700 border-emerald-200',
}

const COUNTRY_LABELS: Record<string, string> = {
  global: 'Global',
  eu: 'UE',
  es: 'España',
  CO: 'Colombia',
  PE: 'Peru',
  EC: 'Ecuador',
  BR: 'Brasil',
  CI: 'Costa de Marfil',
  GH: 'Ghana',
  MY: 'Malasia',
  ID: 'Indonesia',
}

export default function LegalResourcesPage() {
  const [countryFilter, setCountryFilter] = useState<string>('all')
  const [commodityFilter, setCommodityFilter] = useState<string>('all')

  const countries = useMemo(() => {
    const set = new Set<string>()
    for (const r of RESOURCES) for (const t of r.tags) set.add(t)
    return Array.from(set).sort((a, b) => {
      // Globals first
      if (a === 'global') return -1
      if (b === 'global') return 1
      return a.localeCompare(b)
    })
  }, [])

  const commodities = useMemo(() => {
    const set = new Set<string>()
    for (const r of RESOURCES) for (const c of r.commodities) set.add(c)
    return Array.from(set).sort()
  }, [])

  const filtered = useMemo(() => {
    return RESOURCES.filter((r) => {
      if (countryFilter !== 'all' && !r.tags.includes(countryFilter)) return false
      if (
        commodityFilter !== 'all' &&
        !r.commodities.includes(commodityFilter) &&
        !r.commodities.includes('all')
      )
        return false
      return true
    })
  }, [countryFilter, commodityFilter])

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50">
            <BookOpen className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">Biblioteca legal EUDR</h1>
            <p className="text-sm text-muted-foreground">
              Recursos oficiales, bases de datos y metodologias para ejercer due diligence
            </p>
          </div>
        </div>
        <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-3 text-xs text-blue-900 leading-relaxed">
          Trace consolida aqui las fuentes publicas mas utiles para construir
          evidencia de cumplimiento EUDR. Estos recursos son complementarios a
          las verificaciones automaticas del sistema — el operador sigue siendo
          el responsable final de la diligencia debida. Filtros por pais y commodity
          ayudan a acotar rapidamente las referencias pertinentes para tu cadena.
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-muted-foreground"><Globe className="inline h-3 w-3 mr-1" />Pais:</span>
          {['all', ...countries].map((c) => (
            <button
              key={c}
              onClick={() => setCountryFilter(c)}
              className={`text-xs px-3 py-1 rounded-full border transition ${
                countryFilter === c
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-card text-muted-foreground border-border hover:border-blue-300'
              }`}
            >
              {c === 'all' ? 'Todos' : COUNTRY_LABELS[c] ?? c}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-muted-foreground"><Scale className="inline h-3 w-3 mr-1" />Commodity:</span>
          {['all', ...commodities.filter((c) => c !== 'all')].map((c) => (
            <button
              key={c}
              onClick={() => setCommodityFilter(c)}
              className={`text-xs px-3 py-1 rounded-full border transition ${
                commodityFilter === c
                  ? 'bg-purple-600 text-white border-purple-600'
                  : 'bg-card text-muted-foreground border-border hover:border-purple-300'
              }`}
            >
              {c === 'all' ? 'Todos' : c}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {filtered.length === 0 ? (
          <div className="col-span-full flex justify-center py-12 text-muted-foreground">
            Sin recursos para el filtro seleccionado.
          </div>
        ) : (
          filtered.map((r) => (
            <div key={r.title} className="bg-card rounded-xl border border-border p-5 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-sm font-bold text-foreground leading-snug">{r.title}</h3>
                <span className={`shrink-0 inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold ${CATEGORY_COLORS[r.category]}`}>
                  {CATEGORY_LABELS[r.category]}
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-snug">{r.description}</p>
              <div className="flex flex-wrap gap-1">
                {r.tags.map((t) => (
                  <span key={t} className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-700">
                    {COUNTRY_LABELS[t] ?? t}
                  </span>
                ))}
                {r.commodities
                  .filter((c) => c !== 'all')
                  .map((c) => (
                    <span key={c} className="inline-flex rounded-full bg-purple-50 px-2 py-0.5 text-[10px] font-medium text-purple-700">
                      {c}
                    </span>
                  ))}
              </div>
              <a
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
              >
                Visitar recurso <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
