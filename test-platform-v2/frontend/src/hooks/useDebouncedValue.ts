import { useEffect, useState } from 'react'

/**
 * useDebouncedValue — 值防抖（Batch 150 / C147-5）。
 * 输入停止 delay 毫秒后才更新返回值，用于搜索框等高频输入避免逐键发请求。
 */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return debounced
}

export default useDebouncedValue
