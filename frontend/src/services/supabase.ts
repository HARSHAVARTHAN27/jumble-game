import { createClient } from '@supabase/supabase-js'

// This is the browser's single public client. Privileged keys belong only in FastAPI.
const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY
export const supabase = url && key ? createClient(url, key) : null
