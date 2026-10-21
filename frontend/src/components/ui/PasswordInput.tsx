import { Eye, EyeOff } from 'lucide-react'
import { useState, type InputHTMLAttributes } from 'react'

type PasswordInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { label: string; id: string }
export function PasswordInput({ label, id, ...props }: PasswordInputProps) {
  const [visible, setVisible] = useState(false)
  return <div className="field"><label htmlFor={id}>{label}</label><div className="field-control"><input id={id} type={visible ? 'text' : 'password'} autoComplete="new-password" {...props}/><button type="button" className="password-toggle" aria-label={visible ? 'Hide password' : 'Show password'} aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div></div>
}
