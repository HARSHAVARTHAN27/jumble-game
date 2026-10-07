import { useGame } from '../contexts/GameContext'
export function useActiveGame() { const { state, loading, refresh, error } = useGame(); return { game: state, loading, refresh, error } }
