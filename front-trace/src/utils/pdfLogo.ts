import { jsPDF } from 'jspdf'

/**
 * Draw the TraceLog logo using jsPDF primitives.
 * Renders the indigo rounded-rect background with white "T" mark.
 *
 * @param doc  jsPDF instance
 * @param x    left edge (mm)
 * @param y    top edge (mm)
 * @param size square size in mm (default 14)
 */
export function drawLogo(doc: jsPDF, x: number, y: number, size = 14): void {
  const s = size / 34 // scale factor from 34×34 viewBox

  // Background: indigo rounded rect (#4F46E5)
  doc.setFillColor(79, 70, 229)
  doc.roundedRect(x, y, size, size, 8 * s, 8 * s, 'F')

  // Main "T" shape — white
  doc.setFillColor(255, 255, 255)
  // Top horizontal bar: (8,11) → (26,13.5) in viewBox
  doc.rect(x + 8 * s, y + 11 * s, 18 * s, 2.5 * s, 'F')
  // Vertical stem: (15,13.5) → (18.5,25)
  doc.rect(x + 15 * s, y + 13.5 * s, 3.5 * s, 11.5 * s, 'F')

  // Accent mark — white at 70% opacity
  doc.saveGraphicsState()
  const gState = new (doc as any).GState({ opacity: 0.7 })
  doc.setGState(gState)
  doc.setFillColor(255, 255, 255)
  // Vertical part: (20,17) → (22.5,22.5)
  doc.rect(x + 20 * s, y + 17 * s, 2.5 * s, 5.5 * s, 'F')
  // Horizontal part: (20,22.5) → (27,25)
  doc.rect(x + 20 * s, y + 22.5 * s, 7 * s, 2.5 * s, 'F')
  doc.restoreGraphicsState()
}
