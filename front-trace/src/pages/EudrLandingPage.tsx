import { Link } from 'react-router-dom'
import {
  ArrowRight, ArrowLeft, Check, ChevronRight,
  ShieldCheck, MapPin, FileCheck, Clock, CircleAlert, Globe, Award,
} from 'lucide-react'

// ─── Nav ─────────────────────────────────────────────────────────────────────

function Nav() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-card/80 backdrop-blur-xl border-b border-border">
      <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/home" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <span className="text-white font-extrabold text-sm">T</span>
          </div>
          <span className="font-bold text-foreground">TraceLog</span>
        </Link>
        <Link
          to="/register"
          className="bg-primary text-white px-5 py-2.5 rounded-lg text-sm font-bold hover:bg-primary/90 transition-colors"
        >
          Comenzar ahora
        </Link>
      </div>
    </nav>
  )
}

// ─── Hero ────────────────────────────────────────────────────────────────────

function Hero() {
  return (
    <section className="pt-28 pb-16 bg-card">
      <div className="max-w-3xl mx-auto px-6 text-center">
        <div className="inline-flex items-center gap-2 rounded-full bg-red-50 px-4 py-1.5 text-sm mb-6 border border-red-200">
          <CircleAlert className="h-4 w-4 text-red-500" />
          <span className="text-red-700 font-medium">Regulacion EUDR vigente desde diciembre 2025</span>
        </div>

        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-foreground leading-[1.15] tracking-tight">
          Tu comprador europeo ya te pidio el certificado de trazabilidad?
        </h1>

        <p className="mt-6 text-lg text-muted-foreground leading-relaxed max-w-2xl mx-auto">
          La Union Europea exige que cada carga de cafe, cacao, madera y otros productos
          demuestre que no proviene de tierras deforestadas. Sin ese certificado, tu carga no entra.
        </p>

        <div className="mt-8">
          <a
            href="#solucion"
            className="inline-flex items-center gap-2 bg-primary text-white px-8 py-4 rounded-xl text-sm font-bold hover:bg-primary/90 transition-colors shadow-lg shadow-primary/20"
          >
            Ver como resolverlo
            <ArrowRight className="h-4 w-4" />
          </a>
        </div>
      </div>
    </section>
  )
}

// ─── Problem ─────────────────────────────────────────────────────────────────

