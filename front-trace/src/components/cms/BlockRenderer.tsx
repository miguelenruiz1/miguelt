import { HeroBlock } from './blocks/HeroBlock'
import { FeaturesBlock } from './blocks/FeaturesBlock'
import { PricingBlock } from './blocks/PricingBlock'
import { FaqBlock } from './blocks/FaqBlock'
import { TestimonialsBlock } from './blocks/TestimonialsBlock'
import { CtaBlock } from './blocks/CtaBlock'
import { StatsBlock } from './blocks/StatsBlock'
import { ImageTextBlock } from './blocks/ImageTextBlock'
import { CountdownBlock } from './blocks/CountdownBlock'
import { LogosBlock } from './blocks/LogosBlock'
import { CustomHtmlBlock } from './blocks/CustomHtmlBlock'

const BLOCK_MAP: Record<string, React.ComponentType<{ config: any }>> = {
  hero: HeroBlock,
  features: FeaturesBlock,
  pricing: PricingBlock,
  faq: FaqBlock,
  testimonials: TestimonialsBlock,
  cta: CtaBlock,
  stats: StatsBlock,
  image_text: ImageTextBlock,
  countdown: CountdownBlock,
  logos: LogosBlock,
  custom_html: CustomHtmlBlock,
}

interface BlockRendererProps {
  blockType: string
  config: Record<string, any>
  anchorId?: string
  cssClass?: string
}

export function BlockRenderer({ blockType, config, anchorId, cssClass }: BlockRendererProps) {
  const Component = BLOCK_MAP[blockType]
  if (!Component) {
    return (
      <section id={anchorId} className={cssClass}>
        <div style={{ padding: 40, textAlign: 'center', color: '#666' }}>
          Bloque desconocido: <code>{blockType}</code>
        </div>
      </section>
    )
  }

  return (
    <section id={anchorId} className={cssClass}>
      <Component config={config} />
    </section>
  )
}

/** Available block types for the editor */
export const AVAILABLE_BLOCKS = [
  { type: 'hero', label: 'Hero', icon: '🏠', description: 'Seccion principal con titulo, CTAs y stats' },
  { type: 'features', label: 'Funcionalidades', icon: '⭐', description: 'Grid de tarjetas con icono y descripcion' },
  { type: 'pricing', label: 'Precios', icon: '💰', description: 'Tarjetas de planes con precios y features' },
  { type: 'faq', label: 'FAQ', icon: '❓', description: 'Acordeon de preguntas frecuentes' },
  { type: 'testimonials', label: 'Testimonios', icon: '💬', description: 'Tarjetas con citas de clientes' },
  { type: 'cta', label: 'Call to Action', icon: '📢', description: 'Seccion con titulo, subtitulo y botones' },
  { type: 'stats', label: 'Estadisticas', icon: '📊', description: 'Numeros destacados en fila' },
  { type: 'image_text', label: 'Imagen + Texto', icon: '🖼️', description: 'Imagen con texto al lado' },
  { type: 'countdown', label: 'Cuenta Regresiva', icon: '⏰', description: 'Contador hasta una fecha objetivo' },
  { type: 'logos', label: 'Logos', icon: '🏷️', description: 'Fila de logos de socios o integraciones' },
  { type: 'custom_html', label: 'HTML Personalizado', icon: '🔧', description: 'Codigo HTML libre' },
]
