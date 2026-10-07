import { AnimatePresence, motion } from 'framer-motion'
import { useCountdown } from '../../hooks/useCountdown'
import { useGame } from '../../contexts/GameContext'
export function Countdown() {
  const { state, clockOffset } = useGame()
  const number = useCountdown(state.countdownStartedAt, 4, clockOffset)
  return <div className="countdown-screen"><span className="eyebrow">THREE TEAMS. ONE BIG MOMENT.</span><h2>Everybody ready?</h2><AnimatePresence mode="wait"><motion.div key={number} className="countdown-number" initial={{ opacity: 0, scale: 0.55 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 1.3 }}>{number === null ? '…' : number > 1 ? number - 1 : 'Let’s go!'}</motion.div></AnimatePresence><p>The fun is about to begin.</p></div>
}
