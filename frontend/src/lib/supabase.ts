import { createClient, type SupabaseClient } from '@supabase/supabase-js'

let client: SupabaseClient | undefined
let persistence: 'local' | 'session' | 'auto' = 'auto'
const DEMO_USERS_KEY = 'talentiq.demo.users'
const DEMO_SESSION_KEY = 'talentiq.demo.session'

function isDemoMode(): boolean {
  const url = import.meta.env.VITE_SUPABASE_URL
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY
  return !url || !key
}

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback
  try {
    const value = window.localStorage.getItem(key)
    return value ? (JSON.parse(value) as T) : fallback
  } catch {
    return fallback
  }
}

function writeJson<T>(key: string, value: T): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(key, JSON.stringify(value))
}

function makeDemoId(prefix: string): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) return `${prefix}-${crypto.randomUUID()}`
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function makeDemoUser(email: string, metadata: Record<string, unknown> = {}): Record<string, unknown> {
  const id = makeDemoId('demo-user')
  return {
    id,
    email,
    app_metadata: { provider: 'demo' },
    user_metadata: metadata,
    aud: 'authenticated',
    role: 'authenticated',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
}

function makeDemoProfile(user: Record<string, unknown>, metadata: Record<string, unknown> = {}): Record<string, unknown> {
  const accountType = typeof metadata.account_type === 'string' ? metadata.account_type : 'job_seeker'
  const profile = {
    id: user.id,
    full_name: typeof metadata.full_name === 'string' ? metadata.full_name : 'Demo user',
    email: user.email,
    account_type: accountType,
    company_name: typeof metadata.company_name === 'string' ? metadata.company_name : null,
    company_size: typeof metadata.company_size === 'string' ? metadata.company_size : null,
    avatar_url: null,
    phone: null,
    location: null,
    bio: null,
    terms_accepted: Boolean(metadata.terms_accepted),
    gdpr_consent: Boolean(metadata.gdpr_consent),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
  return profile
}

function makeDemoSession(user: Record<string, unknown>): Record<string, unknown> {
  return {
    access_token: makeDemoId('demo-token'),
    refresh_token: makeDemoId('demo-refresh'),
    expires_in: 3600,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    token_type: 'bearer',
    user,
  }
}

function readDemoUsers(): Record<string, unknown>[] {
  return readJson<Record<string, unknown>[]>(DEMO_USERS_KEY, [])
}

function writeDemoUsers(users: Record<string, unknown>[]): void {
  writeJson(DEMO_USERS_KEY, users)
}

function readDemoSession(): Record<string, unknown> | null {
  return readJson<Record<string, unknown> | null>(DEMO_SESSION_KEY, null)
}

function writeDemoSession(session: Record<string, unknown> | null): void {
  if (!session) {
    window.localStorage.removeItem(DEMO_SESSION_KEY)
    return
  }
  writeJson(DEMO_SESSION_KEY, session)
}

function demoQuery(table: string) {
  const key = `talentiq.demo.${table}`
  const rows = () => readJson<Record<string, unknown>[]>(key, [])
  const writeRows = (nextRows: Record<string, unknown>[]) => writeJson(key, nextRows)

  const state: {
    filters: Array<[string, unknown]>;
    orderBy?: [string, boolean];
    updates?: Record<string, unknown>;
    rowLimit?: number;
  } = { filters: [] }

  const applyFilters = (items: Record<string, unknown>[]) => {
    let result = [...items]
    for (const [field, expectedValue] of state.filters) {
      result = result.filter((item) => item[field] === expectedValue)
    }
    if (state.orderBy) {
      const [field, ascending] = state.orderBy
      result = [...result].sort((left, right) => {
        const leftValue = left[field] ?? ''
        const rightValue = right[field] ?? ''
        if (leftValue < rightValue) return ascending ? -1 : 1
        if (leftValue > rightValue) return ascending ? 1 : -1
        return 0
      })
    }
    if (state.rowLimit) result = result.slice(0, state.rowLimit)
    if (state.updates) {
      result = result.map((row) => ({ ...row, ...state.updates }))
      const nextRows = rows().map((row) => {
        const filtered = state.filters.some(([field, expectedValue]) => row[field] === expectedValue)
        if (filtered) return { ...row, ...state.updates }
        return row
      })
      writeRows(nextRows)
    }
    return result
  }

  const query: any = {
    select(): any { return query },
    eq(field: string, value: unknown): any {
      state.filters.push([field, value])
      return query
    },
    order(field: string, opts: { ascending?: boolean } = {}): any {
      state.orderBy = [field, opts.ascending ?? true]
      return query
    },
    limit(size: number): any {
      state.rowLimit = size
      return query
    },
    maybeSingle: async () => {
      const result = applyFilters(rows())[0] ?? null
      return { data: result, error: null }
    },
    single: async () => {
      const result = applyFilters(rows())[0] ?? null
      return { data: result, error: null }
    },
    update(changes: Record<string, unknown>): any {
      state.updates = changes
      return query
    },
    insert(record: Record<string, unknown> | Record<string, unknown>[]): any {
      const list = Array.isArray(record) ? record : [record]
      const nextRows = [...rows(), ...list]
      writeRows(nextRows)
      return query
    },
    delete(): any {
      const nextRows = rows().filter((row) => !state.filters.some(([field, expectedValue]) => row[field] === expectedValue))
      writeRows(nextRows)
      return query
    },
    then: undefined,
  }

  return { ...query, __proto__: null }
}

function createDemoClient(): SupabaseClient {
  const auth = {
    async getSession() {
      const session = readDemoSession()
      return { data: { session: session ?? null }, error: null }
    },
    onAuthStateChange(callback: (event: string, session: Record<string, unknown> | null) => void) {
      const session = readDemoSession()
      callback('INITIAL_SESSION', session ?? null)
      return { data: { subscription: { unsubscribe: () => undefined } } }
    },
    async getUser() {
      const session = readDemoSession()
      return { data: { user: session?.user ?? null }, error: null }
    },
    async signInWithPassword({ email, password }: { email: string; password: string }) {
      const users = readDemoUsers()
      const user = users.find((entry) => entry.email === email && entry.password === password)
      if (!user) {
        return { data: { session: null, user: null }, error: { message: 'Invalid login credentials' } }
      }
      const session = makeDemoSession(user)
      writeDemoSession(session)
      return { data: { session, user }, error: null }
    },
    async signUp({ email, password, options }: { email: string; password: string; options?: { data?: Record<string, unknown> } }) {
      const users = readDemoUsers()
      if (users.some((entry) => entry.email === email)) {
        return { data: { session: null, user: null }, error: { message: 'User already registered' } }
      }
      const metadata = options?.data ?? {}
      const user = makeDemoUser(email, metadata) as Record<string, unknown>
      user.password = password
      users.push(user)
      writeDemoUsers(users)
      const profile = makeDemoProfile(user, metadata)
      const tableRows = readJson<Record<string, unknown>[]>(`talentiq.demo.profiles`, [])
      const nextProfiles = [...tableRows.filter((entry) => entry.id !== profile.id), profile]
      writeJson(`talentiq.demo.profiles`, nextProfiles)
      const session = makeDemoSession(user)
      writeDemoSession(session)
      return { data: { session, user }, error: null }
    },
    async signOut() {
      writeDemoSession(null)
      return { error: null }
    },
    async resetPasswordForEmail(email: string) {
      const users = readDemoUsers()
      const matched = users.some((entry) => entry.email === email)
      return { data: { }, error: matched ? null : { message: 'No account found for that email.' } }
    },
    async updateUser({ password }: { password?: string }) {
      const session = readDemoSession()
      if (!session || !password) return { data: { user: null }, error: { message: 'No active user session.' } }
      const users = readDemoUsers()
      const sessionUser = session.user as Record<string, unknown> | null
      const index = users.findIndex((entry) => entry.id === sessionUser?.id)
      if (index === -1) return { data: { user: null }, error: { message: 'No active user session.' } }
      users[index].password = password
      writeDemoUsers(users)
      return { data: { user: users[index] }, error: null }
    },
    async signInWithOAuth({ provider }: { provider: string; options?: { redirectTo?: string; scopes?: string } }) {
      const pending = JSON.parse(window.sessionStorage.getItem('talentiq.pending-signup-metadata') ?? '{}')
      const metadata = typeof pending === 'object' && pending ? pending : {}
      const email = metadata.email ?? `${provider}.demo@example.com`
      const existingUsers = readDemoUsers()
      let user = existingUsers.find((entry) => entry.email === email)
      if (!user) {
        user = makeDemoUser(email, metadata) as Record<string, unknown>
        user.password = 'demo-password'
        existingUsers.push(user)
        writeDemoUsers(existingUsers)
        const profile = makeDemoProfile(user, metadata)
        const profiles = readJson<Record<string, unknown>[]>(`talentiq.demo.profiles`, [])
        writeJson(`talentiq.demo.profiles`, [...profiles.filter((entry) => entry.id !== profile.id), profile])
      }
      const session = makeDemoSession(user)
      writeDemoSession(session)
      return { data: { session, user }, error: null }
    },
  }

  return {
    auth,
    from(table: string) {
      const query = demoQuery(table)
      return {
        select: () => query,
        eq: (field: string, value: unknown) => query.eq(field, value),
        order: (field: string, opts: { ascending?: boolean } = {}) => query.order(field, opts),
        limit: (size: number) => query.limit(size),
        maybeSingle: async () => query.maybeSingle(),
        single: async () => query.single(),
        update: (changes: Record<string, unknown>) => query.update(changes),
        insert: (record: Record<string, unknown> | Record<string, unknown>[]) => query.insert(record),
      }
    },
  } as unknown as SupabaseClient
}

/** Supabase owns the auth-token format; this adapter only selects browser storage. */
const authStorage = {
  getItem(key: string): string | null {
    if (typeof window === 'undefined') return null
    const sessionValue = window.sessionStorage.getItem(key)
    if (sessionValue !== null) {
      persistence = 'session'
      return sessionValue
    }
    return window.localStorage.getItem(key)
  },
  setItem(key: string, value: string): void {
    if (typeof window === 'undefined') return
    if (persistence === 'session') {
      window.sessionStorage.setItem(key, value)
      window.localStorage.removeItem(key)
    } else {
      persistence = 'local'
      window.localStorage.setItem(key, value)
      window.sessionStorage.removeItem(key)
    }
  },
  removeItem(key: string): void {
    if (typeof window === 'undefined') return
    window.localStorage.removeItem(key)
    window.sessionStorage.removeItem(key)
  },
}

export function setRememberMe(remember: boolean): void {
  persistence = remember ? 'local' : 'session'
}

/** Lazily create the client so the app can run before local Supabase credentials exist. */
export function getSupabaseClient(): SupabaseClient {
  if (isDemoMode()) {
    client ??= createDemoClient()
    return client
  }

  const url = import.meta.env.VITE_SUPABASE_URL ?? 'https://example.supabase.co'
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ?? 'demo-key'
  client ??= createClient(url, key, {
    auth: { storage: authStorage, persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  })
  return client
}