function Problem() {
  const pains = [
    {
      icon: CircleAlert,
      title: 'La regulacion es confusa y cambia rapido',
      desc: 'El Reglamento (UE) 2023/1115 exige una Declaracion de Diligencia Debida (DDS) por cada carga. Incluye coordenadas GPS de parcelas, datos de proveedores y prueba de no-deforestacion. La mayoria de exportadores no saben por donde empezar.',
    },
    {
      icon: Clock,
      title: 'Armar la documentacion toma semanas',
      desc: 'Recoger datos de fincas, lotes, rutas de transporte y certificados de origen en Excel, WhatsApp y correo es lento, propenso a errores, y cada comprador pide el formato diferente.',
    },
    {
      icon: Globe,
      title: 'Un rechazo en puerto te cuesta la temporada',
      desc: 'Si tu carga llega a Europa sin la documentacion correcta, queda retenida. Pierdes el producto, el flete y la confianza del importador. Un error puede costarte toda la relacion comercial.',
    },
  ]

  return (
    <section className="py-16 bg-muted">
      <div className="max-w-4xl mx-auto px-6">
        <p className="text-sm font-bold text-red-500 uppercase tracking-wider text-center mb-3">El problema</p>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground text-center mb-10">
          Exportar a Europa ya no es solo tener buen producto
        </h2>

        <div className="space-y-5">
          {pains.map(p => {
            const Icon = p.icon
            return (
              <div key={p.title} className="bg-card rounded-2xl border border-border p-6 flex gap-5">
                <div className="h-11 w-11 rounded-xl bg-red-50 flex items-center justify-center shrink-0">
                  <Icon className="h-5 w-5 text-red-500" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-foreground mb-1">{p.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{p.desc}</p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

// ─── Solution ────────────────────────────────────────────────────────────────

function Solution() {
  const benefits = [
    {
      icon: MapPin,
      title: 'Registra tus parcelas una sola vez',
      desc: 'Sube las coordenadas GPS o el poligono GeoJSON de cada finca. El sistema valida automaticamente contra datos satelitales de deforestacion.',
    },
    {
      icon: FileCheck,
      title: 'Genera certificados en minutos, no en semanas',
      desc: 'Asocia el lote, proveedor y ruta de transporte. TraceLog genera la Declaracion de Diligencia Debida en PDF con codigo QR verificable.',
    },
    {
      icon: ShieldCheck,
      title: 'Tu comprador verifica al instante',
      desc: 'El importador europeo recibe un link donde puede verificar la cadena completa: desde la parcela hasta el puerto. Sin llamadas, sin correos, sin demoras.',
    },
    {
      icon: Award,
      title: 'Certificados que generan recompra',
      desc: 'Un certificado profesional y verificable le da confianza a tu comprador. Eso se traduce en relaciones de largo plazo y mejores precios.',
    },
  ]

  return (
    <section className="py-16 bg-card" id="solucion">
      <div className="max-w-4xl mx-auto px-6">
        <p className="text-sm font-bold text-primary uppercase tracking-wider text-center mb-3">Lo que TraceLog hace por ti</p>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground text-center mb-4">
          De parcela a certificado EUDR sin complicaciones
        </h2>
        <p className="text-center text-muted-foreground mb-10 max-w-xl mx-auto">
          Tu solo registras tus fincas y proveedores. El sistema hace el resto.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {benefits.map(b => {
            const Icon = b.icon
            return (
              <div key={b.title} className="rounded-2xl border border-border p-6 hover:border-primary/30 hover:shadow-md transition-all">
                <Icon className="h-6 w-6 text-primary mb-3" />
                <h3 className="text-base font-bold text-foreground mb-2">{b.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{b.desc}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

// ─── How it works ────────────────────────────────────────────────────────────

function HowItWorks() {
  const steps = [
    { num: '1', title: 'Registra tus parcelas', desc: 'Sube las coordenadas GPS de cada finca o zona de produccion. Solo se hace una vez.' },
    { num: '2', title: 'Crea un registro por carga', desc: 'Asocia el lote, el proveedor, la cantidad y la ruta de transporte.' },
    { num: '3', title: 'Genera y envia el certificado', desc: 'PDF profesional con QR verificable. Tu comprador lo valida con un click.' },
  ]

  return (
    <section className="py-16 bg-primary/5">
      <div className="max-w-4xl mx-auto px-6">
        <p className="text-sm font-bold text-primary uppercase tracking-wider text-center mb-3">3 pasos</p>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-foreground text-center mb-10">
          Asi de simple es cumplir la EUDR con TraceLog
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {steps.map(s => (
            <div key={s.num} className="bg-card rounded-2xl p-6 text-center border border-primary/20">
              <div className="w-10 h-10 bg-primary text-white rounded-full flex items-center justify-center text-lg font-extrabold mx-auto mb-4">
                {s.num}
              </div>
              <h3 className="text-base font-bold text-foreground mb-2">{s.title}</h3>
              <p className="text-sm text-muted-foreground">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ─── Credibility ─────────────────────────────────────────────────────────────

function Credibility() {
  return (
    <section className="py-16 bg-card">
      <div className="max-w-4xl mx-auto px-6">
        <div className="bg-muted rounded-2xl border border-border p-8 sm:p-10">
          <p className="text-sm font-bold text-primary uppercase tracking-wider text-center mb-6">Respaldo</p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center mb-8">
            <div>
              <p className="text-3xl font-extrabold text-primary">100%</p>
              <p className="text-sm text-muted-foreground mt-1">Alineado con EU 2023/1115</p>
            </div>
            <div>
              <p className="text-3xl font-extrabold text-primary">7</p>
              <p className="text-sm text-muted-foreground mt-1">Commodities cubiertos</p>
            </div>
            <div>
              <p className="text-3xl font-extrabold text-primary">QR</p>
              <p className="text-sm text-muted-foreground mt-1">Verificacion instantanea</p>
            </div>
          </div>

          <div className="space-y-3">
            {[
              'Basado en el Reglamento (UE) 2023/1115 sobre productos libres de deforestacion',
              'Cubre cafe, cacao, aceite de palma, soja, madera, caucho y ganado',
              'Verificacion de deforestacion con datos satelitales de Global Forest Watch',
              'Trazabilidad de cadena de custodia respaldada por blockchain',
              'Creado en Colombia para exportadores latinoamericanos',
            ].map(item => (
              <div key={item} className="flex items-start gap-3">
                <Check className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                <p className="text-sm text-foreground">{item}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

// ─── CTA ─────────────────────────────────────────────────────────────────────

function FinalCTA() {
  return (
    <section className="py-16 bg-[oklch(0.165_0.022_255)]">
      <div className="max-w-3xl mx-auto px-6 text-center text-white">
        <h2 className="text-2xl sm:text-3xl font-extrabold mb-4">
          No esperes a que te rechacen una carga
        </h2>
        <p className="text-muted-foreground mb-8 max-w-xl mx-auto">
          La regulacion EUDR ya esta vigente. Cada embarque que envias sin certificado es un riesgo para tu negocio.
        </p>
        <Link
          to="/register"
          className="inline-flex items-center gap-2 bg-primary text-white px-8 py-4 rounded-xl text-sm font-bold hover:bg-primary/90 transition-colors"
        >
          Empezar a certificar mis cargas
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  )
}

// ─── Footer ──────────────────────────────────────────────────────────────────

function Footer() {
  return (
    <footer className="border-t border-border bg-card py-10">
      <div className="max-w-5xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <Link to="/home" className="flex items-center gap-2">
          <div className="w-7 h-7 bg-primary rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-xs">T</span>
          </div>
          <span className="font-semibold text-foreground text-sm">TraceLog</span>
        </Link>
        <p className="text-xs text-muted-foreground">Cumplimiento EUDR para exportadores. Hecho en Colombia.</p>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <Link to="/home" className="hover:text-foreground">Plataforma</Link>
          <Link to="/login" className="hover:text-foreground">Iniciar sesion</Link>
          <Link to="/register" className="hover:text-foreground">Crear cuenta</Link>
        </div>
      </div>
    </footer>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────

export function EudrLandingPage() {
  return (
    <div className="min-h-screen bg-card">
      <Nav />
      <Hero />
      <Problem />
      <Solution />
      <HowItWorks />
      <Credibility />
      <FinalCTA />
      <Footer />
    </div>
  )
}
