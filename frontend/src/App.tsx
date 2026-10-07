import { useEffect } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Maximize, Volume2, VolumeX, Sparkles, ArrowRight, WifiOff } from 'lucide-react'
import { MotionConfig } from 'framer-motion'
import { GameProvider, useGame } from './contexts/GameContext'
import { Brand, ErrorNotice, Loading } from './components/common/UI'
import { DEMO } from './services/api'
import { useSound } from './hooks/useSound'
import LandingPage from './pages/LandingPage'
import JoinPage from './pages/JoinPage'
import LobbyPage from './pages/LobbyPage'
import PlayerGamePage from './pages/PlayerGamePage'
import PlayerResultsPage from './pages/PlayerResultsPage'
import HostHomePage from './pages/host/HostHomePage'
import GameContentPage from './pages/host/GameContentPage'
import './gameplay.css'
import { HostGuard } from './components/common/HostGuard'
import { SplashGate } from './components/intro/SplashIntro'
export default function App() {
  const pathname = useLocation().pathname
  const control = pathname.startsWith('/control')
  if (pathname === '/host' || pathname === '/host/') return <Navigate to="/control" replace/>
  const content = <GameProvider key={control ? 'control' : 'player'}><Layout/></GameProvider>
  return <MotionConfig reducedMotion="user"><SplashGate>{control ? <HostGuard>{content}</HostGuard> : content}</SplashGate></MotionConfig>
}
function Layout() {
  const location = useLocation(); const navigate = useNavigate(); const host = location.pathname.startsWith('/control')
  const { state, loading, error, connection, refresh } = useGame(); const sound = useSound()
  const lobbyPolling = state.phase === 'lobby' && Boolean(state.id || state.player?.waitingForGame)
  const lobbyPage = ['/lobby', '/control/lobby'].includes(location.pathname)
  const homePage = location.pathname === '/'
  const inSession = ['/lobby', '/game', '/results', '/control/lobby', '/control/game', '/control/results'].includes(location.pathname)
  useEffect(() => {
    if (!inSession || loading || !state.id || (!host && !state.player)) return
    const target = `${host ? '/control' : ''}/${state.phase === 'completed' ? 'results' : state.phase === 'lobby' ? 'lobby' : 'game'}`
    if (location.pathname !== target) navigate(target, { replace: true })
  }, [state.phase, state.id, state.player, host, inSession, loading, location.pathname, navigate])
  useEffect(() => { if (state.phase === 'countdown') sound.play('countdown'); if (state.phase === 'score_revealed') sound.play('score'); if (state.phase === 'completed' && !state.endedReason) sound.play('winner') }, [state.phase])
  const hostTools = host && <div className="header-right"><button className="icon-button" aria-label={sound.enabled ? 'Mute game sounds' : 'Enable game sounds'} aria-pressed={sound.enabled} onClick={sound.toggle}>{sound.enabled ? <Volume2 size={20}/> : <VolumeX size={20}/>}</button><button className="icon-button" aria-label="Toggle projector full screen" onClick={() => { if (document.fullscreenElement) void document.exitFullscreen(); else void document.documentElement.requestFullscreen().catch(() => {}) }}><Maximize size={20}/></button></div>
  return <div className={`app ${lobbyPage ? 'lobby-shell' : homePage ? 'home-shell' : ''}`}>
    {!lobbyPage && !homePage && <header className={`site-header ${host ? 'host-header' : ''}`}><Brand/><div className="header-right">{DEMO && <span className="demo-badge">DEMO GAME</span>}{inSession ? <><span className={`connection-status ${connection}`}><span/>{lobbyPolling && !error ? 'Updates every 5s' : connection === 'connected' ? 'Connected' : connection === 'unavailable' ? 'Live updates unavailable' : 'Reconnecting…'}</span>{hostTools}</> : <span className="header-tag"><Sparkles size={16}/>A little friendly rivalry.</span>}</div></header>}
    {inSession && !lobbyPolling && connection === 'reconnecting' && <div className="reconnect-banner" role="status"><WifiOff size={16}/>Reconnecting… Your place in the game is safe.</div>}{inSession && error && <div className="global-error"><ErrorNotice message={error} retry={() => void refresh()}/></div>}
    {inSession && loading ? <Loading label={state.player ? 'Rejoining your team…' : 'Setting the stage…'}/> : <Routes><Route path="/" element={<LandingPage/>}/><Route path="/play" element={<JoinPage/>}/><Route path="/login" element={<JoinPage/>}/><Route path="/lobby" element={<LobbyPage/>}/><Route path="/game" element={<PlayerGamePage/>}/><Route path="/results" element={<PlayerResultsPage/>}/><Route path="/control" element={<HostHomePage/>}/><Route path="/control/content" element={<GameContentPage/>}/><Route path="/control/lobby" element={<LobbyPage host tools={hostTools}/>}/><Route path="/control/game" element={<PlayerGamePage host/>}/><Route path="/control/results" element={<PlayerResultsPage host/>}/><Route path="*" element={<main className="center-page"><h1>A little off track?</h1><p>The fun’s back this way.</p><Link to="/" className="button primary">Back to Home<ArrowRight size={18}/></Link></main>}/></Routes>}
    {!lobbyPage && !homePage && <footer className="site-footer"><span>Made for teams. Played together.</span><span>All in. All six rounds.<span className="footer-star">✦</span></span></footer>}</div>
}

