import { useGame } from '../contexts/GameContext'
export function usePlayerSession() { const { state, loading, join, submit } = useGame(); return { player: state.player, loading, join, submit } }
