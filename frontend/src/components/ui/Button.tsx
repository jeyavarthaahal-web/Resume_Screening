import type { ButtonHTMLAttributes } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'dark' | 'light' }
export function Button({ className = '', variant = 'dark', ...props }: ButtonProps) {
  return <button className={`button button-${variant} ${className}`} {...props} />
}
