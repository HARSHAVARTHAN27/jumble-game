import { useEffect, useRef, useState } from 'react'
import { useReducedMotion } from 'framer-motion'
export function AnimatedNumber({ value, from, duration = 850 }: { value: number; from?: number; duration?: number }) {
  const [display, setDisplay] = useState(from ?? 0)
  const previous = useRef(from ?? 0)
  const reduce = useReducedMotion()
  useEffect(() => {
    if (reduce) { previous.current = value; setDisplay(value); return }
    const start = previous.current; const started = performance.now(); let frame: number
    const tick = (now: number) => { const progress = Math.min(1, (now - started) / duration); const next = start + (value - start) * (1 - (1 - progress) ** 3); setDisplay(Math.round(next)); if (progress < 1) frame = requestAnimationFrame(tick); else previous.current = value }
    frame = requestAnimationFrame(tick); return () => cancelAnimationFrame(frame)
  }, [value, duration, reduce])
  return <span className="tabular-nums">{display.toLocaleString()}</span>
}
