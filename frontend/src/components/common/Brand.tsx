import { Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

export function Brand() {
  return <Link to="/" className="brand" aria-label="TalentIQ home"><span className="brand-mark"><Sparkles size={17} /></span><span>talent<span className="brand-iq">iq</span></span></Link>
}
