import { supabase } from './supabase'
const messages: Record<string, string> = {
  NO_ACTIVE_GAME: 'The host hasn’t opened a game yet. Check back in a moment.',
  EMPLOYEE_NOT_FOUND: 'We couldn’t find that name or employee ID. Enter your full name or ID from the employee list.',
  DUPLICATE_EMPLOYEE_NAME: 'We found more than one person with that name. Enter your employee code.',
  EMPLOYEE_INACTIVE: 'Your player profile is inactive. Please check with the host.',
  GAME_ALREADY_STARTED: 'A game is already underway. Ask the host about joining.',
  ANSWER_ALREADY_SUBMITTED: 'Your answer is already locked. You’re all set!',
  QUESTION_NOT_ACTIVE: 'This question has closed. Waiting for the host’s next move.',
  UNAUTHORIZED_HOST: 'This account does not have permission to access the control area.',
  UNAUTHORIZED: 'Your session has expired. Enter your name again to rejoin.',
  ROUND_CONTENT_REQUIRED: 'Round content is not configured yet. The lobby remains open.',
  NETWORK_ERROR: 'We couldn’t reach the game server. Check your connection and try again.',
  SERVER_ERROR: 'The game server hit a snag. Please try again.',
  ENDPOINT_UNAVAILABLE: 'This action isn’t available on the connected backend yet.',
  DATABASE_NOT_INITIALIZED: 'The host needs to finish setting up the game database. Please check back soon.',
}
export class ApiError extends Error {
  constructor(public code: string, detail?: string) { super(detail ?? messages[code] ?? messages.SERVER_ERROR) }
}
export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
export const DEMO = import.meta.env.VITE_DEMO === 'true'
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 12000)
  try {
    const token = path.startsWith('/api/host/') ? (await supabase?.auth.getSession())?.data.session?.access_token : undefined
    const response = await fetch(`${API_URL}${path}`, { ...options, credentials: 'include', signal: controller.signal, headers: { ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers } })
    const body = await response.json().catch(() => null)
    if (!response.ok || body?.success === false) {
      throw new ApiError(body?.error?.code || body?.detail?.code || (response.status === 404 ? 'ENDPOINT_UNAVAILABLE' : 'SERVER_ERROR'), body?.error?.message || (response.status === 422 ? 'Some fields are invalid. Check the question content and try again.' : undefined))
    }
    return (body?.data ?? body) as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError('NETWORK_ERROR')
  } finally { window.clearTimeout(timeout) }
}
export const post = <T>(path: string, body: unknown = {}) => request<T>(path, { method: 'POST', body: JSON.stringify(body) })
export function query(params: Record<string, string | undefined>) {
  return '?' + new URLSearchParams(Object.entries(params).filter((entry): entry is [string, string] => entry[1] !== undefined)).toString()
}
