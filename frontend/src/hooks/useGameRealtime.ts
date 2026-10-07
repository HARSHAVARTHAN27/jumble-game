import { useGame } from '../contexts/GameContext'
export function useGameRealtime() { const { connection, refresh } = useGame(); return { connection, reconnect: refresh } }
