import { useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import type { DrawingStroke } from '../../types/game'
interface Props { strokes: DrawingStroke[]; canDraw?: boolean; onStroke?: (stroke: DrawingStroke) => Promise<void> }
export function DrawingCanvas({ strokes, canDraw = false, onStroke }: Props) {
  const [color, setColor] = useState('#30213e'), [width, setWidth] = useState(4), [draft, setDraft] = useState<DrawingStroke | null>(null)
  const [pending, setPending] = useState<DrawingStroke[]>([]), [error, setError] = useState('')
  const active = useRef<DrawingStroke | null>(null)
  const point = (event: PointerEvent<SVGSVGElement>): [number, number] => { const rect = event.currentTarget.getBoundingClientRect(); return [Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)), Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height))] }
  const down = (event: PointerEvent<SVGSVGElement>) => {
    if (!canDraw || active.current || event.button !== 0) return
    event.currentTarget.setPointerCapture(event.pointerId)
    const stroke: DrawingStroke = { id: crypto.randomUUID(), color, width, points: [point(event)] }
    active.current = stroke; setDraft(stroke)
  }
  const move = (event: PointerEvent<SVGSVGElement>) => { if (!active.current || !canDraw) return; if (active.current.points.length < 500) active.current = { ...active.current, points: [...active.current.points, point(event)] }; setDraft(active.current) }
  const up = async () => {
    const stroke = active.current; active.current = null; setDraft(null)
    if (!stroke || !canDraw || !onStroke) return
    setPending(old => [...old, stroke]); setError('')
    try { await onStroke(stroke) }
    catch (e) { setPending(old => old.filter(s => s.id !== stroke.id)); setError(e instanceof Error ? e.message : 'Unable to save the stroke.') }
  }
  const visible = [...strokes, ...pending.filter(s => !strokes.some(v => v.id === s.id)), ...(draft ? [draft] : [])]
  return <div className="drawing-area">{canDraw && <div className="drawing-tools"><span>Pen</span>{['#30213e', '#8860ba', '#c83f50', '#2e856d', '#ffffff'].map(c => <button type="button" key={c} aria-label={c === '#ffffff' ? 'Eraser' : `Pen color ${c}`} aria-pressed={color === c} style={{ background: c }} onClick={() => setColor(c)}/>)}<label>Width <select value={width} onChange={e => setWidth(Number(e.target.value))}><option value={4}>Thin</option><option value={8}>Medium</option><option value={16}>Thick</option></select></label></div>}
    <svg className={`drawing-canvas ${canDraw ? 'drawing-enabled' : ''}`} viewBox="0 0 800 500" role="img" aria-label={canDraw ? 'Drawing canvas. Use your pointer or touch to draw.' : 'Your team’s live drawing'} onPointerDown={down} onPointerMove={move} onPointerUp={() => void up()} onPointerCancel={() => void up()}>
      <rect width="800" height="500" fill="#ffffff"/>{visible.map(s => s.points.length === 1 ? <circle key={s.id} cx={s.points[0][0] * 800} cy={s.points[0][1] * 500} r={s.width / 2} fill={s.color}/> : <polyline key={s.id} points={s.points.map(p => `${p[0] * 800},${p[1] * 500}`).join(' ')} fill="none" stroke={s.color} strokeWidth={s.width} strokeLinecap="round" strokeLinejoin="round"/>)}
    </svg>{error && <p role="alert" className="field-error">{error}</p>}
  </div>
}
