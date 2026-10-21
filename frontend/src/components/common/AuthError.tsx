import { CircleAlert } from 'lucide-react'

export function AuthError({ message, kind = 'error' }: { message: string; kind?: 'error' | 'success' }) {
  return <div className={`auth-feedback ${kind}`} role={kind === 'error' ? 'alert' : 'status'}><CircleAlert size={16}/><span>{message}</span></div>
}

export function friendlyAuthError(error: Error): string {
  const message = error.message.toLowerCase()
  if (message.includes('invalid login credentials')) return 'That email and password combination was not recognized.'
  if (message.includes('user already registered')) return 'An account already exists for this email. Try signing in instead.'
  if (message.includes('password should be at least')) return 'Choose a password with at least 8 characters.'
  if (message.includes('email not confirmed')) return 'Please confirm your email address before signing in.'
  if (message.includes('rate limit')) return 'Too many attempts. Please wait a little and try again.'
  if (message.includes('provider is not enabled') || message.includes('unsupported provider')) return 'This sign-in provider is not enabled in your Supabase project yet.'
  if (message.includes('supabase is not configured')) return error.message
  return 'We could not complete that request. Check your details and try again.'
}
