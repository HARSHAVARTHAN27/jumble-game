import { useRef, useState } from 'react'
export function useSound() {
  const [enabled, setEnabled] = useState(false)
  const audio = useRef<AudioContext | null>(null)
  const toggle = () => { if (!audio.current) audio.current = new AudioContext(); void audio.current.resume(); setEnabled(old => !old) }
  const play = (kind: 'countdown' | 'submit' | 'correct' | 'wrong' | 'score' | 'winner') => {
    if (!enabled || !audio.current) return
    const ctx = audio.current; const oscillator = ctx.createOscillator(); const gain = ctx.createGain()
    oscillator.type = 'sine'; oscillator.frequency.value = { countdown: 440, submit: 550, correct: 660, wrong: 220, score: 740, winner: 880 }[kind]
    gain.gain.setValueAtTime(0.045, ctx.currentTime); gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25)
    oscillator.connect(gain); gain.connect(ctx.destination); oscillator.start(); oscillator.stop(ctx.currentTime + 0.25)
  }
  return { enabled, toggle, play }
}
