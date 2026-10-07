import { Clock3 } from 'lucide-react'
import { useCountdown } from '../../hooks/useCountdown'
import { useGame } from '../../contexts/GameContext'
export function Timer() {
  const { state, clockOffset } = useGame(); const q = state.question
  const remaining = useCountdown(q?.startedAt, q?.durationSeconds ?? 20, clockOffset)
  const active = state.phase === 'active'
  return <div className={`timer ${active && remaining !== null && remaining <= 5 ? 'urgent' : ''}`} role="timer" aria-label={remaining === null ? 'Waiting for server timer' : `${remaining} seconds remaining`}><Clock3 size={20} aria-hidden="true"/><span>{!active ? '—' : remaining === null ? '--:--' : remaining === 0 ? 'TIME!' : `00:${String(remaining).padStart(2, '0')}`}</span><small>{active ? 'left' : 'stand by'}</small></div>
}
