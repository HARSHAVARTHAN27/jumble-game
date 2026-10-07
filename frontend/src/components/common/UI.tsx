import { motion, useReducedMotion } from 'framer-motion'
import { ArrowRight, Gamepad2, LoaderCircle, Shield, Zap, Sparkles, Check, AlertCircle } from 'lucide-react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { TeamName } from '../../types/game'
export function Button({ children, busy, variant = 'primary', className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { busy?: boolean; variant?: 'primary' | 'secondary' | 'quiet' }) {
  return <button {...props} className={`button ${variant} ${className}`} disabled={busy || props.disabled}>{busy && <LoaderCircle className="spin" size={18} aria-hidden="true" />}{children}</button>
}
export function Page({ children, className = '' }: { children: ReactNode; className?: string }) {
  const reduce = useReducedMotion()
  return <motion.main className={`page ${className}`} initial={reduce ? false : { opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>{children}</motion.main>
}
export function Brand() { return <Link to="/" className="brand" aria-label="Jumble home"><span className="brand-mark"><span/><span/><span/><span/></span>jumble<span className="brand-dot">.</span></Link> }
export function TeamIcon({ name, size = 24 }: { name: TeamName; size?: number }) { const Icon = name === 'Ctrl Alt Defeat' ? Gamepad2 : name === 'Titans' ? Shield : Zap; return <Icon size={size} strokeWidth={2} aria-hidden="true" /> }
export function teamClass(name: TeamName) { return name === 'Ctrl Alt Defeat' ? 'coral' : name === 'Titans' ? 'blue' : 'green' }
export function TeamBadge({ name }: { name: TeamName }) { return <span className={`team-badge ${teamClass(name)}`}><TeamIcon name={name} size={17}/>{name}</span> }
export function ErrorNotice({ message, retry }: { message: string; retry?: () => void }) { return <div className="error-notice" role="alert"><AlertCircle size={19} aria-hidden="true"/><span>{message}</span>{retry && <button onClick={retry}>Try again</button>}</div> }
export function Loading({ label = 'Connecting to the fun…' }: { label?: string }) { return <Page className="center-page"><div className="loading-art"><Sparkles size={38}/><span className="loading-ring"/></div><h2>{label}</h2><p className="muted">Just a little moment.</p></Page> }
export function Progress({ value, max, className = '' }: { value: number; max: number; className?: string }) { return <div className={`progress ${className}`} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}><motion.div initial={{ scaleX: 0 }} animate={{ scaleX: Math.min(1, max > 0 ? value / max : 0) }} transition={{ duration: 0.65 }} /></div> }
export function LockedIcon() { return <div className="state-icon success"><Check size={45} strokeWidth={3}/></div> }
export function Arrow() { return <ArrowRight size={19} aria-hidden="true"/> }
