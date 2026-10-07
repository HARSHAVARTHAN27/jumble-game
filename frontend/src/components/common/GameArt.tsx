import { Gamepad2, Shield, Zap, Sparkles, Plus, Star } from 'lucide-react'
export function GameArt({ small = false }: { small?: boolean }) {
  return <div className={`game-art ${small ? 'small' : ''}`} aria-hidden="true">
    <div className="art-orbit orbit-one"/><div className="art-orbit orbit-two"/><div className="art-shadow"/>
    <div className="floating-piece piece-blue"><Shield size={35} fill="#6299f4" stroke="#fff"/></div>
    <div className="floating-piece piece-green"><Zap size={34} fill="#fff" stroke="#fff"/></div>
    <div className="floating-piece piece-coral"><Gamepad2 size={35}/></div>
    <div className="controller"><div className="controller-top"/><div className="controller-line"/><div className="dpad"><span/><span/></div><div className="controller-center"><span/><span/></div><div className="controller-buttons"><i/><i/><i/><i/></div><div className="joystick stick-one"/><div className="joystick stick-two"/></div>
    <div className="art-spark spark-one"><Sparkles size={33}/></div><div className="art-spark spark-two"><Plus size={23}/></div><div className="art-spark spark-three"><Star size={20} fill="currentColor"/></div>
    <div className="art-pill"><span className="live-dot"/> A little competition. A lot of fun.</div>
    <span className="art-dot dot-one"/><span className="art-dot dot-two"/><span className="art-dot dot-three"/>
  </div>
}
