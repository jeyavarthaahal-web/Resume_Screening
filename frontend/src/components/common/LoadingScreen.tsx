export function LoadingScreen({ label = 'Checking your session…' }: { label?: string }) {
  return <main className="auth-page loading-page"><div className="loading-card" role="status" aria-live="polite"><span className="loading-spinner" aria-hidden="true"/><strong>{label}</strong></div></main>
}
