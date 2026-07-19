import { useEffect, useState } from 'react'

interface DecryptedTextProps {
  text: string
  activeKey: string
  className?: string
}

const glyphs = ['0', '1', 'X', '#', '/', '+', '△', '◇']

export function DecryptedText({ text, activeKey, className = '' }: DecryptedTextProps) {
  const [visibleText, setVisibleText] = useState(text)

  useEffect(() => {
    const reduceMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reduceMotion) {
      setVisibleText(text)
      return
    }

    const characters = Array.from(text)
    let frame = 0
    const totalFrames = 12
    const timer = window.setInterval(() => {
      frame += 1
      const revealed = Math.ceil((frame / totalFrames) * characters.length)
      const next = characters
        .map((character, index) => {
          if (character === ' ' || index < revealed) return character
          return glyphs[Math.floor(Math.random() * glyphs.length)]
        })
        .join('')

      setVisibleText(next)
      if (frame >= totalFrames) {
        window.clearInterval(timer)
        setVisibleText(text)
      }
    }, 32)

    return () => window.clearInterval(timer)
  }, [activeKey, text])

  return (
    <span className={className} aria-label={text}>
      <span aria-hidden="true">{visibleText}</span>
    </span>
  )
}
