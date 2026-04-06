/**
 * Safely render HTML coming from the CMS.
 *
 * Strips <script>, on*= handlers, javascript: hrefs, embedded styles with
 * @import / behavior, and other XSS vectors via DOMPurify.
 *
 * Use this in every dangerouslySetInnerHTML for content that originates
 * outside the codebase (CMS, user input, external feed).
 */
import DOMPurify from 'isomorphic-dompurify'

const ALLOWED_TAGS = [
  'a', 'p', 'br', 'hr', 'span', 'div', 'strong', 'em', 'b', 'i', 'u',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'ul', 'ol', 'li',
  'blockquote', 'code', 'pre',
  'img', 'figure', 'figcaption',
  'table', 'thead', 'tbody', 'tr', 'th', 'td',
]

const ALLOWED_ATTR = [
  'href', 'title', 'target', 'rel',
  'src', 'alt', 'width', 'height',
  'class', 'id',
  'colspan', 'rowspan',
]

export function safeHtml(input: string | undefined | null): { __html: string } {
  if (!input) return { __html: '' }
  const clean = DOMPurify.sanitize(input, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
    ALLOW_DATA_ATTR: false,
  })
  return { __html: clean }
}
