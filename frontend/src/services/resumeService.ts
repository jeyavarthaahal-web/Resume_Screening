import { getSupabaseClient } from '../lib/supabase'
import type { ResumeUploadResponse } from '../types/resume'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export async function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const { data, error } = await getSupabaseClient().auth.getSession()
  if (error) throw new Error('We could not verify your sign-in. Please sign in again.')
  const accessToken = data.session?.access_token
  if (!accessToken) throw new Error('Your session has expired. Sign in again to upload a resume.')

  const form = new FormData()
  form.append('file', file, file.name)
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}/api/resumes/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}`, Accept: 'application/json' },
      body: form,
    })
  } catch {
    throw new Error('We could not reach TalentIQ. Check that the backend is running and try again.')
  }

  const payload = await response.json().catch(() => null) as { detail?: unknown } | null
  if (!response.ok) {
    if (response.status === 401) throw new Error('Your session has expired. Sign in again to upload a resume.')
    if (response.status === 413) throw new Error('This file is too large. The maximum size is 10 MB.')
    const detail = typeof payload?.detail === 'string' ? payload.detail : null
    throw new Error(detail ?? 'We could not process this resume. Please try again.')
  }
  return payload as ResumeUploadResponse
}
