import type { InputHTMLAttributes, ReactNode } from 'react'

type InputProps = InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; trailing?: ReactNode }
export function Input({ id, label, hint, trailing, className = '', ...props }: InputProps) {
  const inputId = id ?? props.name
  return <div className="field"><label htmlFor={inputId}>{label}</label><div className="field-control"><input id={inputId} className={className} aria-describedby={hint ? `${inputId}-hint` : undefined} {...props}/>{trailing}</div>{hint && <small id={`${inputId}-hint`} className="field-hint">{hint}</small>}</div>
}
