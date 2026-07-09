import { useEffect } from 'react'

const BASE_TITLE = 'CamelTv 测试平台'

/**
 * Set document.title for the current route. Restores base title on unmount.
 * @param title - Page-specific title segment; appended as "{title} | {BASE_TITLE}"
 * @param deps  - Optional dependency array to re-trigger (defaults to [title]).
 */
export function useDocumentTitle(title: string, deps: unknown[] = [title]) {
  useEffect(() => {
    const prev = document.title
    document.title = title ? `${title} | ${BASE_TITLE}` : BASE_TITLE
    return () => {
      document.title = prev
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}
