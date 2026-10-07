import { useEffect, useState } from 'react'
export function remainingSeconds(startedAt: string | undefined, duration: number, now: number, offset = 0) {
  if (!startedAt || !Number.isFinite(Date.parse(startedAt))) return null
  return Math.max(0, Math.ceil(duration - (now + offset - Date.parse(startedAt)) / 1000))
}
export function useCountdown(startedAt: string | undefined, duration: number, offset = 0) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => { setNow(Date.now()); const interval = setInterval(() => setNow(Date.now()), 200); return () => clearInterval(interval) }, [startedAt])
  return remainingSeconds(startedAt, duration, now, offset)
}
