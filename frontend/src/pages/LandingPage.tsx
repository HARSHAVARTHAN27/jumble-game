import { Link } from 'react-router-dom'
import { ArrowRight, Brain, Code2, Link2, Pencil, Target, Users } from 'lucide-react'
import { Brand, Page } from '../components/common/UI'
import '../home.css'

const rounds = [
  { id: 'memory', title: ['Memory', 'Grid'], description: ['Look closely.', 'Remember every detail.'], skill: 'Memory', Icon: Brain },
  { id: 'emoji', title: ['Emoji', 'Decode'], description: ['Decode the clues.', 'Find the meaning.'], skill: 'Logic', Icon: Brain },
  { id: 'connection', title: ['Connection', 'Hunt'], description: ['Find the links.', 'Spot the pattern.'], skill: 'Pattern', Icon: Link2 },
  { id: 'target', title: ['Target', 'Drop'], description: ['Make the number.', 'Hit the target.'], skill: 'Numbers', Icon: Target },
  { id: 'drawing', title: ['Draw &', 'Guess'], description: ['One secret card.', 'Draw it. Guess it.'], skill: 'Creative', Icon: Pencil },
  { id: 'technical', title: ['Technical', 'Showdown'], description: ['Think. Solve.', 'Win together.'], skill: 'Technical', Icon: Code2 },
]

export default function LandingPage() {
  return <Page className="showcase-home">
    <div className="home-platforms" aria-hidden="true"><span/><span/><span/></div>
    <section className="home-intro" aria-labelledby="home-headline">
      <Brand/>
      <div className="home-pitch">
        <p className="home-eyebrow">3 TEAMS. 6 GAMES. 1 WINNER.</p>
        <h1 id="home-headline" className="home-headline">3 teams.<br/>6 games.<br/><span>1 winner.</span></h1>
        <p className="home-description">Join your team and battle through six live challenges. One showdown.<br/>One champion.</p>
        <Link className="home-join" to="/play">Join Game<ArrowRight size={25} aria-hidden="true"/></Link>
      </div>
      <img className="home-mascot" src="/images/home/mascot.png" alt="" width="1280" height="1280" draggable={false}/>
    </section>
    <section className="home-rounds" aria-label="Six game rounds">
      <div className="home-showdown"><Users size={35} aria-hidden="true"/><p>3 Teams.<br/>One epic showdown.</p><span aria-hidden="true"/></div>
      <ol className="home-round-grid">{rounds.map(({ id, title, description, skill, Icon }, index) => <li key={id} className={'home-round home-round-' + id}>
        <div className="home-round-art"><img src={'/images/home/' + id + '.png'} alt="" width="1280" height="1280" draggable={false}/></div>
        <div className="home-round-content">
          <span className="home-round-number" aria-label={'Round ' + (index + 1)}>{String(index + 1).padStart(2, '0')}</span>
          <h2>{title.map((line, part) => <span key={line}>{part > 0 && ' '}{line}</span>)}</h2>
          <p>{description.map((line, part) => <span key={line}>{part > 0 && ' '}{line}</span>)}</p>
          <span className="home-round-skill"><Icon size={18} aria-hidden="true"/>{skill}</span>
        </div>
      </li>)}</ol>
    </section>
  </Page>
}
