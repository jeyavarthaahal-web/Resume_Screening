import { ArrowLeft, Home } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return <main className="auth-page"><section className="auth-card auth-card-expanded"><div className="eyebrow">404</div><h1>Page not found.</h1><p>The page you requested does not exist or may have moved.</p><div className="auth-foot" style={{ justifyContent: 'space-between' }}>
    <Link to="/" className="button button-dark form-submit"><Home size={16}/> Home</Link>
    <Link to="/login" className="button button-light form-submit"><ArrowLeft size={16}/> Sign in</Link>
  </div></section></main>
}
