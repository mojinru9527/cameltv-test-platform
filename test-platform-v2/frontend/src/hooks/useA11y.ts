import { useEffect, useRef } from 'react'

/**
 * Traps Tab / Shift+Tab focus within a container element when `active` is true.
 * Useful for modals, dialogs, and drawers.
 *
 * @param active - When true, focus is trapped inside the container.
 * @returns A ref to attach to the container element.
 */
export function useFocusTrap(active: boolean) {
  const containerRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!active || !containerRef.current) return

    const container = containerRef.current

    // Collect all focusable elements inside the container
    const getFocusableElements = (): HTMLElement[] => {
      const selector =
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      return Array.from(container.querySelectorAll<HTMLElement>(selector)).filter(
        (el) => el.offsetParent !== null,
      )
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return

      const focusable = getFocusableElements()
      if (focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (e.shiftKey) {
        // Shift+Tab: if focus is on first element, wrap to last
        if (document.activeElement === first || document.activeElement === container) {
          e.preventDefault()
          last.focus()
        }
      } else {
        // Tab: if focus is on last element, wrap to first
        if (document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }

    // Auto-focus the first focusable element on activation
    const focusable = getFocusableElements()
    if (focusable.length > 0) {
      // Defer focus so any opening animation completes first
      const raf = requestAnimationFrame(() => {
        focusable[0].focus()
      })
      document.addEventListener('keydown', handleKeyDown)
      return () => {
        cancelAnimationFrame(raf)
        document.removeEventListener('keydown', handleKeyDown)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [active])

  return containerRef
}

/**
 * Saves the currently focused element before a UI change (e.g. opening a modal)
 * and restores focus when the hook's owner unmounts.
 *
 * @returns An object with `save()` to snapshot current focus now, and `restore()`
 *   to manually put focus back (also called automatically on unmount).
 */
export function useFocusRestore() {
  const savedRef = useRef<HTMLElement | null>(null)

  const save = () => {
    savedRef.current = document.activeElement as HTMLElement | null
  }

  const restore = () => {
    if (savedRef.current && typeof savedRef.current.focus === 'function') {
      savedRef.current.focus()
    }
    savedRef.current = null
  }

  // Restore on unmount
  useEffect(() => {
    return () => {
      if (savedRef.current && typeof savedRef.current.focus === 'function') {
        savedRef.current.focus()
      }
    }
  }, [])

  return { save, restore }
}
