import { safeHtml } from '@/lib/safe-html'

interface CustomHtmlConfig {
  html: string
}

export function CustomHtmlBlock({ config }: { config: CustomHtmlConfig }) {
  if (!config.html) return null
  return (
    <div dangerouslySetInnerHTML={safeHtml(config.html)} />
  )
}
