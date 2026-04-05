interface CustomHtmlConfig {
  html: string
}

export function CustomHtmlBlock({ config }: { config: CustomHtmlConfig }) {
  if (!config.html) return null
  return (
    <div dangerouslySetInnerHTML={{ __html: config.html }} />
  )
}
