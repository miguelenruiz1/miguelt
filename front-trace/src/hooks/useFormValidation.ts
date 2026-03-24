import { useRef, useCallback } from 'react'

/**
 * jQuery Validate-style form validation for React.
 *
 * - Prevents native browser validation popups (uses noValidate)
 * - On submit: marks invalid fields with red borders + shows error labels
 * - Labels turn red for invalid fields
 * - Error messages appear below each invalid field
 *
 * Usage:
 *   const { formRef, handleSubmit } = useFormValidation(onValid)
 *   <form ref={formRef} onSubmit={handleSubmit} noValidate>
 *     <label className="field-label">Nombre</label>
 *     <input required />
 *   </form>
 */
export function useFormValidation(onValid: (e: React.FormEvent) => void | Promise<void>) {
  const formRef = useRef<HTMLFormElement>(null)

  const handleSubmit = useCallback((e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    e.stopPropagation()
    const form = formRef.current
    if (!form) return

    // Clear previous error states
    form.querySelectorAll('.jv-error').forEach(el => el.remove())
    form.querySelectorAll('.jv-invalid').forEach(el => el.classList.remove('jv-invalid'))
    form.querySelectorAll('.jv-label-invalid').forEach(el => el.classList.remove('jv-label-invalid'))

    // Collect all invalid fields
    const invalids: HTMLElement[] = []
    form.querySelectorAll('input, select, textarea').forEach(field => {
      const el = field as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
      if (!el.checkValidity()) {
        invalids.push(el)

        // Red border on the field
        el.classList.add('jv-invalid')

        // Find the label (previous sibling or parent's previous sibling)
        const label = findLabel(el)
        if (label) label.classList.add('jv-label-invalid')

        // Create error message below the field
        const msg = getErrorMessage(el)
        const errorEl = document.createElement('span')
        errorEl.className = 'jv-error'
        errorEl.textContent = msg
        // Insert after the field (or after its parent div if wrapped)
        const insertAfter = el.parentElement?.classList.contains('relative') ? el.parentElement : el
        insertAfter.insertAdjacentElement('afterend', errorEl)
      }
    })

    if (invalids.length > 0) {
      invalids[0].focus()
      return
    }

    // Add listener to clear errors on input
    form.addEventListener('input', clearFieldError, { once: false })
    form.addEventListener('change', clearFieldError, { once: false })

    onValid(e)
  }, [onValid])

  return { formRef, handleSubmit }
}

function findLabel(field: HTMLElement): HTMLElement | null {
  // Check for label as previous sibling
  let prev = field.previousElementSibling
  if (prev?.tagName === 'LABEL') return prev as HTMLElement

  // Check parent's previous sibling (for wrapped inputs)
  const parent = field.parentElement
  if (parent) {
    prev = parent.previousElementSibling
    if (prev?.tagName === 'LABEL') return prev as HTMLElement
  }

  // Check for label with matching for attribute
  const id = field.getAttribute('id')
  if (id) {
    const label = document.querySelector(`label[for="${id}"]`)
    if (label) return label as HTMLElement
  }

  return null
}

function getErrorMessage(el: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement): string {
  if (el.validity.valueMissing) {
    if (el.tagName === 'SELECT') return 'Selecciona una opción'
    return 'Este campo es obligatorio'
  }
  if (el.validity.typeMismatch) return 'Formato inválido'
  if (el.validity.rangeUnderflow) return `El valor mínimo es ${el.min}`
  if (el.validity.rangeOverflow) return `El valor máximo es ${el.max}`
  if (el.validity.tooShort) return `Mínimo ${el.minLength} caracteres`
  if (el.validity.patternMismatch) return 'Formato no válido'
  return 'Campo inválido'
}

function clearFieldError(e: Event) {
  const el = e.target as HTMLElement
  if (!el) return
  el.classList.remove('jv-invalid')
  // Remove error message
  const next = el.nextElementSibling
  if (next?.classList.contains('jv-error')) next.remove()
  // Also check parent wrapper
  const parentNext = el.parentElement?.nextElementSibling
  if (parentNext?.classList.contains('jv-error')) parentNext.remove()
  // Clear label
  const label = findLabel(el)
  if (label) label.classList.remove('jv-label-invalid')
}
