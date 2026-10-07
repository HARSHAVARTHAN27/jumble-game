import { useCallback, useEffect, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { ArrowRight, Flame, Sparkles, Trophy, Zap } from 'lucide-react'
import { INTRO_DURATION, INTRO_STAGES, INTRO_STORAGE_KEY, introSceneAt } from './timeline'
import '../../splash.css'

let seenInMemory = false
const entryPaths = new Set(['/', '/play', '/login'])
const letters = [
  { letter: 'J', color: 'purple', x: '135%', y: '-105%', rotation: '-24deg' },
  { letter: 'U', color: 'white', x: '-80%', y: '110%', rotation: '18deg' },
  { letter: 'M', color: 'blue', x: '20%', y: '-130%', rotation: '22deg' },
  { letter: 'B', color: 'orange', x: '105%', y: '-65%', rotation: '-17deg' },
  { letter: 'L', color: 'purple', x: '-50%', y: '100%', rotation: '24deg' },
  { letter: 'E', color: 'white', x: '-10%', y: '125%', rotation: '-16deg' },
]
const teams = [
  { name: 'Ctrl Alt Defeat', color: 'purple', Icon: Zap },
  { name: 'Titans', color: 'orange', Icon: Flame },
  { name: 'Vibe Tribe', color: 'blue', Icon: Sparkles },
]
const ornaments = [
  { name: 'trophy', color: 'orange', Icon: Trophy },
  { name: 'brain', color: 'purple', image: '/images/home/memory.png' },
  { name: 'target', color: 'blue', image: '/images/home/target.png' },
  { name: 'bolt', color: 'purple', Icon: Zap },
  { name: 'puzzle', color: 'orange', image: '/images/home/connection.png' },
  { name: 'spark', color: 'blue', Icon: Sparkles },
]

function wantsIntro(pathname: string) {
  if (!entryPaths.has(pathname) || seenInMemory || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false
  try { return sessionStorage.getItem(INTRO_STORAGE_KEY) !== 'true' } catch { return true }
}

/** Only public entry pages play the intro. The app remains mounted and preloads beneath it. */
export function SplashGate({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const [show, setShow] = useState(() => wantsIntro(pathname))
  const content = useRef<HTMLDivElement>(null)
  const finish = useCallback((restoreFocus = false) => {
    seenInMemory = true
    try { sessionStorage.setItem(INTRO_STORAGE_KEY, 'true') } catch { /* Private browsing can deny storage. */ }
    setShow(false)
    if (restoreFocus) requestAnimationFrame(() => {
      const heading = content.current?.querySelector<HTMLElement>('main h1')
      if (heading) { heading.tabIndex = -1; heading.focus({ preventScroll: true }) }
    })
  }, [])
  const visible = show && entryPaths.has(pathname)
  return <>
    <div ref={content} className={visible ? 'splash-underlay' : 'splash-content'} inert={visible} aria-hidden={visible || undefined}>{children}</div>
    {visible && <SplashIntro onComplete={finish}/>}
  </>
}

function SplashIntro({ onComplete }: { onComplete: (restoreFocus?: boolean) => void }) {
  const [scene, setScene] = useState(1)
  const skip = useRef<HTMLButtonElement>(null)
  const complete = useCallback(() => onComplete(document.activeElement === skip.current), [onComplete])
  useEffect(() => {
    const started = performance.now()
    const sync = () => {
      const elapsed = performance.now() - started
      if (elapsed >= INTRO_DURATION) complete()
      else setScene(introSceneAt(elapsed))
    }
    const timers = [...INTRO_STAGES.slice(1), INTRO_DURATION].map(time => window.setTimeout(sync, time))
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const changed = () => { if (preference.matches) complete() }
    const keyboard = (event: KeyboardEvent) => { if (event.key === 'Escape') complete() }
    document.addEventListener('visibilitychange', sync)
    document.addEventListener('keydown', keyboard)
    preference.addEventListener('change', changed)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      timers.forEach(clearTimeout)
      document.body.style.overflow = overflow
      document.removeEventListener('visibilitychange', sync)
      document.removeEventListener('keydown', keyboard)
      preference.removeEventListener('change', changed)
    }
  }, [complete])

  return <section className="jumble-splash" data-scene={scene} aria-label="Welcome to Jumble">
    <div className="splash-atmosphere" aria-hidden="true"/>
    <div className="splash-ornaments" aria-hidden="true">{ornaments.map(({name, color, Icon, image}) =>
      <div key={name} className={`splash-object splash-object-${name} splash-material-${color}`}>
        {image ? <img src={image} alt="" draggable={false} width="1280" height="1280"/> : Icon && <Icon strokeWidth={1.6}/>}
      </div>
    )}</div>
    <div className="splash-copy">
      <h1 className="splash-logo" aria-label="JUMBLE"><span className="splash-letter-row" aria-hidden="true">{letters.map(({letter,color,x,y,rotation},i) =>
        <span key={letter} className={`splash-letter splash-material-${color}`} style={{'--scatter-x':x,'--scatter-y':y,'--scatter-rotation':rotation,'--rest-rotation':`${[-7,3,-3,4,-4,6][i]}deg`} as CSSProperties}><span>{letter}</span></span>
      )}</span></h1>
      <div className="splash-impact" aria-hidden="true">{Array.from({length:10},(_,i)=><i key={i} style={{'--ray':`${i*36}deg`,'--accent':['#792cff','#087dff','#ff940c'][i%3]} as CSSProperties}/>)}</div>
      <p className="splash-tagline"><span>6 Games.</span> <span>3 Teams.</span> <span>1 Winner.</span></p>
      <div className="splash-team-reveal">
        <p className="splash-rally">Get ready to think, react &amp; compete.</p>
        <ul className="splash-teams" aria-label="Three teams">{teams.map(({name,color,Icon}) => <li key={name} className={`splash-team splash-team-${color}`}>
          <span className="splash-emblem"><Icon aria-hidden="true" strokeWidth={1.6}/></span><span className="splash-team-name">{name}</span>
        </li>)}</ul>
      </div>
    </div>
    <div className="splash-confetti" aria-hidden="true">{Array.from({length:28},(_,i)=><i key={i} style={{'--x':`${i%2 ? 87+(i*7)%12 : 1+(i*7)%13}%`,'--y':`${4+(i*19)%87}%`,'--spin':`${i*37}deg`,'--delay':`${(i%5)*25}ms`,'--accent':['#792cff','#087dff','#ff940c','#f47caf'][i%4]} as CSSProperties}/>)}</div>
    <div className="splash-footer"><span className="splash-progress" aria-hidden="true"><i/></span><button ref={skip} type="button" className="splash-skip" onClick={complete}>Skip intro<ArrowRight size={17} aria-hidden="true"/></button></div>
  </section>
}
